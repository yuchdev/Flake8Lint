---
description: Run the old Claude post-edit quality flow for the given changed paths.
---

Apply the repository's explicit post-edit workflow to these paths:

`$ARGUMENTS`

Use the narrowest relevant checks:

- Run `/secret-scan $ARGUMENTS` when new or edited files could contain credentials.
- For Python changes, run the repository's formatting and lint workflow with `ruff`, fixing safe mechanical issues first.
- For documentation changes, run `/link-check $ARGUMENTS` and `/doc-xref <target>` when files or headings were renamed.
- For dependency-file changes (`pyproject.toml`, `uv.lock`, `requirements*.txt`), run `/dep-audit`.

Finish by summarizing what was checked, what was fixed automatically, and what still needs human attention.