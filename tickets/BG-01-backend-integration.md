# BG-01 — Backend Integration

Owner: Tech Lead  
Branch: `dev/backend-integration`  
Status: READY

## Goal

Keep backend integration stable and resolve Oracle, API, service, or cross-module integration issues.

## Tasks

- Review backend integration changes.
- Fix approved integration problems.
- Ensure the assessment pipeline remains stable.
- Support merges from backend developers.
- Run regression tests when needed.

## Allowed Area

Backend integration, repository, service, and API areas approved by the Tech Lead.

## Do Not Change

- Compliance rule semantics without an explicit reason and approval.
- Scoring rules or risk override IDs.
- Synthetic dataset fixtures.
- Unrelated frontend code.

## Tests / Verification

- Run relevant backend integration tests.
- Run the full backend regression suite before an integration release when practical.
- Confirm Oracle and assessment API behavior for affected flows.

## Done When

- The integration branch remains stable.
- Relevant backend regressions pass.
- Approved backend changes can be merged without unresolved integration failures.

## Final Report Required

Report:

1. Ticket ID
2. Files created
3. Files modified
4. Tests run
5. Test result
6. Known issues
7. Commit hash
