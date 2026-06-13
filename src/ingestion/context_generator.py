import anthropic
from src.core.config import settings
from src.ingestion.parser import ParsedStep, ParsedSection, ParsedDocument

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_step_context(step: ParsedStep, section: ParsedSection, doc: ParsedDocument) -> str:
    prompt = (
        f"Document: {doc.title} (domain: {doc.domain})\n"
        f"Section: {section.heading}\n"
        f"Step content: {step.clean_content()}\n\n"
        "Write 2-3 sentences explaining what this step does, which machine or process it applies to, "
        "and what hazard or quality outcome it addresses. Be specific and dense."
    )
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text  # type: ignore[index]


def generate_section_summary(section: ParsedSection, step_contexts: list[str]) -> str:
    combined = "\n".join(f"- {ctx}" for ctx in step_contexts)
    prompt = f"Section '{section.heading}' contains these steps:\n{combined}\n\nSummarize this section in 2-3 sentences."
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text  # type: ignore[index]


def generate_document_summary(doc: ParsedDocument, section_summaries: list[str]) -> str:
    combined = "\n".join(f"- {s}" for s in section_summaries)
    prompt = (
        f"Document: {doc.title}\nSection summaries:\n{combined}\n\n"
        "Summarize this document in 3-4 sentences for a manufacturing floor supervisor."
    )
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text  # type: ignore[index]


def generate_term_definitions(name: str) -> tuple[str, str]:
    prompt = (
        f"Define the manufacturing/safety term '{name}'.\n"
        "Return two definitions separated by '|||':\n"
        "1. Plain definition (operator-friendly, simple language)\n"
        "2. Precise definition (standards-compliant, technical language)\n"
        "Format: plain definition ||| precise definition"
    )
    response = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text  # type: ignore[index]
    parts = text.split("|||", 1)
    plain = parts[0].strip() if parts else text
    precise = parts[1].strip() if len(parts) > 1 else text
    return plain, precise
