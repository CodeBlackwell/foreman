# PRD: foreman MVP

## Introduction

foreman is a retrieval system for industrial floor supervisors. It routes a natural language question to the right document domain (Safety, Maintenance, Quality Control), traverses a knowledge graph to pull cross-domain context, and answers with citations to the exact document and section. This MVP builds the synthetic dataset, ingestion pipeline, API, and a chat frontend to demo the full route-then-traverse flow.

## Goals

- Answer questions that cross domain boundaries by routing to one entry domain then graph-traversing into the others
- Return answers sectioned by domain (Safety / Maintenance / QC), each section citing its source document and section
- Cite origin (official standard vs AI paraphrase) per claim
- Abstain rather than guess when confidence falls below threshold
- Demo the system with three hand-authored interlocking documents that exercise all cross-domain edge types

## Agent Roster

| Agent | Wave | Stories | Owned Paths |
|-------|------|---------|-------------|
| foundation | 0 | US-001 to US-004 | `src/core/`, `src/models/`, `src/taxonomy/`, `pyproject.toml`, `justfile`, `.env.example`, `data/FORMAT.md` |
| synthetic-data | 1 | US-010 to US-013 | `data/raw/`, `data/seed.py` |
| ingestion | 1 | US-020 to US-023 | `src/ingestion/` |
| api-core | 2 | US-030 to US-032 | `src/api/app.py`, `src/api/routes/router.py`, `src/api/routes/retrieve.py`, `src/api/dependencies.py` |
| api-answer | 2 | US-040 to US-042 | `src/api/routes/answer.py`, `src/api/curation.py`, `src/api/schemas/` |
| frontend | 3 | US-050 to US-053 | `frontend/` |
| polish | 4 | US-080 to US-083 | All paths (UI refinements only) |

## Wave Plan

```
Wave 0 (foundation)
  ↓ [gate: uv run mypy src/]
Wave 1 (synthetic-data ‖ ingestion)
  ↓ [gate: uv run mypy src/ + manual: just ingest]
Wave 2 (api-core ‖ api-answer)
  ↓ [gate: uv run mypy src/ + uv run pytest tests/]
Wave 3 (frontend)
  ↓ [gate: uv run mypy src/ + browser verify]
Wave 4 (polish)
```

**Note between Wave 1 and Wave 2:** After both Wave 1 agents complete, run `just ingest` to seed the graph before launching Wave 2 agents. The API agents need data in Neo4j to write meaningful integration tests.

### Wave Gates

| After Wave | Validation | Failure Action |
|-----------|-----------|----------------|
| 0 | `uv run mypy src/` | Block Wave 1 until fixed |
| 1 | typecheck + `just ingest` succeeds | Block Wave 2 until graph is seeded |
| 2 | typecheck + `uv run pytest tests/` | Block Wave 3 until fixed |
| 3 | typecheck + browser verify | Block Wave 4 until verified |
| 4 (final) | full suite + manual review | Ship |

## Orchestrator Config

```bash
WAVE_0_AGENTS=("foundation")
WAVE_1_AGENTS=("synthetic-data" "ingestion")
WAVE_2_AGENTS=("api-core" "api-answer")
WAVE_3_AGENTS=("frontend")
WAVE_4_AGENTS=("polish")
```

## Ownership Map

| Path | Owner | Access |
|------|-------|--------|
| `src/core/` | foundation | WRITE |
| `src/models/` | foundation | WRITE |
| `src/taxonomy/` | foundation | WRITE |
| `pyproject.toml` | foundation | WRITE |
| `justfile` | foundation | WRITE |
| `.env.example` | foundation | WRITE |
| `data/FORMAT.md` | foundation | WRITE |
| `data/raw/` | synthetic-data | WRITE |
| `data/seed.py` | synthetic-data | WRITE |
| `src/ingestion/` | ingestion | WRITE |
| `src/api/app.py` | api-core | WRITE |
| `src/api/routes/router.py` | api-core | WRITE |
| `src/api/routes/retrieve.py` | api-core | WRITE |
| `src/api/dependencies.py` | api-core | WRITE |
| `src/api/routes/answer.py` | api-answer | WRITE |
| `src/api/curation.py` | api-answer | WRITE |
| `src/api/schemas/` | api-answer | WRITE |
| `frontend/` | frontend | WRITE |
| `src/core/` | ingestion, api-core, api-answer | READ |
| `src/models/` | ingestion, api-core, api-answer, frontend | READ |
| `src/taxonomy/` | ingestion, api-core | READ |
| `data/FORMAT.md` | synthetic-data, ingestion | READ |
| `data/raw/` | ingestion, data/seed.py | READ |
| `src/ingestion/` | api-core | READ (to call pipeline from seed) |
| `src/api/` | frontend | READ (OpenAPI schema only) |
| `*` | polish | READ (write UI refinements only) |

## Feature Domains

### Domain: Foundation (Wave 0)

**Owner:** foundation-agent

| ID | Story | Status |
|----|-------|--------|
| US-001 | Project scaffold | [ ] |
| US-002 | Neo4j client and index setup | [ ] |
| US-003 | Pydantic schema models | [ ] |
| US-004 | Domain taxonomy | [ ] |

### Domain: Synthetic Data (Wave 1)

**Owner:** synthetic-data-agent

| ID | Story | Status |
|----|-------|--------|
| US-010 | LOTO safety procedure document | [ ] |
| US-011 | Press maintenance manual | [ ] |
| US-012 | QC inspection specification | [ ] |
| US-013 | Seed loader script | [ ] |

### Domain: Ingestion (Wave 1)

**Owner:** ingestion-agent

| ID | Story | Status |
|----|-------|--------|
| US-020 | Parser and classifier | [ ] |
| US-021 | Context generator and recursive summarizer | [ ] |
| US-022 | Voyage embedder | [ ] |
| US-023 | Graph builder (Cypher MERGE + idempotency) | [ ] |

### Domain: API Core (Wave 2)

**Owner:** api-core-agent

| ID | Story | Status |
|----|-------|--------|
| US-030 | FastAPI app scaffold | [ ] |
| US-031 | Router endpoint | [ ] |
| US-032 | Retrieve endpoint | [ ] |

### Domain: API Answer (Wave 2)

**Owner:** api-answer-agent

| ID | Story | Status |
|----|-------|--------|
| US-040 | Evidence curation | [ ] |
| US-041 | Answer generation (sectioned by domain) | [ ] |
| US-042 | Abstain logic and origin disclosure | [ ] |

### Domain: Frontend (Wave 3)

**Owner:** frontend-agent

| ID | Story | Status |
|----|-------|--------|
| US-050 | Vite + React scaffold | [ ] |
| US-051 | Query input component | [ ] |
| US-052 | Sectioned answer display | [ ] |
| US-053 | Citation panel sidebar | [ ] |

### Domain: Polish (Wave 4)

**Owner:** polish-agent

| ID | Story | Status |
|----|-------|--------|
| US-080 | Loading and error states | [ ] |
| US-081 | Abstain UI state | [ ] |
| US-082 | Origin badge and domain color coding | [ ] |
| US-083 | End-to-end smoke test | [ ] |

## Non-Goals

- Public OSHA or ISO document ingestion (synthetic data only for MVP)
- Late binding cross-reference resolution (ingest order is controlled)
- Multi-tenant or multi-plant separation
- Authentication or access control
- Conversation history (single-turn queries only in MVP)
- Document upload via UI (ingest runs from CLI only)
- Real-time document updates

## Technical Decisions Locked

- Graph store: Neo4j with native vector indexes (cosine, 1024 dim)
- Embedder: Voyage (`voyage-2` or `voyage-large-2`, 1024 dim) -- lock before first ingest
- Context and answer generation: Sonnet with prompt caching on shared ingest prefixes
- Citation format: sectioned by domain (Safety / Maintenance / QC blocks), each block cites Document title + Section heading + origin flag
- Router: keyword-first (taxonomy match), LLM fallback for ambiguous queries
- Abstain threshold: minimum cosine similarity 0.70 to answer; below that return abstain response
- Origin values: `official` (from source doc as-is), `ai_paraphrase` (LLM rewrote), `user_edit`

## Progress Tracker

| Wave | Agent | Stories | Completed | Status |
|------|-------|---------|-----------|--------|
| 0 | foundation | 4 | 0 | NOT_STARTED |
| 1 | synthetic-data | 4 | 0 | NOT_STARTED |
| 1 | ingestion | 4 | 0 | NOT_STARTED |
| 2 | api-core | 3 | 0 | NOT_STARTED |
| 2 | api-answer | 3 | 0 | NOT_STARTED |
| 3 | frontend | 4 | 0 | NOT_STARTED |
| 4 | polish | 4 | 0 | NOT_STARTED |
