from src.models.nodes import DomainName

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "Safety": [
        "lockout", "tagout", "loto", "hazard", "ppe", "isolate", "de-energize",
        "stored energy", "safety", "protect", "warn", "guard", "emergency",
        "authorized", "affected", "energy control",
    ],
    "Maintenance": [
        "replace", "bearing", "lubricate", "torque", "press", "calibrate",
        "repair", "install", "remove", "bolt", "shaft", "housing", "grease",
        "service", "maintenance", "overhaul", "assembly", "disassembly",
    ],
    "QualityControl": [
        "tolerance", "inspection", "measurement", "spec", "reject", "pass",
        "fail", "runout", "bore", "diameter", "gauge", "verify", "check",
        "quality", "standard", "deviation", "acceptable", "out of spec",
    ],
}


def classify_by_keyword(text: str) -> DomainName | None:
    lower = text.lower()
    scores: dict[str, int] = {domain: 0 for domain in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                scores[domain] += 1
    top = max(scores, key=lambda d: scores[d])
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] == 0 or (len(ranked) > 1 and ranked[0] == ranked[1]):
        return None
    return top  # type: ignore[return-value]
