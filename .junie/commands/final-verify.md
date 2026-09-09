---
description: Run the old Claude stop-hook validation workflow before finishing a coding session.
---

Run the repository's explicit end-of-session verification flow.

Unless the user has said this is intentional work-in-progress, run these checks in order and stop on the first failure:

1. `uv run ruff check . --fix`
2. `uv run ruff check .`
3. `uv run pytest -q --cov=flake8_lint --cov-report=term-missing`

If Markdown changed, also run `/link-check` on the affected docs or the full documentation corpus as appropriate.

Report each command's result and treat any failure as blocking until it is fixed or explicitly waived by the user.