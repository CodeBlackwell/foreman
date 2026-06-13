import re
import anthropic
from fastapi import APIRouter, Depends, Request
from src.core.neo4j_client import Neo4jClient
from src.core.config import settings
from src.api.dependencies import get_db
from src.api.routes.router import route_question
from src.api.routes.retrieve import retrieve_evidence
from src.api.curation import curate_evidence
from src.models.api import QueryRequest, QueryResponse, CitationRef


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


router = APIRouter()

DOMAIN_ORDER = ["Safety", "Maintenance", "QualityControl"]


def _is_out_of_domain(question: str) -> bool:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        "Does this question relate to industrial equipment maintenance, safety procedures, "
        "lockout/tagout, quality control, or manufacturing plant operations? "
        "Answer only 'yes' or 'no'.\n\nQuestion: " + question
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        messages=[{"role": "user", "content": prompt}],
    )
    return "no" in response.content[0].text.strip().lower()  # type: ignore[index]


def _synthesize(question: str, evidence_text: str) -> str:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = (
        f"You are answering a floor supervisor's question using only the provided evidence.\n\n"
        f"Question: {question}\n\n"
        f"Evidence:\n{evidence_text}\n\n"
        "Rules:\n"
        "1. Use only the evidence above. Do not fabricate steps or values.\n"
        "2. Always respond with something — never return an empty response.\n"
        "3. If the specific procedure or information asked about is absent from the evidence, "
        "begin with one line: 'Note: [exactly what is missing] is not documented in the available records.' "
        "Then describe whatever relevant context IS present.\n"
        "4. Tangentially related content (e.g. LOTO steps, torque specs) is still useful — "
        "present it as supporting context.\n"
        "5. Do not use section headers or domain labels in your response."
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text  # type: ignore[index]


@router.post("/answer")
def answer(request: Request, body: QueryRequest, db: Neo4jClient = Depends(get_db)) -> QueryResponse:
    base = str(request.base_url).rstrip("/")

    if _is_out_of_domain(body.question):
        return QueryResponse(
            response_type="out_of_domain",
            notice="This question is outside the scope of industrial maintenance, safety, and quality control documentation.",
        )

    entry_domain, _ = route_question(body.question, db)
    retrieval = retrieve_evidence(body.question, entry_domain, top_k=3, db=db)
    curated = curate_evidence(retrieval)

    if curated.below_threshold or not curated.sections:
        all_items = [item for s in retrieval.sections for item in s.items if item.content.strip()]
        if not all_items:
            return QueryResponse(
                response_type="partial",
                notice="No documentation was found for this question. Please consult your supervisor or refer to the document library directly.",
            )
        evidence_text = "\n\n".join(
            f"[{item.doc_title} / {item.section_heading}]\n{item.content}" for item in all_items
        )
        citations = [
            CitationRef(doc_title=i.doc_title, section_heading=i.section_heading, origin=i.origin, domains=[entry_domain])
            for i in all_items
        ]
        return QueryResponse(
            answer_text=_synthesize(body.question, evidence_text),
            citations=citations,
            response_type="partial",
            notice="No documentation matched above the confidence threshold. Low-confidence context is shown below.",
        )

    sections_by_domain = {s.domain: s for s in curated.sections}
    citation_keys: dict[tuple[str, str], dict] = {}
    all_usable = []

    for domain in DOMAIN_ORDER:
        section = sections_by_domain.get(domain)  # type: ignore[call-overload]
        if not section:
            continue
        usable = [item for item in section.items if item.content.strip()]
        for item in usable:
            all_usable.append(item)
            key = (item.doc_title, item.section_heading)
            if key not in citation_keys:
                url = f"{base}/docs/{item.doc_id}#{_slug(item.section_heading)}" if item.doc_id else None
                citation_keys[key] = {
                    "doc_title": item.doc_title,
                    "section_heading": item.section_heading,
                    "origin": item.origin,
                    "source_url": url,
                    "domains": [],
                }
            citation_keys[key]["domains"].append(domain)

    evidence_text = "\n\n".join(
        f"[{item.doc_title} / {item.section_heading}]\n{item.content}" for item in all_usable
    )
    answer_text = _synthesize(body.question, evidence_text)
    citations = [CitationRef(**data) for data in citation_keys.values()]
    is_partial = answer_text.strip().lower().startswith("note:")

    return QueryResponse(
        answer_text=answer_text,
        citations=citations,
        response_type="partial" if is_partial else "answered",
        notice="Some information requested is not currently documented. The relevant context found is shown below." if is_partial else None,
    )


@router.get("/answer/abstain-policy")
def abstain_policy() -> str:
    return (
        "Foreman uses three response types: (1) out_of_domain — question unrelated to industrial "
        "maintenance, safety, or quality control; (2) partial — in-domain question but the specific "
        "procedure or value is not documented, relevant context is shown with a note; "
        "(3) answered — full answer with citations from the documentation."
    )
