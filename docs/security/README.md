# Security

Threat models, security review outputs, and posture documentation for Flake8 Linter.

The `security-auditor` agent owns this directory. Every change touching auth,
secrets, external integrations, or untrusted-input ingestion triggers a security
review whose output is stored here.

## Naming convention

`threat-model-<scope>.md` for threat models, `review-<scope>-<YYYY-MM-DD>.md`
for point-in-time reviews.

## What a threat model must contain

1. **Scope** - which components and trust boundaries are in scope.
2. **Assets** - what secrets, PII, and data are handled.
3. **Threat actors** - attacker profiles considered.
4. **STRIDE analysis** - Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation.
5. **Mitigations** - existing controls and open gaps.
6. **Verdict** - CRITICAL (merge blocked) / HIGH / MEDIUM / LOW / INFO.

## Security rules (non-negotiable)

- Never log secrets; rely on this project's log-redaction mechanism (if any)
  and verify it covers new sinks.
- Never hard-code credentials. Read from settings/env.
- Treat all untrusted external input as sensitive - no unredacted raw input
  in logs, exceptions, stored reports, or API error bodies.
- Untrusted input must never reach a shell, SQL string, `eval`, or an AI
  prompt without sanitization/parameterization.

> **SME REVIEW NEEDED (AI-drafted - verify before relying on this):**
>
> ## Draft threat model - `flake8-lint` core
>
> ### 1. Scope
>
> The whole distribution: `src/flake8_lint/` (`api.py`, `registry.py`, `rules.py`, `config.py`,
> `discovery.py`, `cli.py`, `plugin.py`, `testing.py`), the `flake8-lint` console script, and the
> `flake8.extension` / `flake8_lint.rules` entry points. Trust boundaries crossed:
>
> - **Scanned repository → engine.** `api.check_file` reads arbitrary `.py` text
>   (`read_text(encoding="utf-8")`) and hands it to `ast.parse`; `discovery.discover_python_files`
>   walks arbitrary directory trees.
> - **Config file → engine.** `config.load_config` parses TOML with `tomllib`. `_iter_candidate_directories`
>   walks **upward to the filesystem root**, so a config file *outside* the invocation directory
>   can be discovered and honored.
> - **Config / installed package → Python import.** `registry._load_register_function` calls
>   `import_module(module_name)` on `rule_modules` values; `resolve_registry` calls
>   `entry_point.load()` on every installed `flake8_lint.rules` provider.
> - **Engine → operator output.** `format_text`/`format_json` to stdout, warnings and errors to
>   stderr via `print()` in `cli.py`.
>
> Out of scope: PyPI/GitHub release infrastructure (`.github/workflows/publish.yml`, trusted
> publishing) - worth its own model.
>
> ### 2. Assets
>
> No credentials, no PII, no money, no network I/O, and zero runtime dependencies
> (`pyproject.toml` `dependencies = []`). The assets are:
>
> - **Integrity of the lint verdict** - the primary asset. Consumers gate CI on exit code `1` vs
>   `0`, so a suppressed or missed violation is a security-relevant failure for *them*.
> - **Confidentiality of scanned source** - `RuleContext.source` holds whole files of possibly
>   proprietary code that may itself contain secrets.
> - **Filesystem-layout disclosure** - `api._display_filename` falls back to an absolute path when
>   the file is outside both `cwd` and `base_dir`; those paths reach stdout and JSON output.
> - **Integrity of the execution environment** - the `import_module`/`entry_point.load()` path
>   executes third-party code in the developer's or CI runner's interpreter.
>
> ### 3. Threat actors
>
> - **A hostile repository** being linted (e.g. an untrusted PR, a vendored dependency, an
>   automated scan of third-party code) - controls all `.py` text, all `# noqa` comments, and any
>   `pyproject.toml`/`flake8_lint.toml` in or above the tree.
> - **A malicious or compromised rule-provider package** published to PyPI declaring a
>   `flake8_lint.rules` entry point.
> - **A contributor to a consuming project** who wants a banned pattern to pass CI and can edit
>   config or add `# noqa` comments.
>
> ### 4. STRIDE
>
> | Category | Finding | Evidence |
> |---|---|---|
> | **Spoofing** | Low. No identities or auth. A provider can claim any `provider=` label in `RuleRegistration`, which only affects error text. | `registry.py` `register()` |
> | **Tampering** | **Highest-value class.** A hostile repo can weaken its own lint verdict via an upward-discovered config (`select`/`ignore`/`exclude`/`allow_noqa`), or via `# noqa` comments parsed from the scanned source. Mitigated only if the operator pins `--config` and/or sets `noqa_forbidden`. | `config._iter_candidate_directories`, `api._parse_noqa_codes`, `api._path_allows_noqa` |
> | **Repudiation** | Low, but note there is **no logging at all** - `logging` is imported nowhere in `src/`. There is no audit trail of which config file, which providers, or which rule set produced a verdict. `config_path` is captured on `LintConfig` but never printed. | absence of `logging` in `src/flake8_lint/` |
> | **Information disclosure** | Moderate. Rule messages are static strings from `builtin_registrations()` and never quote source text - a good existing control that must be preserved. Absolute paths can leak via `_display_filename`'s fallback. `RuleExecutionError`/`RuleProviderLoadError` interpolate third-party exception text (`f"...: {exc}"`). | `rules.py`, `api._display_filename`, `api.py:96-99`, `registry.py:108-124` |
> | **Denial of service** | Moderate and unmitigated. `ast.parse` on adversarially nested source can raise `RecursionError` or exhaust memory; `lint_paths` accumulates all violations in one unbounded list; `_is_noqa_suppressed` re-`splitlines()` the whole file per violation (quadratic); `rules.py` runs one full `ast.walk` per enabled rule. No timeouts, size caps, or recursion limits anywhere. Impact is a hung/OOM CI job, not compromise. | `api.check_file`, `api.lint_paths`, `api._is_noqa_suppressed` |
> | **Elevation of privilege** | **The one path to code execution.** `rule_modules` → `import_module()` and installed entry points → `entry_point.load()` run arbitrary module-level code in the host interpreter. A repo-local `pyproject.toml` setting `rule_modules = ["evil"]` executes `evil` on `flake8-lint check`, subject to `sys.path`. This is the same trust model as most Python linters, but it must be stated, not assumed. | `registry._load_register_function`, `registry.resolve_registry` |
>
> ### 5. Mitigations
>
> Existing controls:
>
> - Zero runtime dependencies - no transitive supply chain at install time.
> - No shell, SQL, `eval`, `exec`, `subprocess`, or network calls anywhere in `src/`.
> - Rule codes are shape-validated (`RULE_CODE_RE`) and duplicates fail fast
>   (`DuplicateRuleCodeError`), so a hostile provider cannot shadow a built-in `X` code.
> - Provider loading is deterministic (entry points sorted by `(name, value)`) and failures raise
>   rather than being silently skipped.
> - Rule messages never echo scanned source.
> - `--no-rule-plugins` disables installed-provider loading; `noqa_forbidden` and
>   `allow_noqa = false` let an operator override in-source suppression.
> - `discovery` uses `os.walk` with default `followlinks=False`, so symlinked directories are not
>   traversed.
>
> Open gaps (for SME triage):
>
> 1. No documented guidance that **linting an untrusted repository can execute code from that
>    repository's config**. This belongs in `README.md`, not just here.
> 2. Config discovery walking to the filesystem root has no `--no-upward-search` or project-root
>    boundary; a config above the target tree is honored silently.
> 3. No resource limits on `ast.parse` (recursion/size) or on total accumulated violations.
> 4. No audit line recording the resolved `config_path`, resolved provider list, and effective
>    `select`/`ignore` for a given run.
> 5. `api._safe_traversal_root` builds traversal roots from `include` patterns and returns absolute
>    paths when the pattern is absolute, escaping `base_dir` - verify this is intended.
>
> ### 6. Verdict
>
> **Draft: MEDIUM.** Nothing here blocks merge, and the code-execution path matches the accepted
> trust model for Python linters. Items 1 and 2 above are the ones a reviewer should rule on
> first, since together they mean `flake8-lint check` on an untrusted checkout is a
> code-execution decision the operator is not currently warned about.
