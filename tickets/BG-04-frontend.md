# BG-04 — Procurement Officer Frontend

Owner: Frontend Developer
Branch: `dev/frontend`
Priority: P0–P2
Status: READY

API contract: `docs/API_CONTRACT.md`. Build only against documented behavior.

## Objective

Build a professional, desktop-first Procurement Officer interface that completes the BidGuard demo using real backend APIs.

## Exact Scope

Build under `frontend/`:

1. Tender Dashboard
2. Tender Detail
3. Bidder Submissions
4. ZIP and multi-file bidder import
5. Run Assessment
6. Assessment Summary
7. Requirement and Evidence Details
8. Bidder Comparison

Requirements:

- Scaffold React, Vite, and Tailwind as needed.
- Prefer a Vite `/api` proxy instead of requesting backend CORS changes.
- Do not invent `/process`. During `POST /assess`, show "Processing documents and running assessment" or equivalent.
- Implement loading, empty, processing, success, API-error, assessment-unavailable, and assessment-available states.
- Parse string, object, and validation-array error details.
- Display compliance, scores, risks, recommendations, evidence, and review values from APIs.
- Keep the UI simple, professional, government/enterprise styled, desktop-first, without emoji or unnecessary animation.
- Complete functionality before polish and perform browser/build/console QA.

## Files / Modules Allowed

- Entire `frontend/` directory
- Frontend-only configuration, API client, types, routes, pages, components, styles, assets, tests, and documentation

## Files / Modules Prohibited

- All backend files and `docs/API_CONTRACT.md`
- Client-derived compliance, score, risk, override, recommendation, or final decisions
- Hard-coded A/B/C results
- Automatic winner selection or financial/L1 ranking
- Fixtures, mock portal data, or expected results

## Acceptance Criteria

- A user can navigate from dashboard through submissions, import, assessment, requirement details, and comparison.
- Import forms send exact contract multipart fields.
- The UI handles long-running `POST /assess` visibly.
- Unavailable and persisted assessments are distinguished.
- Requirement detail shows status, reason, review flag, evidence, sources, warnings, and points.
- Comparison does not declare a winner.
- `HUMAN_PROCUREMENT_OFFICER` authority is visible.
- A/B/C values come only from live APIs.
- Production build succeeds with no major console errors during the demo flow.

## Focused Test Commands

```bash
cd frontend
npm install
npm run lint
npm run build
```

If configured:

```bash
npm run test
npm run typecheck
```

Manually verify dashboard, tender detail, A/B/C submissions, import, assessment, refresh, requirement details, comparison, and absence of hard-coded results or winner selection.

## Dependencies

- Backend Developer 2 supplies contract clarification, curl examples, and small API fixes.
- Backend Developer 3 supplies verified backend start/health commands.
- Tarun supplies integrated assessment and the release decision.

## Stop / Escalation Conditions

- Stop and report to Backend Developer 2 if a live payload differs from the contract.
- Stop before modifying backend files or requesting a new endpoint.
- Escalate contract changes and processing blockers to Tarun.
- Do not compensate for backend errors by deriving decisions in the browser.

## Git Handoff Procedure

1. Work only on `dev/frontend`.
2. Commit complete vertical slices where practical.
3. Run build and browser verification before handoff.
4. Push and open a PR to `integration`.
5. Include concise visual/manual verification and test results.
6. Request Tarun's review; do not push directly to `integration` or `main`.
