from src.models.retrieval import RetrievalResult, DomainSection, EvidenceItem

ABSTAIN_THRESHOLD = 0.70


def curate_evidence(result: RetrievalResult, max_per_domain: int = 3) -> RetrievalResult:
    curated: list[DomainSection] = []
    for section in result.sections:
        above = [item for item in section.items if item.similarity_score >= ABSTAIN_THRESHOLD and item.content.strip()]
        if not above:
            continue
        ranked = sorted(above, key=lambda e: e.similarity_score, reverse=True)
        kept = ranked[:max_per_domain]
        curated.append(DomainSection(domain=section.domain, items=kept))
    return RetrievalResult(
        entry_domain=result.entry_domain,
        sections=curated,
        below_threshold=len(curated) == 0,
    )
