# Milestone 0001 - Generic Implementation

**Package:** `flakeforge` | **Module root:** `src/flakeforge/`

Turn `flakeforge` from "a linter that works when run from the project root" into a
general-purpose tool that works the same way no matter where it is run from or how it
is installed. It must work as a **100% standalone CLI**: point it at any target
directory and optionally pass one TOML file holding its CLI parameters. It must also
work as a **tool configured in the project**, set up through `pyproject.toml`
`[tool.flakeforge]` or a separate `flakeforge.toml`. Tasks 01.0-02.0 cover those two
requirements. Tasks 03.0-06.0 are improvements proposed on top of them.

## Baseline (as-built, 2026-09-24)

Checked against `src/flakeforge/cli.py`, `config.py`, `api.py`, and `registry.py` on
`master` @ `80ae561`, using a scratch project with `flakeforge.toml` = `ignore = ["X001"]`:

| # | Observed behavior                                                                                                                                                                      | Impact                                                              | Fixed by |
|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|----------|
| G1 | `flakeforge check proj` run from outside `proj/` ignores `proj/flakeforge.toml`. `load_config()` searches upward from **cwd**, not from the target path, so X001 is still reported. | The standalone "point at a directory" use case gives wrong results. | 01.0/01  |
| G2 | `output-format` and `--no-rule-plugins` have no TOML key. A config file can't hold the full set of CLI parameters.                                                                    | The config file can't replace the command line.                     | 01.0/02  |
| G3 | There are no `--include` / `--exclude` flags and no way to skip config discovery.                                                                                                     | The CLI alone can't express a whole config.                         | 01.0/03  |
| G4 | `rule_modules` load through a plain `import_module()` and the project root is never put on `sys.path`. A `pipx`/`uvx` install can't import `my_project.lint_rules`.                  | Custom rules only work when flakeforge shares the project's venv.   | 01.0/04  |
| G5 | Unknown keys are silently ignored (`exlude = [...]` is accepted, and so is `output_format` today).                                                                                    | Typos turn off policy without any error.                            | 02.0/01  |
| G6 | If `flakeforge.toml` and `[tool.flakeforge]` sit in the same directory, the pyproject section is dropped without a word.                                                              | It's not obvious which config file is in effect.                    | 02.0/02  |
| G7 | With `--config` and no paths, display names come out relative to cwd (`private/tmp/.../m.py`), not to the config's `base_dir`.                                                       | Output is noisy and depends on where you run it.                    | 02.0/03  |

## Tasks

| Task | Name                              | Category    | Depends on  | Output                                                                                                                                  |
|------|-----------------------------------|-------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| 01.0 | Standalone CLI Mode               | feature     | -           | `flakeforge check <dir> [--config file.toml]` works from any cwd and any install method. Every CLI parameter has a TOML key.           |
| 02.0 | Tool-Mode Config Surfaces         | feature     | 01.0        | `pyproject.toml [tool.flakeforge]` and `flakeforge.toml` share one strict schema, a documented precedence, and config-relative paths. |
| 03.0 | Config Introspection & Bootstrap  | feature     | 02.0        | `flakeforge config show`, `flakeforge rules`, `flakeforge init`                                                                         |
| 04.0 | CI Output Formats                 | feature     | 01.0        | `github` and `sarif` output formats, plus `--statistics`                                                                                |
| 05.0 | Incremental Adoption              | feature     | 02.0        | `per_file_ignores`, a baseline file, and an unused-`# noqa` report                                                                      |
| 06.0 | Scale & Distribution              | feature     | 01.0, 04.0  | `--jobs` parallel checking, an opt-in result cache, and a pre-commit hook                                                               |

Tasks 01.0 and 02.0 are the **required** scope of this milestone. Tasks 03.0-06.0 are
**proposed** improvements. They are fully specified so the loop can run them, but any
of them can be deferred by recording a deferral in `status.md` under
`## Notes & decisions`, without re-planning.

### Dependency graph

```
01.0 ──► 02.0 ──► 03.0
  │        └────► 05.0
  └────► 04.0 ──► 06.0
  └──────────────► 06.0
```

### Risk markers

- **01.0/04 (project-root rule imports) is security-sensitive and requires a
  `security-auditor` pass.** Putting the target project on `sys.path` means that
  linting a repository runs code that the repository controls (`rule_modules`). That
  is true today too, but only for modules that were already importable. The spec must
  make the trust boundary explicit (see C7).
- **06.0/02 (result cache)** writes files to disk. The cache must never cause a
  violation to be missed. On any fingerprint mismatch it must fall back to a full
  check (fail-open to correctness).

## Shared contracts (authoritative)

These bind every task. If a subtask spec disagrees with one of them, the contract wins.

- **C1 - Exit codes are frozen.** `0` = clean, `1` = violations found, `2` = invalid
  config, invalid invocation, or tool failure. No new flag may change what these mean.
  New flags that fail validation exit `2`.
- **C2 - Value precedence.** For every setting: explicit CLI flag > the selected
  config file > built-in default. List flags (`--select`, `--ignore`, `--include`,
  `--exclude`) **replace** the file's value. `--rule-module` **appends** to it (current
  behavior, kept as is).
- **C3 - Config-file selection.** `--config PATH` > `--no-config` (defaults only) >
  discovery. Discovery walks upward from the *discovery anchor* (C4). In each
  directory, nearest first: `flakeforge.toml` > `pyproject.toml [tool.flakeforge]` >
  `pyproject.toml [tool.flake8_lint]` (deprecated). The first directory with a match
  wins.
- **C4 - Discovery anchor.** No path arguments → cwd. One path → that directory (a
  file counts as its parent directory). Several paths → their deepest common ancestor
  directory. Linting several unrelated projects in one run is out of scope.
- **C5 - One schema, two surfaces.** `flakeforge.toml` top-level keys and
  `[tool.flakeforge]` keys are the same set, parsed by the same code. Unknown keys are
  an error (exit `2`) with a did-you-mean hint. The legacy `[tool.flake8_lint]`
  section stays lenient: unknown keys are only a warning there.
- **C6 - Path base.** Path patterns in a config file (`include`, `exclude`,
  `noqa_allowed`, `noqa_forbidden`, `per_file_ignores` keys) resolve against the
  **directory of that config file**. With `--no-config` they resolve against the
  discovery anchor. Display names are relative to `base_dir` when the file sits under
  it; otherwise the path is shown as given.
- **C7 - Rule-module trust boundary.** Project-local `rule_modules` are imported with
  the config's `base_dir` put first on `sys.path`, only while the providers load. The
  previous `sys.path` is restored afterward, even if loading fails. `--no-config`
  implies that no project rule modules load. `--rule-module` on the CLI remains an
  explicit opt-in.
- **C8 - Zero runtime dependencies.** `[project].dependencies` stays `[]`. Flake8 stays
  an optional integration. Python 3.11+ `tomllib` only, so there is no TOML *writer*
  dependency: `init` (03.0/03) emits text from templates.
- **C9 - Deterministic output.** Every output format orders violations by (filename,
  line, column, code), whatever the `--jobs` value (06.0/01).

## Open decisions (ratify before the dependent subtask starts)

- **D1 - Code for an unused `# noqa` (05.0/03).** Either (a) a new built-in code
  `X015` emitted by the engine, or (b) a separate CLI-level report that has no rule
  code. Recommendation: (a). The repo convention is append-only codes, and a code can
  be selected and ignored like any other. It needs the full built-in-rule lockstep
  (registry, tests, sample file, docs).
- **D2 - Baseline fingerprint (05.0/02).** Recommendation: `sha256(code + relative
  path + normalized source line text)` plus an occurrence index. This survives line
  shifts, and editing the flagged line re-surfaces the violation.

## Milestone exit gates

1. `pytest --cov=flakeforge` is green on Python 3.11-3.14. Line coverage must not drop
   below the value measured at milestone start.
2. `ruff check .` and the `flakeforge` self-check subset used in CI are clean.
3. The CI `wheel-smoke` job is extended with the standalone scenarios from 01.0/05,
   and the precedence matrix from 02.0/04 is green.
4. A `security-auditor` pass on 01.0/04 has no open CRITICAL findings.
5. README, `docs/architecture.md`, and `docs/custom-rules.md` describe the as-built
   behavior. `/link-check` is clean.
