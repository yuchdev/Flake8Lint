# Changelog

## Unreleased

- Implement `X003` as a circular-import rule; the code is no longer reserved/disabled.
  Projects that previously carried `ignore = ["X003"]` now opt in by removing it.
- Add `ModuleImport`, `ModuleLocation` and `ModuleImportGraph` import-graph helpers to `flake8_lint.rules`.
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
