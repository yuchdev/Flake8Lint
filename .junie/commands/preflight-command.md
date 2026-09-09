---
description: Review a proposed shell command for destructive or policy-violating behavior before running it.
---

Review this proposed shell command before execution:

`$ARGUMENTS`

Check it against the repository policy in `.junie/AGENTS.md` and report:

- whether it is safe to run as written,
- any destructive, network, credential, or protected-path risks,
- whether a narrower alternative would be safer,
- and any flags needed for non-interactive execution.

If it is unsafe or ambiguous, say so clearly and propose a safer equivalent instead of approving it.