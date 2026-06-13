# Lessons from PROVE and maisight

Date: 2026-06-13
Status: reference

The proven patterns foreman inherits, where they live in the source repos, and what foreman adds on top. Read the cited files directly when implementing the matching layer.

## From PROVE (`../PROVE`)

PROVE is a code backed skill evidence graph. It is the retrieval engine blueprint.

| Pattern | What it is | Source | foreman use |
|---|---|---|---|
| **Context augmented embeddings** | An LLM writes a dense 2 to 4 sentence paragraph describing what a chunk is and proves; that paragraph is embedded with the content. Makes vector search work at a low similarity threshold without exact vocabulary. | `src/ingestion/context_generator.py` | The `context` property on every `Step`. The single most important pattern to copy. |
| **Hybrid retrieval via tools** | A ReAct agent with both a vector search tool and a graph traversal tool (`get_connected_evidence`) that assembles connected nodes after an entry hit. | `src/qa/agent.py`, `src/qa/tools.py` | The route then traverse flow. Vector search finds the entry, graph edges cross domains. |
| **Controlled taxonomy classification** | Classification output is restricted to a fixed taxonomy, so the LLM cannot invent labels. | `src/ingestion/skill_taxonomy.py`, `src/ingestion/skill_classifier.py` | The Domain and topic taxonomy. No free form labels. |
| **Content hash idempotency** | Each chunk has a content hash; re-ingest skips unchanged chunks and reuses their context and embedding; all Cypher uses MERGE. | `src/ingestion/graph_builder.py` | The whole re-ingest story. Safety docs must reprocess deterministically. |
| **Vector index on graph nodes** | Neo4j native vector index, cosine, embeddings stored as node properties. One store for vector plus graph. | `src/core/neo4j_client.py` | Candidate graph database. Avoids a separate vector store. |
| **Pre generated summaries served verbatim** | Repository architecture summaries are generated once by a strong model and returned verbatim at query time, because a cheap query model is unreliable at regenerating them. | `src/qa/tools.py` (`get_repo_overview`) | Validates the recursive summary layer: generate summaries at ingest, serve them at query time. |
| **Evidence curation** | Before formatting, an LLM keeps the strongest evidence and drops the trivial, deciding inline vs link per item. | `src/qa/agent.py` (curate step) | The curate stage before answering. |
| **Score adjustment in ranking** | Test files are demoted by a 0.7 multiplier so they do not crowd out real evidence. | `src/core/neo4j_client.py` (vector search) | Analog: demote superseded or draft revisions, boost current and approved documents. |

## From maisight (`../maisight`)

maisight is a glossary highlighter for jargon heavy documents, not a graph system. It contributes trust and canonicalization patterns. Its deeper graph design is inherited from `../dearxiv`.

| Pattern | What it is | Source | foreman use |
|---|---|---|---|
| **Two register definitions** | Every term carries a plain definition (welcoming) and a precise definition (rigorous). | `backend/parse/types.py`, `backend/extract/prompts/propose_terms.v2.txt` | Operator friendly vs standards compliant definitions for manufacturing terms. |
| **Acronym and synonym canonicalization** | Pure function (no LLM) that merges acronym and expansion pairs and collapses case and hyphen variants to one canonical id. | `backend/extract/canonicalize.py` | Manufacturing is acronym heavy: PPE, LOTO, MSDS vs SDS, QC. Collapse to one Entity node. |
| **Origin disclosure** | Each definition is marked as coming from the spec, the LLM, or a human edit. | `frontend/src/reading/termOrigin.ts` | The `origin` property. Critical for trust: is this from the official standard or an AI paraphrase? |
| **Prerequisite DAG** | The LLM extracts which terms must be understood first; rendered as "builds on" navigation. | `backend/parse/types.py` (prerequisites field) | `Term -PREREQUISITE_OF-> Term`. Drill down from a step's term to its dependencies. |
| **Forward compatible JSON** | v1 records ignore unknown fields, so the graph layer is a feature flip, not a rewrite. | `backend/parse/types.py` | Lets foreman start with simpler storage and graduate to the full graph without reshaping data. |
| **Late binding resolution** | A reference to a not yet ingested document still links when the target arrives. | `../dearxiv/docs/plan/03_graph_and_resolution.md` | Optional: revision linking ("see Part B Rev 3") that resolves regardless of ingest order. |
| **Prompt caching for cost** | Role and seed content wrapped in ephemeral cache so chunks of the same document hit cache. | `backend/extract/glossary.py` | Large manuals, many documents: cache the shared ingest prompt prefix. |

## What foreman adds

Neither reference repo built recursive summarization. PROVE gets close with pre generated repository summaries served verbatim, but does not summarize a tree level by level. maisight has no document hierarchy at all.

**The recursive summary tree (RAPTOR style) is foreman's own layer.** Each Section node summarizes its Steps, each Document summarizes its Sections, every level is embedded, and retrieval runs over leaves and summaries together. This is what makes "hierarchical tree" real rather than just a parse tree, and it is the right fit for long manufacturing manuals where a flat leaf search loses procedural context.
