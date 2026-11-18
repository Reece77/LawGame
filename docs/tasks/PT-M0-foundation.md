# PT-M0: Foundation

**Goal:** a new repository that already obeys Tech Startup Tycoon's five rules: a pure, seeded simulation core with integer-cent double-entry books, one transaction per turn, the LLM adapter seam, and the UI shell, starting in January 2005 with an empty firm that can press Continue for 360 months.

**ADRs:** TST 0001–0005, 0007–0009, 0012–0014; PT-0001, PT-0002, PT-0003 (chart only), PT-0005, PT-0012 · **Spec:** §1, §4, §16 (shell) · **Reuse map:** §1.1, §2, §4 (shell), §5 · **Depends on:** — · **Lane:** A

## Reece's decisions

- Tech Startup Tycoon (`Reece77/Tech_Executive_Tycoon`) is **read-only**: clone it into a separate folder to read and copy.
- Code is shared by a **selective transplant** with provenance (ADR PT-0001), pending Reece's confirmation of that ADR.

## Out of scope

People, matters, clients, rivals, events (each a later milestone). No stub modules for them.

## Sub-tasks (commit after each)

1. **Repository and tooling.** `partner-track` with `backend/ptk/`, `frontend/`, `docs/`, the TST `Makefile` targets, `ruff.toml`, `uv`, `pnpm`, pre-commit, CI workflows (`check`, `e2e`, `determinism`, `nightly`, `tag-milestone`) adapted from TST's with the tag pattern `pt-m*-done`. `CLAUDE.md` and `AGENTS.md` adapted from TST's (same five rules, same definition of done, the repository map, the stream table pointer, the read-only rule for TST).
2. **Vendored kernel.** Copy AS IS from TST at one recorded SHA: `rng.py`, `money.py`, `ledger.py`, `dmath.py`, `scale.py`, `log.py`, `decisions.py`, `errors.py` (base classes and generic errors only), `llm/` (base, Anthropic, offline, settings), `db/session.py`, `migrate.py`, `backup.py`, `saves.py`, `history.py` (framework), `holiday.py`, `ui_settings.py`, `mods/`. Write `VENDORED.md` (file, TST path, SHA, AS IS or ported) and `tools/check_vendored.py` (fails when an AS IS file differs from its recorded upstream content without a `VENDORED.md` note).
3. **Calendar from data** (ADR PT-0002): `scenarios.yaml` `start_ym` (default 2005-01); `turn_to_ym` and `ym_to_turn` take it from `GameData`; tests for 2005 and 2010 bases.
4. **Chart of accounts** (ADR PT-0003 §1) in `accounts.yaml`, the client book's accounts, and the starting capital entry (debit cash, credit partners' capital by partner).
5. **State and turn.** `GameState` (save meta, firms, empty tuples for later systems), the 12 phases as no-ops with PT names (spec §4.1) in fixed order, `advance_turn` with TST ADR-0012's signature, `TurnResult`, snapshot.
6. **Persistence and API.** Alembic schema v1, one file per save (`.ptk.sqlite`), transactional turns, backups every 12 turns, FastAPI app with `new-game`, `advance`, `state`, `saves`; OpenAPI and the generated TS client; CLI `ptk new-game`, `advance`, `inspect`.
7. **Front end shell.** Copy TST's shell, tables, Explain plumbing, command palette, hotkeys, tokens and fonts; screens: Main menu, New game (scenario, difficulty, firm name), Overview (date, cash, Continue), Saves, Settings (LLM budget meter).
8. **Guards.** Port TST's purity test, turn-order test, stream-uniqueness test, ledger and clamp property tests, migration-chain test, golden-snapshot and state-cache frameworks; add golden seeds 1–3 for 360 empty turns.

## Acceptance criteria

- [ ] `make check` and CI green; `check_vendored.py` passes.
- [ ] A new game in January 2005 advances 360 turns headless (`ptk advance --turns 360`) and ends in December 2034; the save reloads cold at any turn.
- [ ] Killing the process mid-turn leaves the save at the previous turn (test).
- [ ] Every ledger entry balances; assets = liabilities + equity each month (property test).
- [ ] The purity test fails if `ptk/sim` imports `ptk.db`, `ptk.api`, `ptk.llm`, `random`, `time` or the filesystem.
- [ ] Merged through a pull request with `Milestone-Tag: pt-m0-done`.

## Manual check (Reece)

Start the game with the launcher, create a firm, press Continue a few times, close and reopen the save.

## Decisions made

## Follow-ups
