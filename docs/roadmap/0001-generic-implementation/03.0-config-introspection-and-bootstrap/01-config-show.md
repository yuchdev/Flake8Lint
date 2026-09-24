# 01 - `flakeforge config show`

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- `flakeforge config show [PATH ...] [--config F | --no-config] [check overrides...]`
  prints the effective, validated config:
  - the source file and section (or `defaults`), the discovery anchor, and `base_dir`;
  - every schema key with its value and its origin (`default` / `file` / `cli`).
- `--output-format json` gives a stable, `sort_keys` JSON document.
- Warnings (legacy section, shadowed file) are printed to stderr as `check` does.

## Files

- `src/flakeforge/cli.py`. Origin tracking goes in a small helper in `config.py`.
  Don't add the tracking to `LintConfig` equality.
- `tests/test_cli.py`.
