# 03 - Config-relative path semantics

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete
**Depends on:** [01-unified-strict-schema.md](01-unified-strict-schema.md)

## Requirements

- Every path pattern in a config file resolves against that file's directory
  (`base_dir`), whether the file was discovered or passed with `--config`, and
  whatever the cwd is (C6).
- Explicit path arguments stay cwd-relative. They are what the user typed.
- Display names are relative to `base_dir` when the file sits under it; otherwise
  they are shown as given. This fixes G7. Use the same rule in `api.py`'s
  `_display_filename()` and in `# noqa` path policy matching.
- `noqa_allowed` / `noqa_forbidden` matching uses the same base-relative path as
  `include` / `exclude`.

## Files

- `src/flakeforge/api.py`, `src/flakeforge/discovery.py`.
- `tests/test_api.py`, `tests/test_discovery.py`, `tests/test_noqa.py`: running with
  `--config` from cwd = `/` and from a sibling directory gives identical, base-relative
  output.

## Acceptance

- The G7 reproduction prints `pkg/m.py:3:0: ...`.
