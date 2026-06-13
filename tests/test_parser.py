from pathlib import Path
from src.ingestion.parser import parse_document, CrossRef, EntityMention


SAFETY_DOC = Path("data/raw/safety_loto.md")
MAINTENANCE_DOC = Path("data/raw/maintenance_press.md")
QC_DOC = Path("data/raw/quality_inspection.md")


def test_frontmatter_parse():
    doc = parse_document(SAFETY_DOC)
    assert doc.doc_id == "DOC-001"
    assert doc.domain == "Safety"
    assert doc.origin == "official"
    assert doc.title == "Lockout/Tagout Safety Procedure"


def test_cross_ref_extraction():
    doc = parse_document(MAINTENANCE_DOC)
    all_steps = [step for section in doc.sections for step in section.steps]
    all_refs = [ref for step in all_steps for ref in step.cross_refs]
    ref_types = {r.type for r in all_refs}
    assert "REQUIRES_SAFETY" in ref_types
    assert "VALIDATES_WITH" in ref_types
    loto_ref = next((r for r in all_refs if r.type == "REQUIRES_SAFETY"), None)
    assert loto_ref is not None
    assert loto_ref.target_doc_id == "DOC-001"
    assert loto_ref.target_section == "Lockout Procedure"


def test_entity_extraction():
    doc = parse_document(SAFETY_DOC)
    all_steps = [step for section in doc.sections for step in section.steps]
    all_entities = [e for step in all_steps for e in step.entity_mentions]
    names = {e.name for e in all_entities}
    assert "X200 Press" in names
    assert "Stored Energy" in names
    assert "LOTO" in names


def test_content_hash_deterministic():
    doc = parse_document(MAINTENANCE_DOC)
    all_steps = [step for section in doc.sections for step in section.steps]
    hashes = [step.content_hash for step in all_steps]
    assert len(hashes) == len(set(hashes)), "Duplicate content hashes found"


def test_qc_back_reference():
    doc = parse_document(QC_DOC)
    all_steps = [step for section in doc.sections for step in section.steps for child in section.children for step in child.steps] + \
                [step for section in doc.sections for step in section.steps]
    all_refs = [ref for step in all_steps for ref in step.cross_refs]
    ref_to_maintenance = [r for r in all_refs if r.target_doc_id == "DOC-002"]
    assert len(ref_to_maintenance) >= 1
