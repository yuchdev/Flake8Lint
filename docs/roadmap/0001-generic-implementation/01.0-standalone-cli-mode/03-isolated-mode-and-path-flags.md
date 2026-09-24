# 03 - Isolated mode and path flags

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [01-target-anchored-discovery.md](01-target-anchored-discovery.md)

## Requirements

- `--include PATTERN` / `--exclude PATTERN` (repeatable, comma-splittable like
  `--select`) **replace** the file's lists (C2).
- `--no-config` skips discovery entirely: defaults plus CLI flags only, with patterns
  resolved against the discovery anchor (C6). `--config` and `--no-config` together
  → exit `2`.
- `--no-config` also means no project-local `rule_modules` are loaded (C7).
  Entry-point providers still follow `rule_plugins`.

## Files

- `src/flakeforge/cli.py` - flags and the mutual-exclusion group.
- `src/flakeforge/config.py` - a `LintConfig(base_dir=anchor)` path for isolated mode.
- `tests/test_cli.py` - an isolated run that ignores a hostile `flakeforge.toml`, and
  include/exclude override tests.

## Acceptance

- In a directory whose `flakeforge.toml` sets `ignore = ["X"]`,
  `flakeforge check --no-config --select X001 .` reports X001.
