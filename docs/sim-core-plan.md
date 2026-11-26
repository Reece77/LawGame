# `sim-core` extraction plan (PT-M19 checkpoint)

**Status: PROPOSED, for Reece's decision (2026-11-26).** This is the checkpoint set by ADR PT-0001 §5 and `docs/v3-outline.md` ("The `sim-core` checkpoint is now due"). It was written by reading TST (`Reece77/Tech_Executive_Tycoon`, read-only) at `main` `3da2f5b` (M54 merged; M55 and M52 still running; M57 not yet briefed) and Partner Track at `main` `0329497` (PT-M12's fix merged; PT-M18 not started). Plaza's accepted reuse map (PL-D0, "Plaza Reuse Map v0.1", 2026-11-26) is an input, and its §8 asks are treated as requirements. Nothing here has been built. Every line count is measured with `wc -l` or an import scan on those commits; every cost is an estimate.

## The answer first

- **Does the extraction cost at most two milestones?** **Yes, for the route Plaza needs; no, for moving all three games.**
  - **Two milestones** give a `sim-core` 0.2 that Partner Track runs on with unchanged golden snapshots and state cache, and that Plaza can start on: **SC-1** builds the package (kernel, registries, books, cases, governing body, interfaces, persistence, LLM) in a new repository; **SC-2** moves Partner Track onto it and lifts PT's people, hiring, org, automation, events, founder and family into it.
  - **Moving TST as well costs three more** (five in all): one to put TST on the kernel and the registries without changing a single draw (**SC-3**), and about two to replace TST's own rich modules with the shared ones (**SC-4**), which changes TST's behaviour, re-records its golden snapshots and M30's state cache, and needs a balance pass. SC-3 and SC-4 need TST sessions Reece authorises, and they freeze TST's lanes while they run.
- **Recommendation:** extract now on the two-milestone route; Plaza starts on `sim-core` 0.2, so ADR PL-0001's transplant fallback is **not** triggered. TST takes SC-3 after it closes v6 (M57), as its roadmap's deferred M56; **SC-4 is deferred** and decided later, only if a shared world (spec §19 idea 12) or a third rich consumer makes it worth TST's balance cost.
- **Sequencing:** SC-1 runs beside PT-M18 (it touches no PT file); SC-2 runs **alone** after PT-M18 merges and **before** PT-M19's world framework writes any code, because PT-M19's multi-currency ledger belongs in `sim-core`'s ledger, not in a third copy of it.

## 1. What the code says (the measurements behind the plan)

1. **Partner Track removed TST's industry imports but added law imports in their place.** Plaza's map (finding 1) says PT "already paid the de-tech cost". That holds for products and markets, but PT's general modules now import law modules instead. Import sites from a candidate core module into a PT domain package (not the kernel, not another core module, and not `state`, `data_models` or `interfaces`):

   | PT module | Lines | Domain imports | Into |
   | --- | ---: | ---: | --- |
   | `people/` | 1,455 | 0 | — |
   | `founder/` | 2,515 | 0 | (2 through `interfaces`) |
   | `family/` | 1,527 | 0 | (2 through `interfaces`) |
   | `events/` | 2,731 | 2 | `matters` |
   | `hiring/` | 2,354 | 10 | `geo` 5, `matters` 2, `rankings`, `reputation`, `macro` |
   | `actions/` | 216 | 10 | one each from ten domain packages (the dispatcher) |
   | `org/` | 4,307 | 16 | `matters` 6, `partnership` 4, `geo` 3, `rivals` 2, `billing` |
   | `automation/` | 2,424 | 21 | `partnership` 8, `matters` 5, `tech` 3, `risk` 3, `billing`, `rivals` |

   Every one of them also imports `GameState` and `GameData` directly (people 9 times, org 23, automation 14). So PT is a much better starting point than TST (TST's `org` imports 16 other packages at 72 sites, and `automation` 22 at 105), but it is not extraction-ready: about 60 import sites must go through interfaces, and the monolithic state and data imports must become registered sub-states and data sections.

2. **The two copies have already diverged.** Share of identical lines between PT's port and TST's current file (after the `tst` → `ptk` rename): `people/` 0.56–0.80, `events/director.py` 0.55, `hiring/phases.py` 0.26, `org/authority.py` 0.11, `org/pitches.py` 0.10, `automation/rules.py` 0.12, `founder/phase.py` 0.12, `family/succession.py` 0.08, `family/estate.py` 0.08. The "intersection of the two codebases" that ADR PT-0001 §5 imagined is small outside the kernel and people. `sim-core`'s rich modules will therefore be **one game's version made generic**, and the other game's adoption changes that game's behaviour. Partner Track's versions are the better base (fewer imports, already composed state), so TST is the one whose behaviour would move (SC-4).

3. **The "AS IS" copies are already stale.** Of the 12 backend Python files `VENDORED.md` lists as AS IS, 6 differ from TST's `main` today (changed lines after the rename): `llm/base.py` (94), `llm/anthropic_adapter.py` (37), `llm/offline.py` (24), `llm/settings.py` (13), `config.py` (4) and `db/backup.py` (3). `tools/check_vendored.py` passes because it checks against the hash recorded at `02fba2aa`, not against TST's head. This is the drift ADR PT-0001 predicted, nine days in, and v3 would add four more ported TST modules (`markets_public/`, `talks/`, `modes/`, `dynasty/`).

4. **State and turn wiring.** PT's `GameState` has 25 fields, 20 of them already per-system sub-states (`org`, `billing`, `risk`, …); its `turn.py` has 12 phase functions and 40 `ptk.sim` imports. TST's `GameState` has **225 fields** (Plaza's map and PT's reuse map said about 150: it has grown by half in v5–v6) and its `turn.py` has 92 `tst.sim` imports. Composable sub-states and a phase registry are a modest refactor in PT and a large one in TST.

5. **Two of Plaza's asks already have a working seed in PT.** PT's ledger already rejects entries that mix books (the personal book `9…` from TST 32.2 and the client-money book `C…` from ADR PT-0003 §7). PT's `risk/` already runs three staged cases (malpractice claims, discipline cases, regulators' inquiries), each with `stage`, `stage_until`, ranges and seeded outcomes, beside TST's `regulation/cases.py`. PT's `partnership/` (governance, election, flight) and TST's `finance/board.py` are the two governing bodies to abstract.

6. **TST's own roadmap already reserves the slot.** `docs/roadmap.md` in TST lists "M56, the shared core (deferred unless the law firm game outgrows a fork)". SC-3 is that milestone.

## 2. Module list with marks

Marks:

- **CORE**: moves into `sim-core` and is deleted from the game; the game imports it.
- **FRAMEWORK**: the mechanism moves into `sim-core`; each game keeps its own bodies (rules, kinds, effects, data) as registered providers.
- **NEW**: written in `sim-core` for Plaza's §8 asks, from the named seeds.
- **LATER**: a `sim-core` candidate, not in 0.x; it waits for a second real consumer (the rule of two).
- **GAME**: stays in each game.
- **UI-VENDORED**: the canonical copy lives in `sim-core/ui/`; games copy it with a hash check (section 3).

Source: where `sim-core`'s version comes from. Release: the `sim-core` version that first carries it.

### 2.1 Kernel and turn machinery

| Module | Source | Mark | Release | Notes |
| --- | --- | --- | --- | --- |
| `rng.py` | TST (derivation), PT (table form) | CORE | 0.1 | The derivation (`SeedSequence`, `turn_key`, ADR-0024's negative turns) unchanged to the bit; `STREAM_IDS` becomes a registry (section 4) |
| `money.py`, `dmath.py`, `scale.py`, `decisions.py` | TST (identical in PT) | CORE | 0.1 | Byte-identical in both games today |
| `log.py` | TST | CORE | 0.1 | |
| `calendar.py` | PT | CORE | 0.1 | Turn 0 as a data value (ADR PT-0002) plus TST's negative turns (ADR-0024) |
| `errors.py` | both | CORE (base classes) | 0.1 | Base and generic errors only; domain errors stay in each game, subclassing them |
| `ledger.py` | PT | CORE + NEW | 0.1 | The multi-book ledger (section 2.4) |
| `snapshot.py`, `score.py`, `whatnext.py` | PT | FRAMEWORK | 0.1 | Mechanism through `KpiProvider`; each game's KPIs stay |
| `state.py` | PT (pattern) | NEW | 0.1 | Composable sub-states (section 2.4); each game's sub-states stay GAME |
| `turn.py` | PT (pattern) | NEW | 0.1 | The phase registry (section 2.4); phase bodies stay GAME |
| `interfaces.py` | PT | FRAMEWORK | 0.1 | `WorkSource`, `KpiProvider`, `AreaRule`, `EffectType` and the hooks PT already uses (delegate hiring, partner flight's shape); the law-specific views (`MatterBillingView`, `ClientBillingView`, …) stay in PT |
| `data_models.py` | PT | FRAMEWORK | 0.1 | Pydantic schemas for shared YAML (personality, interests, tags, names, skills and roles schemas, events); each game registers its own data sections |
| `setup.py`, `unlocks.py`, `coo.py` | — | GAME | — | Thin and game-shaped |

### 2.2 People and organisation

| Module | Source | Mark | Release | Notes |
| --- | --- | --- | --- | --- |
| `people/` (models, formulas, generator, growth, reveal, founder build) | PT | CORE | 0.2 | No domain imports today; skills and roles from data; strain as an optional per-person component |
| `hiring/` (searches, offers, acceptance, payroll, morale, resignation, tag reveals) | PT | CORE | 0.2 | PT's campus cycle and salary scale stay GAME as a channel provider; the 10 domain imports become a `RecruitContext` provider |
| `org/` units, delegates, span and manager quality, reports, rules | PT | CORE | 0.2 | The practice-group noun becomes a game-defined unit kind |
| `org/` seats, authority, pitches | PT | CORE | 0.2 | Seats data (`seats.yaml`) stays GAME; `org/practices.py` (entering a practice) stays GAME |
| `actions/` (ADR-0014 framework) | PT | FRAMEWORK | 0.2 | The dispatcher becomes a registry; each action body registers from its own package |
| `automation/` (areas, owners, limits, one-offs, digest, run) | PT | FRAMEWORK | 0.2 | Areas register through `AreaRule`; PT's area rules (billing, partnership, risk, tech) stay GAME |
| `founder/` (persona, stress, personal book, legacy, foundation) | PT | CORE | 0.2 | No domain imports today |
| `family/` (members, life events, adviser, estate, succession trigger) | PT | CORE | 0.2 | No domain imports today; who succeeds is the governing body's (2.4) |
| `rivals/` utility AI | PT | LATER | — | Plaza marks it "AI only"; PT's and TST's rivals differ in kind. Revisit after Plaza's rivals exist |

### 2.3 Events, persistence, LLM, front end

| Module | Source | Mark | Release | Notes |
| --- | --- | --- | --- | --- |
| `events/` director, slots, severity caps, storylines, modifiers, render | PT | FRAMEWORK | 0.2 | Triggers and effects register through `EffectType`; templates and the event library stay GAME |
| `ptk/events/` (service, validator) | PT | FRAMEWORK | 0.2 | The validator's clamp and schema checks are core; content rules (PT's real-people rule, Plaza's content rules) register as validators |
| `db/` session, migrate, backup, saves, history framework, inbox | TST (newest) | CORE (`simcore_db`) | 0.1 | One SQLite file per save, one transaction per turn (ADR-0004). Each game keeps its own tables, mappers and Alembic chain; `sim-core` owns no table |
| `llm/` base, anthropic adapter, offline, settings, mock | TST (newest) | CORE (`simcore_llm`) | 0.1 | Takes TST's current versions (finding 3); hidden values never reach a prompt (ADR-0005, ADR-0023) |
| `api/` errors mapping, interruptions, Explain plumbing | TST | LATER | — | Small; vendored until a second release |
| Front end: shell, tables, Explain, help, inbox, Holiday, saves, settings, `formatMoney`, `attr.ts` | TST | UI-VENDORED | 0.1 | Section 3 |
| `negotiation/`, `meetings/`, `talks/`, `conversations/` | TST | LATER | 0.3+ | Plaza marks them core; PT ports them in PT-M28. They enter `sim-core` once two games run them |
| `modes/`, `dynasty/` | TST | LATER | 0.3+ | PT ports them in PT-M29 and PT-M31; same rule |
| `geo/` | PT | LATER | — | PT-M19 rebuilds it for the world; enter after PT-M19 if Plaza's plazas sit on it |
| Every industry or law module (`matters`, `billing`, `partnership` bodies, `risk` bodies, `products`, …) | — | GAME | — | |

### 2.4 Plaza's five asks, as `sim-core` components

1. **Phase registry and composable sub-states** (NEW, 0.1).
   - `SubState` protocol: a frozen dataclass with a key, an empty value, a schema version and a digest contribution. `GameState` becomes `CoreState` (save meta, turn, the entities `sim-core` owns: people, employments, reveals, and the core sub-states) plus a sorted mapping of registered sub-states. Access is typed (`state.sub(BillingState)`), and replacement returns a new state.
   - `PhaseRegistry`: the 12 ADR-0012 slots stay; a game registers `(slot, name, fn, after=…, before=…)`; the order inside a slot is a deterministic topological sort with name as the tie-break, frozen at start-up and printed by a test. Registration order and import order cannot change it.
   - The acceptance test for SC-2 is that PT's registered order reproduces today's hand-wired `turn.py` exactly (golden snapshots and `state_hashes.json` unchanged).
2. **Multi-book ledger** (NEW, 0.1). A book is declared data: `Book(code, prefix, owner)`. PT declares `firm`, `personal` (`9`) and `client_money` (`C`); TST declares `company` and `personal`; Plaza declares `dirty` and `clean`. Every entry balances within one book; an entry that touches two books is refused, as today. Movement between books is a declared `BookBridge(from, to, rule)`: a pair of linked entries (for Plaza, laundering with leakage; for PT, a transfer from client money to the firm for a paid bill). Currency is a second dimension in 0.1's design (integer minor units per currency, a functional currency per reporting unit, translation to a reporting currency), so that PT-M19 implements its multi-currency ledger there, not in PT. A single-book, single-currency game (TST today) sees no change.
3. **Generic case machinery** (NEW, 0.2; seeds PT `risk/` and TST `regulation/cases.py`). `CaseKind` declares its stages (with length ranges), the odds shown as a range around a hidden true value, the warnings shown ahead, the player's responses at each stage (settle or contest, plea or trial) and the outcomes with their effects (through `EffectType`). The machinery runs the stage clock, the draws and the reveal; every draw uses a stream the game passes in (section 4). PT's claims, discipline cases and inquiries become three `CaseKind`s; Plaza's investigations, raids, indictments and trials four more.
4. **Governing-body abstraction** (NEW, 0.2; seeds PT `partnership/governance.py`, `election.py`, `flight.py` and TST `finance/board.py`). A `GoverningBody` has members with weights, each member's confidence in the leader, motions with thresholds (in basis points), votes with seeded noise, removal of the leader, and succession that always yields a leader or a defined vacancy. PT's partnership, TST's board and Plaza's council are bodies; their compensation, capital and tribute rules stay GAME.
5. **Interfaces tested against Plaza before they freeze** (FRAMEWORK, 0.1–0.2). `sim-core`'s tests carry three fixture consumers (`tests/consumers/pt_like`, `tst_like`, `plaza_like`). `plaza_like` implements Plaza's **heat** (per person, site, route and organisation, slow decay: a `KpiProvider`, an `EffectType` and a sub-state) and **territory** (plazas with control, tax yield and contest: an `AreaRule`, a `WorkSource` and a sub-state), written from Plaza's design, not from its code. The interfaces stay 0.x (changeable) until Plaza's first territory milestone (PL-M3a) runs on them; they freeze at 1.0.

## 3. Package layout and versioning

**Repository:** a new private repository, `Reece77/sim-core`, created by Reece (no session may create repositories). It is written only by sessions Reece names for an SC milestone, through pull requests, with the same rules as TST and PT (pure core, seeded randomness, integer cents, merge commits, milestone tags `sc-N-done`).

```text
sim-core/
  CLAUDE.md  AGENTS.md  CHANGELOG.md  Makefile
  docs/adr/                  SC-0001 onwards; inherits TST ADR-0001..0005, 0012..0014, 0024
  pyproject.toml             one distribution, three import packages
  simcore/                   PURE: never imports simcore_db, simcore_llm or any game
    kernel/                  rng, money, ledger (books, bridges, currencies), dmath, scale,
                             log, decisions, calendar, errors, snapshot
    state/                   SubState protocol, CoreState, registry, digest
    turn/                    slots, PhaseRegistry, TurnContext
    interfaces/              WorkSource, KpiProvider, AreaRule, EffectType, hooks
    data/                    shared Pydantic schemas and a DataRegistry
    people/ hiring/ org/ actions/ automation/ events/ founder/ family/
    cases/                   CaseKind, stages, odds ranges, outcomes
    governance/              GoverningBody, motions, votes, removal, succession
  simcore_db/                session, migrate helpers, backup, saves, history, inbox
  simcore_llm/               adapter base, anthropic, offline, mock, settings
  ui/                        canonical shell, tables, Explain, inbox, formatMoney, attr.ts
  tests/                     unit, property, determinism corpus, consumers/{pt,tst,plaza}_like
```

**How games depend on it.**

- **Python:** a uv git dependency pinned to a tag, `simcore @ git+https://github.com/Reece77/sim-core@v0.2.0`, locked to its commit in `uv.lock`. No package index is needed. CI and cloud sessions need read access to the private repository: a fine-grained read-only token as an Actions secret in each consumer (decision 3).
- **Front end:** the `ui/` folder is copied into each game's `frontend/src/core/` with `tools/check_vendored.py` checking it against the pinned `sim-core` tag (not TST's commit). A pnpm git dependency on a subfolder is possible, but not worth the build friction for about 4,000 slow-changing lines; revisit at 1.0.
- `VENDORED.md` shrinks to the UI files and the TST modules v3 still ports (`markets_public/`, `talks/`, …) until they enter `sim-core`.

**Versioning (SemVer, with determinism as the contract).**

- **Patch** (0.2.x): no change to any result. Proved by `sim-core`'s own determinism corpus and by every consumer's golden snapshots and state cache, run against the candidate in `sim-core`'s CI before the tag.
- **Minor while 0.x, major from 1.0**: any change to an interface **or to any draw, rounding or result**. It ships with a CHANGELOG note saying which consumers' snapshots move and why. A consumer upgrades in its own milestone and re-records its snapshots there, under its own CLAUDE.md rule.
- A consumer never pins a branch (a test fails on a non-tag pin). Bug flow becomes `sim-core`-first: a bug in a core module is fixed in `sim-core`, released as a patch (or a minor if it changes results), and taken up by each game.

## 4. The RNG stream table policy

The derivation never changes: `SeedSequence(entropy=master_seed, spawn_key=(turn, id, *key))`. A stream's id is part of every draw, so ids can never be renumbered without moving every snapshot. The policy keeps every game's existing draws as they are.

1. **Ids 1–19 are `sim-core`'s, with TST's names and meanings**, as ADR PT-0012 already keeps them: `people_gen` 1, `hiring` 2, `morale` 3, `events` 6, `founder` 7, `growth` 8, `reveal` 9, `tags` 10, `resign` 11, `retire` 12, `actions` 13, `delegate` 14, `poach` 19.
2. **Id 17 is renamed `governance`** (TST's `board`, PT's `partnership`); both games' existing names stay as registered aliases of id 17, so neither game's draws move.
3. **Ids 4, 5, 15, 16 and 18 are reserved "game-defined"** (TST's `market`, `rivals`, `product_dev`, `finance`, `rival_spawn`): `sim-core` never draws on them, TST keeps them, and no other game may register them.
4. **A core module draws only on ids 1–19, or on a stream name its caller passes in.** The case machinery, the governing body's vote noise, automation's quality draw and the event director's per-kind draws take the stream from the registering game. So PT's `risk_case` 141, `vote` 28 and `auto_quality` 60, and Plaza's future streams, stay each game's own, and SC-2 moves no draw.
5. **Ids 200–299 are reserved for streams `sim-core` itself adds later**, above every id in use (TST's highest is 99, PT's 147). Id 99 `misc` stays for tests in every game.
6. **Ids 20–199 and 300+ are each game's own table**, registered at start-up (`register_streams(game_table)`). Registration fails on an id or name that collides with the core range, with an alias, or within the game. TST and PT already overlap in 20–99. That is harmless while every save belongs to one game.
7. **Plaza** registers its table from 20 as PT did, avoiding 200–299.
8. **A shared world later** (spec §19 idea 12, which v3 must not preclude) would add a game-namespace part to the spawn key **only in shared-world saves**, so single-game saves keep their draws. This plan reserves the policy and builds nothing for it.
9. ADR PT-0012's table stays the PT record. `sim-core` gets ADR SC-0002 with the core rows and these rules, and a test that freezes ids 1–19 and 200–299.

## 5. Migration order

| Step | Milestone | Where | Runs | What | Exit test |
| --- | --- | --- | --- | --- | --- |
| 0 | This plan | PT docs | now | Reece's decisions (section 9); Reece creates `Reece77/sim-core` and adds it to the authorised sessions | Decisions recorded in `docs/v3-outline.md` |
| 1 | **SC-1**, `sim-core` 0.1 | `sim-core` | beside PT-M18 (touches no PT or TST file) | Kernel from TST's newest files with PT's calendar; stream registry; `SubState` and `PhaseRegistry`; multi-book, multi-currency ledger design and code; interfaces; `simcore_db`, `simcore_llm`; `ui/`; the guard suite (section 6); the three fixture consumers, with Plaza's heat and territory providers | `make check` in `sim-core`; the determinism corpus equals TST's and PT's `RngFactory` output for a fixed grid |
| 2 | **SC-2**, PT on `sim-core` 0.2 | PT, then `sim-core` | **alone**, after PT-M18 merges, before PT-M19's code | PT replaces its kernel, state and turn wiring with the registries (its 20 sub-states register; its 12 phases register in today's order). It lifts `people/`, `hiring/`, `org/` (with seats, authority and pitches), `actions/` and `automation/` frameworks, the `events/` framework, `founder/` and `family/` into `sim-core`, behind interfaces, and releases 0.2. The case machinery and governing body land in 0.2 from PT's `risk/` and `partnership/` | **PT's golden snapshots and `state_hashes.json` unchanged**; `make check`, `make e2e`, T12's timing gate within its budget; `VENDORED.md` reduced |
| 3 | PT-M19 onward | PT | as planned | The world framework uses `sim-core`'s currency dimension (any ledger change is a `sim-core` minor release made in PT-M19's lane) | PT-M19's own criteria |
| 4 | Plaza PL-M0 onward | Plaza | from `sim-core` 0.2 | Plaza depends on `sim-core`; its heat and territory milestones replace the fixtures with the real providers; 1.0 freezes after PL-M3a | Plaza's own |
| 5 | **SC-3**, TST on the kernel and registries | TST (a TST session Reece authorises) | alone in TST, after M57 closes v6 (TST's M56 slot) | TST takes `simcore` (kernel, `simcore_db`, `simcore_llm`), registers its 225 fields as sub-states in groups and its 92 phase calls in the registry. Its own people, org, automation, events, founder and family stay TST's | **TST's golden snapshots and M30's state cache unchanged** |
| 6 | **SC-4**, TST on the shared rich modules | TST | deferred; decided after SC-3 | TST replaces its rich modules with `sim-core`'s, through providers for products and markets; re-records its snapshots and state cache; a balance pass | TST's balance targets on seeds 1–40 |

**Cut line inside SC-2.** If SC-2 runs long, `automation/` and `founder/`/`family/` may stay in PT and move in 0.3. Plaza's v1 needs neither from the core: its map marks family as v2 and its automation areas as new. 0.2 then ships kernel, registries, books, people, hiring, org, events, cases and governance, which is what Plaza needs to start. That cut is what keeps the route to two milestones.

## 6. Guard tests

In `sim-core` (all in its `make check`):

1. **Purity** (ported from both games' `test_sim_purity.py`): `simcore` never imports `simcore_db`, `simcore_llm`, any game package, the clock, the network, the filesystem, the global `random` or module-level `numpy.random`.
2. **No game nouns**: a lint test fails if `simcore/` names a game concept (matter, practice, partner, product, plaza, cell, client, …; the list lives in the test).
3. **Determinism corpus**: hashes of `RngFactory(seed).stream(turn, id, *key)` output over a fixed grid (seeds, turns including negative ones, ids 1–299, keys), recorded once and never re-recorded. It also checks `money` rounding and `dmath` on fixed inputs. A change here moves every game, so it can never ship as a patch.
4. **Stream registry**: ids 1–19 and 200–299 frozen; collisions, alias clashes and unknown names fail at registration; every `stream(` call site in `simcore/` uses a core name or a passed-in name (the call-site enumeration test from both games).
5. **Ledger** (Hypothesis): every entry balances within its book and currency; an entry touching two books is refused; a bridge's two entries balance and are linked; translation preserves each book's totals in its functional currency; integer cents only (TST's `money_guard`).
6. **Clamp properties**: attributes stay in [1.0, 20.0] through every people, growth and event path.
7. **Phase registry**: the order is the same for any registration or import order; an unknown slot or a cycle fails; the frozen order is printed and compared.
8. **Sub-states**: every registered sub-state is frozen, has an empty value, round-trips through the save mapper contract and contributes to the state digest; a save missing a registered sub-state fails to load.
9. **Hidden values**: core view types (candidate, person, case and body views) carry only revealed ranges; a test fails if a view exposes a field marked hidden.
10. **Cases and governance**: shown odds ranges contain the true odds; stages never skip; seeded outcomes repeat; a vote's result is the same for any member order; succession always yields a leader or a defined vacancy.
11. **Consumer contracts**: `pt_like`, `tst_like` and `plaza_like` each build a state, register their phases and run 24 turns twice with identical digests. `plaza_like`'s heat and territory providers must pass before any interface is marked stable.
12. **Downstream check**: `sim-core`'s CI checks out PT's `main` (later TST's and Plaza's), pins it to the candidate commit and runs its golden snapshots and state cache. A release whose downstream snapshots move must be a minor (0.x) or major release.

In each game:

13. **Unchanged across the move**: SC-2 (PT) and SC-3 (TST) succeed only if golden snapshots and the state cache are unchanged. No re-recording is allowed in an extraction milestone.
14. **Tag pin**: a test fails if `simcore` is pinned to anything but a release tag.
15. **No shadow copies**: a test fails if a game file under `ptk/sim/` (or `tst/sim/`) duplicates a `sim-core` module's path or public names.
16. **Turn time**: T12's gate (PT) and TST's timing budgets must stay within their budgets after the registries' indirection.

## 7. Cost in milestones

| Milestone | Repository | Estimate | Main work |
| --- | --- | --- | --- |
| SC-1 | `sim-core` | 1 | About 9,000 lines: kernel, registries, books, interfaces, db, LLM, UI and the guard suite, mostly moved, about 2,500 new |
| SC-2 | PT, `sim-core` | 1 (the risky one) | About 17,500 lines move from PT (people 1,455, hiring 2,354, org 4,307, actions 216, automation 2,424, events 2,731, founder 2,515, family 1,527), about 60 domain imports re-routed, cases and governance (about 3,000 new) |
| **Plaza's route** | | **2** | `sim-core` 0.2 at about 28,000 lines, inside ADR PT-0001's 25,000–35,000 |
| SC-3 | TST | 1 | 225 fields into sub-states, 92 phase imports into the registry, kernel swap; no behaviour change |
| SC-4 | TST | about 2 | TST's rich modules replaced; snapshots re-recorded; a balance pass |
| **All three games** | | **about 5** | |

## 8. Risks

1. **Byte-identical moves are hard.** Any reordered draw, changed float operation or changed tuple order moves PT's snapshots. *Mitigation:* SC-2 moves code first and redesigns nothing it does not have to; its exit test is unchanged snapshots; the cut line keeps it at one milestone.
2. **SC-2 is large for one milestone** (about 17,500 lines touched). *Mitigation:* the cut line (section 5); a single owner; no other PT lane open.
3. **Interfaces frozen too early, designed without Plaza's code.** *Mitigation:* 0.x until PL-M3a; Plaza's heat and territory fixtures; a minor release is cheap while there are two consumers.
4. **TST diverges further while it waits** (its `GameState` grew from about 150 fields to 225 since 2026-11-17). *Mitigation:* SC-3 changes no behaviour and is sized by mechanical work; SC-4 is an explicit later choice, not an implied debt.
5. **Three repositories add friction**: private access for CI and cloud sessions, a release before each consumer can use a fix, version bumps in each game. *Mitigation:* tag pins, a release workflow, the downstream check, one read-only token per consumer.
6. **PT-M19's ledger built twice.** *Mitigation:* SC-1 designs currencies into the books; SC-2 lands before PT-M19's code; PT-M19 extends `sim-core`'s ledger through a minor release.
7. **Turn time.** The registries add one indirection per phase and sub-state access. *Mitigation:* guard 16; registration and order are fixed at start-up, not per turn; access is a mapping lookup.
8. **Stale "AS IS" copies until SC-2** (finding 3). *Mitigation:* SC-1 takes TST's newest `llm/` and `db/` files; until then, nothing changes in PT, because re-copying now is churn that SC-2 replaces.
9. **Scope creep**: conversations, modes, dynasty and rivals are attractive core candidates. *Mitigation:* the rule of two; they are LATER until a second game runs them.
10. **Plaza waits on SC-2.** If SC-2 slips past one milestone even after the cut line, Plaza's ADR PL-0001 fallback (transplant) still applies, and Plaza can transplant from `sim-core` 0.1 plus PT, which is no worse than today.

## 9. Decisions for Reece (proposed defaults)

1. **Extract on the two-milestone route** (SC-1 beside PT-M18, SC-2 alone before PT-M19's code), and tell Plaza that ADR PL-0001's fallback is not triggered. *Default: yes.*
2. **A new private repository, `Reece77/sim-core`**, created by Reece, written only by sessions he names for SC milestones (Partner Track sessions keep never writing to TST). *Default: yes.*
3. **CI access**: a fine-grained, read-only token for `sim-core` as an Actions secret in PT (later TST and Plaza), so consumers' CI can install the tagged package and `sim-core`'s CI can run their snapshots. *Default: yes.*
4. **Base versions**: Partner Track's for people, hiring, org, automation, events, founder and family; TST's newest for `llm/`, `db/` and the UI shell; PT's calendar. *Default: yes.*
5. **PT-M19's slot**: SC-2 runs as "PT-M19a" before the world framework, and PT-M19's multi-currency ledger is built in `sim-core`. *Default: yes.*
6. **TST's extent**: SC-3 only (kernel and registries, no behaviour change), as TST's M56 after M57 closes v6; SC-4 deferred and decided after SC-3. *Default: yes.*
7. **Stream policy** as in section 4 (1–19 core with TST's meanings, 17 renamed `governance` with aliases, 4/5/15/16/18 game-defined, 200–299 reserved for the core, core machinery draws on streams passed in). *Default: yes.*
8. **No re-recording in extraction milestones**: SC-2 and SC-3 must leave golden snapshots and state caches unchanged; a move that cannot is cut to the next release. *Default: yes.*
9. **Versioning**: SemVer, with any change to a result counted as breaking; interfaces freeze at 1.0 after Plaza's PL-M3a. *Default: yes.*
10. **UI shell vendored from `sim-core`** (hash-checked against the pinned tag) rather than a pnpm package, until 1.0. *Default: yes.*

## Follow-ups (not part of this plan)

- Briefs for SC-1 and SC-2 once decisions 1–5 are made; SC-1 needs a `sim-core` CLAUDE.md derived from both games'.
- Report to Reece for a TST session: TST's `llm/` and `db/backup.py` have moved since `02fba2aa`. No re-copy into PT is proposed before SC-2.
- Plaza's map should note that PT's general modules carry about 60 law imports (finding 1), so its porting estimate assumes `sim-core` 0.2, not raw PT files.
