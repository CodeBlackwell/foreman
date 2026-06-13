from pydantic import BaseModel, ConfigDict
from src.models.nodes import OriginKind


class QueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    question: str


class CitationRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    doc_title: str
    section_heading: str
    origin: OriginKind
    source_url: str | None = None
    domains: list[str] = []


class QueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    answer_text: str = ""
    citations: list[CitationRef] = []
    # "answered" | "partial" | "out_of_domain"
    response_type: str
    notice: str | None = None
