# Milestone 0001 - Generic Implementation - Status

Tracks progress against [plan.md](plan.md). Updated as each task lands.

## Current status

| Task | Name                             | Status         | Tests |
|------|----------------------------------|----------------|-------|
| 01.0 | Standalone CLI Mode              | ✅ Complete    | `test_cli.py`, `test_config.py`, `test_custom_rules.py`, `test_docs_smoke.py`, CI `wheel-smoke` |
| 02.0 | Tool-Mode Config Surfaces        | ⬜ Not started | -     |
| 03.0 | Config Introspection & Bootstrap | ⬜ Not started | -     |
| 04.0 | CI Output Formats                | ⬜ Not started | -     |
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
