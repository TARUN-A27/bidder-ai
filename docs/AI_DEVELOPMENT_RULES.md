# AI Development Rules

These rules apply when using any AI coding assistant on BidGuard AI.

1. Read the assigned ticket completely before editing.
2. Inspect the current code before making changes.
3. Implement only the assigned task.
4. Do not redesign unrelated components.
5. Do not modify compliance, scoring, recommendation, or risk behavior unless the ticket explicitly requires it.
6. Never use `expected_result.json` as runtime input.
7. Never print or expose `.env` credentials or other secrets.
8. Never modify synthetic dataset fixtures.
9. Run the tests required by the ticket.
10. Do not claim a test passed unless it was actually run successfully.
11. Report every file created or modified.
12. Report known issues honestly.
13. Preserve backward compatibility where possible.
14. Do not commit secrets, local credentials, generated caches, or private environment files.
15. Stop when the ticket is complete.
