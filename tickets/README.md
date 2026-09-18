# BidGuard AI Tickets — Today's Four-Person Hackathon Team

## Active Allocation

| Developer | Ticket | Branch | Primary ownership |
|---|---|---|---|
| Tarun / Tech Lead / Backend Lead | BG-01 | `dev/backend-integration` | Heavy backend, imported-PDF assessment integration, architecture, difficult Oracle/Azure/runtime blockers, review, final regression, release gate |
| Backend Developer 3 | BG-02 | `dev/backend-ingestion` | Runtime/setup, demo operations, import/API smoke QA, simple setup documentation |
| Backend Developer 2 | BG-03 | `dev/backend-api` | Frozen API tests, small router/schema fixes, curl examples, frontend support |
| Frontend Developer | BG-04 | `dev/frontend` | Procurement Officer UI, real API integration, browser/build/console QA |

There is no dedicated QA developer today. BG-05 documents distributed QA; `dev/qa` is inactive.

## Today's Rules

1. Read the assigned ticket before editing.
2. Work only within its allowed files and branch.
3. Stop and report work crossing a prohibited boundary.
4. Treat `docs/API_CONTRACT.md` as frozen.
5. Preserve A `100.0 / LOW`, B `80.5 / HIGH`, and C `34.0 / CRITICAL`.
6. Never use `expected_result.json` in runtime code or modify benchmark fixtures.
7. Never expose `.env`, credentials, or secrets.
8. Run focused tests first and report results honestly.
9. Commit, push the assigned branch, and open a PR to `integration`.
10. Do not push directly to `integration` or `main`.
11. Tarun reviews backend PRs, controls merges, runs final regression, and owns release.
12. Stop when assigned acceptance criteria are met.

## Execution Order

1. Backend Developer 3 validates runtime while Backend Developer 2 begins contract tests and Frontend builds the vertical slice.
2. Tarun implements imported-PDF assessment integration and resolves difficult blockers.
3. Backend Developer 2 supports live frontend integration; Backend Developer 3 runs smoke checks.
4. Tarun reviews and merges backend work, then runs final A/B/C regression.
5. Tarun and Frontend complete the browser rehearsal before release.
