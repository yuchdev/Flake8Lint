# 01 - Unified strict schema

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- Define the config schema once, as a module-level mapping of key → (coercer,
  default). `LintConfig.from_mapping()` is driven by that mapping, and both surfaces
  go through it (C5). Adding a key in a later task (`per_file_ignores`, `jobs`,
  `cache_dir`) is a one-line schema entry.
- Unknown keys raise `ConfigValidationError`. The error names the source file, the
  section (`flakeforge.toml` or `[tool.flakeforge]`), the key, and a did-you-mean hint
  from `difflib.get_close_matches`. Example:
  `flakeforge.toml: unknown key 'exlude' (did you mean 'exclude'?)`.
- Type errors carry the same file/section prefix.
- Legacy `[tool.flake8_lint]`: an unknown key is appended to `warnings` instead of raising.
- Also accept `flakeforge.toml` wrapped as `[tool.flakeforge]`, so a snippet can be
  copied between the two files. If the file has both top-level keys and the wrapper
  table, that's an error.

## Files

- `src/flakeforge/config.py`.
- `tests/test_config.py` - unknown key (strict and legacy), did-you-mean, type-error
  message, and wrapped-vs-flat `flakeforge.toml` equivalence.

## Acceptance

- The G5 reproduction (`exlude = [...]`) exits `2` with the hint on stderr.
