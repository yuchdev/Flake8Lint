# Task 06.0 - Scale & Distribution

**Parent milestone:** [plan.md](../plan.md)
**Status:** ⏸ Deferred (see [status.md](../status.md#notes--decisions))
**Depends on:** [01.0](../01.0-standalone-cli-mode/README.md), [04.0](../04.0-ci-output-formats/README.md)

## Scope

Make the standalone CLI fast on large repositories and trivial to wire into
developer workflows.

## Subtasks

| #  | Document                                    | Status         | Blocks |
|----|---------------------------------------------|----------------|--------|
| 01 | [Parallel checking](01-parallel-checking.md) | ⬜ Not started | 02     |
| 02 | [Result cache](02-result-cache.md)          | ⬜ Not started | -      |
| 03 | [pre-commit hook](03-pre-commit-hook.md)    | ⬜ Not started | -      |

## Key constraints

- The output must be byte-identical for every `--jobs` value and with the cache cold
  or warm (C9).
