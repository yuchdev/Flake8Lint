---
description: Run the repository's iterative documentation maintenance workflow in Junie.
---

Run the repository's iterative documentation maintenance flow.

Target: `$ARGUMENTS`

Support two modes:

- no argument or `--scan` for a full documentation-corpus audit,
- a path argument for focused propagation after editing one document.

Use this workflow:

1. Linkify bare `.md` mentions first.
2. Run the documentation link and registry checks appropriate to the selected mode.
3. Apply only high-confidence automatic fixes.
4. Surface ambiguous or review-needed cases instead of guessing.
5. Re-run checks until the targeted docs are clean or the remaining work requires human judgement.

At the end of the run, report whether the docs are clean or what follow-up iteration is still needed.