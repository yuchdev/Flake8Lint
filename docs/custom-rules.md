# Custom Rules

## Public rule interface

Custom rules follow the shared engine contract:

```python
from collections.abc import Iterable
from flake8_lint.api import Rule, RuleContext, RuleViolation


class MyRule:
    code = "ORG001"
    description = "Example custom rule"

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        return ()
```

## RuleContext

`RuleContext` provides the parsed AST, filename, and optional source text used for `# noqa` filtering.

## RuleViolation

Every built-in and custom rule returns the same `RuleViolation` dataclass.

## RuleRegistry

Providers register rules explicitly:

```python
from flake8_lint.registry import RuleRegistry


def register_rules(registry: RuleRegistry) -> None:
    registry.register(MyRule(), provider="my_project.lint_rules")
```

Rule codes must be unique. Duplicate codes fail clearly instead of using last-writer-wins behavior.

## Project-local modules

Configure project-local modules in `pyproject.toml` or `flake8_lint.toml`:

```toml
[tool.flake8_lint]
rule_modules = ["my_project.lint_rules"]
```

## Packaged provider entry points

Reusable provider packages should expose an entry point in the `flake8_lint.rules` group:

```toml
[project.entry-points."flake8_lint.rules"]
my_rules = "my_rules_package:register_rules"
```

## select/ignore interaction

`select` and `ignore` apply equally to built-in and custom codes. `ignore` wins when both match.

## noqa interaction

`# noqa` handling is shared across all rules. `allow_noqa`, `noqa_allowed`, and `noqa_forbidden` are resolved in the core engine, not in integrations.

## Testing guidance

Prefer unit tests around `check_tree()`, `check_file()`, `lint_paths()`, and registry loading for custom providers. Update `tests/test_custom_rules.py` when changing extension contracts.

## Compatibility and versioning

Task 0001 establishes the extension surface. Task 0002 will harden the implementation details and validate documented examples against the first working release.
