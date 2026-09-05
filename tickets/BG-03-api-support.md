# BG-03 — API Support

Owner: Developer 3  
Branch: `dev/backend-api`  
Status: READY

## Goal

Maintain the backend APIs used by the frontend.

## Tasks

- Maintain tender APIs.
- Maintain submission APIs.
- Maintain assessment and comparison APIs.
- Fix response-model and schema issues.
- Support frontend integration.

## Allowed Area

Backend API routers, API schemas, API dependencies, approved read repositories/services, and API tests.

## Do Not Change

- Compliance rules.
- Scoring, recommendation, or risk behavior.
- Ingestion internals unless coordinated with Developer 2.
- Oracle schema unless approved by the Tech Lead.

## Tests / Verification

- Run relevant API tests.
- Run `python scripts/test_assessment_persistence_api.py` for assessment-facing changes when dependencies are available.
- Verify response status codes and typed response compatibility.

## Done When

- Affected endpoints return stable, documented response shapes.
- Frontend integration is supported without changing core decision logic.
- Relevant API and persistence regressions pass.

## Final Report Required

Report:

1. Ticket ID
2. Files created
3. Files modified
4. Tests run
5. Test result
6. Known issues
7. Commit hash
