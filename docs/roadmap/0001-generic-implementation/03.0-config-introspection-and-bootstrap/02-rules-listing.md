# 02 - `flakeforge rules`

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- `flakeforge rules` lists every registered rule in the resolved registry: code, short
  description, provider origin (`builtin`, `rule_module:<name>`, or
  `entry_point:<dist>`), and whether it is enabled under the effective `select`/`ignore`.
- It supports `--output-format json`.
- It reuses `resolve_registry()` exactly as `check` does, including `rule_plugins` and
  project-root imports.

## Files

- `src/flakeforge/cli.py`, and `src/flakeforge/registry.py` if a provider origin has
  to be recorded on `RuleRegistration`. That is an extension-surface change, so
  update `tests/test_custom_rules.py` too.
- `tests/test_cli.py`.
