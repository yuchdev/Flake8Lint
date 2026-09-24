# Milestone 0001 - Generic Implementation - Status

Tracks progress against [plan.md](plan.md). Updated as each task lands.

## Current status

| Task | Name                             | Status         | Tests |
|------|----------------------------------|----------------|-------|
| 01.0 | Standalone CLI Mode              | ✅ Complete    | `test_cli.py`, `test_config.py`, `test_custom_rules.py`, `test_docs_smoke.py`, CI `wheel-smoke` |
| 02.0 | Tool-Mode Config Surfaces        | ✅ Complete    | `test_config.py`, `test_config_precedence.py`, `test_cli.py`, `test_api.py`, `test_discovery.py`, `test_noqa.py`, CI `wheel-smoke` |
| 03.0 | Config Introspection & Bootstrap | ✅ Complete    | `test_cli.py`, `test_config.py`, `test_custom_rules.py`, CI `wheel-smoke` |
| 04.0 | CI Output Formats                | ✅ Complete    | `test_api.py`, `test_cli.py`, `test_config.py`, `tests/golden/sarif_basic.json` |
| 05.0 | Incremental Adoption             | ⬜ Not started | -     |
| 06.0 | Scale & Distribution             | ⬜ Not started | -     |

**Legend:** ✅ Complete · 🔶 In progress / partial · ⬜ Not started

## Notes & decisions

- 2026-09-24 - The milestone was renamed from the template `0001-working-implementation`
  (with its illustrative `01.0-hello-world-endpoint` task) to `0001-generic-implementation`.
  The template task was removed. It described a `GET /health` endpoint that doesn't apply
  to a lint CLI.
- Open: D1 (unused-`noqa` code) and D2 (baseline fingerprint). See
  [plan.md](plan.md#open-decisions-ratify-before-the-dependent-subtask-starts).
- 2026-09-24 - 01.0/01: a nonexistent path argument exited `0` on the baseline, although the
  spec said "still exit 2". Ruling (user): exit `2` with `flakeforge: path does not exist: ...`
  on stderr (C1 "invalid invocation"). The check lives in `cli.py`; `lint_paths()` is unchanged.
  Recorded in `CHANGELOG.md`.
- 2026-09-24 - 01.0/04 security-auditor: PASS_WITH_FOLLOWUP, no CRITICAL. MEDIUM finding (a target
  without a config file was put on `sys.path` for an explicit `--rule-module`) fixed via
  `LintConfig.rule_module_root`. Two LOW findings accepted; see
  [the threat model](../../security/2026-09-24-project-root-rule-imports.md).

- 2026-09-24 - 01.0 review follow-ups: test cleanup done (`monkeypatch.chdir`, no bare assert in
  fakes, explicit `--no-config --rule-module` test). Confining include traversal roots
  (`api._safe_traversal_root`, security LOW, CWE-22) moves to **02.0/03** by user ruling. A
  config-relative `../src` include is a supported, tested use case, so the confinement rule must
  be designed together with C6. Plain `is_relative_to(base_dir)` would break it.

- 2026-09-24 - 02.0/03 confinement ruling (user): an **absolute** path pattern in a config file
  exits `2` with an error naming the pattern. Relative patterns, including `..` (e.g.
  `include = ["../src"]` from `project/config/`), stay allowed. This closes the CWE-22 LOW
  finding from the 01.0 review.

## Task details

### Task 01.0 - Standalone CLI Mode (✅ 2026-09-24)

**Delivered**

- 01: `discovery_anchor()` (C4). Config discovery starts from the target path, not cwd (fixes G1).
  A nonexistent path argument now exits `2` (user ruling, see Notes & decisions).
- 02: `output_format` and `rule_plugins` TOML keys and `LintConfig` fields. `--noqa` and
  `--rule-plugins` use `BooleanOptionalAction`. `api.KNOWN_OUTPUT_FORMATS`,
  `validate_output_format()`, and `format_result()` added. An invalid format exits `2` (fixes G2).
- 03: `--include`/`--exclude` (these replace the file's lists), plus `--no-config` via
  `config.isolated_config()`. `--no-config` cannot be combined with `--config` (exit `2`). Fixes G3.
- 04 🔒: `resolve_registry(project_root=...)` and `_project_root_on_syspath` (restores
  `sys.path` in place, even on failure). `LintConfig.rule_module_root` only trusts the directory
  of a loaded config file. "Trust boundary" section added to `docs/custom-rules.md` (fixes G4).
- 05: four standalone scenarios in the `wheel-smoke` job; README "Standalone CLI" section;
  discovery anchor documented in `docs/architecture.md`.

**Tests / gate**

- 166 → 203 tests, all passing. Coverage 91.10% → 91.74%. `ruff` is clean, and the
  `--select X001,X009,X010 src` self-check is clean.
- The extended `wheel-smoke` script passed locally against a freshly built wheel. `/link-check`
  is clean.
- Every subtask got a `/verify-subtask` verdict: 01 was PARTIAL and resolved by the ruling,
  02-05 PASS. `/pr-review`: feature-reviewer LGTM, security-auditor PASS_WITH_FOLLOWUP with no
  CRITICAL finding, so the task is APPROVED.
- Accepted LOW follow-ups: a scanned repo's own config can silence findings (use `--no-config`
  for gating); `api._safe_traversal_root` doesn't confine `..`/absolute include patterns
  (pre-existing, API-only); `sys.modules` residue (revisit in 06.0/01).

### Task 02.0 - Tool-Mode Config Surfaces (✅ 2026-09-24)

**Delivered**

- 01: one strict schema (`_CONFIG_SCHEMA`) drives `LintConfig.from_mapping()` for both surfaces
  (C5). An unknown key exits `2` with a file/section prefix and a did-you-mean hint (fixes G5).
  Legacy `[tool.flake8_lint]` stays lenient for unknown keys. `flakeforge.toml` may be flat or
  wrapped as `[tool.flakeforge]`, but not both at once.
- 02: same-directory `flakeforge.toml` beats a sibling `pyproject.toml` section and adds exactly
  one shadow warning (discovery only, not for `--config`). The nearest directory wins, and a
  `pyproject.toml` without a flakeforge section doesn't stop the upward search (fixes G6).
- 03: config path patterns resolve against the config file's directory, and display names are
  relative to `base_dir` regardless of cwd (fixes G7). Any anchored pattern in a config file
  (POSIX `/`, Windows drive or drive-relative, UNC, root-relative) exits `2`. Relative `..`
  patterns stay supported. This closes the CWE-22 LOW finding from 01.0.
- 04: `tests/test_config_precedence.py`, a 24-cell matrix plus one extra test. Seven precedence
  scenarios added to `wheel-smoke`. The README now has a single "Configuration" section (key
  table, C2/C3/C6, when to pick which file), and `docs/architecture.md` is updated.

**Tests / gate**

- 203 → 267 tests, all passing. Coverage 92.75%. `ruff` is clean (venv and `uv run`), and the
  self-check subset is clean. The extended `wheel-smoke` script passed locally. `/link-check` is
  clean.
- `/verify-subtask` PASS on 01-04. `/pr-review`: feature-reviewer LGTM, security-auditor
  PASS_WITH_FOLLOWUP with no CRITICAL finding, so the task is APPROVED. The one actionable LOW
  (drive-relative `C:foo` wasn't caught) was fixed before close.
- Accepted LOW/INFO: `..` patterns can still reach outside `base_dir` (by design, read-only AST
  lint); no size limit when parsing the sibling `pyproject.toml` (same as a normal config load).
  UX idea for later: a clearer error for a `flakeforge.toml` holding an unrelated `[tool.*]`
  table.

### Task 04.0 - CI Output Formats (✅ 2026-09-24)

**Delivered**

- 01: `api.FORMATTERS` is now the single public formatter registry, and CLI `choices` and
  `validate_output_format()` derive from it. `KNOWN_OUTPUT_FORMATS` is kept, derived from it.
  JSON output gains `"schema_version": 1` (additive).
- 02: a `github` format (`::error` workflow commands, escaped with the official toolkit rules,
  1-based columns) and a `sarif` format (SARIF 2.1.0, stdlib `json`, rule list from the new
  `LintResult.registered_rules`, `uri` relative to `base_dir`). SARIF was validated against the
  official OASIS schema. The CLI no longer prints an empty line when a github run is clean.
  README gains a "CI output formats" section with an `upload-sarif` example.
- 03: `--statistics` / TOML `statistics`. Text output gets an aligned per-code summary; JSON gets
  an additive `statistics` object (still `schema_version` 1). `github`/`sarif` ignore it with a
  warning. It never changes the exit code.

**Tests / gate**

- 267 → 306 tests, all passing. Coverage ~93%. `ruff` is clean (venv and `uv run`), the
  self-check is clean, and `/link-check` is clean.
- Spec compliance: 01 and 03 checked inline (short specs), 02 got a `/verify-subtask` PASS.
- `/pr-review`: security-auditor PASS_WITH_FOLLOWUP (workflow-command injection neutralized, no
  CRITICAL or HIGH finding). feature-reviewer REQUEST_CHANGES → resolved: the warning wording is
  now correct when statistics comes from the config file (new test), and the README
  `output_format` row lists all four formats.
- Accepted LOW: SARIF/github paths for files outside `base_dir` can be absolute or contain
  `..`. Every result has level `error` (no severity mapping).

### Task 03.0 - Config Introspection & Bootstrap (✅ 2026-09-24)

**Delivered**

- 01: `flakeforge config show` prints the effective, validated config: source file/section,
  discovery anchor, `base_dir`, and every schema key with its value and origin
  (`default`/`file`/`cli`). Text or stable JSON output. Origin tracking lives in config.py
  (`resolve_config_origins`, `describe_config_source`, `CONFIG_KEYS`) and isn't part of
  `LintConfig` equality. `cli.py` now has a shared parent parser, and `check --help` is
  byte-identical to before.
- 02: `flakeforge rules` lists every registered rule with its enabled/disabled state (the same
  logic the engine uses) and provider origin (`builtin`, `rule_module:<name>`,
  `entry_point:<dist>`). New additive `RuleRegistration.origin` plus
  `RuleRegistry.registering_origin`; `docs/custom-rules.md` and `test_custom_rules.py` updated.
- 03: `flakeforge init [--pyproject] [DIR]` writes all schema keys at their defaults from a
  template (C8). A test keeps the template in step with the schema. It refuses to overwrite,
  duplicate, shadow in either direction, or touch a malformed pyproject (exit `2`). New files
  are created exclusively (safe against dangling symlinks), and an existing pyproject is only
  appended to.

**Tests / gate**

- 306 → 353 tests, all passing (including the full `flakeforge check .` self-lint). `ruff` is clean (venv and `uv run`), the self-check is clean, and
  `/link-check` is clean. `wheel-smoke` gained init / config show / rules / bare-`config`
  scenarios, and the extended script passed locally.
- `/verify-subtask`: 01 and 02 PASS; 03 checked by hand. `/pr-review`: security-auditor
  PASS_WITH_FOLLOWUP (no CRITICAL). Its MEDIUM finding (introspection commands run
  `rule_modules`) is documented in the Trust boundary section and the README, and its LOW
  symlink/TOCTOU finding in `init` is fixed with tests. feature-reviewer REQUEST_CHANGES →
  resolved: bare `flakeforge config` exited `0` via argparse help and now exits `2` (test
  added). The reviewer's `-> None` suggestion was declined: it conflicts with the project's own
  X008 rule.
- Accepted: CWE-209 (a rule-module `SyntaxError` line can be echoed on stderr).
  `cli.py` reuses the private `api._is_rule_enabled`; making it public is a possible cleanup.

**Reconciliation note**

- Task README Key constraint "each subcommand accepts the same `--config`/`--no-config`/anchor
  arguments": this holds for `check`, `config show` and `rules`. It is **not applicable** to
  `init`, which writes a new config and never reads or discovers one. Adding those flags would
  advertise behavior it doesn't have. There is an inline note in `build_parser`.
