# 05 - Standalone smoke tests and docs

**Parent task:** [README.md](README.md)
**Status:** ⬜ Not started
**Depends on:** [02](02-cli-toml-parameter-parity.md), [03](03-isolated-mode-and-path-flags.md), [04](04-project-root-rule-imports.md)

## Requirements

- Extend the `wheel-smoke` job in `.github/workflows/ci.yml`. From a cwd *outside*
  the fixture project, assert exit codes and output for:
  1. `flakeforge check <proj>`: the target's `flakeforge.toml` is honored (G1);
  2. `flakeforge check --config <file.toml> <proj>`: a CLI-parameters-only config file
     (`output_format`, `rule_plugins`, `select`) is honored (G2);
  3. `flakeforge check --no-config <proj>`: the project config is ignored (03);
  4. a project-local `rule_modules` loads from a project that isn't installed (G4).
- README: a new "Standalone CLI" section with a worked example of a CLI-parameters
  config file, the CLI ↔ TOML table from 02, and the C3/C4 rules.
- `docs/architecture.md`: the discovery anchor in the config/discovery layer.

## Files

- `.github/workflows/ci.yml`, `README.md`, `docs/architecture.md`.
- `tests/test_docs_smoke.py`: keep it in step with the new README examples.

## Acceptance

- The `wheel-smoke` job is green on CI, and `/link-check` is clean.
