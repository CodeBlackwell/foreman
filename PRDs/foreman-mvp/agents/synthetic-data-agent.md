# Synthetic Data Agent Specification

## Identity

- **Name**: synthetic-data-agent
- **Wave**: 1
- **Stories**: US-010 to US-013
- **Context Budget**: 4 stories (normal)

## Mission

Write three hand-authored interlocking documents that exercise every cross-domain edge type in the graph (REQUIRES_SAFETY, VALIDATES_WITH, REFERENCES), plus a seed loader script that runs the ingestion pipeline on them. The data must be deliberate: the maintenance procedure must reference the safety procedure, and the safety procedure must reference the QC spec -- so that a query about bearing replacement pulls content from all three domains.

## Owned Paths (WRITE access)

- `data/raw/` -- three markdown documents following FORMAT.md
- `data/seed.py` -- seed loader script

## Shared Paths (READ-ONLY)

- `data/FORMAT.md` -- format spec for how to write the documents (owned by foundation-agent)
- `src/models/nodes.py` -- DomainName and OriginKind values to use in frontmatter
- `src/ingestion/` -- imported and called by seed.py (owned by ingestion-agent; read after Wave 1 gate)

## DO NOT MODIFY

- `src/` (except reading for imports in seed.py)
- `pyproject.toml`
- `justfile`

## Dependencies

- Wave 0 (foundation) must be complete: `data/FORMAT.md` must exist before writing documents
- ingestion-agent runs in parallel in Wave 1; `data/seed.py` calls the ingestion pipeline, so it is written to call `src.ingestion.pipeline.run_pipeline(path)` -- the exact function name ingestion-agent exports from `src/ingestion/pipeline.py`

## Progress File

`progress/progress-synthetic-data.txt`

---

## Stories

### US-010: LOTO Safety Procedure Document

**Description:** As a floor supervisor asking about hazardous energy control, I want a complete LOTO safety procedure so that the system has authoritative Safety domain content to retrieve.

**Acceptance Criteria:**

- [ ] `data/raw/safety_loto.md` exists with valid FORMAT.md frontmatter (`domain: Safety`, `doc_id: DOC-001`, `origin: official`)
- [ ] Document has at least 3 top-level sections: Scope, Lockout Procedure, Tagout Procedure
- [ ] Lockout Procedure section has at least 5 numbered steps covering: notify affected employees, identify energy sources, shut down equipment, apply lockout device, verify de-energization
- [ ] Each step wraps relevant entities: `{{Machine:X200 Press}}`, `{{Hazard:Stored Energy}}`, `{{Part:Lockout Device}}`, `{{Term:LOTO}}`
- [ ] At least one step includes `[REFERENCES: DOC-003 §Post-Repair Inspection]` (cross-reference to the QC spec, so traversal from QC can reach Safety)
- [ ] Document reads as plausible OSHA-style safety procedure language
- [ ] Typecheck passes (no Python files changed; this is a documentation story -- criterion is that `python data/seed.py` will not crash on this file's format)

---

### US-011: Press Maintenance Manual

**Description:** As a floor supervisor asking how to replace a bearing on the X200 press, I want a detailed maintenance manual so that the system retrieves the specific bearing replacement procedure and follows cross-domain edges into Safety and QC.

**Acceptance Criteria:**

- [ ] `data/raw/maintenance_press.md` exists with valid FORMAT.md frontmatter (`domain: Maintenance`, `doc_id: DOC-002`, `origin: official`)
- [ ] Document has at least 4 top-level sections: General Maintenance Schedule, Bearing Replacement Procedure, Lubrication Points, Torque Specifications
- [ ] Bearing Replacement Procedure section has at least 6 numbered steps
- [ ] Step for "de-energize the press" includes `[REQUIRES_SAFETY: DOC-001 §Lockout Procedure]` -- this is the primary cross-domain edge that the graph traversal will follow
- [ ] A step near the end includes `[VALIDATES_WITH: DOC-003 §Bearing Housing Tolerance]` -- so retrieval from Maintenance reaches into QC
- [ ] Entities wrapped: `{{Machine:X200 Press}}`, `{{Part:Drive Bearing}}`, `{{Part:Bearing Housing}}`, `{{Term:Torque}}`
- [ ] Torque Specifications section includes a table with at least 3 rows (bolt, torque value, unit)
- [ ] Typecheck passes

---

### US-012: QC Inspection Specification

**Description:** As a floor supervisor checking post-repair quality, I want a QC inspection spec so that the system has Quality Control domain content that the maintenance manual references.

**Acceptance Criteria:**

- [ ] `data/raw/quality_inspection.md` exists with valid FORMAT.md frontmatter (`domain: QualityControl`, `doc_id: DOC-003`, `origin: official`)
- [ ] Document has at least 3 top-level sections: Scope, Dimensional Tolerances, Post-Repair Inspection
- [ ] Post-Repair Inspection section has a subsection `## Bearing Housing Tolerance` (this is the target of the VALIDATES_WITH reference from DOC-002)
- [ ] Bearing Housing Tolerance subsection specifies at least 2 numeric tolerances with units (e.g. bore diameter 75.000 +0.025/-0.000 mm)
- [ ] At least one step in Post-Repair Inspection includes `[REFERENCES: DOC-002 §Torque Specifications]` (back-reference to maintenance, exercising bidirectional traversal)
- [ ] Entities wrapped: `{{Machine:X200 Press}}`, `{{Part:Bearing Housing}}`, `{{Term:Tolerance}}`, `{{Term:Runout}}`
- [ ] Typecheck passes

---

### US-013: Seed Loader Script

**Description:** As a developer, I want a single command to ingest all three synthetic documents into Neo4j so that the graph is populated before Wave 2 API agents need queryable data.

**Acceptance Criteria:**

- [ ] `data/seed.py` imports `from src.ingestion.pipeline import run_pipeline` and calls it for each `.md` file found in `data/raw/`
- [ ] Script prints the filename being processed and confirms completion (or error) for each file
- [ ] Script runs without error when invoked as `python data/seed.py` (requires Neo4j running and `.env` populated)
- [ ] Script is idempotent: running it twice does not duplicate nodes (relies on ingestion pipeline's content hash MERGE behavior)
- [ ] `just ingest` in the justfile calls `python data/seed.py`
- [ ] Typecheck passes

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] Three `.md` files exist in `data/raw/` and each passes FORMAT.md structure
- [ ] Cross-reference tags are present and point to valid doc_id and section heading pairs
- [ ] `uv run mypy src/` passes (seed.py is not in src/ so mypy scope is unaffected)
- [ ] No files created outside owned paths
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

- ingestion-agent reads files from `data/raw/` -- the FORMAT.md spec is the contract; if any file deviates, the parser will fail
- The exact cross-reference strings must match: `DOC-001 §Lockout Procedure`, `DOC-002 §Torque Specifications`, `DOC-003 §Bearing Housing Tolerance` -- these are the section headings ingestion-agent will use to resolve REQUIRES_SAFETY, VALIDATES_WITH, and REFERENCES edges
- api-core and api-answer agents: the primary test query is "How do I safely replace the bearing on press 4?" -- this should return a sectioned answer hitting all three domains
