# Ingestion Agent Specification

## Identity

- **Name**: ingestion-agent
- **Wave**: 1
- **Stories**: US-020 to US-023
- **Context Budget**: 4 stories (normal)

## Mission

Build the five-stage ingestion pipeline (parse, classify, context-gen, embed, link) that turns a FORMAT.md-conforming markdown file into a fully populated knowledge graph in Neo4j. The pipeline must be idempotent: re-ingesting a file that has not changed skips unchanged chunks.

## Owned Paths (WRITE access)

- `src/ingestion/` -- all pipeline stages

## Shared Paths (READ-ONLY)

- `src/core/neo4j_client.py` -- Neo4jClient; import as `from src.core.neo4j_client import Neo4jClient`
- `src/core/config.py` -- settings; import as `from src.core.config import settings`
- `src/models/nodes.py` -- node types, DomainName, OriginKind, EntityKind
- `src/taxonomy/domains.py` -- classify_by_keyword, DOMAIN_KEYWORDS
- `data/FORMAT.md` -- the markdown format spec; the parser must handle exactly this structure
- `data/raw/` -- files to read during integration testing

## DO NOT MODIFY

- `src/core/` (owned by foundation-agent)
- `src/models/` (owned by foundation-agent)
- `src/taxonomy/` (owned by foundation-agent)
- `pyproject.toml`

## Dependencies

- Wave 0 (foundation) must be complete: Neo4jClient, models, taxonomy all exist before ingestion can import them
- synthetic-data-agent runs in parallel; the parser is written against FORMAT.md, not the actual files -- do not wait for the files to exist before building the parser

## Progress File

`progress/progress-ingestion.txt`

---

## Stories

### US-020: Parser and Classifier

**Description:** As the ingestion pipeline, I want to parse a FORMAT.md-conforming markdown file into a tree of Section and Step nodes and classify each chunk to a domain so that downstream stages have typed, domain-labeled data.

**Acceptance Criteria:**

- [ ] `src/ingestion/parser.py` exports `parse_document(path: Path) -> ParsedDocument` where `ParsedDocument` holds frontmatter fields (title, domain, doc_id, revision, origin) and a list of `ParsedSection` objects (heading, level, steps: list[ParsedStep], children: list[ParsedSection])
- [ ] Each `ParsedStep` holds: `content` (paragraph text), `cross_refs` (list of parsed cross-reference tags: type, target_doc_id, target_section), `entity_mentions` (list of parsed entity tags: kind, name)
- [ ] `src/ingestion/classifier.py` exports `classify_step(text: str, frontmatter_domain: DomainName) -> DomainName` -- uses `classify_by_keyword` first; if None (ambiguous), returns the frontmatter domain as default (no LLM call in the classifier -- LLM fallback is in the router, not here)
- [ ] Parser correctly extracts `[REQUIRES_SAFETY: DOC-001 §Lockout Procedure]` into `CrossRef(type="REQUIRES_SAFETY", target_doc_id="DOC-001", target_section="Lockout Procedure")`
- [ ] Parser correctly extracts `{{Machine:X200 Press}}` into `EntityMention(kind="Machine", name="X200 Press")`
- [ ] `uv run pytest tests/test_parser.py` passes (write at least 3 tests: frontmatter parse, cross-ref extraction, entity extraction)
- [ ] Typecheck passes

---

### US-021: Context Generator and Recursive Summarizer

**Description:** As the embedder, I want each Step to carry a dense context paragraph and each Section to carry an LLM summary so that embeddings are rich and retrieval works at low similarity thresholds.

**Acceptance Criteria:**

- [ ] `src/ingestion/context_generator.py` exports `generate_step_context(step: ParsedStep, section: ParsedSection, doc: ParsedDocument) -> str` -- calls Anthropic Sonnet to write a 2-4 sentence paragraph explaining what this step does and where it fits (machine, process, hazard); uses prompt caching by wrapping the document-level prefix in a `cache_control: ephemeral` block
- [ ] `src/ingestion/context_generator.py` exports `generate_section_summary(section: ParsedSection, step_contexts: list[str]) -> str` -- summarizes the section's steps in 2-3 sentences
- [ ] `src/ingestion/context_generator.py` exports `generate_document_summary(doc: ParsedDocument, section_summaries: list[str]) -> str` -- summarizes the document in 3-4 sentences
- [ ] For `EntityKind.Term` entities, `generate_term_definitions(name: str) -> tuple[str, str]` returns `(plain_definition, precise_definition)` (operator-friendly vs standards-compliant)
- [ ] Context generation is skipped for a Step if `step.content_hash` already exists in Neo4j with a non-null `context` field (cache reuse from PROVE pattern)
- [ ] Typecheck passes

---

### US-022: Voyage Embedder

**Description:** As the graph builder, I want embeddings at every tree level (Step, Section, Document) so that vector search retrieves the specific step and its surrounding context in one collapsed tree search.

**Acceptance Criteria:**

- [ ] `src/ingestion/embedder.py` exports `embed_text(text: str) -> list[float]` -- calls Voyage API (`voyage-2` model, 1024 dimensions); raises `ValueError` if returned dimension != 1024
- [ ] `embed_step(step_content: str, step_context: str) -> list[float]` embeds `context + "\n\n" + content` concatenated (context-augmented embedding, the PROVE pattern)
- [ ] `embed_batch(texts: list[str]) -> list[list[float]]` batches calls to Voyage (max 128 per request) to avoid rate limits
- [ ] Embedder skips re-embedding a Step if `step.content_hash` already exists in Neo4j with a non-null `embedding` (idempotency)
- [ ] `uv run pytest tests/test_embedder.py` passes with a mock Voyage client (do not call the real API in tests; use `monkeypatch` or a fixture)
- [ ] Typecheck passes

---

### US-023: Graph Builder (Cypher MERGE and Idempotency)

**Description:** As the system, I want all parsed and enriched nodes written to Neo4j with MERGE so that re-ingesting a file is safe and unchanged nodes are not touched.

**Acceptance Criteria:**

- [ ] `src/ingestion/graph_builder.py` exports `build_graph(doc: ParsedDocument, enriched_steps: list[EnrichedStep], client: Neo4jClient)` -- an `EnrichedStep` is a `ParsedStep` plus `context`, `summary` (if section parent), and `embedding`
- [ ] All Cypher writes use `MERGE ... ON CREATE SET ... ON MATCH SET ...` so re-runs are idempotent; `Step` nodes are keyed by `content_hash` (SHA-256 of raw `content`)
- [ ] Creates tree edges: `(Domain)-[:CONTAINS]->(Document)-[:CONTAINS]->(Section)-[:CONTAINS]->(Step)`
- [ ] Creates `(Section)-[:SUMMARIZES]->(Section or Step)` edges for the recursive summary layer
- [ ] Creates `(Step)-[:MENTIONS]->(Entity)` for each entity mention; Entity nodes use `MERGE` on `canonical_id` (lowercase name + kind)
- [ ] Creates cross-domain edges: `REQUIRES_SAFETY`, `VALIDATES_WITH`, `REFERENCES` from the cross-ref tags; uses `MERGE` on `(source_step)-[:TYPE]->(target_doc_id + target_section)` with late binding: if target Section does not yet exist, create a placeholder node and link -- real node merges in when target doc is ingested
- [ ] `src/ingestion/pipeline.py` exports `run_pipeline(path: Path)` -- calls parser, classifier, context generator, embedder, graph builder in order; this is what `data/seed.py` imports
- [ ] `uv run pytest tests/test_graph_builder.py` passes with a real Neo4j test instance or a mocked client (at minimum, test that MERGE queries are emitted with correct structure)
- [ ] Typecheck passes

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest tests/` passes for all ingestion tests
- [ ] `src/ingestion/pipeline.py` exports `run_pipeline(path: Path)` at the documented import path
- [ ] No files created outside `src/ingestion/`
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

- `data/seed.py` (synthetic-data-agent) calls `from src.ingestion.pipeline import run_pipeline` -- this exact import path must work
- api-core-agent: the router classify logic is in `src/taxonomy/domains.py` (foundation), not in ingestion -- the ingestion classifier is only for chunking, not for query routing
- api-answer-agent: the curate stage operates on `EvidenceItem` objects returned by the retriever; the `origin` field on each Step node distinguishes `official` from `ai_paraphrase` context paragraphs -- the graph builder must write this correctly
- The `content_hash` on each Step is SHA-256 of the raw `content` string before context generation; api-answer-agent does not need this but it is the idempotency key for future re-ingests
