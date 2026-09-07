# Architecture

`flake8-lint` keeps the rule engine independent from its integrations.

```text
                    +-----------------------+
                    |   rules + registry    |
                    |   reusable core API   |
                    +-----------+-----------+
                                |
         +----------------------+----------------------+
         |                      |                      |
         v                      v                      v
   standalone runner       Flake8 adapter        pytest helper
   and CLI                  thin integration      explicit opt-in
```

Key decisions for Task 0001:

- `flake8_lint.api` owns the authoritative public result types and engine entry points.
- `flake8_lint.registry` resolves built-in rules plus explicit provider registration hooks.
- `flake8_lint.plugin` adapts Flake8's AST plugin interface to the shared engine and built-in registry.
- `flake8_lint.testing` is explicit opt-in and never auto-registers repository-wide linting in pytest.
- `flake8_lint.discovery` handles repository traversal so tests do not own production file discovery logic.
