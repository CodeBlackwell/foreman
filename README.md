# foreman

A retrieval system that helps industrial floor supervisors get accurate answers from the right plant documentation.

A supervisor asks a question. **foreman** routes it to the correct source (safety procedures, maintenance manuals, or quality control standards), follows cross references into the other domains when a real task spans more than one, and answers with citations to the exact document and section.

Live demo: [foreman.codeblackwell.ai](https://foreman.codeblackwell.ai)

## The idea in one line

Build a contextual document tree (structural hierarchy plus recursive summaries plus context-augmented leaves), fold it into a knowledge graph with cross-domain edges, route each question to its entry domain, then traverse the graph to assemble a grounded, cited answer.

## Why a tree into a graph

Plant questions cross document boundaries. "How do I safely replace the bearing on press 4" is a maintenance procedure that requires a safety lockout procedure and ends in a quality control tolerance check. A router alone picks one bucket and misses the other two. The graph is what lets an answer follow those cross references.

## Response types

foreman distinguishes three outcomes rather than silently abstaining:

| Type | Meaning |
|---|---|
| `answered` | Evidence found and directly addresses the question |
| `partial` | In-domain question but the specific procedure is not documented. Relevant context is shown with a note stating what is missing. |
| `out_of_domain` | Question is unrelated to industrial maintenance, safety, or quality control |

## Stack

- **API** — FastAPI, Neo4j (vector + graph), Voyage AI embeddings, Claude (routing + answering)
- **UI** — Streamlit
- **Infra** — Docker Compose, Caddy reverse proxy

## Running locally

Copy the env file and fill in your keys:

```bash
cp .env.example .env
```

Start Neo4j, ingest the seed data, then run the dev server:

```bash
just ingest
just dev
```

`just dev` kills any existing processes on ports 8001 and 8501, starts the FastAPI server in the background, and opens the Streamlit UI in the foreground. Both run together.

## Just recipes

| Recipe | What it does |
|---|---|
| `just dev` | Kill ports 8001 + 8501, start API + UI together |
| `just ingest` | Parse seed docs and load the knowledge graph |
| `just setup-indexes` | Create Neo4j vector indexes (run once after first ingest) |
| `just test` | Run the test suite |
| `just typecheck` | mypy over `src/` |
| `just deploy` | Push to GitHub and rebuild on Hetzner |

## Seed data

Three interlocking synthetic documents live in `data/raw/`:

| File | Domain | Content |
|---|---|---|
| `safety_loto.md` | Safety | Lockout/tagout procedure for the X200 Press |
| `maintenance_press.md` | Maintenance | Bearing replacement procedure (references LOTO) |
| `quality_inspection.md` | QualityControl | Post-repair tolerance spec (referenced by maintenance) |

Cross-domain edges (`REQUIRES_SAFETY`, `VALIDATES_WITH`) are explicit in the documents so graph traversal is demonstrable from day one.

## Architecture

```
question
  |
  v
out-of-domain check (Haiku)
  |
  +-- yes --> out_of_domain response
  |
  v
keyword router (LLM fallback)  -->  entry Domain
  |
  v
hybrid retrieval: vector search + graph traversal
  (follows REQUIRES_SAFETY, VALIDATES_WITH, REFERENCES edges)
  |
  v
per-domain answer (Sonnet)
  always returns something: full answer or Note: [missing] + context
  |
  v
cited response with similarity scores and origin disclosure
```

Full schema and pipeline details in `docs/architecture/2026-06-13_tree-into-graph-architecture.md`.

## Docs

| Doc | Contents |
|---|---|
| `docs/plans/2026-06-13_design-considerations.md` | The brainstorm, the flow, and the open decisions |
| `docs/architecture/2026-06-13_tree-into-graph-architecture.md` | Node and edge schema, ingestion pipeline, query flow |
| `docs/reference/2026-06-13_lessons-prove-maisight.md` | Proven patterns inherited from PROVE and maisight |
| `docs/reference/2026-06-13_qa-questions.md` | QA questions for evaluating citation quality and cross-domain traversal |

## Lineage

The retrieval engine pattern comes from **PROVE** (context-augmented embeddings, hybrid vector plus graph retrieval, controlled taxonomy, content hash idempotency). The trust and canonicalization patterns come from **maisight** (two-register definitions, acronym and synonym collapse, origin disclosure, late-binding cross references). The recursive summary tree is the piece neither built and the one this project adds.
