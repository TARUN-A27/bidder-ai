# BG-02 — Runtime, Demo Operations, and Smoke QA

Owner: Backend Developer 3
Branch: `dev/backend-ingestion`
Priority: P0–P2
Status: READY

## Objective

Make the existing backend straightforward to start and demonstrate, then execute bounded runtime, import, and API smoke checks that remove operational work from the Tech Lead.

This ticket does not own uploaded-PDF assessment integration. That work belongs to Tarun under BG-01.

## Exact Scope

- Verify dependency installation from `backend/requirements.txt`.
- Verify backend startup and `/health` plus `/health/database`.
- Verify required Oracle, Azure, storage, and prototype dataset settings without printing secrets.
- Verify the configured prototype dataset path contains expected A/B/C inputs.
- Add a confirmed missing package declaration such as `azure-ai-documentintelligence`.
- Correct `.env.example`, README, or a concise demo runbook with setup/start/smoke commands.
- Test tender-scoped ZIP and multi-file import using existing regression scripts.
- Test seeded A/B/C API reads, persisted assessments, requirement results, and comparison.
- Report failures with exact commands, status codes, and sanitized errors.
- Perform the runtime/import portion of distributed QA.

## Files / Modules Allowed

- `backend/requirements.txt` for missing declarations only
- `backend/.env.example` for safe variable documentation
- `README.md` and narrowly scoped demo/runbook documentation
- Existing `backend/scripts/` only for a small smoke-test correction approved by Tarun
- Test reports and ticket documentation

## Files / Modules Prohibited

- `backend/app/services/assessment/`, including `PrototypeEvidenceProvider`
- Assessment or document-processing orchestration
- Compliance, scoring, recommendation, or risk engines
- Oracle schema or migrations
- API routers or response schemas
- Ingestion services, archive validation, repositories, or storage internals
- Fixtures, mock portal data, expected results, or frontend files

## Acceptance Criteria

- A teammate can follow documented commands to install dependencies and start the backend.
- The runbook covers health, database, dataset path, import, assessment reads, and comparison.
- Azure and dataset-root variables are documented without credentials.
- Confirmed missing dependency declarations are corrected.
- ZIP and multi-file smoke checks have reproducible results.
- Seeded A/B/C API data can be read when demo services are available.
- Blocker reports include command, expectation, actual result, and sanitized environment context.

## Focused Test Commands

From `backend/`, using the active virtual environment:

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python -c "import fastapi, oracledb; import azure.ai.documentintelligence; print('dependency imports OK')"
PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/health/database
PYTHONPATH=. python scripts/test_bidder_ingestion.py
```

After Tarun confirms assessment integration is ready:

```bash
PYTHONPATH=. python scripts/test_assessment_persistence_api.py
```

Do not repeatedly run the full pytest suite. Tarun owns the final full regression.

## Dependencies

- Tarun confirms approved runtime configuration and handles complex failures.
- Backend Developer 2 may provide endpoint curl examples or API findings.
- Live checks require authorized Oracle/Azure configuration.

## Stop / Escalation Conditions

- Stop and report to Tarun if a fix needs a version pin/change, application-code edit, database change, or architectural decision.
- Obtain Tarun approval before committing dependency compatibility changes.
- Stop if a failure enters assessment, extraction, normalization, ingestion internals, API schemas, Oracle transactions, or decision logic.
- Never print `.env`, credentials, or sensitive connection strings.

## Git Handoff Procedure

1. Work only on `dev/backend-ingestion` for this reassigned ticket.
2. Keep setup/documentation and approved dependency declarations in focused commits.
3. Include commands and sanitized results in the PR description.
4. Push and open a PR to `integration`.
5. Request Tarun's review for dependency changes.
6. Do not push directly to `integration` or `main`.
