# Team Workflow

## Branches

- `main`: stable and demo-ready.
- `integration`: combined team work after review.
- `dev/backend-integration`: Tech Lead backend integration work.
- `dev/backend-ingestion`: ingestion work.
- `dev/backend-api`: backend API work.
- `dev/frontend`: frontend work.
- `dev/qa`: QA and regression work.

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
