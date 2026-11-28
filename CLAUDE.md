# CLAUDE.md — Partner Track

Read this file fully before every task. It is the contract between the owner (Reece) and any coding agent working in this repository. It follows Tech Startup Tycoon's CLAUDE.md, with Partner Track's changes.

## 1. What this project is

A single-player, turn-based law firm management game for personal use. The player founds a firm in **January 2005** and grows it, over a **360-turn (30-year)** standard campaign to December 2034, into a global partnership. Interface and people depth follow Football Manager.

- Design source of truth: `docs/spec/game-design-spec.md`.
- Technical decisions: `docs/adr/` (start with `docs/adr/README.md`; Tech Startup Tycoon's ADRs are inherited where that index says so).
- Reece's game-setting decisions: ADR PT-0013.
- Current task: the brief in `docs/tasks/` named in your instructions.

Precedence: on technical matters ADRs override the spec. Any other conflict: stop and ask. Never resolve a conflict by guessing.

## 2. The five rules that matter most

1. **The simulation core is pure.** Code in `backend/ptk/sim/` never imports `ptk.db`, `ptk.api`, `ptk.llm`, `ptk.loader` or `ptk.config`; never reads the clock; never touches the network or filesystem; never uses the global `random` module or `numpy.random` module-level functions. (ADR-0002)
2. **Randomness is seeded and derived.** Get a generator only from `RngFactory.stream(turn, name, *key)` (`ptk.sim.streams`, sim-core's factory on PT's table); one stream name per call site; add new names to `OWN_ROWS` in `ptk/sim/streams.py` and ADR PT-0012's table. (ADR-0002, ADR-0013, ADR PT-0012)
3. **Money is integer cents; hours are integer tenths.** Never floats. Every cash movement is a balanced double-entry `LedgerEntry`. Client money is a separate book and never enters a firm entry. (ADR-0003, ADR PT-0003, ADR PT-0005)
4. **One turn = one database transaction.** A crash mid-turn leaves the save exactly as it was. (ADR-0004)
5. **The LLM proposes, the engine disposes.** LLM output is untrusted, validated and clamped; the LLM never receives hidden true values and never writes state. (ADR-0005)

## 3. Tech Startup Tycoon is read-only

Partner Track shares code with Tech Startup Tycoon (`Reece77/Tech_Executive_Tycoon`) by a **selective transplant** (ADR PT-0001). Clone TST into a separate folder to read and copy; **never commit, push, open pull requests or run workflows there**. Every copied or ported file is listed in `VENDORED.md` with its upstream commit; `tools/check_vendored.py` (in `make check`) fails if an AS IS file drifts. A bug in an AS IS file is reported to Reece for a TST session to fix, then re-copied; do not fix it here.

## 4. Scope discipline

- Build only what the current brief lists; put better ideas under "Follow-ups".
- No systems from a later milestone, not even as stubs (the turn's no-op phases are the exception, by design).
- Dependencies: ADR-0001's list only. Ask before adding any package.
- Do not reformat or refactor files unrelated to the task; never reformat an AS IS vendored file.

## 5. Real people (ADR PT-0013)

Real lawyers and judges appear by name. Never attach misconduct, discipline, malpractice blame, scandals, negative tags, private-life, health or death events to a person flagged `real`; judges' traits are procedural only and never favour a side. Tests enforce this from PT-M3a and PT-M5.

## 6. Repository map

```text
CLAUDE.md  AGENTS.md  VENDORED.md  CHANGELOG.md  Makefile
docs/        spec, adr, tasks, roadmap, balance targets, reuse map, data dictionary
backend/
  ptk/       sim/ (PURE engine), db/, api/, llm/, loader.py, cli.py, config.py
  data/      seed YAML: accounts, scenarios, balance
  migrations/ Alembic
  tests/     unit/ property/ golden/ integration/
frontend/    src/ (api/ is GENERATED: never hand-edit), e2e/
tools/       check_vendored.py, dev.py
```

## 7. Commands

```bash
cd backend && uv sync && uv run pytest -q -n auto      # tests
uv run ptk new-game --name dev --seed 42               # a save in saves/
uv run ptk advance --save dev --turns 12
uv run ptk inspect --save dev
cd frontend && pnpm install && pnpm gen:api && pnpm dev
make check     # vendoring, backend lint, types, tests, API sync, frontend. Must pass.
make e2e       # Playwright smoke tests (set PLAYWRIGHT_CHROMIUM_PATH in cloud sessions)
```

Each session works in its **own clone or worktree**; never share a folder with another session.

## 8. Definition of done (every task)

- [ ] Every acceptance criterion in the brief is met, and you state how each was verified.
- [ ] `make check` and `make e2e` pass.
- [ ] New engine logic has unit tests; randomness has a seeded test; invariants have Hypothesis property tests.
- [ ] Golden snapshots unchanged, or regenerated with `make golden` and the reason in `CHANGELOG.md`.
- [ ] Schema changes have an Alembic migration and `docs/data-dictionary.md` is updated.
- [ ] Tunable numbers live in `backend/data/balance.yaml` with a comment (unit and intent).
- [ ] Decisions the spec and ADRs did not cover are written down (an ADR or the brief's "Decisions made").
- [ ] Final message: summary, files touched, how each criterion was verified, follow-ups.

### Merging

`main` changes arrive through pull requests whose `check` and `e2e` runs are green on a branch up to date with `main`. Merge with a **merge commit** whose message ends with `Milestone-Tag: pt-mX-done`; the `tag-milestone` workflow tags it. Never force-push or rewrite `main`. Commit as `Claude <noreply@anthropic.com>`.

## 9. Conventions

- Python 3.12, full type hints, `mypy --strict` for `ptk/sim`. Sim models are `@dataclass(frozen=True, slots=True)`; return new objects; tuples sorted by id.
- IDs are `int`. Turn 0 = the scenario's start month (January 2005 by default); convert with `ptk.sim.calendar` and the save's `start_ym` only.
- Attributes are floats in [1.0, 20.0], shown as integers; clamp on every write.
- No `print` in library code. Domain errors live in `ptk.sim.errors`.
- Front end: strict TypeScript, TanStack Query and Table, Mantine, dark theme; no game logic; money arrives as integer cents and is shown with `formatMoney()`.
- Seed and balance data are YAML validated by Pydantic at load; invalid data fails at startup.

## 10. Never

- Never expose hidden true values through the API or a prompt.
- Never call the Anthropic API in tests; use `MockLLMAdapter`.
- Never commit secrets (`ANTHROPIC_API_KEY` comes from `.env`).
- Never edit an applied migration or delete golden snapshots to make tests pass; never weaken a test.
- Never write to Tech Startup Tycoon's repository.

## 11. When unsure

Ask one short, specific question with your proposed default. Engineering details you may decide and note in your summary. Tech Startup Tycoon's decision rules (its CLAUDE.md §9) apply here by analogy.

## 12. Balance, seeds and lanes (Reece, 2026-11-25)

These rules settle routine balance outcomes without a decision from Reece or the product manager. "The next balance milestone" is PT-M18 until it merges, then the next one named in `docs/roadmap.md`.

1. **Seeds.** Until PT-M18 merges, targets and nightly guards are judged on seeds 1-10, with seeds 11-40 for seed-luck checks. From PT-M18, every target and guard is judged on seeds 1-40, with thresholds written as shares of seeds.
2. **Seed variance: settle it yourself.** A target or guard that misses on seeds 1-10 but passes on seeds 11-40, on both your branch and `main`, is seed variance. Record a known-miss row (a target) or a non-strict xfail (a guard) owned by the next balance milestone, with both readings for both sides, in the brief's "Decisions made"; then merge. Rule 2 is retired when seeds 1-40 arrive.
3. **Inherited misses: settle them yourself.** A target or guard that fails on `main` too, and is no worse on your branch over seeds 1-40, is inherited: record it as in rule 2 and merge.
4. **Real regressions: stop.** If your branch is worse than `main` over seeds 1-40 (11-40 until PT-M18), first try a fix within the files and keys your lane owns. If that fails, stop and bring the table to the product manager or Reece.
5. **Bounds and markers.** A row you add yourself is bounded at your reading, never wider. Never widen a target's band or change how it is measured: those stay Reece's decisions. Expected failures are non-strict unless the product manager asks for strict.
6. **One owner per simulated system.** Each system's keys and data (its `balance.yaml` section and its data files) belong to the milestone that built it. Once it merges, they pass to the next balance milestone, not to whichever lane merges next. A lane may set values for its own new entities in another system (for example, claim weights for its own new practices), but it does not retune another system's existing keys; if its work moves another system's guard, that is rule 4. This rule applies to lanes launched after 2026-11-25; PT-M12 finishes under the decisions it already has.
