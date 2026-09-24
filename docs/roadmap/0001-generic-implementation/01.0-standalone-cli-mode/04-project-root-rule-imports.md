# 04 - Project-root rule imports 🔒

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Security:** requires a `security-auditor` pass (plan contract C7)

## Requirements

- While `resolve_registry()` imports **project-local** `rule_modules`, put the loaded
  config's `base_dir` first on `sys.path`. Use a context manager that restores the
  previous `sys.path` exactly, even when an import raises.
- Entry-point providers are **not** affected. They resolve through installed metadata.
- The `base_dir` passed in must be the resolved config directory, never a raw path
  argument. `--no-config` passes none (03).
- A failing import stays a `RuleProviderLoadError` → exit `2`. The message names the
  module and `base_dir`.
- `docs/custom-rules.md` gains a "Trust boundary" note: running `flakeforge` on a
  repository executes the modules listed in that repository's `rule_modules`. Use
  `--no-config` on untrusted checkouts.

## Files

- `src/flakeforge/registry.py` - a `project_root` parameter on `resolve_registry()`
  and the `sys.path` context manager.
- `src/flakeforge/cli.py`, `src/flakeforge/api.py` - pass `config.base_dir` through.
- `tests/test_custom_rules.py` - import from a project that isn't installed, run from
  another cwd, and assert that `sys.path` is restored after both success and failure.
- `docs/custom-rules.md`.

## Acceptance

- A `flakeforge` console script installed into an isolated venv loads
  `my_project.lint_rules` from the target project without the project being installed.
