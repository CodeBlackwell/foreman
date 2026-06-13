from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.core.neo4j_client import Neo4jClient
from src.api.dependencies import get_db
from src.ingestion.embedder import embed_text
from src.models.nodes import DomainName
from src.models.retrieval import RetrievalResult, DomainSection, EvidenceItem

router = APIRouter()
ABSTAIN_THRESHOLD = 0.70


class RetrieveRequest(BaseModel):
    question: str
    entry_domain: str
    top_k: int = 3


def retrieve_evidence(
    question: str, entry_domain: str, top_k: int, db: Neo4jClient
) -> RetrievalResult:
    embedding = embed_text(question)
    raw = db.vector_search("step_embedding", embedding, top_k=top_k, domain_filter=entry_domain)

    seen: set[str] = set()
    evidence: list[EvidenceItem] = []

    for row in raw:
        node = dict(row["node"])
        score: float = float(row["score"])
        content_hash = node.get("content_hash", "")
        if content_hash in seen:
            continue
        seen.add(content_hash)
        item = _node_to_evidence(node, score, db)
        if item:
            evidence.append(item)

    # graph traversal: follow cross-domain edges from entry steps
    for row in raw:
        node = dict(row["node"])
        parent_score: float = float(row["score"])
        content_hash = node.get("content_hash", "")
        traversal = _traverse(content_hash, parent_score, db)
        for t_node, t_score in traversal:
            h = t_node.get("content_hash", "")
            if h in seen:
                continue
            seen.add(h)
            item = _node_to_evidence(t_node, t_score, db)
            if item:
                evidence.append(item)

    all_above = [e for e in evidence if e.similarity_score >= ABSTAIN_THRESHOLD]
    if not all_above:
        return RetrievalResult(
            entry_domain=entry_domain,  # type: ignore[arg-type]
            sections=[],
            below_threshold=True,
        )

    by_domain: dict[str, list[EvidenceItem]] = {}
    for item in all_above:
        by_domain.setdefault(item.domain, []).append(item)

    sections = [DomainSection(domain=d, items=items) for d, items in by_domain.items()]  # type: ignore[arg-type]
    return RetrievalResult(entry_domain=entry_domain, sections=sections, below_threshold=False)  # type: ignore[arg-type]


def _node_to_evidence(node: dict, score: float, db: Neo4jClient) -> EvidenceItem | None:
    content_hash = node.get("content_hash", "")
    if not content_hash:
        return None
    ctx = db.run(
        """
        MATCH (sec:Section)-[:CONTAINS]->(s:Step {content_hash: $hash})
        MATCH (doc:Document)-[:CONTAINS]->(sec)
        RETURN doc.title AS doc_title, sec.heading AS section_heading, doc.doc_id AS doc_id
        LIMIT 1
        """,
        {"hash": content_hash},
    )
    if not ctx:
        return None
    row = ctx[0]
    return EvidenceItem(
        domain=node.get("domain", "Maintenance"),  # type: ignore[arg-type]
        doc_id=row.get("doc_id", ""),
        doc_title=row.get("doc_title", ""),
        section_heading=row.get("section_heading", ""),
        content=node.get("content", ""),
        origin=node.get("origin", "official"),  # type: ignore[arg-type]
        similarity_score=score,
    )


def _traverse(content_hash: str, parent_score: float, db: Neo4jClient) -> list[tuple[dict, float]]:
    rows = db.run(
        """
        MATCH (s:Step {content_hash: $hash})-[:REQUIRES_SAFETY|VALIDATES_WITH|REFERENCES]->(target:Section)
        MATCH (target)-[:CONTAINS]->(step2:Step)
        RETURN step2
        LIMIT 5
        """,
        {"hash": content_hash},
    )
    result: list[tuple[dict, float]] = []
    for row in rows:
        node = dict(row.get("step2", {}))
        if node and node.get("content_hash"):
            result.append((node, parent_score))
    return result


@router.post("/retrieve")
def retrieve(body: RetrieveRequest, db: Neo4jClient = Depends(get_db)) -> RetrievalResult:
    return retrieve_evidence(body.question, body.entry_domain, body.top_k, db)
