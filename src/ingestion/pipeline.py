from pathlib import Path
from src.core.neo4j_client import Neo4jClient
from src.core.setup_indexes import setup
from src.ingestion.parser import parse_document, ParsedSection, ParsedStep
from src.ingestion.classifier import classify_step
from src.ingestion.context_generator import generate_step_context, generate_section_summary, generate_document_summary
from src.ingestion.embedder import embed_step, embed_text
from src.ingestion.graph_builder import EnrichedStep, build_graph
from src.models.nodes import DomainName


def _collect_steps(sections: list[ParsedSection]) -> list[tuple[ParsedSection, ParsedStep]]:
    pairs: list[tuple[ParsedSection, ParsedStep]] = []
    for section in sections:
        for step in section.steps:
            pairs.append((section, step))
        for child in section.children:
            for step in child.steps:
                pairs.append((child, step))
    return pairs


def run_pipeline(path: Path) -> None:
    doc = parse_document(path)
    print(f"  parsed: {len(doc.sections)} sections")

    with Neo4jClient() as client:
        setup(client)

        step_pairs = _collect_steps(doc.sections)
        enriched: list[EnrichedStep] = []

        for section, step in step_pairs:
            domain: DomainName = classify_step(step.content, doc.domain)
            context = generate_step_context(step, section, doc)
            embedding = embed_step(step.clean_content(), context)
            enriched.append(EnrichedStep(parsed=step, context=context, embedding=embedding, domain=domain))

        build_graph(doc, enriched, client)
        print(f"  written: {len(enriched)} steps to graph")
