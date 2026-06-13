from typing import Literal
from pydantic import BaseModel, ConfigDict

DomainName = Literal["Safety", "Maintenance", "QualityControl"]
OriginKind = Literal["official", "ai_paraphrase", "user_edit"]
EntityKind = Literal["Machine", "Part", "Hazard", "Term"]


class DocumentNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    doc_id: str
    title: str
    domain: DomainName
    revision: str
    origin: OriginKind
    summary: str = ""
    embedding: list[float] = []


class SectionNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    heading: str
    level: int
    doc_id: str
    summary: str = ""
    embedding: list[float] = []


class StepNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    content: str
    content_hash: str
    context: str = ""
    origin: OriginKind
    domain: DomainName
    embedding: list[float] = []


class EntityNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    canonical_id: str
    kind: EntityKind
    name: str


class TermNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    canonical_id: str
    name: str
    definition_plain: str = ""
    definition_precise: str = ""
