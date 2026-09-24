# 01 - Formatter registry

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- Replace the `text`/`json` branch in `cli.py` with a `FORMATTERS: dict[str,
  Callable[[LintResult], str]]` in `api.py`. The CLI `choices` and the config
  validation both read it.
- Add `"schema_version": 1` to the JSON output. This is additive, and existing keys
  are unchanged.

## Files

- `src/flakeforge/api.py`, `src/flakeforge/cli.py`, `tests/test_api.py`, `tests/test_cli.py`.
