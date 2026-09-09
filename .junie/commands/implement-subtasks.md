---
description: Drive one roadmap task to completion using the repository's existing subtask loop rules.
---

Drive one roadmap task to completion, implementing exactly one subtask per run.

Target task: `$ARGUMENTS`

Accepted task forms:

- `0001/1.0` or `0001 1.0`
- `1.0`
- a task title substring

Use this workflow:

1. Resolve the task unambiguously from `docs/roadmap/{NNNN}-*/plan.md`. If zero or multiple tasks match, stop and ask.
2. Gate on the milestone `status.md`. If the task is already complete, verify it instead of rebuilding it.
3. Read the task `README.md` subtask queue and pick the next pending subtask only.
4. Implement exactly one subtask.
5. Run the relevant verification and quality gates for that subtask.
6. Update the task records to reflect the finished subtask.
7. Report the new state, the next pending subtask, and whether this command should be run again.

Never batch multiple subtasks into one run, and never guess through ambiguous milestone or task resolution.