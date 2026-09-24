# Threat Model - project-root rule imports - 2026-09-24

Pre-implementation review of subtask `01.0-standalone-cli-mode/04-project-root-rule-imports.md`
(plan contract C7). No product code was changed by this review.

## Assets & trust boundaries

- **Asset:** the developer/CI machine and process running `flakeforge check <dir>`, its
  environment (secrets in env, SSH agent, cloud creds), and the integrity of lint results.
- **Trust boundary crossed:** the linted repository is *untrusted input*. Before this change,
  `flakeforge check <untrusted-dir>` parses files as AST data only — it never imports code the
  target repo controls (project-local `rule_modules` today require the module to be importable
  from an already-configured `sys.path`, i.e. installed). **After this change** the config's
  `base_dir` is prepended to `sys.path` while loading `rule_modules`, so a config file checked
  into the target repo (`flakeforge.toml` / `pyproject.toml [tool.flakeforge] rule_modules = [...]`)
  causes arbitrary attacker-controlled Python at that path to execute at import time. This is
  arbitrary code execution by design (CWE-829 Untrusted Search Path, CWE-426 Untrusted Search
  Path), so the boundary must be explicit and opt-out-able.
- **Boundary rules from C7:** `base_dir` on `sys.path` only while providers load, restored
  afterward even on failure; `--no-config`/`isolated_config` loads *no* project rule modules
  (verified: `isolated_config` returns `LintConfig(base_dir=...)` with `rule_modules=()`);
  `--rule-module` on the CLI stays an explicit opt-in; entry-point providers resolve through
  installed metadata and are unaffected.

## Findings

### [CRITICAL] Arbitrary code execution is inherent; the trust boundary must be documented and honored, not silently widened
- Vector / evidence: `docs/.../04-project-root-rule-imports.md:9-16`; loader at
  `src/flakeforge/registry.py:148-154` calls `import_module(module_name)` which runs module
  top-level code. Putting `base_dir` first on `sys.path` (C7) makes any `rule_modules` entry in
  a repo-controlled config execute that repo's code.
- Impact: cloning + linting a hostile repo runs its code with the user's privileges (secret
  exfiltration, workstation/CI compromise). This is unavoidable given the feature, so the risk
  is managed by scoping and disclosure, not eliminated.
- Mitigation / requirement: implement exactly per C7 — project rule modules load only from a
  *discovered/explicit config*, never from a raw path argument; `--no-config` must load zero
  project rule modules; add the `docs/custom-rules.md` "Trust boundary" note telling users to
  run `--no-config` on untrusted checkouts. Any deviation that broadens this (e.g. loading from
  a path arg, or auto-enabling for unknown checkouts) is a BLOCK-level regression.

### [HIGH] `sys.path` must be restored exception-safely by restoring the saved list object's contents, not rebinding a name
- Vector / evidence: C7 "restored afterward, even if loading fails"; spec asks for a context
  manager (`04...:10-11`). Naive `saved = sys.path; sys.path = [base]+sys.path; ... ; sys.path = saved`
  breaks any code (or C-level cache) holding the original `sys.path` object, and a bare rebind in
  `finally` can still leak if the insert and save straddle the `try`.
- Impact: path pollution persists after the call — later imports in the same process resolve
  against the target repo (privilege of the ACE bug extends process-wide), or unrelated tooling
  sharing the interpreter misbehaves.
- Mitigation / requirement: use a context manager that snapshots `sys.path[:]` (a copy) *inside*
  the `try` setup, inserts `base_dir` at index 0, and in `finally` restores in place via
  `sys.path[:] = saved` so the same list object is preserved. The insert and the save must be
  paired such that `finally` always runs (enter before any import). Add tests asserting
  `sys.path` identity and contents are unchanged after both success and `RuleProviderLoadError`.

### [HIGH] `sys.modules` pollution and shadowing of stdlib / flakeforge by project modules placed first on `sys.path`
- Vector / evidence: `sys.path` restore does **not** unwind `sys.modules`; `import_module`
  caches every imported name (and its transitively-imported submodules) globally. With `base_dir`
  first, a target repo can ship `os.py`, `json.py`, `logging.py`, or a top-level `flakeforge/`
  / `api.py` / `registry.py` that shadows the real module for the *first* import that resolves it.
- Impact: (1) a malicious/careless repo module named like a stdlib or like `flakeforge` itself is
  imported and cached, corrupting the linter's own later imports within the process (worse under a
  long-lived process); (2) even benign name collisions make results depend on load order.
- Mitigation / requirement: keep `base_dir` insertion scoped to the narrowest possible window
  (one module load), document that shadowing is possible, and prefer inserting `base_dir` such
  that it cannot pre-empt already-imported `flakeforge` internals for the linter's own use (the
  linter's own modules should be imported before entering the context). Consider snapshotting
  `sys.modules` keys and warning on, or (best-effort) not persisting, newly-cached top-level names
  that collide with stdlib or `flakeforge`. At minimum: add a test that a target module named
  `flakeforge`/`os` does not corrupt the linter's subsequent behavior in-process. Note the residual
  `sys.modules` pollution explicitly in the threat-model note.

### [HIGH] `base_dir` must be the resolved config directory, never a raw CLI path argument
- Vector / evidence: `04...:13-14`; `base_dir` is set only by `load_config`/`_load_path`/
  `_load_pyproject` (`config.py:243,293,303`, all `.resolve()`d) and by `isolated_config`.
- Impact: if a raw positional path (attacker-influenced, possibly relative/symlinked) were put on
  `sys.path`, `--no-config` and "no config found" runs would start executing target code — a
  direct bypass of the C7 boundary and CWE-426.
- Mitigation / requirement: thread only `config.base_dir` (already resolved) into
  `resolve_registry(project_root=...)`; when `base_dir` is `None` or `rule_modules` is empty,
  insert nothing on `sys.path`. Never derive the inserted path from `paths`/argv. Add a test that
  a no-config run with a repo-local `flakeforge.toml` present does not import its `rule_modules`.

### [MEDIUM] Parallel `--jobs` (task 06.0/01) each mutate the *worker's* `sys.path`; keep the mutation inside the worker and short-lived
- Vector / evidence: `06.0/01-parallel-checking.md:8-12` — `ProcessPoolExecutor`; "workers rebuild
  the registry from `(rule_modules, rule_plugins, base_dir)`". Each worker calls `resolve_registry`
  and thus enters the `sys.path` context.
- Impact: process isolation is favorable (no shared `sys.path` across workers, no data race on the
  parent's list). Risk is (a) if a future in-process/thread executor is ever used, the global
  `sys.path` mutation is not thread-safe and two loads would race/leak; (b) reusable pool workers
  accumulate `sys.modules` pollution across tasks in the same long-lived worker.
- Mitigation / requirement: keep provider loading in a `ProcessPoolExecutor` (never a thread pool)
  precisely because `sys.path`/`sys.modules` are process-global mutable state; document that the
  context manager is not thread-safe. Enter/exit the `sys.path` context once per registry build and
  before fan-out where practical, so worker file-checking does not run with `base_dir` still on the
  path. Add the `--jobs 1` vs `--jobs 4` byte-identical-output test (already required by 06.0) as a
  regression guard against load-order-dependent behavior.

### [MEDIUM] Failing import must stay a `RuleProviderLoadError` → exit 2, and its message must not leak sensitive content
- Vector / evidence: `04...:15-16`; existing handler `registry.py:153-154` wraps into
  `RuleProviderLoadError` with `{exc}` interpolated.
- Impact: exit-code contract (C1) preserved only if new exceptions raised while `base_dir` is on
  the path are still funneled through this wrapper; an unwrapped `ImportError`/`SyntaxError` from
  the target module could crash differently. Interpolating raw exception text into the message can
  surface target-file contents/paths in logs (information disclosure, CWE-209), though impact is
  low for a local dev tool.
- Mitigation / requirement: ensure the new project-root load path is inside the same
  `except (...) -> RuleProviderLoadError` funnel and that the raised message names the module and
  `base_dir` (per spec) without echoing arbitrary target source; the `finally` restore must run
  before the exception propagates.

### [LOW] Symlink / resolved-path considerations for `base_dir`
- Vector / evidence: `base_dir` is `.resolve()`d in `config.py`; `isolated_config` uses
  `discovery_anchor` which also `.resolve()`s.
- Impact: a symlinked config directory resolves to its real target before going on `sys.path`;
  acceptable, but worth asserting so a future refactor does not put an unresolved/relative path on
  `sys.path` (which would be CWD-dependent and spoofable).
- Mitigation / requirement: assert/guarantee the inserted entry is an absolute, resolved directory;
  add a test loading a project via a symlinked checkout run from a different cwd (spec already asks
  for "run from another cwd").

## Implementer requirements (summary)
1. (CRITICAL) Load project `rule_modules` only from a discovered/explicit config; `--no-config`/`isolated_config` loads none; add the `docs/custom-rules.md` "Trust boundary" note.
2. (HIGH) Restore `sys.path` in place via `sys.path[:] = saved_copy` inside `finally`; snapshot before insert; test restoration after success and failure.
3. (HIGH) Treat `sys.modules` pollution/shadowing of stdlib and `flakeforge` as a known risk: import linter internals before entering the context, keep the window minimal, and test that a target module named like `flakeforge`/`os` does not corrupt the linter in-process.
4. (HIGH) Pass only the resolved `config.base_dir` to `resolve_registry(project_root=...)`; insert nothing when it is `None` or `rule_modules` is empty; never use a raw path argument.
5. (MEDIUM) Do provider loading only in a `ProcessPoolExecutor` (never threads); document the context manager as not thread-safe; keep the `--jobs 1` vs `--jobs 4` identical-output test.
6. (MEDIUM) Keep the new load path inside the existing `RuleProviderLoadError` funnel (exit 2), name module + `base_dir` without echoing target source, and ensure `finally` restore runs before propagation.
7. (LOW) Guarantee the inserted `sys.path` entry is absolute and resolved; add a symlinked-checkout, foreign-cwd test.

## Verdict: PASS_WITH_FOLLOWUP

The design (C7) is sound and the untrusted-input boundary is acknowledged. There is no CRITICAL
*defect* to block on because this is a pre-implementation review of a not-yet-written change; the
CRITICAL item is an inherent-risk requirement, not an existing flaw. Merge is gated on the
implementation satisfying requirements 1-4 (a violation of any of those — especially loading
project modules under `--no-config`, from a raw path arg, or failing to restore `sys.path` — turns
this into a BLOCK). Hand fixes to `python-expert` and the restoration/shadowing/`--no-config`
regression tests to `testing-expert`.

## Post-implementation review (2026-09-24)

As-built review of subtask 01.0/04 against implementer requirements 1-7. Evidence:
`src/flakeforge/registry.py` (`resolve_registry(project_root=...)`,
`_project_root_on_syspath`, `_rule_module_load_message`), `src/flakeforge/cli.py`
(`main`, `_build_cli_config`), `src/flakeforge/api.py` (`check_tree`/`lint_paths`
thread `project_root=effective_config.base_dir`), `src/flakeforge/config.py`
(`isolated_config`, `discovery_anchor`, `load_config`), `tests/test_custom_rules.py`,
`docs/custom-rules.md` (Trust boundary).

- **Req 1 (CRITICAL) — PASS.** `cli.main` passes `project_root=None if args.no_config
  else config.base_dir`; `isolated_config` returns `rule_modules=()`; `resolve_registry`
  inserts nothing when `project_root is None`. `--no-config` therefore loads zero project
  modules and never places the target on `sys.path`, even when `--rule-module` is supplied
  (project_root stays `None`). The `docs/custom-rules.md` "Trust boundary" note is present
  and correct. No open CRITICAL.
- **Req 2 (HIGH) — PASS.** `_project_root_on_syspath` snapshots `saved = sys.path[:]`,
  inserts at index 0, and restores in place with `sys.path[:] = saved` in `finally`. Tests
  `test_project_root_restores_syspath_after_success/after_failure` assert both list identity
  (`is`) and contents after success and `RuleProviderLoadError`.
- **Req 3 (HIGH) — PASS (with known residual).** `builtin_registrations` is imported before
  the `sys.path` window opens; `test_target_module_named_like_stdlib_or_flakeforge_does_not_corrupt`
  confirms already-cached `os`/`flakeforge` are not shadowed. Residual `sys.modules` pollution
  (a not-yet-imported name could be cached from the target, and `base_dir` stays on the path for
  the whole `rule_modules` loop, not one module at a time) is documented in the context-manager
  docstring and accepted.
- **Req 4 (HIGH) — PASS with one MEDIUM caveat.** `resolve_registry` receives only the resolved
  `config.base_dir`, `.resolve()`s it again, and inserts nothing when `rule_modules` is empty.
  Caveat: in default mode with *no config file found*, `load_config` returns
  `LintConfig(base_dir=<discovery anchor>)`, and the anchor is derived from the positional path
  argument; combined with an explicit `--rule-module`, the target directory is prepended to
  `sys.path[0]`. See finding 1.
- **Req 5 (MEDIUM) — PASS (deferred/documented).** No parallel executor is introduced in this
  subtask; the context-manager docstring documents that it mutates process-global `sys.path`, is
  not thread-safe, and that fan-out must use `ProcessPoolExecutor`. The `--jobs` identity test
  belongs to task 06.0.
- **Req 6 (MEDIUM) — PASS with LOW caveat.** The project-module load stays inside the
  `except (...) -> RuleProviderLoadError` funnel; `_rule_module_load_message` names the module and
  `base_dir`, and the context-manager `finally` runs before the exception propagates
  (`test_load_error_message_names_module_and_base_dir`). Caveat: the message interpolates raw
  `{exc}`, which for a `SyntaxError` can embed a line of target source (CWE-209). See finding 2.
- **Req 7 (LOW) — PASS.** The inserted entry is the already-`.resolve()`d `base_dir`
  (absolute, symlink-resolved); `test_project_root_accepts_symlinked_checkout_from_foreign_cwd`
  and `test_project_root_loads_uninstalled_module_from_foreign_cwd` cover symlink + foreign-cwd.

### Post-implementation findings

### [MEDIUM] No-config-file default run derives `base_dir` from the target path, so `--rule-module` can be shadowed by the untrusted checkout
- Vector / evidence: `config.py:228` (`return LintConfig(base_dir=base)` with `base` = the
  `discovery_anchor` of the positional paths) → `cli.py` `project_root=config.base_dir` →
  `registry.py` inserts `base_dir` at `sys.path[0]`. Triggered by
  `flakeforge check --rule-module NAME <untrusted-dir>` when no config file is discovered.
- Impact: the untrusted target directory precedes installed packages on `sys.path`, so a repo
  shipping a top-level `NAME` package/module shadows the operator's intended installed one
  (CWE-426/CWE-427 untrusted search path). This is inside the already-accepted "default mode trusts
  the target" boundary and requires an explicit `--rule-module`, but it widens req 4's "never a raw
  path argument" intent, and `docs/custom-rules.md` only promises target-dir isolation under
  `--no-config`.
- Mitigation: acceptable as documented for now; consider not defaulting `base_dir` to the target
  anchor when no config file is found, or appending (not prepending) the anchor for CLI-supplied
  `--rule-module`. Route to `python-expert` if hardened.

### [LOW] Load-error message interpolates raw exception text (CWE-209)
- Vector / evidence: `registry.py` `_rule_module_load_message` -> `f"...: {exc}"`; a `SyntaxError`
  from the target module embeds the offending source line in the `RuleProviderLoadError` message
  and thus in CLI stderr/logs.
- Impact: minor information disclosure of target-file content; low for a local dev tool.
- Mitigation: name module + `base_dir` + exception *type* without the raw payload, or restrict to
  the exception class. Regression test to `testing-expert` if changed.

### [LOW] Residual `sys.modules` pollution outlives the `sys.path` window
- Vector / evidence: `registry.py` `_project_root_on_syspath` restores `sys.path` but not
  `sys.modules`; `base_dir` remains on the path for the full `rule_modules` loop.
- Impact: a not-yet-imported (e.g. lazily-loaded stdlib) name imported from the target stays cached
  process-wide after the call. Documented and accepted; matters more under a future long-lived
  worker pool (06.0).
- Mitigation: keep the window minimal; revisit when parallel workers land.

## Post-implementation verdict: PASS_WITH_FOLLOWUP

Requirements 1-4 (the merge gate) are satisfied: `--no-config` loads no project modules, `sys.path`
is restored in place on success and failure, and only the resolved `base_dir` reaches `sys.path`.
No CRITICAL finding is open. Two LOW and one MEDIUM residual/follow-up items remain (findings above);
none block merge into `master`.

### Follow-up (2026-09-24)

- Finding 1 (MEDIUM) **fixed**: `LintConfig.rule_module_root` returns `base_dir` only when the
  config was loaded from a file (`config_path` set). The CLI and `api.py` pass it as
  `project_root`, so a target with no config file is never put on `sys.path`, even with an
  explicit `--rule-module`. Regression test:
  `tests/test_custom_rules.py::test_cli_rule_module_is_not_imported_from_target_without_config`.
- Findings 2-3 (LOW) accepted as documented; finding 3 is revisited in 06.0/01 (`--jobs`).
