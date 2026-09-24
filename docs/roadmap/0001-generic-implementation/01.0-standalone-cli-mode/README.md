# Task 01.0 - Standalone CLI Mode

**Parent milestone:** [plan.md](../plan.md)
**Status:** ✅ Complete

## Scope

Make `flakeforge` a 100% standalone CLI tool. `flakeforge check <target-dir>` must give
the same result whatever the cwd and whether the tool is installed in the project's
venv or with `pipx`/`uvx`. One TOML file passed with `--config` must be able to hold
every CLI parameter, and the CLI alone (with `--no-config`) must be able to express
every setting in that file. Fixes baseline gaps G1-G4 in [plan.md](../plan.md#baseline-as-built-2026-09-24).

## Subtasks

| #  | Document                                                        | Status         | Blocks |
|----|-----------------------------------------------------------------|----------------|--------|
| 01 | [Target-anchored discovery](01-target-anchored-discovery.md)    | ✅ Complete    | 02, 03 |
| 02 | [CLI ↔ TOML parameter parity](02-cli-toml-parameter-parity.md)  | ✅ Complete    | 05     |
| 03 | [Isolated mode and path flags](03-isolated-mode-and-path-flags.md) | ✅ Complete    | 05     |
| 04 | [Project-root rule imports](04-project-root-rule-imports.md) 🔒 | ✅ Complete    | 05     |
| 05 | [Standalone smoke tests and docs](05-standalone-smoke-and-docs.md) | ✅ Complete    | -      |

🔒 = security-sensitive and needs a `security-auditor` pass (plan contract C7).

## Key constraints

- Exit codes are frozen (C1). Value precedence follows C2, file selection C3, and the
  anchor C4.
- No new runtime dependencies (C8).
- `cli.py` stays thin. Discovery-anchor logic belongs in `config.py`, and path
  resolution in `api.py`/`discovery.py`.
