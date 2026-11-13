
from typing import Any, TypedDict,Any
from models import ReportSection, SourceDoc,ConflictFlag

class AgentState(TypedDict):
    query:str
    max_sources:int
    sub_quries:list[str]
    sources:list[SourceDoc]
    raw_citations:list[dict[str,Any]]
    conflicts_flag:list[ConflictFlag]
    summary:str
    sections:list[ReportSection]
    error:str | None
    report_id:str | None
    log_callback:Any
