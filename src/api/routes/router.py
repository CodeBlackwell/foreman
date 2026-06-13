import sys
import anthropic
from fastapi import APIRouter, Depends
from src.models.api import QueryRequest
from src.models.nodes import DomainName
from src.taxonomy.domains import classify_by_keyword
from src.core.neo4j_client import Neo4jClient
from src.api.dependencies import get_db
from src.core.config import settings

router = APIRouter()

_DOMAIN_DESCRIPTIONS = {
    "Safety": "lockout/tagout, hazard control, PPE, de-energization, LOTO",
    "Maintenance": "bearing replacement, lubrication, torque, repair, press service",
    "QualityControl": "dimensional tolerance, inspection, measurement, pass/fail criteria",
}


def route_question(question: str, db: Neo4jClient) -> tuple[DomainName, str]:
    domain = classify_by_keyword(question)
    if domain is not None:
        return domain, "keyword"

    desc = "\n".join(f"- {d}: {v}" for d, v in _DOMAIN_DESCRIPTIONS.items())
    prompt = (
        f"Classify this question into exactly one domain.\n\nDomains:\n{desc}\n\n"
        f"Question: {question}\n\nRespond with only the domain name."
    )
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()  # type: ignore[index]
        for d in ("Safety", "Maintenance", "QualityControl"):
            if d.lower() in text.lower():
                return d, "llm"  # type: ignore[return-value]
    except Exception as exc:
        print(f"Router LLM fallback failed: {exc}", file=sys.stderr)

    return "Maintenance", "llm"


@router.post("/route")
def route(body: QueryRequest, db: Neo4jClient = Depends(get_db)) -> dict:
    domain, method = route_question(body.question, db)
    return {"entry_domain": domain, "method": method}
