# Vendored files

Files copied or ported from Tech Startup Tycoon (`Reece77/Tech_Executive_Tycoon`, read-only) under ADR PT-0001. Upstream commit for every row below: **`02fba2aae1be2e43b179d3b6c1794d48e5dcdf56`** (2026-11-17).

- **AS IS**: identical to upstream after the package rename (`tst` → `ptk`, `TST_` → `PTK_`, `.tst.sqlite` → `.ptk.sqlite`, the game's name). `tools/check_vendored.py` checks each against the recorded hash; CI fails on drift. To change one, fix it in TST first (a TST session, TST's process), re-copy, and re-record with `python tools/check_vendored.py --record <tst clone>`; or mark it `ported` with a header saying what changed.
- **ported**: copied, then changed; the file's header names its upstream path, commit and what changed.

| Local | Upstream | Mark | SHA-256 after rename |
| --- | --- | --- | --- |
| `backend/ptk/sim/money.py` | `backend/tst/sim/money.py` | AS IS | 8f8874d2bbe3e504b3b7a438196d3674256067b6c0bb1a8ac918d1e30c70a88e |
| `backend/ptk/sim/dmath.py` | `backend/tst/sim/dmath.py` | AS IS | 393d6385fbfd59e1e2a36f4d1ae7c4e7bec5ba2e9d5542b9f772bff4dad49fa9 |
| `backend/ptk/sim/scale.py` | `backend/tst/sim/scale.py` | AS IS | 523d04548df6c24877bd61032924a22f7fbcb47c22c4cbb0fa57f40ae6342f2c |
| `backend/ptk/sim/decisions.py` | `backend/tst/sim/decisions.py` | AS IS | eae6d01d583ebd6c5f5dd3219bb2d1978ab1b1c9e8322ae1b09ce4bda88d57a3 |
| `backend/ptk/db/session.py` | `backend/tst/db/session.py` | AS IS | 6dfda42e7fb17ceeced01bbf7572dd79ec83a12b7139c5dc20d5cc68ea253139 |
| `backend/ptk/db/backup.py` | `backend/tst/db/backup.py` | AS IS | b7c52b11c994f857c729599e2e88d14272057e8b1671aba65f193c488c2dd7f6 |
| `backend/ptk/db/migrate.py` | `backend/tst/db/migrate.py` | AS IS | 76e1757e66b73c0d94660a1224630e8d16f642985972c6e0dad4f6dc5513cf8b |
| `backend/ptk/llm/base.py` | `backend/tst/llm/base.py` | AS IS | 16fe420641f1238d2502ef40e53325a3fc1cf04d1dd87a58bb5e589766ec93e0 |
| `backend/ptk/llm/anthropic_adapter.py` | `backend/tst/llm/anthropic_adapter.py` | AS IS | f3eaaf654bacbc01bac6942c6dc212f79c5d5f292cd50ea9d450215642a21882 |
| `backend/ptk/llm/offline.py` | `backend/tst/llm/offline.py` | AS IS | aef6f1df81a0fb310637b5b4e9052240f49942264e8c3e094e7810202e126793 |
| `backend/ptk/llm/settings.py` | `backend/tst/llm/settings.py` | AS IS | b47d436e94c9dea7fa0a3cfd3a526fdeaa4df8cb46e8f1c8a43437b69d3cf5ad |
| `backend/ptk/config.py` | `backend/tst/config.py` | AS IS | 9e06cae529e5b7bad224049a81cd59bf91465a086ee6c96a8b9333a8b82b86e4 |
| `backend/migrations/env.py` | `backend/migrations/env.py` | AS IS | a6f666ebb069ace1194d48e791ff46417bb161ff90ab9bc85ff8368dc446a6f7 |
| `backend/migrations/script.py.mako` | `backend/migrations/script.py.mako` | AS IS | 525cbde01738dc04ba12b7430f2344185eea0709537631a6292d91c368a48182 |
| `backend/scripts/export_openapi.py` | `backend/scripts/export_openapi.py` | AS IS | 71b2ff6f5ffb55d55a68536ee9469ecc014ad2eca6532d8933794883daf3ad10 |
| `frontend/scripts/gen-api.mjs` | `frontend/scripts/gen-api.mjs` | AS IS | 201b3f6312a44e0c978035bff4942ef4b1596b99d7d13d81abab2465380d86ae |
| `frontend/eslint.config.js` | `frontend/eslint.config.js` | AS IS | 11d17b914a43bd7c3ac0aa0482a6b1367ff62355942968943fd2fd23f4c45e0f |
| `frontend/tsconfig.json` | `frontend/tsconfig.json` | AS IS | e8d6f7b50828db3953e21c7e92584f9206b3cd2551b4012507372afbb7fe9ce3 |
| `frontend/tsconfig.app.json` | `frontend/tsconfig.app.json` | AS IS | 82a5db4f3335b292a2080cc9b9981e7ddf06cab32089a7096282e3949fe75d28 |
| `frontend/tsconfig.node.json` | `frontend/tsconfig.node.json` | AS IS | bdc4ff59093bf9a08d6117c6bae4823201bbb1e6bbd4ef1fe70acc6b28035db6 |
| `frontend/.prettierrc.json` | `frontend/.prettierrc.json` | AS IS | 85378d4d734cb7d35641c44ffdf322fe0bc76a3b12841927f20aa5f0eba12695 |
| `backend/data/personality.yaml` | `backend/data/personality.yaml` | AS IS | 9086d8dd35efdb93894aa85dbb880d42f120d080a6bcc43980ad00d4e5972ad8 |
| `backend/data/interests.yaml` | `backend/data/interests.yaml` | AS IS | b3be7dd7e48fe844b67f57e27ab8f6556d194c529658d9417ae96b862bd111ff |
| `backend/ptk/sim/rng.py` | `backend/tst/sim/rng.py` | ported | — |
| `backend/ptk/sim/calendar.py` | `backend/tst/sim/calendar.py` | ported | — |
| `backend/ptk/sim/errors.py` | `backend/tst/sim/errors.py` | ported | — |
| `backend/ptk/sim/ledger.py` | `backend/tst/sim/ledger.py` | ported | — |
| `backend/ptk/sim/log.py` | `backend/tst/sim/log.py` | ported | — |
| `backend/ptk/sim/snapshot.py` | `backend/tst/sim/snapshot.py` | ported | — |
| `backend/tests/unit/test_sim_purity.py` | `backend/tests/unit/test_sim_purity.py` | ported | — |
| `backend/tests/unit/test_rng_call_sites.py` | `backend/tests/unit/test_rng_call_sites.py` | ported | — |
| `frontend/src/main.tsx` | `frontend/src/main.tsx` | ported | — |
| `backend/ptk/sim/people/models.py` | `backend/tst/sim/people/models.py` | ported | — |
| `backend/ptk/sim/people/formulas.py` | `backend/tst/sim/people/formulas.py` | ported | — |
| `backend/ptk/sim/people/generator.py` | `backend/tst/sim/people/generator.py` | ported | — |
| `backend/ptk/sim/people/reveal.py` | `backend/tst/sim/people/reveal.py` | ported | — |
| `backend/ptk/sim/people/founder.py` | `backend/tst/sim/people/founder.py` | ported | — |
| `backend/ptk/sim/people/growth.py` | `backend/tst/sim/people/growth.py` | ported | — |
| `frontend/src/lib/attr.ts` | `frontend/src/lib/attr.ts` | ported | — |
| `frontend/src/components/AttributeRange.tsx` | `frontend/src/components/AttributeRange.tsx` | ported | — |
| `backend/data/tags.yaml` | `backend/data/tags.yaml` | ported | — |
| `backend/data/names.yaml` | `backend/data/names.yaml` | ported | — |
| `backend/data/backgrounds.yaml` | `backend/data/backgrounds.yaml` | ported | — |
| `backend/ptk/sim/hiring/models.py` | `backend/tst/sim/hiring/models.py` | ported | — |
| `backend/ptk/sim/hiring/formulas.py` | `backend/tst/sim/hiring/formulas.py` | ported | — |
| `backend/ptk/sim/hiring/rules.py` | `backend/tst/sim/hiring/rules.py` | ported | — |
| `backend/ptk/sim/hiring/phases.py` | `backend/tst/sim/hiring/phases.py` | ported | — |
| `backend/ptk/sim/hiring/actions.py` | `backend/tst/sim/actions/hiring.py` | ported | — |
| `backend/ptk/sim/actions/__init__.py` | `backend/tst/sim/actions/__init__.py` | ported | — |
| `backend/ptk/db/inbox.py` | `backend/tst/db/inbox.py` | ported | — |
| `backend/data/inbox_templates.yaml` | `backend/data/inbox_templates.yaml` | ported | — |
| `backend/ptk/sim/org/models.py` | `backend/tst/sim/org/models.py` | ported | — |
| `backend/ptk/sim/org/formulas.py` | `backend/tst/sim/org/formulas.py` | ported | — |
| `backend/ptk/sim/org/rules.py` | `backend/tst/sim/org/rules.py` | ported | — |
| `backend/ptk/sim/org/actions.py` | `backend/tst/sim/actions/org.py` | ported | — |
| `backend/ptk/sim/org/delegates.py` | `backend/tst/sim/org/delegates.py` | ported | — |
| `backend/ptk/sim/events/data.py` | `backend/tst/sim/events/data.py` | ported | — |
| `backend/ptk/sim/events/models.py` | `backend/tst/sim/events/models.py` | ported | — |
| `backend/ptk/sim/events/formulas.py` | `backend/tst/sim/events/formulas.py` | ported | — |
| `backend/ptk/sim/events/modifiers.py` | `backend/tst/sim/events/modifiers.py` | ported | — |
| `backend/ptk/sim/events/render.py` | `backend/tst/sim/events/render.py` | ported | — |
| `backend/ptk/sim/events/triggers.py` | `backend/tst/sim/events/triggers.py` | ported | — |
| `backend/ptk/sim/events/director.py` | `backend/tst/sim/events/director.py` | ported | — |
| `backend/ptk/sim/events/effects.py` | `backend/tst/sim/events/effects.py` | ported | — |
| `backend/ptk/sim/events/describe.py` | `backend/tst/sim/events/describe.py` | ported | — |
| `backend/ptk/sim/events/colleagues.py` | `backend/tst/sim/people/relationships.py` | ported | — |
| `backend/ptk/sim/events/actions.py` | `backend/tst/sim/actions/events.py` | ported | — |
| `backend/ptk/events/validator.py` | `backend/tst/events/validator.py` | ported | — |
| `backend/ptk/events/drafts.py` | `backend/tst/events/drafts.py` | ported | — |
| `backend/ptk/events/context.py` | `backend/tst/events/context.py` | ported | — |
| `backend/ptk/events/service.py` | `backend/tst/events/service.py` | ported | — |
| `frontend/src/lib/table.ts` | `frontend/src/lib/table.ts` | AS IS | ba4074bf9854c56cf8b945b9b83a369484a5b3e37b56345e87126c1f0c88dcfb |
| `frontend/src/components/DataTable.tsx` | `frontend/src/components/DataTable.tsx` | ported | — |
| `frontend/src/components/ViewsMenu.tsx` | `frontend/src/components/ViewsMenu.tsx` | ported | — |
| `frontend/src/hooks/useTableViews.ts` | `frontend/src/hooks/useTableViews.ts` | ported | — |
| `frontend/src/components/Explain.tsx` | `frontend/src/components/Explain.tsx` | ported | — |
| `frontend/src/lib/explain.ts` | `frontend/src/lib/explain.ts` | ported | — |
| `backend/ptk/sim/rivals/formulas.py` | `backend/tst/sim/rivals/formulas.py` | ported | — |
| `backend/ptk/sim/rivals/models.py` | `backend/tst/sim/rivals/models.py` | ported | — |
| `backend/ptk/balance/game.py` | `backend/tst/balance/game.py` | ported | — |
| `backend/ptk/balance/report.py` | `backend/tst/balance/report.py` | ported | — |
| `backend/ptk/balance/known_misses.py` | `backend/tst/balance/known_misses.py` | ported | — |
| `tools/balance_runner.py` | `tools/balance_runner.py` | ported | — |
| `.github/workflows/nightly.yml` | `.github/workflows/nightly.yml` | ported | — |
| `backend/ptk/balance/state_cache.py` | `backend/tst/balance/m30.py` | ported | — |
| `backend/tests/balance/test_state_cache.py` | `backend/tests/balance/test_m30_state_cache.py` | ported | — |
| `backend/ptk/sim/partnership/governance.py` | `backend/tst/sim/finance/board.py` | ported | — |
| `backend/ptk/sim/partnership/formulas.py` | `backend/tst/sim/finance/formulas.py` | ported | — |
| `backend/ptk/sim/org/seats.py` | `backend/tst/sim/org/executives.py` | ported | — |
| `backend/ptk/sim/org/seat_models.py` | `backend/tst/sim/org/models.py` | ported | — |
| `backend/ptk/sim/org/authority.py` | `backend/tst/sim/org/authority.py` | ported | — |
| `backend/ptk/sim/org/pitches.py` | `backend/tst/sim/org/pitches.py` | ported | — |
| `backend/ptk/sim/org/reports.py` | `backend/tst/sim/org/reports.py` | ported | — |
| `backend/ptk/sim/founder/config.py` | `backend/tst/sim/founder/config.py` | ported | — |
| `backend/ptk/sim/founder/models.py` | `backend/tst/sim/founder/models.py` | ported | — |
| `backend/ptk/sim/founder/personal.py` | `backend/tst/sim/founder/personal.py` | ported | — |
| `backend/ptk/sim/founder/persona.py` | `backend/tst/sim/founder/persona.py` | ported | — |
| `backend/ptk/sim/founder/foundation.py` | `backend/tst/sim/founder/foundation.py` | ported | — |
| `backend/ptk/sim/founder/influence.py` | `backend/tst/sim/founder/influence.py` | ported | — |
| `backend/ptk/sim/founder/legacy.py` | `backend/tst/sim/founder/legacy.py` | ported | — |
| `backend/ptk/sim/founder/phase.py` | `backend/tst/sim/founder/phase.py` | ported | — |
| `backend/ptk/sim/family/models.py` | `backend/tst/sim/family/models.py` | ported | — |
| `backend/ptk/sim/family/people.py` | `backend/tst/sim/family/people.py` | ported | — |
| `backend/ptk/sim/family/setup.py` | `backend/tst/sim/family/setup.py` | ported | — |
| `backend/ptk/sim/family/phase.py` | `backend/tst/sim/family/phase.py` | ported | — |
| `backend/ptk/sim/family/estate.py` | `backend/tst/sim/family/estate.py` | ported | — |
| `backend/ptk/sim/family/adviser.py` | `backend/tst/sim/family/adviser.py` | ported | — |
| `backend/ptk/sim/family/succession.py` | `backend/tst/sim/family/succession.py` | ported | — |
| `backend/ptk/sim/automation/config.py` | `backend/tst/sim/automation/config.py` | ported | — |
| `backend/ptk/sim/automation/models.py` | `backend/tst/sim/automation/models.py` | ported | — |
| `backend/ptk/sim/automation/owners.py` | `backend/tst/sim/automation/owners.py` | ported | — |
| `backend/ptk/sim/automation/limits.py` | `backend/tst/sim/automation/limits.py` | ported | — |
| `backend/ptk/sim/automation/run.py` | `backend/tst/sim/automation/run.py` | ported | — |
| `backend/ptk/sim/automation/rules.py` | `backend/tst/sim/automation/rules.py` | ported | — |
| `backend/ptk/sim/automation/events.py` | `backend/tst/sim/automation/events.py` | ported | — |
| `backend/ptk/sim/automation/digest.py` | `backend/tst/sim/automation/digest.py` | ported | — |
| `backend/ptk/sim/automation/actions.py` | `backend/tst/sim/automation/actions.py` | ported | — |
| `frontend/src/screens/AutomationScreen.tsx` | `frontend/src/screens/AutomationScreen.tsx` | ported | — |
| `frontend/src/components/RunBy.tsx` | `frontend/src/components/RunBy.tsx` | ported | — |
| `frontend/src/components/OwnerRecord.tsx` | `frontend/src/components/OwnerRecord.tsx` | ported | — |
| `frontend/src/lib/automation.ts` | `frontend/src/hooks/automation.ts` | ported | — |

Changes in ported files:

- `backend/ptk/sim/rng.py`: Partner Track's STREAM_IDS table.
- `backend/ptk/sim/calendar.py`: turn 0 from the scenario, not a constant.
- `backend/ptk/sim/errors.py`: generic errors only.
- `backend/ptk/sim/ledger.py`: PT chart; practice and office dimensions; client book apart.
- `backend/ptk/sim/log.py`: link kinds; firm_id.
- `backend/ptk/sim/snapshot.py`: PT KPIs.
- `backend/tests/unit/test_sim_purity.py`: package rename.
- `backend/tests/unit/test_rng_call_sites.py`: known names a parameter.
- `frontend/src/main.tsx`: no glossary or busy retry yet.
- `backend/ptk/sim/people/models.py` (PT-M1a): class-year levels; familiarity, school tier, bar, strain, book and portability on a person; every person has a role; employment with a firm.
- `backend/ptk/sim/people/formulas.py` (PT-M1a): growth times `learn(h)`; familiarity and strain formulas; no salary expectation yet.
- `backend/ptk/sim/people/generator.py` (PT-M1a): school tier first; familiarity and portability draws last; one US pool; no cities or salary.
- `backend/ptk/sim/people/reveal.py` (PT-M1a): firm observers; familiarity records (narrow); TST's first six actions.
- `backend/ptk/sim/people/founder.py` (PT-M1a): the founding partner build: home practice role at equity partner, familiarity, book, bar admissions, age 34-52; stream keyed by founder index.
- `backend/ptk/sim/people/growth.py` (PT-M1a): growth times `learn(h)` from a month of work; familiarity growth and decay; growth in the person's own role.
- `frontend/src/lib/attr.ts` (PT-M1a): ranges as `{lo, hi}`; a strain band; no morale band yet.
- `frontend/src/components/AttributeRange.tsx` (PT-M1a): ranges as `{lo, hi}`.
- `backend/data/tags.yaml` (PT-M1a): PT's seven new tags appended; the `negative` flag (ADR PT-0013).
- `backend/data/names.yaml` (PT-M1a): one `us` pool (TST's north_america list); rival names dropped.
- `backend/data/backgrounds.yaml` (PT-M1a): PT's five founding-partner backgrounds; TST's presets as is.
- `backend/ptk/sim/hiring/models.py` (PT-M1b): firms; campus, recruiter, job post and referral channels; tier filters and a target level on a search; the ask on the candidate; campus offers signed a year ahead; per-person energy and morale; the firm's pay policy; no equity, NextIds, rival, exec or city searches.
- `backend/ptk/sim/hiring/formulas.py` (PT-M1b): no equity or stage terms, a prestige term instead; fit counts interests the practice favours; recruiter fee 20% or 25%; no runway term; PT's hours, interesting-work, prospects and bonus-fairness morale terms; resignation with lifer, burnout, bonus timing and lateral heat; no retirement.
- `backend/ptk/sim/hiring/rules.py` (PT-M1b): no option pool or mission; the campus calendar; the hint from revealed ranges with prestige.
- `backend/ptk/sim/hiring/phases.py` (PT-M1b): campus pools, summer months and a September start; payroll to PT's accounts with December bonuses; the scale raises associates in phase 9; PT's morale terms and bonus timing; no rivals, options, offices, divisions, free agents, relocation or retirement.
- `backend/ptk/sim/hiring/actions.py` (PT-M1b): PT's channels and campus months; scouting and the pay policy as actions; no firing, equity, poach, exec, interest or city searches.
- `backend/ptk/sim/actions/__init__.py` (PT-M1b): hiring actions only; decision_log payloads.
- `backend/ptk/db/inbox.py` (PT-M1b): firms; no archive, bookmarks, digest or event links.
- `backend/data/inbox_templates.yaml` (PT-M1b): PT's hiring templates only.
- `backend/ptk/sim/people/generator.py` (PT-M1b): a fixed school tier for tier-filtered searches and campus visits (drawn first all the same); `weighted_pick` public.
- `backend/ptk/sim/people/models.py` (PT-M1b): an employment's salary.
- `backend/ptk/sim/org/models.py` (PT-M2): unit kinds are practice groups and teams; membership, raise history and one-off morale in an `OrgState` on the game state; PT's plan channels (campus, referral), no equity; no seats, authority, proposals, pitches, policies or offices.
- `backend/ptk/sim/org/formulas.py` (PT-M2): span, supervisor quality, W_mgr and its label, M_growth, the offer pitch and the raise test only; `OrgBalance` keys.
- `backend/ptk/sim/org/rules.py` (PT-M2): units and membership from `GameState.org`; the root's leader is the player's founding partner; no teammate-tag morale, work policy or memo cache; growth multipliers and the practice-group gate added.
- `backend/ptk/sim/org/actions.py` (PT-M2, from `actions/org.py`): practice groups (one per practice, from 10 lawyers) and teams; co-founding partners may lead; ADR PT-0006 promotions (accelerated class years, no partnership); raises through `interfaces.salary_cents`/`set_salary`; plan owners lead a unit or are recruiting managers; campus targets per group; no founder energy, divisions or policies; one-off morale as nudges.
- `backend/ptk/sim/org/delegates.py` (PT-M2): every step is a request through PT-M1b's delegate hook (`ptk.sim.interfaces`); energy given and spent through the hook; hires placed from accepted offers; per-search scouting; campus plans; no executives' reuse.
- `backend/ptk/sim/events/data.py` (PT-M6): spec 15's eight categories; Partner Track's triggers (people, clients, matters, partnership, market, regulatory, technology), matter draws, crises (a key exit, a key client walking, a key matter's trial) and engine-queued criticals; law effect types (client relationship, colleague pair, cash, reputation placeholder, a matter's hours, strain, WIP write-down, merits shift, confidence placeholder) and placeholders; a `restricted` flag (ADR PT-0013); every category needs every severity; the events and colleagues balance models live here.
- `backend/ptk/sim/events/models.py` (PT-M6): firms; events name a client, a matter and a practice; `ColleaguePair`; one `EventsState` with its own id counters; spec 15's text kinds.
- `backend/ptk/sim/events/formulas.py` (PT-M6): the cash base from monthly fees; no loan effects; `above_strength`.
- `backend/ptk/sim/events/modifiers.py` (PT-M6): people, units and the firm; the stats are a person's morale target and strain gain (`person_factor`).
- `backend/ptk/sim/events/render.py` (PT-M6): client, GC, matter, practice and court placeholders.
- `backend/ptk/sim/events/triggers.py` (PT-M6): Partner Track's triggers and crises; matter draws on the events stream.
- `backend/ptk/sim/events/director.py` (PT-M6): matter and client cooldowns; restricted templates never name a real person; engine-queued events; read-only text requests; no press, persona or public names.
- `backend/ptk/sim/events/effects.py` (PT-M6): law effects; WIP write-downs, reputation and confidence through `ptk.sim.interfaces` hooks (write-downs through PT-M3b's next-bill write-down; reputation and confidence no-ops until PT-M5 and PT-M4); Continue blocked by critical events only; restricted effects never touch a real person.
- `backend/ptk/sim/events/describe.py` (PT-M6): law effects in words; a merits shift only in words.
- `backend/ptk/sim/events/colleagues.py` (PT-M6, from `people/relationships.py` and the monthly step of `org/relationships.py`): pairs form on matter teams; no W_rel morale term yet.
- `backend/ptk/sim/events/actions.py` (PT-M6, the choose_event action of `actions/events.py`): Partner Track's effects.
- `backend/ptk/events/validator.py` (PT-M6): law effects and targets; no engine steps; drafts that resign a real person or reveal one's tag are rejected (ADR PT-0013).
- `backend/ptk/events/drafts.py` (PT-M6): law target words; restricted effects on a real person left out.
- `backend/ptk/events/context.py` (PT-M6): legal state (people as revealed words, public matter facts, clients by relationship score, GCs by name only); the real-person rule in the system prompt; spec 15's text asks.
- `backend/ptk/events/service.py` (PT-M6): KPIs and text kinds for law; the real-person rule; no lender, public or press cases; `write_pending_events` for in-memory runs.
- `backend/ptk/sim/hiring/phases.py` (PT-M6): event modifiers multiply a person's morale target.
- `frontend/src/components/DataTable.tsx` (PT-M3c): no glossary `Term` on headers (Partner Track has no glossary yet).
- `frontend/src/components/ViewsMenu.tsx` (PT-M3c): unchanged but for its header; ported only because the vendoring rename would turn its `tst-` class names into `ptk-` ones.
- `frontend/src/hooks/useTableViews.ts` (PT-M3c): views in the browser's `localStorage` (`ptk.tableViews`), not `saves/ui_settings.json` through an API; the hook's interface is TST's.
- `frontend/src/components/Explain.tsx` (PT-M3c): the breakdown, a band and the note only (no 12-month trend or Ask why); Partner Track's `useExplain`.
- `frontend/src/lib/explain.ts` (PT-M3c): Partner Track's units (hours, ratio, a revealed range, text); `itemText`.
- `backend/ptk/sim/rivals/formulas.py` (PT-M5, from TST @ 121d3180): `utility`, `poach_score`, `poach_probability`, `poach_band` and `rounded_headcount` as TST's; law's needs (a gap over a span); the money label reads margin and the PEP trend, not months of cash; TST's unvested-options term dropped.
- `backend/ptk/sim/rivals/models.py` (PT-M5, from TST @ 121d3180): `RivalMove`, `Approach` (TST's `PoachApproach`), `FreeAgent` and `stream_key` keep TST's shape; a rival is a `RivalFirm` with practice pools, key people are `Member`s generated on demand.

PT-M5 (rival firms) ported `tst/sim/rivals/formulas.py` and `models.py` from upstream commit **`121d3180`** (2026-11-20, TST at M44), not the commit above: each file's header names it and what changed.
- `backend/ptk/sim/partnership/governance.py` (PT-M4, the monthly confidence step of `board_month`): equity partners' confidence in the managing partner; the months-below counter becomes the no-confidence petition (an election, ADR PT-0007 3); no meetings; votes added.
- `backend/ptk/sim/partnership/formulas.py` (PT-M4, the confidence functions only): `clamp_confidence` and `next_confidence` as is; ADR PT-0007 1's target terms; the whip count's label and ranges for TST's confidence label.

PT-M7 (balance and v1 close) ported TST's balance runner framework from upstream commit **`121d318a`** (2026-11-19, TST at M44), not the commit above: each file's header names it and what changed.
- `backend/ptk/balance/game.py`: Partner Track's actions (player actions and org actions), the turn answers critical events and writes events with the mock adapter, each month records the law targets' numbers (revenue, profit, PEP, people, burnout, ratios, practice revenue) instead of founder value.
- `backend/ptk/balance/report.py`: the framework (`play`, `run_all` with worker processes, `Row`, `table`, `runs_table`) as TST's; Partner Track's targets T1-T12, strategies and the T5/T8/T9 extra runs.
- `backend/ptk/balance/known_misses.py`: TST's `KnownMiss`, `Reading` and `verdict` as they are; Partner Track's own (empty) list.
- `tools/balance_runner.py`: Partner Track's package, 132 turns and the extra runs.
- `.github/workflows/nightly.yml`: two parts (`make balance`, `make nightly`), no shards; the changed-main skip as TST's. PT-M18: the balance run in seed-range shards with a summary job, the nightly tests in duration-balanced shards, a `nightly` job over them all, and a 120-minute limit.
- `backend/ptk/balance/state_cache.py` and `backend/tests/balance/test_state_cache.py`: TST M30's state cache (PT-M0 deferred it): Partner Track's strategies (steady, pyramid, boutique), 132 turns, its loader and fixture (`tests/fixtures/state_hashes.json`); the Digester and the fixture format as TST's.
- Holiday was ported in PT-M7a (`backend/ptk/holiday.py`, TST 17.1's stop reasons; synchronous, see its brief).

PT-M8 (seats, authority and pitches) ported TST's executives from upstream commit **`121d318aa2aa413ea21b90871482ce8cb1f4032b`** (2026-11-19, TST at M44), not the commit above: each file's header names it and what changed.
- `backend/ptk/sim/org/seats.py` (from `org/executives.py` and the seat functions of `org/formulas.py`): seats from `seats.yaml` with a stage each; partner and business-services eligibility; the MP's seat is the partnership's MP and a practice group leader's is PT-M2's unit leader; the executive committee's slots and mean effect; appointing moves a partner holder's confidence by ambition (no exec salary); appoint, authority and exco-term actions.
- `backend/ptk/sim/org/seat_models.py` (the seat, authority, decision and pitch records of `org/models.py`): slots; Partner Track's pitch kinds with integer cases; the firm's committee mode; one `LeadershipState`.
- `backend/ptk/sim/org/authority.py` (from `org/authority.py`): Partner Track's seat rules through the player's actions; its own energy budget; stream `seat_act` (45) keyed (seat index, firm, slot); spec 9.4's one-offs refused.
- `backend/ptk/sim/org/pitches.py` (from `org/pitches.py`): Partner Track's kinds; stream `pitch` (46) keyed (firm, person); the committee's effect on quality; no Holiday auto-approval; follow-through against the central case.
- `backend/ptk/sim/org/reports.py` (from `org/reports.py` and `org/voices.py`): reports through PT-M6's read-only texts; the voice from revealed traits and tags; the partners' meeting and the committee's December.
PT-M17 (the founder's life, family and succession, lane C) ported `tst/sim/founder/` and `tst/sim/family/` from upstream commit **`121d318a`** (2026-11-19, TST at M44), not the commit above: each file's header names it and what changed. TST's founder modules with no Partner Track counterpart (`angel.py`, `shares.py`, `investing*.py`, `wealth.py`, `draws.py`, `events.py`, `stress.py`, `effects.py`, `family_office.py`) and family modules (`answers.py`, `divorce.py`, `dynasty.py`, `rules.py`, `steps.py`, `transfers.py`, `config.py`) were read, not copied: stress is the person's strain (ADR PT-0006), there are no shares, and dynasty mode is v3; the parts used are folded into the files below.
- `backend/ptk/sim/founder/config.py` (with `tst/sim/family/config.py`): one module for `founder_life.*`, `family.*` and `succession.*`; personal book, persona sources (spec 2.3), causes (access to justice added, climate dropped), bar politics, legacy, annuities; school and law school; the US estate tax by year; succession.
- `backend/ptk/sim/founder/models.py`: Partner Track's personal chart (draws, true-up, capital in the firm and its loan, tax, annuity income); a `PersonalBook` of running balances per player; status, bar politics and the succession plan on a life; annuities, succession records and the adviser's opinions; no hidden scandal risk.
- `backend/ptk/sim/founder/personal.py`: the month's mirror of PT-M4's sub-ledgers (draws, true-up, capital and its return), tax on the profit share as paid, the capital loan, investment and family-office returns; the income statement.
- `backend/ptk/sim/founder/persona.py`: spec 2.3's sources; effects on partner confidence and recruiting; a successor's starting persona (TST 45.5).
- `backend/ptk/sim/founder/foundation.py`: causes and their effects in Partner Track's units (recruiting; resignations); no cities.
- `backend/ptk/sim/founder/influence.py`: bar politics (a committee, spend on 6950, bar office) instead of regional lobbying; no scandals.
- `backend/ptk/sim/founder/legacy.py`: the firm's best year, the name on the door, the foundation, the persona, the family and bar office; no company score or net worth.
- `backend/ptk/sim/founder/phase.py`: Partner Track's phases 7 and 10 and the month's start (see its header).
- `backend/ptk/sim/family/models.py`: no shares, trust holders, seats or dynasty generations; school and law school; a child at the firm.
- `backend/ptk/sim/family/people.py`: Partner Track's generator; a child's monthly pull toward potential; never a real person.
- `backend/ptk/sim/family/setup.py`: Partner Track's state; a founder flagged real has no family.
- `backend/ptk/sim/family/phase.py`: family time eases strain; marriage after `marriage_months`; divorce splits liquid personal assets; nepotism through partner confidence; nothing for a real head.
- `backend/ptk/sim/family/estate.py`: the personal book's estate; gifts to heirs and a trust; the US federal history.
- `backend/ptk/sim/family/adviser.py`: opinions on partnership votes; partner confidence when overruled.
- `backend/ptk/sim/family/succession.py`: any equity partner may succeed; the election through PT-M4's vote functions (`ptk.sim.interfaces`); Partner Track's triggers.
- `backend/ptk/sim/hiring/phases.py` (PT-M17): the player's recruiting term on offers and resignation factor, through `ptk.sim.interfaces`.
- `backend/ptk/sim/actions/__init__.py` (PT-M17): the founder's and family's actions.
- `backend/ptk/sim/ledger.py` (PT-M17): accounts 2600 and 6950 posted by the engine.
- `backend/ptk/sim/rng.py` (PT-M17): streams `founder_life` 50, `family` 51, `investments` 52.

PT-M16 (reputation, press and rankings, lane C) ported TST's press (`tst/sim/press/`) and rival characters (`tst/sim/rivals/characters.py`) and the pattern of its industry rankings (`tst/sim/modes/rankings.py`, formulas.md 30.4) from upstream commit **`80a380792db2a4a63b01cfe880f48b62614ebeec`** (2026-11-22, TST at M43), not the commit above: each file's header names it and what changed. TST's `press/draws.py` (the one call site of stream `press`) is folded into `claims.check` and `characters.month` with Partner Track's ids (70, 71); `press/shares.py` (products' displayed share, quality, prices and research lead) has no Partner Track counterpart and was read, not copied: claims are judged on the firm's public lawyers, bands and pay policy; TST 29.5's recruitment fixes (`Departure`, Replace) stay in TST.
- `backend/ptk/sim/press/config.py` (from `press/config.py`): Partner Track's triggers (spec 12.2) and claim kinds, ADR PT-0013's restricted triggers, audience by the firm's stage, reputation points for brand-target points, the promise and feud blocks under `press`.
- `backend/ptk/sim/press/models.py` (from `press/models.py`): moments name a practice, a rival firm and a person; claims (TST's promises) in Partner Track's kinds; one `PressState`; no departures.
- `backend/ptk/sim/press/moments.py` (from `press/moments.py`): the press's own moments answered on the Press screen (an action), not the event director; reputation pulses for brand modifiers; backfires on reputation; the press office's measured answer for an unanswered moment.
- `backend/ptk/sim/press/claims.py` (from `press/promises.py`): headcount, no layoffs, matching the scale and a directory band, judged on public values; partner confidence for trust in the founder; the founder's Reckless persona (PT-M17's `broken_claim`); no sentiment.
- `backend/ptk/sim/press/characters.py` (from `rivals/characters.py` and `press/names.py`): law firms' managing partners through `ptk.sim.interfaces`; real rivals only; Partner Track's moves and causes; a jab from a firm whose managing partner is real comes from its spokesperson (ADR PT-0013); rivalry moves PT-M5's stance.
- `backend/ptk/sim/press/phase.py` (from `press/phase.py`): Partner Track's triggers from the month (rivals' moves, layoffs, verdicts, stars, ranking days, the salary scale), read through `ptk.sim.interfaces` and the turn's start state.
- `backend/ptk/sim/rankings/models.py`, `backend/ptk/sim/rankings/lists.py` (from `modes/models.py`'s `Ranking` and `modes/rankings.py`'s list building): the measure-order-cut pattern and the tie rule; Partner Track's lists (spec 12.3: the spring tables, quarterly league tables, October's directory bands and individuals, Best places to work), the latest editions in the state and the history appended to `ranking_entry`.
PT-M9 (automation everywhere, lane B) ported `tst/sim/automation/` (not `chain.py`, TST's M27b supply-chain areas, which Partner Track has no counterpart for) and the Automation screen from upstream commit **`80a380792db2a4a63b01cfe880f48b62614ebeec`** (2026-11-22, TST at M43), not the commit above: each file's header names it and what changed. TST's `plan.py` (Automate everything), `scope.py` (subsidiaries) and `kpis.py` were read, not copied: Partner Track has no subsidiaries, Automate everything is a follow-up, and the areas' KPIs are folded into `digest.py`.
- `backend/ptk/sim/automation/config.py`: spec 9.4's thirteen areas in `balance.yaml` with an owner seat each; spec 9.4's one-offs by the action kinds that carry them; the managing partner's own partnership actions carried out in the MP's name.
- `backend/ptk/sim/automation/models.py`: an owner row's slot (a practice group for staffing) and its monthly limit; automation's own proposals; one `AutomationState`.
- `backend/ptk/sim/automation/owners.py`: the seat's holder owns the area (a vacant seat cannot be automated); a group's leader its staffing; any partner pro bono; no leads, CEOs or subsidiaries.
- `backend/ptk/sim/automation/limits.py`: Partner Track's commitments (plans, write-downs, lateral offers, the pro bono credit) and one-offs.
- `backend/ptk/sim/automation/run.py`: one quality draw an area a month from stream `auto_quality` (60) keyed (area index, firm, slot); overload lowers q; per-decision and monthly limits; proposals in automation's own records.
- `backend/ptk/sim/automation/rules.py`: Partner Track's area rules; seat areas run PT-M8's authority rules through `interfaces.run_seat_rule`.
- `backend/ptk/sim/automation/events.py`: Partner Track's event categories and effects; stream `auto_events` (61) keyed (event id,).
- `backend/ptk/sim/automation/digest.py` (with `kpis.py`): one inbox item at month end, Partner Track's KPIs, a templated opening.
- `backend/ptk/sim/automation/actions.py`: give, take over, settings and answer a proposal, as the managing partner.
- `frontend/src/screens/AutomationScreen.tsx`, `components/RunBy.tsx`, `components/OwnerRecord.tsx`, `lib/automation.ts` (TST's `hooks/automation.ts`): one firm, Partner Track's endpoints, Take over and Hand back, proposals and the digest on the screen.


PT-M11 (offices, cities and London, lane B) ported TST's geography (`tst/sim/geo/`, formulas.md 19) from upstream commit **`718997f0b761e0054f58984229a74ddbb2455907`** (2026-11-23, TST at M43r), not the commit above: each file's header names it and what changed. TST's `geo/markets.py` (regional product markets, sizes and prices) and `geo/marketing.py` (marketing splits by region) were read, not copied: a law firm's city market is its clients (`Client.city`, `ptk/sim/geo/markets.py` is Partner Track's own), and there is no marketing budget.

| Local | Upstream | Mark | SHA-256 after rename |
| --- | --- | --- | --- |
| `backend/ptk/sim/geo/models.py` | `backend/tst/sim/geo/models.py` | ported | — |
| `backend/ptk/sim/geo/formulas.py` | `backend/tst/sim/geo/formulas.py` | ported | — |
| `backend/ptk/sim/geo/cities.py` | `backend/tst/sim/geo/cities.py` | ported | — |
| `backend/ptk/sim/geo/offices.py` | `backend/tst/sim/geo/offices.py` | ported | — |

- `backend/ptk/sim/geo/models.py`: an office is a law firm's lease (term, rent per lawyer seat, fit-out, how it was opened); the home office is implicit (id 0); no regional markets, marketing splits or product regions; Partner Track's admissions, pro hac vice, training contracts and trainees.
- `backend/ptk/sim/geo/formulas.py`: rent per lawyer seat by city over a term; the lease as a liability (2500) against a right-of-use asset (1510); fit-out capitalised (1500) and amortised straight-line; a city's rate factor; no localisation, regional sizes or talent bonuses.
- `backend/ptk/sim/geo/cities.py`: a person works in the firm's office in their city; a client's work is its city's; rivals are present in their headquarters' region; no units' offices, remote work or flexible seats.
- `backend/ptk/sim/geo/offices.py`: the lease's monthly postings, renewal and break, England and Wales's indemnity insurance, each office's P&L from the ledger's office dimension; no crowding or flexible-seat costs.
