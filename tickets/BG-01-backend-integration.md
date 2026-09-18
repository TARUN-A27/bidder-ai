# BG-01 — Tech Lead Backend Integration and Release Gate

Owner: Tarun — Tech Lead / Backend Lead
Branch: `dev/backend-integration`
Priority: P0–P2
Status: READY

## Objective

Own the difficult cross-module backend work and deliver a stable end-to-end demo without changing the frozen API or validated compliance outcomes.

## Exact Scope

### P0 — Imported-document assessment integration

- Close the gap where `PrototypeEvidenceProvider` reads source PDFs from the external prototype dataset instead of PDFs imported under `storage/uploads`.
- Ensure imported Bidder A, B, and C PDFs are used by Azure extraction during assessment.
- Preserve a safe, explicit fallback for pre-seeded submissions without stored uploads, if the demo requires it.
- Continue using trusted tender configuration and mock authoritative verification data.
- Keep `POST /api/v1/submissions/{submission_id}/assess` as the combined processing and assessment operation. Do not create a processing endpoint.
- Preserve the frozen response contract and benchmarks: A `100.0 / LOW`, B `80.5 / HIGH`, C `34.0 / CRITICAL`.

### P1 — Runtime and integration stabilization

- Resolve difficult Azure, Oracle, assessment-orchestration, dependency, or runtime blockers.
- Approve any dependency version pin proposed by Backend Developer 3.
- Review backend PRs and resolve cross-module conflicts.
- Support final frontend/backend integration without broad API redesign.

### P2 — Release gate

- Run the final integrated A/B/C regression after backend merges.
- Verify import, assessment, persisted assessment, requirement detail, and comparison flows.
- Control merge order and decide when the demo build is release-ready.

## Files / Modules Allowed

- `backend/app/services/assessment/`
- Approved orchestration under `backend/app/services/document_processing/`
- Narrowly scoped backend repository and API dependency wiring changes required by this integration
- `backend/app/core/`, `backend/app/db/`, and runtime configuration for demonstrated blockers
- Relevant backend tests and regression scripts
- `backend/requirements.txt`, `backend/.env.example`, and setup documentation when integration requires them

## Files / Modules Prohibited

- Compliance semantics, scoring rules, risk thresholds, override IDs, or recommendations without explicit approval
- Synthetic dataset fixtures, ground-truth files, or `expected_result.json`
- Frozen API paths, fields, or enums without an approved contract change
- Unrelated frontend code or cosmetic work
- Oracle migrations unless a demonstrated blocker is reviewed first

## Acceptance Criteria

- Imported A/B/C assessment extracts from stored imported PDFs, not silently from the external source-document directory.
- Missing, incomplete, or mismatched stored uploads fail safely without mixing uploaded and fixture document sets.
- Any pre-seeded fallback is explicit, tested, and prototype-only.
- ZIP and multi-file imports remain compatible with assessment.
- The frozen `POST /assess` response is unchanged.
- A/B/C remain exactly `100.0 / LOW`, `80.5 / HIGH`, and `34.0 / CRITICAL`.
- The final browser/API workflow passes on the demo host.

## Focused Test Commands

Run affected tests first, adjusting the virtual-environment path if needed:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python -m pytest -q tests/test_assessment.py
PYTHONPATH=. ../.venv/bin/python -m pytest -q tests/test_submission_ingestion.py
```

After backend PRs are integrated, run the live/full regression once:

```bash
cd backend
PYTHONPATH=. ../.venv/bin/python scripts/test_bidder_ingestion.py
PYTHONPATH=. ../.venv/bin/python scripts/test_assessment_persistence_api.py
PYTHONPATH=. ../.venv/bin/python -m pytest -q
```

Do not repeatedly run Azure/Oracle regressions after small edits.

## Dependencies

- Backend Developer 3 provides runtime/setup findings and reproducible failures.
- Backend Developer 2 provides API contract results and frontend bug reproductions.
- Frontend Developer provides browser workflow and build/console results.

## Stop / Escalation Conditions

- Stop before changing the frozen API, Oracle schema, compliance, scoring, or risk behavior.
- Stop if arbitrary-bidder or generalized production processing becomes necessary; it is out of scope.
- Require a reproducible failure before broad dependency or architecture changes.
- Escalate to Sol High for imported-PDF integration, difficult Azure/Oracle integration, or multi-module debugging.
- Use Astra only if a concrete blocker cannot be solved with Sol High. Never use Astra xhigh unless explicitly authorized.

## Model to Use

- Default: GPT-5.6 Sol Medium.
- Sol High: imported-PDF assessment integration, difficult Azure/Oracle work, or cross-module debugging.
- Astra: only for a concrete blocker Sol High cannot solve.
- Astra xhigh: do not use unless explicitly authorized.

## Token / Usage Strategy

- Reserve Codex for heavy backend reasoning, cross-module integration, difficult debugging, review, and the release gate.
- Do not spend Codex usage on formatting, simple documentation, repetitive tests, cosmetic frontend work, or manual smoke checks.
- Inspect targeted files, run focused tests first, and run live/full regressions once at the integration gate.
- Stop after P0–P2 acceptance criteria pass.

## Git Handoff Procedure

1. Work only on `dev/backend-integration`.
2. Keep heavy integration and runtime fixes in focused commits.
3. Review incoming backend PRs into `integration` before merging.
4. Update from `integration` before the final PR update when required.
5. Push and open a PR to `integration`; never push directly to `main`.
6. After final regression, the Tech Lead controls the `integration` to `main` release.
