---
description: Drive an entire roadmap milestone using the repository's existing milestone loop rules.
---

Drive one roadmap milestone to completion, one verified subtask at a time.

Target milestone: `$ARGUMENTS`

Accepted milestone forms:

- `0002`
- `0002-example-slug` or `example-slug`
- a milestone title substring

Use this workflow:

1. Resolve the milestone folder under `docs/roadmap/` and stop if the match is ambiguous or lacks `plan.md`.
2. Research the milestone before execution: tasks, dependency order, shared contracts, and exit gates.
3. Use `status.md` as the source of truth for current progress.
4. Pick the next eligible task whose dependencies are satisfied.
5. Run that task through the subtask workflow, still implementing exactly one subtask this run.
6. Update milestone status after the subtask closes.
7. Report the current task, next pending subtask, and whether the milestone needs another run.

Do not jump ahead of dependency order, and stop to ask whenever scope, resolution, or required decomposition is unclear.