---
description: Recreate the old Claude session-start briefing for this repository.
---

Build a short working brief for the current repository state.

- Read `.junie/AGENTS.md` first.
- Summarize the current branch, uncommitted changes, and the most recent commits.
- If the task mentions a GitHub issue or PR, inspect that context too.
- Highlight likely quality gates for the touched area.
- Call out any risky paths from the repo policy, especially `.env`, `.env.*`, `*.dmp`, and `prototype/*.db`.

Return a concise session brief the user can act on immediately.