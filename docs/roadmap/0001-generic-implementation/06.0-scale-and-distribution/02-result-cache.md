# 02 - Result cache

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [01-parallel-checking.md](01-parallel-checking.md)

## Requirements

- The cache is opt-in: `--cache-dir PATH` (TOML key `cache_dir`, relative to `base_dir`).
- The per-file key is `sha256(file bytes) + config fingerprint + registry fingerprint
  (codes + provider versions) + flakeforge version`. Any mismatch → re-check the file.
- Rules whose result depends on other files (X003 today) are never served from the
  cache; they always re-run. A per-registration `cacheable` flag defaults to `True`
  for custom rules. That is an extension-surface change, so update
  `tests/test_custom_rules.py` and `docs/custom-rules.md`.
- A corrupt or unreadable cache is ignored with a warning. It never causes exit `2`
  and never hides a violation (plan risk marker).
- Add `--no-cache` to override the file setting.

## Files

- A new `src/flakeforge/cache.py`, plus `api.py`, `cli.py`, `config.py`, and tests
  (cold vs. warm give identical output, and editing a file invalidates its entry).
