# Changelog

## Unreleased

- **Renamed the project from `flake8-lint` to `flakeforge`** (package, CLI command, canonical
  config section, custom-rule entry-point group). The name was easy to mistake for `flake8`
  itself rather than an extension of it; renaming now, before wider adoption, keeps the cost
  low. `[tool.flake8_lint]` is accepted as a deprecated fallback for `[tool.flakeforge]`, the
  same way `[tool.flake8_lint_tests]` was accepted before this rename (and is now retired).
- Implement `X003` as a circular-import rule; the code is no longer reserved/disabled.
  Projects that previously carried `ignore = ["X003"]` now opt in by removing it.
- Add `ModuleImport`, `ModuleLocation` and `ModuleImportGraph` import-graph helpers to `flakeforge.rules`.
- Add built-in `X013` (require `subprocess.Popen`/`socket.socket` to be used as a context manager).
- Add built-in `X014` (enforce tracked `TODO`/`FIXME` comment metadata).

## 1.0.0

- Extract existing AST lint rules into reusable `flake8-lint` package.
- Add standalone `flake8-lint check` CLI.
- Support `pyproject.toml` and `flake8_lint.toml` configuration.
- Preserve X001-X012 codes and reserved X003.
- Add missing X012 test coverage.
- Add configurable `# noqa` policy.
- Add thin Flake8 adapter.
- Add explicit pytest helper without automatic repository scanning.
- Add project-local custom rule modules.
- Add installed custom-rule provider entry points.
- Add custom-rule authoring documentation.
