# 03 - pre-commit hook

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started

## Requirements

- Add `.pre-commit-hooks.yaml` at the repo root with an `id: flakeforge` hook:
  `entry: flakeforge check`, `language: python`, `types: [python]`,
  `require_serial: false`. pre-commit passes the staged file paths, and the anchor
  rule (C4) finds the project config from them.
- README: a "pre-commit" section with a `.pre-commit-config.yaml` snippet pinned to a
  release tag.
- Verify the hook with a `wheel-smoke` step that runs `pre-commit try-repo .` on a
  fixture repo. pre-commit is installed only in that CI job, so no YAML dependency
  is added to the package or the test suite (C8).

## Files

- `.pre-commit-hooks.yaml`, `README.md`, `.github/workflows/ci.yml`.
