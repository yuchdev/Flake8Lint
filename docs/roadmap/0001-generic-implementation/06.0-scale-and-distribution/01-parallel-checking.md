# 01 - Parallel checking

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started

## Requirements

- `--jobs N` (TOML key `jobs`, int ≥ 0, default `1`; `0` = `os.cpu_count()`) checks
  files in a `concurrent.futures.ProcessPoolExecutor`.
- Workers rebuild the registry from `(rule_modules, rule_plugins, base_dir)`, not by
  pickling rule callables.
- Results are merged and sorted per C9.
- A worker crash is exit `2`, and the error names the file.
- X003 (circular imports) runs per file but reads sibling modules from disk
  (`build_import_graph` in `rules.py`). That is safe across workers because it is
  read-only, but it means an X003 result depends on files other than the one being
  checked. See 02 for what that means for caching.

## Files

- `src/flakeforge/api.py`, `src/flakeforge/cli.py`, `src/flakeforge/config.py`, and
  `tests/test_api.py` (determinism: `--jobs 1` vs `--jobs 4` give identical JSON).
