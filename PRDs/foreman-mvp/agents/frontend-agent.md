# Frontend Agent Specification

## Identity

- **Name**: frontend-agent
- **Wave**: 3
- **Stories**: US-050 to US-053
- **Context Budget**: 4 stories (normal)

## Mission

Build the chat interface: a query input, a sectioned answer display organized by domain (Safety / Maintenance / QC), and a collapsible citation panel. The frontend is a Vite + React SPA that calls only `POST /answer` and displays the `QueryResponse`.

## Owned Paths (WRITE access)

- `frontend/` -- all frontend files (Vite project, React components, Tailwind config)

## Shared Paths (READ-ONLY)

- `src/api/schemas/` -- OriginBadge labels (read the values; don't import Python -- read the file to know the label strings)
- `src/models/api.py` -- read to understand `QueryResponse` shape; implement matching TypeScript types in the frontend

## DO NOT MODIFY

- `src/` (owned by foundation, ingestion, api-core, api-answer agents)
- `pyproject.toml`
- `justfile` (add `frontend` target only if foundation-agent left a placeholder; otherwise do not modify)

## Dependencies

- Wave 0 (foundation): project scaffold complete
- Wave 2 (api-core + api-answer): `POST /answer` must exist and return `QueryResponse`; frontend calls this endpoint at `http://localhost:8000/answer` in development

## Progress File

`progress/progress-frontend.txt`

---

## Stories

### US-050: Vite + React Scaffold

**Description:** As a developer, I want a minimal Vite + React + Tailwind frontend so that I have a runnable base to build components on.

**Acceptance Criteria:**

- [ ] `frontend/` is a Vite project with React and TypeScript (`npm create vite@latest frontend -- --template react-ts` or equivalent)
- [ ] Tailwind CSS configured (tailwind.config.js, postcss.config.js, index.css with directives)
- [ ] `frontend/src/types/api.ts` defines TypeScript interfaces matching the Python models: `CitationRef { doc_title: string; section_heading: string; origin: "official" | "ai_paraphrase" | "user_edit" }`, `AnswerSection { domain: string; answer_text: string; citations: CitationRef[] }`, `QueryResponse { sections: AnswerSection[]; abstained: boolean; abstain_reason: string | null }`
- [ ] `frontend/src/api/client.ts` exports `askQuestion(question: string): Promise<QueryResponse>` -- calls `POST http://localhost:8000/answer` with `{ question }` body; throws on non-2xx
- [ ] `npm run dev` starts the Vite dev server without errors
- [ ] `npm run build` produces a production bundle without errors
- [ ] Verify changes work in browser

---

### US-051: Query Input Component

**Description:** As a floor supervisor, I want a query input field with a submit button so that I can type my question and send it to the system.

**Acceptance Criteria:**

- [ ] `frontend/src/components/QueryInput.tsx` renders a textarea (not a single-line input -- questions can be long) and a "Ask" button
- [ ] While a query is in flight, the button shows "Thinking..." and is disabled to prevent duplicate submissions
- [ ] Pressing Enter (without Shift) submits the form; Shift+Enter inserts a newline
- [ ] Component accepts `onSubmit: (question: string) => void` and `isLoading: boolean` as props
- [ ] Input is cleared after submit
- [ ] Textarea has placeholder text: "Ask a question about safety, maintenance, or quality control..."
- [ ] Typecheck passes (`npm run typecheck` or `tsc --noEmit`)
- [ ] Verify changes work in browser

---

### US-052: Sectioned Answer Display

**Description:** As a floor supervisor, I want the answer organized into clearly labeled domain blocks so that I can immediately see which part is from Safety, Maintenance, or Quality Control.

**Acceptance Criteria:**

- [ ] `frontend/src/components/AnswerDisplay.tsx` accepts `response: QueryResponse` as a prop
- [ ] Renders one block per `AnswerSection` in `response.sections`, in the order returned (Safety -> Maintenance -> QC)
- [ ] Each block has: a domain header label (e.g. "Safety", "Maintenance", "Quality Control") with a colored left border (Safety: red/orange, Maintenance: blue, QC: green), the `answer_text` rendered as paragraph text, and a "Show sources" toggle button that opens the citation panel (see US-053)
- [ ] If `response.abstained` is true, renders a single warning block instead: "No relevant documentation found. [abstain_reason]" with a warning icon and yellow/amber styling
- [ ] If `response.sections` is empty and `abstained` is false (unexpected state), renders "Something went wrong. Please try again."
- [ ] Typecheck passes
- [ ] Verify changes work in browser

---

### US-053: Citation Panel Sidebar

**Description:** As a floor supervisor auditing an answer, I want a collapsible citation panel that lists the source documents and sections used for each domain block so that I can verify the answer against the original documents.

**Acceptance Criteria:**

- [ ] `frontend/src/components/CitationPanel.tsx` accepts `citations: CitationRef[]` and `isOpen: boolean` and `onClose: () => void` as props
- [ ] Renders as a slide-in panel from the right side of the screen (CSS transition, not a modal)
- [ ] Each citation shows: document title, section heading, and an origin badge (pill label: "Official Standard" for `official`, "AI Paraphrase" for `ai_paraphrase`, "User Edit" for `user_edit`)
- [ ] Origin badge colors: "Official Standard" green, "AI Paraphrase" amber, "User Edit" blue
- [ ] Panel has a close button (X) that calls `onClose`
- [ ] Clicking "Show sources" on an `AnswerSection` opens the panel with that section's citations (only that domain's citations, not all domains combined)
- [ ] Clicking "Show sources" on a different section replaces the panel content with the new domain's citations
- [ ] Typecheck passes
- [ ] Verify changes work in browser

---

## Verification Checklist

- [ ] All stories marked [x] in progress file
- [ ] `npm run build` passes without TypeScript errors
- [ ] `npm run dev` + backend running: query "How do I safely replace the bearing on press 4?" returns a sectioned response in the UI with all three domain blocks
- [ ] Citation panel opens and closes correctly for each domain block
- [ ] Abstain state renders correctly (test by asking a nonsense question)
- [ ] No files created outside `frontend/`
- [ ] Agent writes the completion signal to the progress file

## Handoff Notes

- polish-agent will refine: loading skeleton states, error boundaries, responsive layout, domain color accessibility, and origin badge hover tooltips
- The API base URL `http://localhost:8000` is hardcoded in `frontend/src/api/client.ts` for MVP -- polish-agent or future work can parameterize it via env
- Do not add routing (React Router) -- single page with one query form is the MVP scope
