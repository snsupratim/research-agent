

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class ReportStatus(str,Enum):
    PENDING="pending"
    RESEARCHING="researching"
    CRITIQUING="critiquing"
    WRITING="writing"
    DONE="done"
    FAILED="failed"

class SourceType(str,Enum):
    WEB="web"
    PDF="pdf"
    ARXIV="arxiv"

class SourceDoc(BaseModel):
    url:str
    title:str
    source_type:SourceType
    snippet:str
    confidence_score:float=Field(ge=0.0,le=1.0)
    fetched_at:datetime=Field(default_factory=datetime.utcnow)
    metadata:dict[str,Any]=Field(default_factory=dict)


class ConflictFlag(BaseModel):
    claim:str
    source_a:str
    source_b:str
    description:str
    

class ReportSection(BaseModel):
    heading:str
    content:str
    citations:list[str]=Field(default_factory=list)


class ResearchRequest(BaseModel):
    query:str=Field(min_length=10, max_length=500)
    max_sources:int=Field(default=5,ge=1,le=15)

class ResearchResponse(BaseModel):
    report_id:str
    status:ReportStatus
    message:str
