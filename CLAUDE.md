# CLAUDE.md — foreman

Guidance for Claude Code working in this repo. This file is a navigation hub: it points at `docs/` rather than inlining knowledge. Read the linked doc before working in a layer.

## What foreman is

A retrieval system for industrial floor supervisors. It routes a question to the right document domain (safety, maintenance, quality control), traverses a knowledge graph to pull cross domain context, and answers with citations to the exact document and section. See [README.md](README.md).

The core data model is a **contextual tree folded into a knowledge graph**: a structural document hierarchy, a recursive summary layer on top of it, context augmented leaf chunks underneath, and an entity graph woven across all three with cross domain edges.

## Status

Design phase. No code yet. The design lives under `docs/`.

## Key docs

| Doc | Contents |
|-----|----------|
| [docs/plans/2026-06-13_design-considerations.md](docs/plans/2026-06-13_design-considerations.md) | the brainstorm, the mapped flow, the open decisions to lock before code |
| [docs/architecture/2026-06-13_tree-into-graph-architecture.md](docs/architecture/2026-06-13_tree-into-graph-architecture.md) | node and edge schema, ingestion pipeline, query and routing flow |
| [docs/reference/2026-06-13_lessons-prove-maisight.md](docs/reference/2026-06-13_lessons-prove-maisight.md) | proven patterns inherited from PROVE and maisight, and what foreman adds |

## Reference repos

These are sibling repos in the BLACKBOX workspace whose patterns foreman draws on. Read them directly when implementing the matching layer.

- **PROVE** (`../PROVE`) — the retrieval engine blueprint. The context stage, hybrid vector plus graph retrieval, controlled taxonomy classification, content hash idempotency.
- **maisight** (`../maisight`) — trust and canonicalization. Two register definitions, acronym and synonym collapse, origin disclosure. Its deferred graph design is inherited from `../dearxiv` (late binding cross references).

## Engineering standards

This repo follows the workspace minimalist principles (YAGNI, small functions, no speculative abstraction) and the house tooling style (uv plus a justfile) once code begins. Safety critical posture: answers cite their source, disclose origin (official standard vs AI paraphrase), and abstain rather than guess.

## Documentation discipline

`docs/` is categorical: `architecture/` (system shape), `reference/` (lookup), `plans/` (dated planning and decision records). Dated docs follow `YYYY-MM-DD_slug.md`. This `CLAUDE.md` is a hub, not a knowledge sink. Point at docs, do not inline.

## Writing conventions

No dash punctuation in any document or user facing copy (no em dashes, no en dashes, no dashes used as connectors). Use commas, periods, parentheses, or colons instead.
