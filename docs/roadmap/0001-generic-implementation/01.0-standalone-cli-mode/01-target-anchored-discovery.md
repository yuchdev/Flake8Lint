# 01 - Target-anchored discovery

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete

## Requirements

- When `--config` is not given, config discovery starts at the **discovery anchor**
  (plan contract C4), not at cwd:
  - no path arguments → cwd (current behavior);
  - one path → that directory, or the parent directory if the path is a file;
  - several paths → their deepest common ancestor directory (`os.path.commonpath`
    after `resolve()`).
- Add a pure helper `discovery_anchor(paths, *, cwd) -> Path` in `config.py` and pass
  its result as `load_config(cwd=...)`. `cli.py` just calls the helper.
- The public `lint_paths()` / `load_config()` signatures stay unchanged. The new
  helper is exported for API callers that want the CLI's behavior.
- A missing path argument is still exit `2` with a `flakeforge: ...` message on stderr.

## Files

- `src/flakeforge/config.py` - `discovery_anchor()`.
- `src/flakeforge/cli.py` - `_build_cli_config()` uses the anchor.
- `tests/test_config.py`, `tests/test_cli.py` - anchor unit tests, and a CLI test that
  runs from a cwd *outside* a project holding `flakeforge.toml` with `ignore = ["X001"]`.

## Acceptance

- The G1 reproduction (`cd /elsewhere && flakeforge check /path/proj`) honors
  `proj/flakeforge.toml`.
- Running from inside the project gives byte-identical results before and after the change.
