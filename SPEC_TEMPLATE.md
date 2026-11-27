# Feature / Task: [Short Title]

## 1. Objective & Context
- **Goal:** [1–2 sentences on the user or system outcome]
- **Target Files / Modules:** [Exact paths, e.g., `src/api/billing.ts`, `db/migrations/`]
- **Reference Patterns:** [Existing files to mirror for style/conventions]

## 2. Explicit Non-Goals (Out of Scope)
- Do NOT modify [specific modules, public contracts, or unrelated UI].
- Do NOT introduce new external dependencies without explicit approval.

## 3. Functional & Interface Requirements
- **Inputs / Triggers:** [API payloads, events, CLI args, or UI states]
- **Business Rules:**
  - [Rule 1: Specific condition -> expected behaviour]
  - [Rule 2: Edge case / error handling]
- **Outputs / Side Effects:** [Return schemas, DB writes, emitted events]

## 4. Acceptance Criteria & Verification
- [ ] Unit tests added/updated in `[test path]` covering happy path and edge cases.
- [ ] Integration/E2E suite passes via `[exact test command]`.
- [ ] Linter and type-checker pass with zero warnings (`[exact lint/build command]`).

For each check, specify the expected evidence and mark genuinely inapplicable checks explicitly, with a reason. Approve the filled spec before implementation. Amend it explicitly if scope changes.
