# 01 - `per_file_ignores`

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started

## Requirements

- New schema key `per_file_ignores`: a table mapping a glob to a list of code
  prefixes, e.g. `{"tests/**" = ["X002"], "scripts/*.py" = ["X0"]}`. Globs resolve
  against `base_dir` (C6), and codes are validated like `ignore`.
- CLI: a repeatable `--per-file-ignores "GLOB:CODE[,CODE]"` that replaces the file's table (C2).
- It is applied in `api.py` after rule execution and before `# noqa` handling.

## Files

- `src/flakeforge/config.py`, `src/flakeforge/api.py`, `src/flakeforge/cli.py`,
  `tests/test_api.py`, `tests/test_config.py`, README.
