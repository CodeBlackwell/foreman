# Architecture: Tree into Knowledge Graph

Date: 2026-06-13
Status: proposed

How foreman turns plant documents into a contextual tree, folds that tree into a knowledge graph, and answers a supervisor's question by routing then traversing.

## Node and edge schema

```
Domain ─CONTAINS→ Document ─CONTAINS→ Section ─CONTAINS→ Step      (the structural tree)
Section ─SUMMARIZES→ its children                                  (recursive summary layer)
Document ─SUMMARIZES→ its sections

Step ─MENTIONS→ Entity {Machine | Part | Hazard | Term}            (entity weave)

Step ─REQUIRES_SAFETY→ SafetyProcedure                             (cross domain)
Step ─VALIDATES_WITH→ QCSpec                                       (cross domain)
Step ─REFERENCES→ Document or Section                              (late binding, resolves out of order)

Term ─PREREQUISITE_OF→ Term                                        (pedagogical DAG, from maisight)
```

### Node types

| Node | Purpose | Key properties |
|------|---------|----------------|
| `Domain` | one of the three routing targets | `name` in {Safety, Maintenance, QualityControl} |
| `Document` | a manual, procedure, or standard | `title`, `origin` (official / AI / user edit), `revision`, `summary`, `embedding` |
| `Section` | a chapter or section, organizes children | `heading`, `level`, `summary`, `embedding` |
| `Step` | a leaf chunk (a procedure step, a rule, a tolerance) | `content`, `context` (generated paragraph), `embedding`, `content_hash`, `origin` |
| `Entity` | a shared real world thing referenced across domains | `kind` (Machine / Part / Hazard / Term), `name`, canonical `id` |
| `Term` | a glossary term (specialization of Entity) | `definition_plain`, `definition_precise`, `prerequisites` |

### The three stacked tree layers

1. **Structural**: `Domain -> Document -> Section -> Step`, built from heading hierarchy at parse time.
2. **Summary** (recursive, RAPTOR style): `SUMMARIZES` edges from each parent to its children, with an LLM generated `summary` stored and embedded on the parent. Retrieval runs over leaves and summaries together (collapsed tree), so a query lands on the specific step and its surrounding context at once.
3. **Context augmented leaves**: every `Step` carries a `context` paragraph generated before embedding. The embedding covers `context + content`, not raw content alone.

### The cross domain edges are the point

`REQUIRES_SAFETY`, `VALIDATES_WITH`, and `REFERENCES` are what let a maintenance answer reach into safety and quality control. They are populated at link time from explicit document cross references and from entity co mention.

## Ingestion pipeline

Adapted from PROVE's five stages. PROVE parses code with tree sitter and classifies into engineering skills. foreman parses prose and tables by heading hierarchy and classifies into document domains.

| PROVE stage | foreman version |
|---|---|
| parse (tree sitter) | structure aware parse by heading level into a Section / Step tree (prose and tables, not code) |
| classify (controlled taxonomy) | route each chunk to a Domain and topic via a controlled taxonomy; extract entities and terms; no free form labels |
| context (Sonnet) | generate a context paragraph per Step, two register definitions for terms where it helps, and a recursive summary per parent Section and Document |
| embed | embed at every tree level: leaf Steps, Section summaries, Document summaries |
| link (Cypher MERGE) | MERGE tree edges, entity edges, and cross references; idempotent via content hash |

Idempotency follows PROVE: every chunk carries a `content_hash`, re-ingest skips unchanged chunks (keeping their context and embedding), and all Cypher uses MERGE so re-runs are safe. Context generation is cached on the node and reused.

## Query and routing flow

```
question
  │
  ▼
ROUTE   keyword match first, LLM fallback for ambiguity
  │     picks the entry Domain (Safety / Maintenance / QC)
  ▼
RETRIEVE (hybrid, collapsed tree)
  │     vector search over leaves + summaries, scoped or biased to the entry Domain
  │     then graph traversal: follow REQUIRES_SAFETY, VALIDATES_WITH, REFERENCES
  │     into the other domains
  ▼
CURATE  keep the strongest evidence, drop the trivial (PROVE curation pattern)
  ▼
ANSWER  grounded text with citations to Document + Section,
        origin disclosed (official vs AI), abstain if confidence is low
```

Routing and the graph are sequential. The router scopes the entry. The graph crosses domains. This is the explicit version of what PROVE does implicitly when its vector search finds an entry node and a graph tool assembles connected evidence.

## What is deliberately deferred

- public OSHA and ISO ingestion (synthetic data first)
- late binding cross reference resolution (only if revision linking across out of order ingests is required)
- any UI beyond a query interface
- multi tenant or multi plant separation
