# BG-05 — QA

Owner: Developer 5  
Branch: `dev/qa`  
Status: READY

## Goal

Test the complete BidGuard flow and catch regressions without rewriting core logic.

## Tasks

- Test Bidder A, B, and C.
- Test ZIP and multi-file upload/import.
- Test assessment and comparison flows.
- Test expected error cases.
- Add end-to-end or regression tests where useful.
- Report bugs with reproducible steps.

Known benchmarks:

- A: `100.0 / LOW`, 21 PDFs.
- B: `80.5 / HIGH`, 21 PDFs, EPFO contribution failure.
- C: `34.0 / CRITICAL`, 19 PDFs, missing OEM authorization, GST cancellation, PAN mismatch, 32% local content, and active debarment.

## Allowed Area

QA scripts, tests, test documentation, bug reports, and approved test-support code.

## Do Not Change

- Compliance or scoring behavior to make tests pass.
- Risk behavior or override IDs.
- Expected-result fixtures.
- Synthetic dataset files.
- Core application logic without a separately approved fix ticket.

## Tests / Verification

- Run relevant end-to-end and regression scripts.
- Run `PYTHONPATH=. pytest -q` from `backend`.
- Verify the known A/B/C benchmarks and controlled failure cases.

## Done When

- A/B/C and upload, assessment, comparison, and error flows are covered.
- Regressions have reproducible reports.
- Added QA tests pass without altering expected core behavior.

## Final Report Required

Report:

1. Ticket ID
2. Files created
3. Files modified
4. Tests run
5. Test result
6. Known issues
7. Commit hash
