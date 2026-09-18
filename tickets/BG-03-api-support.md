# BG-03 — Frozen API Reliability and Frontend Support

Owner: Backend Developer 2
Branch: `dev/backend-api`
Priority: P0–P2
Status: READY

API contract: `docs/API_CONTRACT.md`. Treat it as frozen.

## Objective

Give the Frontend Developer a reliable API surface through bounded contract verification and small router/schema fixes only.

## Exact Scope

- Verify every frozen endpoint against `docs/API_CONTRACT.md`.
- Add focused tests for response fields, status codes, and nullable values.
- Verify multipart behavior for `import-zip` and `import-files`.
- Verify string, structured-object, and FastAPI validation-array error details.
- Reproduce frontend-reported API bugs before changing code.
- Fix only small router or Pydantic schema defects that preserve the contract.
- Give Frontend working curl examples for tenders, submissions, imports, assess, assessment reads, requirement results, and comparison.
- Perform the API-contract portion of distributed QA.

## Files / Modules Allowed

- `backend/app/api/v1/assessments.py`
- `backend/app/api/v1/ingestion.py`
- `backend/app/schemas/assessment.py`
- `backend/app/schemas/submission_ingestion.py`
- New focused API contract tests under `backend/tests/`
- API curl examples or support documentation

## Files / Modules Prohibited

- `backend/app/services/assessment/prototype_evidence.py`
- Assessment or document-processing orchestration
- Compliance, scoring, recommendation, or risk engines
- Oracle repositories, schema, or migrations
- Ingestion/archive/storage internals
- Fixtures, mock portal data, expected results, or frontend source
- `docs/API_CONTRACT.md` without Tarun approval

## Acceptance Criteria

- All ten frozen workflow endpoints have an executable assertion or documented manual verification.
- Tests cover success responses and documented error-detail shapes.
- Multipart tests use `file`, repeated `files`, `bidder_metadata`, `bidder_profile`, and `document_manifest` exactly as contracted.
- No endpoint, field, enum, score, or risk behavior changes.
- Every fixed frontend API bug has a reproducing test.
- Frontend receives copy-paste curl examples using backend-returned IDs.

## Focused Test Commands

From `backend/`, using the active virtual environment:

```bash
PYTHONPATH=. python -m pytest -q tests/test_assessment.py
PYTHONPATH=. python -m pytest -q tests/test_upload_api.py
PYTHONPATH=. python -m pytest -q tests/test_frontend_api_contract.py
```

If the new contract module has another name, run that exact module. Use live contract endpoints at `http://127.0.0.1:8000`; never embed fixed UUIDs in application code.

## Dependencies

- Frontend supplies reproducible browser requests/errors.
- Backend Developer 3 supplies running-API and environment smoke results.
- Tarun handles issues outside router/schema/test boundaries.

## Stop / Escalation Conditions

- Stop and report to Tarun if a fix touches assessment orchestration, ingestion internals, Oracle, compliance, scoring, risk, or dependency versions.
- Stop before any frozen contract change and report its impact to Tarun.
- Do not refactor speculatively or create endpoints.
- If TestClient/runtime blocks tests, report the exact command and timeout instead of changing dependencies independently.

## Git Handoff Procedure

1. Work only on `dev/backend-api`.
2. Keep tests and demonstrated small API fixes in focused commits.
3. Include request examples and test results in the PR description.
4. Push and open a PR to `integration`.
5. Request Tarun's review; do not push directly to `integration` or `main`.
