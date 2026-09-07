# Architecture

`flake8-lint` keeps the production rule engine independent from CLI argument parsing, project discovery policy, Flake8 internals, and pytest integration details.

```text
                  +---------------------------+
                  |   rules + registry        |
                  |   shared execution core   |
                  +-------------+-------------+
                                |
        +-----------------------+------------------------+
        |                       |                        |
        v                       v                        v
  config + discovery       standalone API/CLI      Flake8 + pytest
  path policy              orchestration           thin integrations
```

## Core rules / registry

- `flake8_lint.rules` defines the built-in X001–X012 rules.
- `flake8_lint.registry` owns registration, duplicate detection, rule-code validation, and provider loading.
- Built-in rules are registered through the same registry mechanism used by custom rules.
- `X003` is kept in the authoritative registry as known but disabled/reserved.

That shared registration path matters because extension behavior should exercise the real engine path instead of a separate bolt-on custom-rule system.

## Config

`flake8_lint.config` owns:

- typed config parsing
- discovery precedence for `--config`, `flake8_lint.toml`, canonical `pyproject.toml`, legacy `pyproject.toml`, and defaults
- legacy migration metadata and warnings
- rule-selector validation against the resolved registry

Config parsing does not print warnings directly. Integrations choose whether to surface warnings.

## Custom provider loading

`flake8_lint.registry.resolve_registry()` builds one resolved registry from:

1. built-in rules
2. configured project-local `rule_modules`
3. installed `flake8_lint.rules` entry points, unless disabled

Provider loading is deterministic. Duplicate codes and invalid codes fail fast. Import and provider registration failures are surfaced as tool/configuration errors instead of being silently ignored.

## Discovery

`flake8_lint.discovery` owns:

- recursive Python file traversal
- include/exclude path filtering
- default cache/build/virtualenv directory skipping
- stable ordering and duplicate removal

The discovery layer is intentionally filesystem-focused. It does not parse rule logic or format output.

## API runner

`flake8_lint.api` owns the reusable orchestration surface:

- `check_tree()`
- `check_file()`
- `check_source()`
- `lint_paths()`
- structured `RuleViolation` and `LintResult`

The API is the shared execution boundary. It validates config selectors against the resolved registry, runs built-in and custom rules in deterministic order, and applies the common `# noqa` semantics.

## CLI

`flake8_lint.cli` is a thin integration over the API:

- parses command-line options
- loads config with precedence rules
- resolves providers
- emits text or JSON output
- maps outcomes to exit codes `0`, `1`, and `2`

The CLI is responsible for warning presentation, not low-level modules.

## Flake8 adapter

`flake8_lint.plugin.ProjectRulesPlugin` is a thin AST adapter:

- reuses the shared engine for built-in diagnostics
- maps Flake8 select/ignore and disable-noqa options into engine config
- intentionally keeps installed external provider discovery authoritative in the standalone CLI/API

That boundary avoids over-claiming support for provider-loading behavior that Flake8 itself does not own.

## pytest helper

`flake8_lint.testing.assert_lint_clean()` is explicit opt-in:

- it calls the shared API
- it formats failures for assertions
- it does not auto-register linting during ordinary `pytest`

Recommended CI remains separate lint and test steps so test suites can still run when lint finds violations.
