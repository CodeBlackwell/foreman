# foreman

A retrieval system that helps industrial floor supervisors get accurate answers from the right plant documentation.

A supervisor asks a question. **foreman** routes it to the correct source (safety procedures, maintenance manuals, or quality control standards), follows cross references into the other domains when a real task spans more than one, and answers with citations to the exact document and section.

## The idea in one line

Build a contextual document tree (structural hierarchy plus recursive summaries plus context augmented leaves), fold it into a knowledge graph with cross domain edges, route each question to its entry domain, then traverse the graph to assemble a grounded, cited answer.

## Why a tree into a graph

Plant questions cross document boundaries. "How do I safely replace the bearing on press 4" is a maintenance procedure that requires a safety lockout procedure and ends in a quality control tolerance check. A router alone picks one bucket and misses the other two. The graph is what lets an answer follow those cross references.

## Status

Design phase. No code yet. The thinking is documented under `docs/`:

- `docs/plans/2026-06-13_design-considerations.md` — the brainstorm, the flow, and the open decisions
- `docs/architecture/2026-06-13_tree-into-graph-architecture.md` — node and edge schema, the ingestion pipeline, the query flow
- `docs/reference/2026-06-13_lessons-prove-maisight.md` — the proven patterns inherited from PROVE and maisight, and what we add

## Lineage

The retrieval engine pattern comes from **PROVE** (context augmented embeddings, hybrid vector plus graph retrieval, controlled taxonomy, content hash idempotency). The trust and canonicalization patterns come from **maisight** (two register definitions, acronym and synonym collapse, origin disclosure, late binding cross references). The recursive summary tree is the piece neither built and the one this project adds.
