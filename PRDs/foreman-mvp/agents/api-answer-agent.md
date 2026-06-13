# API Answer Agent Specification

## Identity

- **Name**: api-answer-agent
- **Wave**: 2
- **Stories**: US-040 to US-042
- **Context Budget**: 3 stories (light)

## Mission

Build the curate, answer, and abstain stages of the query flow. This agent owns the final endpoint (`POST /answer`) that the frontend calls. It takes a question, orchestrates the route and retrieve stages internally, curates evidence, and returns a sectioned answer with citations -- or an abstain response if confidence is too low.

## Owned Paths (WRITE access)

- `src/api/routes/answer.py` -- the `/answer` endpoint
- `src/api/curation.py` -- evidence curation logic
- `src/api/schemas/` -- response schema types used in answer formatting

## Shared Paths (READ-ONLY)

- `src/core/neo4j_client.py` -- Neo4jClient (via dependency injection)
- `src/core/config.py` -- settings
- `src/models/api.py` -- QueryRequest, QueryResponse, AnswerSection, CitationRef
- `src/models/retrieval.py` -- RetrievalResult, DomainSection, EvidenceItem
- `src/api/app.py` -- app instance (to mount route)
- `src/api/dependencies.py` -- get_db dependency
- `src/api/routes/router.py` -- `route_question(question, db)` internal function (if api-core-agent exports it)
- `src/api/routes/retrieve.py` -- `retrieve_evidence(question, entry_domain, top_k, db)` internal function

## DO NOT MODIFY

- `src/core/` (owned by foundation-agent)
- `src/models/` (owned by foundation-agent)
- `src/api/app.py` (owned by api-core-agent)
- `src/api/routes/router.py` (owned by api-core-agent)
- `src/api/routes/retrieve.py` (owned by api-core-agent)
- `src/api/dependencies.py` (owned by api-core-agent)

## Dependencies

- Wave 0 (foundation): models
- Wave 1 gate: graph seeded with synthetic data (needed for real integration)
- api-core-agent (Wave 2 parallel): `/route` and `/retrieve` internal functions must be callable from `answer.py`; coordinate on function signatures -- api-core-agent should export `route_question` and `retrieve_evidence` as importable functions, not just as route handlers

## Progress File

`progress/progress-api-answer.txt`

---

## Stories

### US-040: Evidence Curation

**Description:** As the answer stage, I want curated evidence that keeps only the strongest items per domain and drops redundant or tangential results so that the answer is concise and grounded.

**Acceptance Criteria:**

- [ ] `src/api/curation.py` exports `curate_evidence(result: RetrievalResult, max_per_domain: int = 3) -> RetrievalResult`
- [ ] Keeps up to `max_per_domain` EvidenceItems per DomainSection, ranked by `similarity_score` descending
- [ ] Drops any EvidenceItem whose `similarity_score` is below 0.70 (the abstain threshold defined in PRD technical decisions)
- [ ] If after filtering, a DomainSection has zero items, it is removed from the result (do not return empty domain blocks)
- [ ] Calls an Anthropic Haiku LLM pass only when the top-k pool for a domain has more than `max_per_domain` items above threshold -- the LLM decides which `max_per_domain` items are most relevant and returns their indices; if pool size is already <= max_per_domain, skip the LLM call
- [ ] `uv run pytest tests/test_curation.py` passes with at least 3 test cases: all items above threshold, mixed above/below, empty result
- [ ] Typecheck passes

---

### US-041: Answer Generation (Sectioned by Domain)

**Description:** As a floor supervisor, I want an answer that is clearly organized by domain with citations so that I can see which part of my question was answered by Safety, Maintenance, and QC respectively.

**Acceptance Criteria:**

- [ ] `src/api/routes/answer.py` exports a FastAPI router mounted at `POST /answer`
- [ ] Endpoint accepts `QueryRequest` (question: str) and returns `QueryResponse`
- [ ] Internally calls `route_question` then `retrieve_evidence` then `curate_evidence`; if curated result has no sections (all below threshold), returns an abstain response (see US-042)
- [ ] For each non-empty DomainSection in curated result, calls Anthropic Sonnet with a prompt containing: the question, the domain name, and the evidence items' content; instructs it to answer only using the evidence and to abstain if evidence is insufficient for this domain
- [ ] Each `AnswerSection` in the response has: `domain` (e.g. "Safety"), `answer_text` (Sonnet output), `citations: list[CitationRef]` built from the evidence items used (doc_title, section_heading, origin)
- [ ] `QueryResponse.sections` is ordered: Safety first, then Maintenance, then QualityControl -- regardless of which domain was the entry domain
- [ ] `QueryResponse.abstained` is False when at least one section has content
- [ ] `uv run pytest tests/test_answer.py` passes with mocked route, retrieve, and Sonnet calls
- [ ] Typecheck passes

---

### US-042: Abstain Logic and Origin Disclosure

**Description:** As a floor supervisor in a safety-critical environment, I want the system to refuse to guess rather than fabricate a procedure, and I want to know whether each citation is from an official standard or an AI paraphrase.

**Acceptance Criteria:**

- [ ] If `curate_evidence` returns an empty `RetrievalResult` (zero sections above threshold), `POST /answer` returns `QueryResponse(sections=[], abstained=True, abstain_reason="No relevant documentation found. Please consult your supervisor or refer to the document library directly.")`
- [ ] If a specific domain's Sonnet call returns a response that includes a phrase indicating insufficient evidence (e.g. starts with "I cannot" or "The provided evidence does not"), that domain's section is dropped and not included in `QueryResponse.sections` -- this is per-domain abstain
- [ ] Each `CitationRef` in the response includes `origin: OriginKind` drawn from the `EvidenceItem.origin` field (which came from the Step node's `origin` property set at ingest)
- [ ] `src/api/schemas/` contains at least `OriginBadge` (a mapping from `OriginKind` to a display label string: `"official" -> "Official Standard"`, `"ai_paraphrase" -> "AI Paraphrase"`, `"user_edit" -> "User Edit"`) -- this is used by the frontend to render badges
- [ ] `GET /answer/abstain-policy` returns a plain-text description of the abstain thresholds (similarity >= 0.70 to answer, per-domain Sonnet abstain check) for operator reference
- [ ] `uv run pytest tests/test_abstain.py` passes with at least 2 test cases: full below-threshold abstain, partial domain abstain
- [ ] Typecheck passes

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest tests/test_curation.py tests/test_answer.py tests/test_abstain.py` passes
- [ ] `POST /answer` with the test query "How do I safely replace the bearing on press 4?" returns a sectioned response with all three domains represented (requires seeded graph)
- [ ] No files created outside owned paths
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

- frontend-agent: the only endpoint it calls is `POST /answer` with `{"question": "..."}` body; it receives `QueryResponse` with `sections: list[AnswerSection]`, `abstained: bool`, `abstain_reason: str | None`
- `AnswerSection` has: `domain: str`, `answer_text: str`, `citations: list[CitationRef]`
- `CitationRef` has: `doc_title: str`, `section_heading: str`, `origin: str` (one of `"official"`, `"ai_paraphrase"`, `"user_edit"`)
- `GET /answer/abstain-policy` is useful for the frontend to display a tooltip explaining why the system sometimes refuses to answer
- The domain ordering in `QueryResponse.sections` is always Safety -> Maintenance -> QualityControl; frontend can render in this order
