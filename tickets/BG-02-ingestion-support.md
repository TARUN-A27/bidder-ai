# BG-02 — Ingestion Support

Owner: Developer 2  
Branch: `dev/backend-ingestion`  
Status: READY

## Goal

Maintain and improve bidder ZIP and folder/multi-file ingestion.

## Tasks

- Support ZIP import.
- Support multi-file and folder-style upload.
- Validate PDFs and preserve SHA256 hashes.
- Fix ingestion bugs.
- Support deterministic document classification.
- Resolve approved storage issues.

## Allowed Area

Backend ingestion services, ingestion schemas and APIs, submission/document repositories, storage handling, and ingestion tests.

## Do Not Change

- Compliance or scoring engines.
- Risk behavior.
- Frontend code.
- Oracle schema unless the Tech Lead approves a demonstrated blocker.

## Tests / Verification

- Run `python scripts/test_bidder_ingestion.py` when integration dependencies are available.
- Run ingestion-related pytest tests.
- Verify ZIP safety, PDF validation, hashing, cleanup, and duplicate handling for changed behavior.

## Done When

- ZIP and multi-file ingestion work for the assigned change.
- Storage and database metadata remain consistent.
- Relevant ingestion and pytest tests pass.

## Final Report Required

Report:

1. Ticket ID
2. Files created
3. Files modified
4. Tests run
5. Test result
6. Known issues
7. Commit hash
