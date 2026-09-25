# 03 - Unused `# noqa` report

**Parent task:** [README.md](README.md)
**Status:** ✅ Complete
**Blocked on:** decision D1 (plan.md)

## Requirements

- If D1 = (a): the engine emits built-in `X015` "unused `# noqa` directive" for a
  `# noqa` comment (bare or coded) that suppressed nothing in that run. This
  requires the full built-in lockstep: registry entry, a `rules.py` stub or
  engine-emitted registration, a `tests/samples/x015_*` sample, tests, README and docs.
- A coded `# noqa: CODE` naming a code that isn't registered is also an `X015`.
- It is suppressed automatically when `allow_noqa = false`, since every noqa is
  already ignored then.

## Files

- `src/flakeforge/api.py`, `src/flakeforge/registry.py`, `src/flakeforge/rules.py`,
  `tests/test_noqa.py`, `tests/samples/`, README.
