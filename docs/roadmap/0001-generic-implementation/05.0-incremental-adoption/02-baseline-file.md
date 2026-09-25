# 02 - Baseline file

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete
**Blocked on:** decision D2 (plan.md)

## Requirements

- `--write-baseline PATH` writes every current violation's fingerprint (D2) to a
  JSON file and exits `0`.
- `--baseline PATH` (TOML key `baseline`, resolved relative to `base_dir`) drops any
  violation whose fingerprint is in the file. Only new violations count toward exit `1`.
- A baseline entry that no longer matches anything is reported as "fixed", as a
  count in text output and a list in JSON, so the baseline can be shrunk. It never
  fails the run.
- A malformed baseline exits `2`.

## Files

- A new `src/flakeforge/baseline.py`, plus `api.py`, `cli.py`, `config.py`, and tests,
  including a line-shift test (insert lines above a violation → still suppressed).
