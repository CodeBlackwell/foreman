# Design Considerations

Date: 2026-06-13
Status: brainstorm captured, decisions open

This is the founding design record for foreman. It captures the problem, the shape of the solution, how the two reference repos map into the flow, and the forks to lock before any code is written.

## The problem

A plant operator wants floor supervisors to get answers from the right documentation. The system should route a question to the appropriate source (safety procedures, maintenance manuals, or quality control standards) and provide accurate answers.

## The core insight

The prompt says route to one source. Real shop floor questions cross sources.

> How do I safely replace the bearing on press 4?

That is a maintenance procedure (replace the bearing) that requires a safety procedure (lockout the press) and ends in a quality control check (post repair tolerance). A pure router picks one bucket and misses the other two.

So the design is not router versus graph. It is **router then graph**: the router picks the entry domain, the graph traversal follows cross references into the other domains. The two are sequential.

## The contextual tree into the knowledge graph

The tree is three layers stacked on the same nodes, plus an entity graph woven across them.

1. **Structural hierarchy** (from parsing): `Domain -> Document -> Section -> Step`. The three Domains (Safety, Maintenance, Quality Control) are literally the three routing targets.
2. **Summary tree** (the recursive summary layer, RAPTOR style): every Section node carries an LLM summary of its children, every Document carries a summary of its sections. We embed at every level so a query retrieves the specific step and its surrounding context in one collapsed tree search. Neither reference repo built this. It is the piece foreman adds.
3. **Context augmented leaves** (the PROVE move): each Step chunk gets a dense context paragraph generated before embedding, so `torque to 40 Nm` becomes findable as `bearing housing bolts, X200 press, post replacement`.

Woven across all of it, an entity graph (the maisight contribution): shared nodes for Machine, Part, Hazard, and Term, plus typed cross domain edges (`REQUIRES_SAFETY`, `VALIDATES_WITH`, `REFERENCES`) and a term prerequisite DAG.

Full schema in [the architecture doc](../architecture/2026-06-13_tree-into-graph-architecture.md).

## How routing relates to the graph

PROVE already does this without naming it. Its vector search finds an entry snippet, then a graph tool walks edges to assemble the full picture. foreman makes it explicit:

- The **router** (keyword first, LLM fallback, both cheap) scopes or biases the initial vector search to one Domain.
- The **graph traversal** then crosses domains by following `REQUIRES_SAFETY` and `VALIDATES_WITH`, which is exactly what single source routing cannot do.

## Accuracy posture (safety critical)

Safety retrieval should fail loud, not guess. This changes the answer contract, so it is a now decision, not a later one:

- every claim cites its Document and Section
- every answer discloses origin (official standard vs AI paraphrase), the maisight pattern
- the system abstains ("I cannot find this, check with your supervisor") rather than fabricating a plausible procedure

## Decisions to lock before code

1. **Recursive summary tree: in or out.** Recommendation: in. Manufacturing manuals are long and a flat leaf search loses procedural context. The summary layer is what makes "hierarchical tree" real rather than just a parse tree. Cost is one extra summarization pass per parent at ingest, paid once.
2. **Graph database.** PROVE uses Neo4j with vector indexes on nodes (cosine), which gives hybrid retrieval in one store. Recommendation: follow PROVE, Neo4j with native vector index, unless we want a separate vector store.
3. **Embedder.** Dimension is frozen at ingest, so this is locked early. PROVE uses Voyage at 1024 dim. Decide before ingesting any synthetic data.
4. **Router implementation.** Keyword router as the default with an LLM fallback for ambiguous questions, or LLM only from the start.
5. **Guardrail policy.** The abstain and citation rules above are policy, not plumbing. Confirm the exact thresholds (minimum similarity to answer, when to abstain).

## Data plan

Start with synthetic data. Hand author three small interlocking documents with deliberate cross references so the cross domain traversal is demonstrable on day one:

- a lockout / tagout (LOTO) safety procedure
- a press maintenance manual (including a bearing replacement procedure that references the LOTO)
- a quality control inspection spec (including a post repair tolerance referenced by the maintenance procedure)

Public OSHA and ISO style documents swap in later behind the same parser, if time allows.

## Build base

Greenfield. Not a CHASSIS re-skin. We borrow patterns from PROVE and maisight rather than inheriting a base repo.

## Open question carried forward

The exact ingestion order independence requirement: maisight (via dearxiv) uses late binding resolution so a reference to a document that has not been ingested yet still links when it arrives. Decide whether foreman needs this for revision linking ("see Part B Rev 3") or whether ingest order can be controlled.
