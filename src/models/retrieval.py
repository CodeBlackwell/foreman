from pydantic import BaseModel, ConfigDict
from src.models.nodes import DomainName, OriginKind


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    domain: DomainName
    doc_id: str
    doc_title: str
    section_heading: str
    content: str
    origin: OriginKind
    similarity_score: float


class DomainSection(BaseModel):
    model_config = ConfigDict(frozen=True)
    domain: DomainName
    items: list[EvidenceItem]


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    entry_domain: DomainName
    sections: list[DomainSection]
    below_threshold: bool = False
