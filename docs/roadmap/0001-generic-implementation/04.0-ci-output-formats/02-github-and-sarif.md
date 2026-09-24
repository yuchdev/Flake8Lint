# 02 - `github` and `sarif` formats

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete
**Depends on:** [01-formatter-registry.md](01-formatter-registry.md)

## Requirements

- `github`: one `::error file={f},line={l},col={c+1},title={code}::{message}` line per
  violation, following the GitHub Actions workflow-command escaping rules. Columns
  are 1-based in the output (the engine uses 0-based `col_offset`).
- `sarif`: a SARIF 2.1.0 document with `tool.driver.name = "flakeforge"`, the version,
  one `rules[]` entry per registered code, and `results[]` with `artifactLocation.uri`
  relative to `base_dir`. It is built with the `json` stdlib only (C8).
- Both formats are valid on an empty result.

## Files

- `src/flakeforge/api.py`, `tests/test_api.py`. Include a golden-file test for the
  SARIF structure, and the escaping cases (`%`, `\r`, `\n`, `:`, `,`).
- A README CI section with a `github/codeql-action/upload-sarif` example.
