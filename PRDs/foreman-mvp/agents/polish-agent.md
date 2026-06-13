# Polish Agent Specification

## Identity

- **Name**: polish-agent
- **Wave**: 4
- **Stories**: US-080 to US-083
- **Context Budget**: 4 stories (normal)

## Mission

Refine the UI for production readiness: loading states, error handling, the abstain case UI, origin badge accessibility, and a manual end-to-end smoke test. This agent has read access to everything but writes only UI refinements -- no new features, no backend changes.

## Owned Paths (WRITE access)

- `frontend/src/` -- UI refinements only (loading states, error states, styling, accessibility)

## Shared Paths (READ-ONLY)

- `src/` -- read API shapes and schemas as needed; DO NOT modify
- `data/` -- reference only
- `frontend/src/` -- primary read and write target

## DO NOT MODIFY

- `src/` (all backend)
- `pyproject.toml`, `justfile`
- `data/`

## Dependencies

- All prior waves must be complete and verified before Polish starts
- `POST /answer` must be running and returning real data
- `npm run dev` must be running and displaying the full UI

## Progress File

`progress/progress-polish.txt`

---

## Stories

### US-080: Loading and Error States

**Description:** As a floor supervisor, I want visual feedback while the system is thinking and a clear error message if the query fails so that I never wonder if the system is broken.

**Acceptance Criteria:**

- [ ] While query is in flight (`isLoading: true`), the answer area shows a skeleton loader: three placeholder blocks with animated pulse, approximately the height of a typical answer section
- [ ] If `askQuestion()` throws (network error, 5xx), the answer area shows: "The system is currently unavailable. Please try again or contact your supervisor." with a retry button that re-submits the last question
- [ ] If the server returns a 4xx, shows: "Your query could not be processed. Please rephrase your question." -- no retry button (rephrasing is needed)
- [ ] Error state clears when the user submits a new query
- [ ] Typecheck passes
- [ ] Verify changes work in browser

---

### US-081: Abstain State UI Refinement

**Description:** As a floor supervisor, I want the abstain state to feel like a safety guardrail -- not a broken UI -- so that I trust the system's caution rather than finding workarounds.

**Acceptance Criteria:**

- [ ] Abstain response renders with a yellow/amber left border and a warning triangle icon (SVG inline or Heroicons if already in dependencies -- do not add a new icon library)
- [ ] Abstain message text is: "This system could not find relevant documentation for your question. Do not proceed based on assumptions. Consult your supervisor or check the document library directly."
- [ ] If `abstain_reason` is present in the response, render it in smaller text below the main message
- [ ] A tooltip (title attribute or simple hover div) on the warning icon reads: "The system abstains when retrieved documents fall below the minimum relevance threshold. This is a safety feature."
- [ ] Typecheck passes
- [ ] Verify changes work in browser

---

### US-082: Origin Badge and Domain Color Accessibility

**Description:** As a user with color vision differences, I want origin badges and domain blocks to be distinguishable without relying solely on color so that the UI is accessible.

**Acceptance Criteria:**

- [ ] Domain blocks use both color (left border) AND a text label in the header (not color alone): "Safety", "Maintenance", "Quality Control" with an icon prefix (shield for Safety, wrench for Maintenance, clipboard for QC -- SVG inline)
- [ ] Origin badges use color AND a text label: not just a colored dot but a pill with text ("Official Standard", "AI Paraphrase", "User Edit")
- [ ] All text meets WCAG AA contrast ratio (verify visually against the background color -- use Tailwind's documented accessible color pairs)
- [ ] `frontend/src/components/OriginBadge.tsx` is extracted as a standalone component (used in CitationPanel) with `origin: CitationRef["origin"]` as its only prop
- [ ] Typecheck passes
- [ ] Verify changes work in browser

---

### US-083: End-to-End Smoke Test

**Description:** As the team, I want a written smoke test checklist that verifies the full system works from query to sectioned answer so that we have a reproducible validation step before shipping.

**Acceptance Criteria:**

- [ ] `docs/smoke-test.md` exists with a checklist of manual steps:
  1. Start Neo4j (`docker compose up -d neo4j` or equivalent)
  2. Run `just ingest` and confirm all three documents ingest without errors
  3. Start the API (`just dev`) and confirm `GET /health` returns 200
  4. Start the frontend (`npm run dev` in `frontend/`) and confirm it loads
  5. Submit query: "How do I safely replace the bearing on press 4?" -- verify all three domain sections appear (Safety, Maintenance, QC)
  6. Click "Show sources" on the Maintenance block -- verify citation panel opens with at least one citation showing "Official Standard" badge
  7. Click "Show sources" on the Safety block -- verify panel updates to Safety citations
  8. Submit a nonsense query (e.g. "What is the capital of France?") -- verify abstain state renders
  9. Disconnect from Neo4j (`docker compose stop neo4j`) and submit a query -- verify error state renders with retry button
  10. Click retry -- confirm it re-submits without reloading the page
- [ ] All checklist items pass when run against the deployed local stack
- [ ] `docs/smoke-test.md` follows the project's writing conventions (no dash punctuation)

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] `npm run build` passes without TypeScript errors
- [ ] `uv run mypy src/` still passes (polish-agent must not have touched backend)
- [ ] All 10 smoke test steps in `docs/smoke-test.md` pass
- [ ] No backend files modified
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

This is the final wave. After polish completes and all smoke tests pass, the system is demo-ready. Next steps (not in this PRD) are public document ingestion (OSHA, ISO) and deployment.
