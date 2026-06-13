# Foundation Agent Specification

## Identity

- **Name**: foundation-agent
- **Wave**: 0
- **Stories**: US-001 to US-004
- **Context Budget**: 4 stories (normal)

## Mission

Stand up the project skeleton and all shared infrastructure that every downstream agent reads: pyproject, justfile, Neo4j client, Pydantic models, and the domain taxonomy. Everything in Wave 1+ depends on this being correct.

## Owned Paths (WRITE access)

- `src/core/` -- Neo4j client, config loader
- `src/models/` -- Pydantic schema models
- `src/taxonomy/` -- domain taxonomy and keyword rules
- `pyproject.toml` -- project metadata and dependencies
- `justfile` -- dev and ops commands
- `.env.example` -- environment variable template
- `data/FORMAT.md` -- markdown format spec that synthetic-data and ingestion agents both read

## Shared Paths (READ-ONLY)

None. This is Wave 0.

## DO NOT MODIFY

Nothing is off limits in Wave 0 since you own the scaffold. But do not add placeholder code or TODO stubs -- if a file is not part of your stories, do not create it.

## Dependencies

None. Wave 0 runs first.

## Progress File

`progress/progress-foundation.txt`

---

## Stories

### US-001: Project Scaffold

**Description:** As a developer, I want a complete project skeleton so that every downstream agent can start work without resolving setup questions.

**Acceptance Criteria:**

- [ ] `pyproject.toml` declares project name `foreman`, Python `>=3.11`, and dependencies: `fastapi`, `uvicorn[standard]`, `neo4j`, `voyageai`, `anthropic`, `pydantic>=2`, `python-dotenv`, `mypy`, `pytest`, `httpx`
- [ ] `justfile` has targets: `dev` (start api with uvicorn reload), `ingest` (run `python data/seed.py`), `test` (run pytest), `typecheck` (run mypy src/)
- [ ] `.env.example` has keys: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `VOYAGE_API_KEY`, `ANTHROPIC_API_KEY`
- [ ] `src/__init__.py`, `src/core/__init__.py`, `src/models/__init__.py`, `src/taxonomy/__init__.py`, `src/ingestion/__init__.py`, `src/api/__init__.py`, `src/api/routes/__init__.py`, `src/api/schemas/__init__.py` all exist (empty)
- [ ] `uv sync` installs without errors (verified manually after creation)
- [ ] Typecheck passes

---

### US-002: Neo4j Client and Index Setup

**Description:** As the ingestion pipeline, I want a shared Neo4j client so that all agents connect the same way and vector indexes are created exactly once.

**Acceptance Criteria:**

- [ ] `src/core/neo4j_client.py` exports a `Neo4jClient` class with `__enter__`/`__exit__` (context manager), `run(query, params)`, `vector_search(index_name, embedding, top_k, domain_filter)`, and `close()`
- [ ] `src/core/config.py` loads all `.env` keys via `python-dotenv` and exposes them as typed attributes; raises `ValueError` on missing required keys
- [ ] `src/core/setup_indexes.py` creates Neo4j vector indexes (cosine, 1024 dim) on `Step.embedding`, `Section.embedding`, `Document.embedding` and uniqueness constraints on `Step.content_hash` and `Entity.canonical_id`; uses `CREATE INDEX IF NOT EXISTS` so it is idempotent
- [ ] `src/core/setup_indexes.py` can be run as `python -m src.core.setup_indexes` and prints confirmation of each index created or already existing
- [ ] Typecheck passes

---

### US-003: Pydantic Schema Models

**Description:** As every agent that reads or writes graph nodes, I want typed Pydantic models so that data shapes are consistent across ingestion and API.

**Acceptance Criteria:**

- [ ] `src/models/nodes.py` defines: `DomainName` (Literal enum: `Safety`, `Maintenance`, `QualityControl`), `OriginKind` (Literal: `official`, `ai_paraphrase`, `user_edit`), `EntityKind` (Literal: `Machine`, `Part`, `Hazard`, `Term`), and dataclasses or Pydantic models for `DocumentNode`, `SectionNode`, `StepNode`, `EntityNode`, `TermNode` -- each with the properties from the architecture doc (`content_hash`, `embedding`, `origin`, `summary` where applicable)
- [ ] `src/models/retrieval.py` defines: `EvidenceItem` (domain, doc_title, section_heading, content, origin, similarity_score), `DomainSection` (domain, items: list[EvidenceItem]), `RetrievalResult` (entry_domain, sections: list[DomainSection])
- [ ] `src/models/api.py` defines: `QueryRequest` (question: str), `CitationRef` (doc_title, section_heading, origin), `AnswerSection` (domain, answer_text, citations: list[CitationRef]), `QueryResponse` (sections: list[AnswerSection], abstained: bool, abstain_reason: str | None)
- [ ] All models use `model_config = ConfigDict(frozen=True)` or equivalent immutability
- [ ] Typecheck passes

---

### US-004: Domain Taxonomy

**Description:** As the router and classifier, I want a controlled domain taxonomy so that every chunk and query resolves to exactly one of the three domains without free-form labels.

**Acceptance Criteria:**

- [ ] `src/taxonomy/domains.py` defines `DOMAIN_KEYWORDS: dict[DomainName, list[str]]` with at least 10 representative keywords per domain (Safety: lockout, tagout, hazard, PPE, LOTO, isolate, de-energize...; Maintenance: replace, bearing, lubricate, torque, press, calibrate...; QualityControl: tolerance, inspection, measurement, spec, reject, pass/fail...)
- [ ] `src/taxonomy/domains.py` defines `classify_by_keyword(text: str) -> DomainName | None` -- returns the domain whose keyword list has the most matches, or None if tied or no match
- [ ] `data/FORMAT.md` is written (see format below) -- this file specifies the markdown structure that synthetic-data-agent must follow and ingestion-agent must parse
- [ ] Typecheck passes

**data/FORMAT.md content to write:**

```markdown
# Synthetic Document Format

Each document is a markdown file in data/raw/.

## File naming

<domain>_<slug>.md  (e.g. safety_loto.md, maintenance_press.md, quality_inspection.md)

## Required frontmatter (YAML block at top of file)

---
title: "Full Document Title"
domain: Safety | Maintenance | QualityControl
doc_id: "DOC-001"  # unique across all docs
revision: "1.0"
origin: official | ai_paraphrase
---

## Heading structure

# Section heading  (level 1 = top-level section)
## Subsection      (level 2 = subsection, parsed as child Section)

## Step content

Steps are paragraphs under a heading. Each paragraph becomes one Step node.
A paragraph that begins with a number followed by a period (e.g. "1. ") is a procedure step.

## Cross references

To link a Step to another document use the tag on its own line:

[REQUIRES_SAFETY: DOC-001 §Section heading]
[VALIDATES_WITH: DOC-003 §Section heading]
[REFERENCES: DOC-002 §Section heading]

## Entity mentions

Wrap entity mentions in double braces to extract them as Entity nodes:

{{Machine:X200 Press}}
{{Part:Drive Bearing}}
{{Hazard:Stored Energy}}
{{Term:LOTO}}
```

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] `uv run mypy src/` passes
- [ ] `data/FORMAT.md` exists and is complete
- [ ] No files created outside owned paths
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

Wave 1 agents read these files from foundation:

- `src/models/nodes.py` -- DomainName, OriginKind, all node types (ingestion writes instances; api agents read them)
- `src/models/retrieval.py` -- EvidenceItem, DomainSection, RetrievalResult (api-answer writes to this shape)
- `src/models/api.py` -- QueryRequest, QueryResponse, AnswerSection (api-core and api-answer use these as FastAPI request/response types)
- `src/core/neo4j_client.py` -- Neo4jClient class; import path is `from src.core.neo4j_client import Neo4jClient`
- `src/core/config.py` -- Settings instance; import as `from src.core.config import settings`
- `src/taxonomy/domains.py` -- DOMAIN_KEYWORDS, classify_by_keyword; import as `from src.taxonomy.domains import classify_by_keyword, DOMAIN_KEYWORDS`
- `data/FORMAT.md` -- format spec for synthetic-data-agent to write docs and ingestion-agent to parse them
