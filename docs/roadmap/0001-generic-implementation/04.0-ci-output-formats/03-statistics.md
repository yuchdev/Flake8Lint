# 03 - `--statistics`

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [01-formatter-registry.md](01-formatter-registry.md)

## Requirements

- `--statistics` (TOML key `statistics`, bool) adds a per-code count summary after the
  text output: `X001  3  Do not use bare except...`. In JSON it adds a `statistics`
  object.
- It is ignored for `github`/`sarif`, with a warning.

## Files

- `src/flakeforge/api.py`, `src/flakeforge/cli.py`, `src/flakeforge/config.py` (a schema entry), tests.
