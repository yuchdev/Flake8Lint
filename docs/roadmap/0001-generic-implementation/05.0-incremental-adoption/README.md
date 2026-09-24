# Task 05.0 - Incremental Adoption

**Parent milestone:** [plan.md](../plan.md)
**Status:** ⬜ Not started (proposed)
**Depends on:** [02.0](../02.0-tool-mode-config-surfaces/README.md)

## Scope

Let an existing codebase adopt `flakeforge` without fixing every violation on day one,
and keep suppressions honest over time.

## Subtasks

| #  | Document                                        | Status         | Blocks |
|----|-------------------------------------------------|----------------|--------|
| 01 | [`per_file_ignores`](01-per-file-ignores.md)    | ⬜ Not started | -      |
| 02 | [Baseline file](02-baseline-file.md)            | ⬜ Not started | -      |
| 03 | [Unused `# noqa` report](03-unused-noqa.md)     | ⬜ Not started | -      |

## Key constraints

- Suppression stays engine-owned in `api.py` (repo convention). Rules never see
  per-file ignores, baselines, or noqa state.
- 02 needs decision D2 and 03 needs decision D1 ratified first (plan.md).
