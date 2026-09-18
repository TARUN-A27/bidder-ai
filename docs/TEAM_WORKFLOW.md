# Team Workflow

## Today's Four-Person Allocation

- Tarun / Tech Lead / Backend Lead — `dev/backend-integration`: heavy backend integration, imported-PDF assessment orchestration, difficult Oracle/Azure/runtime blockers, review, final regression, and release gate.
- Backend Developer 3 — `dev/backend-ingestion`: runtime/setup verification, demo operations, import/API smoke QA, and simple setup documentation.
- Backend Developer 2 — `dev/backend-api`: frozen API contract verification, small router/schema fixes, and frontend support.
- Frontend Developer — `dev/frontend`: Procurement Officer UI and browser/build/console QA.
- There is no dedicated QA developer today. `dev/qa` is inactive; QA is distributed as documented in `tickets/BG-05-qa.md`.

## Branches

- `main`: stable and demo-ready.
- `integration`: combined team work after review.
- `dev/backend-integration`: Tech Lead backend integration work.
- `dev/backend-ingestion`: ingestion work.
- `dev/backend-api`: backend API work.
- `dev/frontend`: frontend work.
- `dev/qa`: reserved/inactive today; do not assign a fifth developer.

## Workflow

`developer branch → commit → push → PR to integration → review → QA → integration → main`

Frontend/backend integration uses `docs/API_CONTRACT.md` as the shared contract.

## Rules

- Do not push directly to `main`.
- Avoid direct pushes to `integration`; use a pull request.
- Use the assigned developer branch for one ticket area.
- Communicate before editing another developer's area.
- Keep commits focused and understandable.
- Pull the latest `integration` before the final PR update when needed.
- The Tech Lead controls the final merge from `integration` to `main`.
