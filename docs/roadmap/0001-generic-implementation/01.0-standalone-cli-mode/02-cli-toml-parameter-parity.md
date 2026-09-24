# 02 - CLI ↔ TOML parameter parity

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [01-target-anchored-discovery.md](01-target-anchored-discovery.md)

## Requirements

- Every `check` option maps to exactly one config key, and every config key maps to a
  CLI option:

  | CLI                                       | TOML key         | Type / default        |
  |-------------------------------------------|------------------|-----------------------|
  | `--select`                                | `select`         | list[str] / `[]`      |
  | `--ignore`                                | `ignore`         | list[str] / `[]`      |
  | `--include` (03)                          | `include`        | list[str] / `[]`      |
  | `--exclude` (03)                          | `exclude`        | list[str] / `[]`      |
  | `--noqa` / `--no-noqa`                    | `allow_noqa`     | bool / `true`         |
  | `--rule-module`                           | `rule_modules`   | list[str] / `[]`      |
  | `--rule-plugins` / `--no-rule-plugins`    | `rule_plugins`   | bool / `true`  (new)  |
  | `--output-format`                         | `output_format`  | `"text"`/`"json"` / `"text"` (new) |
  | *(file-only)*                             | `noqa_allowed`, `noqa_forbidden` | list[str] / `[]` |

- Boolean flags use `argparse.BooleanOptionalAction`, so the CLI can override a
  file's value in either direction (C2). The existing `--no-noqa` and
  `--no-rule-plugins` spellings keep working.
- `output_format` and `rule_plugins` become fields of `LintConfig`. Validate
  `output_format` against the set of registered formatters (04.0 extends that set).
- `resolve_registry(include_entry_points=...)` reads the *merged* `rule_plugins`
  value, not the raw flag.
- `noqa_allowed` / `noqa_forbidden` stay file-only. Record that in the README table.

## Files

- `src/flakeforge/config.py` - new fields, parsing, `merge()`.
- `src/flakeforge/cli.py` - `BooleanOptionalAction` flags, format selection from the config.
- `tests/test_cli.py`, `tests/test_config.py` - one precedence test per new key
  (file only, CLI only, CLI overriding the file in both directions).

## Acceptance

- `flakeforge check --config ci.toml <dir>` with `output_format = "json"` and
  `rule_plugins = false` in `ci.toml` gives the same output as the equivalent flags.
