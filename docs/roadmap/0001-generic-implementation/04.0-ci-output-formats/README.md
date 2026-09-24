# Task 04.0 - CI Output Formats

**Parent milestone:** [plan.md](../plan.md)
**Status:** ⬜ Not started (proposed)
**Depends on:** [01.0](../01.0-standalone-cli-mode/README.md)

## Scope

A standalone CLI is used mostly in CI. Add output formats that CI systems understand
natively, and a summary mode. Formats register in one formatter table in `api.py`, so
`output_format` validation (01.0/02) picks them up automatically.

## Subtasks

| #  | Document                                          | Status         | Blocks |
|----|---------------------------------------------------|----------------|--------|
| 01 | [Formatter registry](01-formatter-registry.md)    | ⬜ Not started | 02, 03 |
| 02 | [`github` and `sarif` formats](02-github-and-sarif.md) | ⬜ Not started | -      |
| 03 | [`--statistics`](03-statistics.md)                | ⬜ Not started | -      |

## Key constraints

- Every format keeps the C9 ordering and exit codes follow C1. No format may change
  what exit code a run produces.
