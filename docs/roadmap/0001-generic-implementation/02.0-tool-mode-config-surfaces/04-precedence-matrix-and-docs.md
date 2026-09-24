# 04 - Precedence matrix tests and docs

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [02](02-same-directory-precedence.md), [03](03-config-relative-paths.md)

## Requirements

- Add a parametrized test matrix over {no file, `flakeforge.toml`, `[tool.flakeforge]`,
  legacy, both files in the same directory, parent/child nesting} × {cwd inside,
  cwd outside, `--config`, `--no-config`}. Each case asserts which file was used, the
  effective `ignore`, and the exit code.
- Add a matching (smaller) matrix to the `wheel-smoke` job.
- README: merge the `pyproject.toml` and `flakeforge.toml` sections into one
  "Configuration" section. It needs the single key reference table (with the
  CLI-flag column from 01.0/02), the precedence rules C2/C3, the path rule C6, and
  "when to pick which file".

## Files

- `tests/test_config_precedence.py` (new), `.github/workflows/ci.yml`, `README.md`.

## Acceptance

- The matrix and `wheel-smoke` are green, and the README examples pass
  `tests/test_docs_smoke.py`.
