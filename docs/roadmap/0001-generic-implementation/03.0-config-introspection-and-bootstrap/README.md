# Task 03.0 - Config Introspection & Bootstrap

**Parent milestone:** [plan.md](../plan.md)
**Status:** ✅ Complete
**Depends on:** [02.0](../02.0-tool-mode-config-surfaces/README.md)

## Scope

Once two config surfaces, a discovery anchor, and CLI overrides all interact, users
need a way to ask "what is actually in effect, and why?" This task adds three
read-mostly subcommands that reuse the existing core without changing it.

## Subtasks

| #  | Document                                      | Status         | Blocks |
|----|-----------------------------------------------|----------------|--------|
| 01 | [`config show`](01-config-show.md)            | ✅ Complete    | -      |
| 02 | [`rules` listing](02-rules-listing.md)        | ✅ Complete    | -      |
| 03 | [`init`](03-init.md)                          | ✅ Complete    | -      |

## Key constraints

- Each subcommand accepts the same `--config` / `--no-config` / path-anchor arguments
  as `check` (via a shared parent parser), so what it reports is exactly what `check`
  would use.
- Exit codes follow C1: a successful report exits `0`, and invalid config exits `2`.
