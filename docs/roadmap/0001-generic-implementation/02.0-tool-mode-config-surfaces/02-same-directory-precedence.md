# 02 - Same-directory precedence

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete
**Depends on:** [01-unified-strict-schema.md](01-unified-strict-schema.md)

## Requirements

- When one directory holds both `flakeforge.toml` and a `pyproject.toml` that has
  `[tool.flakeforge]` (or the legacy section), `flakeforge.toml` wins (C3). Add a
  warning: `pyproject.toml [tool.flakeforge] is shadowed by flakeforge.toml; remove one`.
- Nearest directory wins. A `pyproject.toml [tool.flakeforge]` in a subdirectory
  beats a `flakeforge.toml` in a parent. Lock this in with a test, since it is
  already the behavior.
- A `pyproject.toml` *without* a flakeforge section never stops the upward search.
  That is today's behavior; keep it for monorepos whose sub-packages have their own
  `pyproject.toml`.
- `--config` accepts either file type. `--config pyproject.toml` without a section
  stays exit `2`.

## Files

- `src/flakeforge/config.py` - the shadow check in the `load_config()` discovery loop.
- `tests/test_config.py`.

## Acceptance

- The G6 reproduction prints exactly one shadow warning on stderr and exits based on
  the `flakeforge.toml` policy.
