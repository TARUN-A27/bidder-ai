# BG-05 — Distributed QA Ownership

Owner: No dedicated QA developer today
Branch: No active QA branch assignment
Priority: P0–P2
Status: DISTRIBUTED — NOT A SEPARATE IMPLEMENTATION TICKET

## Objective

Document QA ownership across today's four developers. Do not assign a fifth developer or start work on `dev/qa`.

## Exact Scope

- Tarun: heavy backend verification, final A/B/C regression, E2E release gate, and merge approval.
- Backend Developer 2: API contract tests, response/error verification, and frontend API bug reproduction.
- Backend Developer 3: dependency/setup, startup, health, Oracle/Azure configuration, dataset path, import, and API smoke QA.
- Frontend Developer: browser workflow, UI states, production build, and console QA.
- Each developer records exact commands and honest results in their own handoff.

## Files / Modules Allowed

- Tests, scripts, and documentation allowed by each active ticket
- Reproducible bug reports
- This distributed-QA coordination document

## Files / Modules Prohibited

- Independent QA application-code changes
- Decision-logic changes merely to satisfy tests
- Fixture, benchmark, expected-result, API contract, schema, or migration changes
- New work on `dev/qa` today

## Acceptance Criteria

- Every active ticket reports its focused verification.
- Import, assessment, persisted reads, requirement details, comparison, and expected errors are collectively covered.
- Final regression confirms A `100.0 / LOW` with 21 PDFs, B `80.5 / HIGH` with 21 PDFs, and C `34.0 / CRITICAL` with 19 PDFs.
- Final browser demo passes without major console errors.
- Failures are routed to their owner rather than fixed across boundaries.

## Focused Test Commands

BG-01 through BG-04 define owner-specific commands. Tarun's final release gate includes:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python scripts/test_bidder_ingestion.py
PYTHONPATH=. ../.venv/bin/python scripts/test_assessment_persistence_api.py
PYTHONPATH=. ../.venv/bin/python -m pytest -q
```

Frontend additionally runs its configured lint/build/test commands and browser workflow.

## Dependencies

- All four tickets report assigned verification.
- Live regression requires authorized Oracle/Azure configuration and demo data.
- Tarun decides whether a failure blocks release.

## Stop / Escalation Conditions

- Stop when QA reveals a bug outside the tester's ticket and report it to the owner and Tarun.
- Stop before changing benchmarks, contracts, schemas, migrations, fixtures, or decision logic.
- Do not assume an absent fifth-developer role.

## Git Handoff Procedure

- There is no separate BG-05 code handoff or active `dev/qa` PR today.
- QA evidence travels with BG-01 through BG-04 PRs.
- Tarun records final regression and browser-release results in the integration/release handoff.
