
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from slowapi import Limiter
from slowapi.util import get_remote_address

from agents.graph import run_research_agent
from db import get_db
from models import (
    ReportDocument,
    ReportStatus,
    ResearchRequest,
    ResearchResponse,
    Citation,
    ConflictFlag,
    ReportSection,
)
from router.websocket import manager


router=APIRouter(tags=["reports"])
limiter=Limiter(key_func=get_remote_address, default_limits=["100/hour"])

# helper function to create a new report document in the database

def _oid(report_id:str)-> ObjectId:
    """Convert a normal string report id into mongodb bson suports ObjectId."""
    try:
        return ObjectId(report_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid report id: {report_id}. Error: {str(e)}")


def _serialize(doc:dict)-> dict:
    """Serialize a ObjectId into string for JSON response."""
    doc["id"]=str(doc.pop("_id",""))
    return doc


#  background task function to run the research agent and update the report document in the database

async def _run_and_save(report_id:str, query:str, max_sources:int):
    db=get_db()
    try:
        #  update the status to researching
        await db.reports.update_one(
            {"_id": _oid(report_id)},
            {"$set":{"status":ReportStatus.RESEARCHING}},
        )
        await manager.broadcast(report_id,{"statis":ReportStatus.RESEARCHING.value})

        async def on_status_update(data:dict):
            await manager.broadcast(report_id,data)

        final_state= await run_research_agent(
            query,
            max_sources,
            report_id=report_id,
            update_callback=on_status_update
        )

        all_text= final_state.get("summary","") + " ".join(
            s.content for s in final_state.get("sections",[])
        )

        word_count=len(all_text.split())
    #  Using .model_dump() to convert Pydantic models to dictionaries for MongoDB storage
        update_doc: dict[str, Any] = {
            "status": final_state["status"],
            "summary": final_state.get("summary", ""),
            "sections": [s.model_dump() for s in final_state.get("sections", [])],
            "citations": final_state.get("raw_citations", []),
            "conflict_flags": [
                f.model_dump() for f in final_state.get("conflict_flags", [])
            ],
            "sources_searched": len(final_state.get("sources", [])),
            "word_count": word_count,
            "completed_at": datetime.utcnow(),
        }

        if final_state["status"] == ReportStatus.FAILED:
            update_doc["error_message"] = final_state.get("error")

        await db.reports.update_one(
            {"_id": _oid(report_id)},
            {"$set": update_doc},
        )


    except Exception as e:
        await db.reports.update_one(
            {"_id": _oid(report_id)},
            {"$set": {"status": ReportStatus.FAILED, "error": str(e)}},
        )
        await manager.broadcast(report_id, {"status": ReportStatus.FAILED.value, "error": str(e)})


@router.post("/reports",response_model=ResearchResponse, status_code=202)
@limiter.limit("10/minute")
async def create_report(
    request:Request,
    body:ResearchRequest,
    background_tasks:BackgroundTasks
):
    """Trigger the research agent to create a new report based on the provided query and max_sources."""

    db=get_db()
    doc = {
        "query": body.query,
        "max_sources": body.max_sources,
        "status": ReportStatus.PENDING,
        "summary": "",
        "sections": [],
        "citations": [],
        "conflict_flags": [],
        "sources_searched": 0,
        "word_count": 0,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "error": None,
    }

    result = await db.reports.insert_one(doc)
    report_id=str(result.inserted_id)

    background_tasks.add_task(_run_and_save, report_id, body.query, body.max_sources)


    return ResearchResponse(report_id=report_id, status=ReportStatus.PENDING,message="Report creation initiated. You can check the status using the /api/v1/reports/{report_id}.")