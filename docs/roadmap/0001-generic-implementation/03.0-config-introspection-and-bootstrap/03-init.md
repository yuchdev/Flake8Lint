# 03 - `flakeforge init`

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- `flakeforge init [DIR]` writes `DIR/flakeforge.toml` with every schema key at its
  default, one comment line per key.
- `flakeforge init --pyproject [DIR]` appends a `[tool.flakeforge]` table to
  `DIR/pyproject.toml`.
- It refuses to overwrite or duplicate: if the target file already exists, or already
  has either section, it exits `2` with a message. `--force` is out of scope.
- Output is rendered from a template string with no TOML writer dependency (C8). A
  test round-trips it through `tomllib` and `load_config()`.

## Files

- `src/flakeforge/cli.py`, with the template in `src/flakeforge/config.py` next to the schema.
- `tests/test_cli.py`.
