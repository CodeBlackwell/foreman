# API Core Agent Specification

## Identity

- **Name**: api-core-agent
- **Wave**: 2
- **Stories**: US-030 to US-032
- **Context Budget**: 3 stories (light)

## Mission

Build the FastAPI application scaffold, the domain router endpoint, and the hybrid retrieval endpoint. These are the first two stages of the query flow (route then retrieve) and are the dependency that api-answer-agent reads from.

## Owned Paths (WRITE access)

- `src/api/app.py` -- FastAPI app instance and lifespan
- `src/api/routes/router.py` -- domain routing endpoint
- `src/api/routes/retrieve.py` -- retrieval endpoint
- `src/api/dependencies.py` -- FastAPI dependency injection (Neo4jClient, Settings)

## Shared Paths (READ-ONLY)

- `src/core/neo4j_client.py` -- Neo4jClient
- `src/core/config.py` -- settings
- `src/models/nodes.py` -- DomainName
- `src/models/api.py` -- QueryRequest (used as request body type)
- `src/models/retrieval.py` -- EvidenceItem, DomainSection, RetrievalResult
- `src/taxonomy/domains.py` -- classify_by_keyword

## DO NOT MODIFY

- `src/core/` (owned by foundation-agent)
- `src/models/` (owned by foundation-agent)
- `src/taxonomy/` (owned by foundation-agent)
- `src/ingestion/` (owned by ingestion-agent)
- `src/api/routes/answer.py` (owned by api-answer-agent)
- `src/api/curation.py` (owned by api-answer-agent)
- `src/api/schemas/` (owned by api-answer-agent)

## Dependencies

- Wave 0 (foundation): Neo4jClient, models, taxonomy
- Wave 1 (ingestion): graph must be seeded before retrieval queries return real results -- the `just ingest` gate between Wave 1 and Wave 2 handles this
- Wave 1 (synthetic-data): indirectly -- the retrieval endpoint queries what ingestion wrote

## Progress File

`progress/progress-api-core.txt`

---

## Stories

### US-030: FastAPI App Scaffold

**Description:** As a developer, I want a runnable FastAPI application with health check and CORS configured so that frontend agents can connect and downstream agents have an app to mount their routes onto.

**Acceptance Criteria:**

- [ ] `src/api/app.py` creates the FastAPI app with a lifespan that opens a Neo4jClient on startup and closes it on shutdown; the client is stored in `app.state.db`
- [ ] `src/api/dependencies.py` exports `get_db() -> Neo4jClient` as a FastAPI dependency that yields `request.app.state.db`
- [ ] CORS middleware allows all origins in development (`allow_origins=["*"]`) with methods GET and POST
- [ ] `GET /health` returns `{"status": "ok"}` and 200
- [ ] `uvicorn src.api.app:app --reload` starts without errors (verified manually)
- [ ] Router and retrieve routes are mounted in `app.py` (import and `app.include_router(...)`)
- [ ] Typecheck passes

---

### US-031: Router Endpoint

**Description:** As the query flow, I want a domain routing endpoint that classifies a question into one entry domain so that the retriever knows where to start.

**Acceptance Criteria:**

- [ ] `POST /route` accepts `QueryRequest` (question: str) and returns `{"entry_domain": "Maintenance", "method": "keyword" | "llm"}` plus a `200` status
- [ ] Keyword routing: calls `classify_by_keyword(question)` first; if it returns a domain, respond with `method: "keyword"` without an LLM call
- [ ] LLM fallback: if `classify_by_keyword` returns None, calls Anthropic Haiku (cheap model) with a system prompt that lists the three domains and their descriptions, asks it to return exactly one domain name, and parses the response; respond with `method: "llm"`
- [ ] LLM call uses a `max_tokens=20` limit (we only need one word back)
- [ ] If LLM also fails to return a valid domain (malformed response), defaults to `"Maintenance"` with a warning logged to stderr
- [ ] `uv run pytest tests/test_router.py` passes with at least 3 test cases: clear Safety query, clear Maintenance query, ambiguous query (triggers LLM path with monkeypatched client)
- [ ] Typecheck passes

---

### US-032: Retrieve Endpoint

**Description:** As the answer stage, I want a retrieval endpoint that runs hybrid vector search scoped to the entry domain then graph-traverses into other domains so that evidence spans all relevant domains.

**Acceptance Criteria:**

- [ ] `POST /retrieve` accepts `{"question": str, "entry_domain": str, "top_k": int = 5}` and returns a `RetrievalResult`
- [ ] Vector search: calls `client.vector_search(index_name="step_embedding", embedding=embed_text(question), top_k=top_k, domain_filter=entry_domain)` to get the top-k entry Steps
- [ ] Graph traversal: for each entry Step, runs a Cypher query that follows `REQUIRES_SAFETY`, `VALIDATES_WITH`, and `REFERENCES` edges out one hop and collects the target Steps with their Document and Section context
- [ ] Deduplicates Steps across entry and traversal results by `content_hash`
- [ ] Groups results by domain into a `RetrievalResult` (entry_domain, sections: list[DomainSection]) where each `DomainSection` holds the `EvidenceItem` list for that domain
- [ ] If no Steps exceed similarity 0.70 (the abstain threshold), returns a `RetrievalResult` with empty sections and sets a flag `below_threshold: True` -- api-answer-agent uses this to trigger abstain
- [ ] `uv run pytest tests/test_retrieve.py` passes with a mocked Neo4jClient that returns fixture evidence items
- [ ] Typecheck passes

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest tests/test_router.py tests/test_retrieve.py` passes
- [ ] `GET /health` returns 200 when server is running
- [ ] No files created outside owned paths
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

- api-answer-agent mounts its route at `POST /answer` in `src/api/routes/answer.py`; it receives the `RetrievalResult` from `/retrieve` (either by calling it internally or by taking it as input -- api-answer-agent decides)
- The `below_threshold` flag on `RetrievalResult` is the trigger for api-answer-agent's abstain logic; make sure this field is in the `RetrievalResult` model (coordinate with foundation-agent's `src/models/retrieval.py` if the field is not already there -- add it to retrieval.py since api-core owns the retrieve response shape)
- frontend-agent: the primary endpoint it calls is `POST /answer` (api-answer-agent), not `/route` or `/retrieve` directly -- those are internal pipeline steps; the frontend calls one endpoint and gets a complete `QueryResponse` back
