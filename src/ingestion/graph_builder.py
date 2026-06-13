from dataclasses import dataclass, field
from src.core.neo4j_client import Neo4jClient
from src.ingestion.parser import ParsedDocument, ParsedSection, ParsedStep
from src.models.nodes import DomainName


@dataclass
class EnrichedStep:
    parsed: ParsedStep
    context: str
    embedding: list[float]
    domain: DomainName


def build_graph(doc: ParsedDocument, enriched_steps: list[EnrichedStep], client: Neo4jClient) -> None:
    _upsert_domain(doc.domain, client)
    doc_embedding = _doc_embedding(enriched_steps)
    _upsert_document(doc, doc_embedding, client)

    step_index: dict[str, tuple[ParsedSection, ParsedStep]] = {}

    for section in doc.sections:
        _upsert_section(doc, section, client)
        for step in section.steps:
            step_index[step.content_hash] = (section, step)

        for child in section.children:
            _upsert_section(doc, child, client, parent_heading=section.heading)
            for step in child.steps:
                step_index[step.content_hash] = (child, step)

    for enriched in enriched_steps:
        step = enriched.parsed
        section, _ = step_index.get(step.content_hash, (None, None))
        section_heading = section.heading if section else "Unknown"
        _upsert_step(doc, section_heading, enriched, client)
        _upsert_entities(doc, step, client)
        _upsert_cross_refs(doc, section_heading, step, client)


def _upsert_domain(domain: str, client: Neo4jClient) -> None:
    client.run("MERGE (d:Domain {name: $name})", {"name": domain})


def _upsert_document(doc: ParsedDocument, embedding: list[float], client: Neo4jClient) -> None:
    client.run(
        """
        MERGE (d:Domain {name: $domain})
        MERGE (doc:Document {doc_id: $doc_id})
        ON CREATE SET doc.title = $title, doc.revision = $revision,
                      doc.origin = $origin, doc.embedding = $embedding
        ON MATCH SET doc.title = $title, doc.revision = $revision
        MERGE (d)-[:CONTAINS]->(doc)
        """,
        {
            "domain": doc.domain,
            "doc_id": doc.doc_id,
            "title": doc.title,
            "revision": doc.revision,
            "origin": doc.origin,
            "embedding": embedding,
        },
    )


def _upsert_section(
    doc: ParsedDocument, section: ParsedSection, client: Neo4jClient, parent_heading: str | None = None
) -> None:
    client.run(
        """
        MERGE (doc:Document {doc_id: $doc_id})
        MERGE (sec:Section {doc_id: $doc_id, heading: $heading})
        ON CREATE SET sec.level = $level
        MERGE (doc)-[:CONTAINS]->(sec)
        """,
        {"doc_id": doc.doc_id, "heading": section.heading, "level": section.level},
    )
    if parent_heading:
        client.run(
            """
            MATCH (parent:Section {doc_id: $doc_id, heading: $parent})
            MATCH (child:Section {doc_id: $doc_id, heading: $child})
            MERGE (parent)-[:CONTAINS]->(child)
            """,
            {"doc_id": doc.doc_id, "parent": parent_heading, "child": section.heading},
        )


def _upsert_step(
    doc: ParsedDocument, section_heading: str, enriched: EnrichedStep, client: Neo4jClient
) -> None:
    step = enriched.parsed
    client.run(
        """
        MERGE (s:Step {content_hash: $hash})
        ON CREATE SET s.content = $content, s.context = $context,
                      s.origin = $origin, s.domain = $domain,
                      s.embedding = $embedding
        ON MATCH SET s.context = $context, s.embedding = $embedding
        WITH s
        MATCH (sec:Section {doc_id: $doc_id, heading: $heading})
        MERGE (sec)-[:CONTAINS]->(s)
        """,
        {
            "hash": step.content_hash,
            "content": step.clean_content(),
            "context": enriched.context,
            "origin": doc.origin,
            "domain": enriched.domain,
            "embedding": enriched.embedding,
            "doc_id": doc.doc_id,
            "heading": section_heading,
        },
    )


def _upsert_entities(doc: ParsedDocument, step: ParsedStep, client: Neo4jClient) -> None:
    for mention in step.entity_mentions:
        canonical_id = f"{mention.kind.lower()}:{mention.name.lower()}"
        client.run(
            """
            MERGE (e:Entity {canonical_id: $cid})
            ON CREATE SET e.kind = $kind, e.name = $name
            WITH e
            MATCH (s:Step {content_hash: $hash})
            MERGE (s)-[:MENTIONS]->(e)
            """,
            {"cid": canonical_id, "kind": mention.kind, "name": mention.name, "hash": step.content_hash},
        )


def _upsert_cross_refs(
    doc: ParsedDocument, section_heading: str, step: ParsedStep, client: Neo4jClient
) -> None:
    for ref in step.cross_refs:
        client.run(
            f"""
            MATCH (s:Step {{content_hash: $hash}})
            MERGE (target:Section {{doc_id: $target_doc, heading: $target_sec}})
            MERGE (s)-[:{ref.type}]->(target)
            """,
            {
                "hash": step.content_hash,
                "target_doc": ref.target_doc_id,
                "target_sec": ref.target_section,
            },
        )


def _doc_embedding(enriched_steps: list[EnrichedStep]) -> list[float]:
    if not enriched_steps:
        return [0.0] * 1024
    dim = len(enriched_steps[0].embedding)
    avg = [0.0] * dim
    for es in enriched_steps:
        for i, v in enumerate(es.embedding):
            avg[i] += v
    n = len(enriched_steps)
    return [v / n for v in avg]
