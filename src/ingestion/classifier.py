from src.models.nodes import DomainName
from src.taxonomy.domains import classify_by_keyword


def classify_step(text: str, frontmatter_domain: DomainName) -> DomainName:
    result = classify_by_keyword(text)
    return result if result is not None else frontmatter_domain
