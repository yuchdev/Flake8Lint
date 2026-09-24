# Task 02.0 - Tool-Mode Config Surfaces

**Parent milestone:** [plan.md](../plan.md)
**Status:** ✅ Complete
**Depends on:** [01.0](../01.0-standalone-cli-mode/README.md)

## Scope

Make project setup through `pyproject.toml [tool.flakeforge]` and through a separate
`flakeforge.toml` behave the same way, and make them fail loudly. The two surfaces
share one strict schema (C5), follow a documented precedence when both exist (C3),
and resolve paths against their own directory (C6). `flakeforge.toml` works for both
auto-discovered tool mode and `--config` in CLI mode (01.0), with the same meaning in
each. Fixes baseline gaps G5-G7 in [plan.md](../plan.md#baseline-as-built-2026-09-24).

## Subtasks

| #  | Document                                                         | Status         | Blocks |
|----|------------------------------------------------------------------|----------------|--------|
| 01 | [Unified strict schema](01-unified-strict-schema.md)             | ✅ Complete    | 02, 03 |
| 02 | [Same-directory precedence](02-same-directory-precedence.md)     | ✅ Complete    | 04     |
| 03 | [Config-relative path semantics](03-config-relative-paths.md)    | ✅ Complete    | 04     |
| 04 | [Precedence matrix tests and docs](04-precedence-matrix-and-docs.md) | ✅ Complete    | -      |

## Key constraints

- `config.py` still doesn't print anything. Warnings go into `LintConfig.warnings`,
  and the CLI surfaces them.
- The legacy `[tool.flake8_lint]` section stays accepted and lenient (C5).
- Configs that are valid today must load unchanged. The only new errors are for
  unknown keys and wrong value types.
