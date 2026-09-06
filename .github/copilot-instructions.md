# Copilot Instructions

- Production code must not import from tests.
- Built-in rule behavior lives in the core engine.
- Integrations remain adapters.
- X003 is reserved.
- Do not renumber existing X-codes.
- Adding a built-in rule requires registry, tests, samples, and docs.
- Adding or changing extension APIs requires `test_custom_rules.py` updates.
- Duplicate custom rule codes are errors.
- CLI exit codes are a public contract.
- Ordinary pytest must not auto-run repository lint.
- Run tests and build before completing implementation work.
