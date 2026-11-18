# Reuse map: Tech Startup Tycoon → Partner Track

**Status: DRAFT for Reece's review (2026-11-17).** Read against `Reece77/Tech_Executive_Tycoon` at `main` as cloned on 2026-11-17 (v4 closed at `m35b-done`; v5 in progress: M36, M37, M38, M39, M41 merged; M40, M42, M43a, M44, M45 and M43 still to come).

## How to read this

| Mark | Meaning |
| --- | --- |
| **AS IS** | Copied unchanged (module, tests and data schema). Only imports and the package name change (`tst` → `ptk`). |
| **CHANGED** | Copied, then adapted. The column says what changes. The formulas and the shape of the code stay; the domain nouns and some terms change. |
| **PATTERN** | The code is not copied, because it is written around tech-industry nouns, but its structure, rules and tests are the template for a new module. |
| **NOT USED** | Tech, chain or industry specific. Nothing is carried over. |

**Sizes.** Line counts are Python or TypeScript lines in each module today. The backend is about 169,000 lines in 729 files; the simulation core (`tst/sim`) is about 103,000 of them.

### The one structural finding that drives everything below

The *generic* parts of Tech Startup Tycoon are genuinely general, but they are **wired to the tech domain in three places**:

1. **`GameState` is one frozen dataclass with about 150 fields** (`sim/state.py`, 2,139 lines), most of them industry-specific (`products`, `facilities`, `fabs`, `mines`, `vehicles`, …). Every module imports it.
2. **`turn.py` imports every industry's phase function directly** (vehicles, robotics, mining, power, …) into the fixed 12-phase pipeline.
3. **The general modules import industry modules.** Measured by `from tst.sim.<x>` imports: `org` imports `products` 9 times, `markets_public` 6, `hardware` and `research` once each; `automation` imports `products`, `mining`, `fabs`, `exploration` and `research`; `events`, `founder`, `family` and `finance` import `markets_public`, `rivals` and `press`; `rivals` imports `products` 6 times.

So "reused as is" is true only for the kernel (RNG, money, ledger, calendar, deterministic maths, people generation and growth, the LLM adapters, persistence helpers and the UI shell). Most of the rich systems (org, automation, events, founder, family, finance) are **CHANGED**: the formulas port, but each touches products or markets somewhere and needs that dependency replaced by matters and practice areas. This is the main input to the code-sharing recommendation (ADR PT-0001).

---

## 1. Simulation core: `backend/tst/sim/`

### 1.1 Kernel (no domain knowledge)

| Module | Lines | Mark | Notes |
| --- | --- | --- | --- |
| `rng.py` | 170 | **AS IS** | `RngFactory`, `SeedSequence` derivation, keyed streams (ADR-0002, 0013). `STREAM_IDS` becomes Partner Track's own append-only table (ADR PT-0012). |
| `money.py` | 155 | **AS IS** | `Cents`, `cents()`, `pct_of()`, round half to even. |
| `ledger.py` | 197 | **AS IS** | `LedgerLine`, `LedgerEntry`, balance checks. |
| `dmath.py` | 212 | **AS IS** | Deterministic maths (M35a). |
| `scale.py` | 34 | **AS IS** | Attribute 1–20, CA/PA 10–200, morale 0–100. |
| `log.py` | 66 | **AS IS** | Log items. |
| `errors.py` | 414 | **CHANGED** | Keep the base classes and generic errors (energy, not found, game over); drop about 70% of domain errors; add matter, conflict, partnership-vote and trust-account errors. |
| `calendar.py` | 50 | **CHANGED** | Turn 0 becomes a data value (January 2005 by default), not a constant (ADR PT-0002). |
| `decisions.py` | 14 | **AS IS** | |
| `snapshot.py` | 66 | **CHANGED** | Same mechanism; KPIs become revenue, PEP, leverage, utilisation, realisation, lockup, headcount by level. |
| `setup.py` | 201 | **CHANGED** | New-game creation: the founding partners, the starting book of business, capital, bank line. |
| `state.py` | 2,139 | **PATTERN** | A new `GameState` built the same way (frozen, sorted tuples, cash derived from the ledger), with Partner Track's own fields. The ~40 people, org, finance, events, founder and family fields are copied; the ~110 industry fields are not. |
| `turn.py` | 855 | **PATTERN** | Same 12 phase slots, same `TurnContext` threading and signature (ADR-0012); new phase bodies (spec §4). |
| `data_models.py` | 2,431 | **CHANGED** | Keep the Pydantic loader schemas for people, personality, tags, interests, regions, cities, macro history, investors (as lenders), banks, events, glossary, achievements; drop the rest; add practice areas, rate cards, clients, rival firms, jurisdictions, bar rules, rankings. |
| `unlocks.py` | 503 | **CHANGED** | Mechanism as is; the systems list becomes the firm's (practice groups at 10 lawyers, offices, executive committee, automation, mergers, ABS). |
| `whatnext.py` | 133 | **CHANGED** | Same Overview "what next" rules, new candidates (unstaffed matters, overdue bills, partnership vote prep). |
| `score.py` | 220 | **CHANGED** | Firm score from revenue, PEP, rankings bands and reputation instead of ARR and market share. |
| `coo.py` | 156 | **CHANGED** | "Ask my COO" briefing; answerer becomes the COO or the firm's executive director. |

### 1.2 People, hiring and org

| Module | Lines | Mark | Notes |
| --- | --- | --- | --- |
| `people/` (models, formulas, generator, growth, reveal, relationships, founder) | 1,157 | **CHANGED** (light) | The model is data-driven: skills come from `skills.yaml`, roles from `roles.yaml`. Changes: levels become class years and titles (ADR PT-0006); generation draws law school tier and bar admissions; growth's learning term reads **hours worked in each practice area** (practice familiarity) instead of a product's difficulty; the founder build becomes the founding partner build. Reveal (ADR-0007) as is. |
| `hiring/` (formulas, models, phases, recruit, rules) | 1,530 | **CHANGED** | Offers, acceptance logistic, interviews, references, payroll, morale, resignations and tag reveals port. New: the **campus cycle** (summer programme, autumn offers, September start), the **associate salary scale** (market-wide steps), **lateral partners with a book of business** and guarantees, headhunter fees. Imports of `products`, `facilities` and `press` replaced. |
| `org/` (units, delegates, divisions, executives, authority, CEO, pitches, reports, relationships, morale, replace) | 4,722 | **CHANGED** | Span of control, manager quality, mentoring, reorganising, raises and promotions, delegated hiring, seats and authority (§18, §24), pitches (§27) and reports port nearly line for line. Units become **practice groups, teams and offices**; "divisions" become **regions**; seats become the firm's (spec §9); the CEO becomes the **managing partner** (elected). Product-reading parts (CTO and CPO rules, product pitches) are replaced with matter and practice rules. |
| `actions/` (19 files) | 5,754 | **CHANGED / PATTERN** | The immediate-action framework (ADR-0014) and `authority`, `events`, `family`, `founder`, `hiring`, `org`, `press`, `recruit` actions port. `finance` and `mna` are CHANGED (partnership capital and law-firm combinations). `commodities`, `facilities`, `hardware`, `investing` (kept only as the founder's personal investing), `products`, `public`, `research`, `scaleup`, `geo` are replaced by new matter, client, office and pricing actions. |
| `automation/` (areas, owners, limits, one-offs, digest, KPIs, rules, run, scope, chain) | 3,890 | **CHANGED** | §40's machinery (areas, owners, money limits, commitments, one-offs as proposals, decision quality, workload in energy, digest, routine events) ports as is. The area table and each area's rule are new (spec §9.4). `chain.py` (M27b) is NOT USED. |

### 1.3 Money, governance and the founder

| Module | Lines | Mark | Notes |
| --- | --- | --- | --- |
| `finance/` (statements, captable, fundraising, board, debt, insolvency, macro, divisions, consolidation, options) | 3,154 | **CHANGED** | Statements, debt and covenants, insolvency, the macro layer, consolidation and division P&L port. The **cap table, options, SAFEs and priced rounds are NOT USED** (a partnership has capital accounts and points, not shares; ADR PT-0003). The **board** becomes the **partnership's confidence in the managing partner** with votes (ADR PT-0007). Macro gains legal-demand indicators. |
| `founder/` (stress, persona, personal book, foundation, influence, investing, family office, legacy, wealth, angel, shares) | 3,501 | **CHANGED** (light) | Stress and burnout, persona traits, the personal account, foundation, influence and scandal, personal investing and the family office, legacy: all port. `shares.py` and `wealth.py` read partnership capital and draws instead of shares; angel investing stays for the founder's personal money. |
| `family/` (partner, children, education, heirs, succession, estate, divorce, adviser) | 3,059 | **CHANGED** | Family, children, education, estate tax and the adviser port. Succession changes: the successor is **a partner elected as managing partner** (a child is one possible candidate, if a lawyer at the firm); the old founder becomes **senior partner/chair**, then retires under the firm's mandatory retirement age (spec §2.5). Divorce splits personal assets and capital-account value, not shares. |
| `dynasty/` | 988 | **CHANGED** (later) | A second 30 years is possible for a firm that outlives its founder; seeded eras beyond history. Not in v1. |
| `modes/` | 1,311 | **CHANGED** | Campaign, Sandbox, scenarios, rankings and "continue until" port; scenario list is new. |
| `group/` (holding company, subsidiaries, NCI, transfer prices, conglomerate discount) | 2,745 | **CHANGED** (v2) | Becomes the **Swiss verein and multi-entity firm** (member firms with their own books under one brand, profit pooled or not) and **ABS subsidiaries** (an alternative legal services arm, a consultancy). Conglomerate discount NOT USED. |
| `mna/` (valuation, diligence, offers, antitrust, integration) | 2,824 | **CHANGED** (v2) | Diligence, closing, the brand-or-integrate choice and culture-clash flight port. Valuation by price and tender offers are replaced by **combinations voted by both partnerships**, with points ratios and conflicts clearance (spec §8.8). Antitrust NOT USED (replaced by conflicts clearance). |
| `markets_public/` (listings, share price, earnings, analysts, activists) | 1,763 | **CHANGED** (v3, optional) | Only for an **ABS that lists** (the UK from 2015-style listings, Australia from 2007). Off by default. |
| `press/` (press moments, promises, credibility, feuds, rival CEOs) | 1,084 | **CHANGED** | Becomes legal press and rankings: the legal trade press, league tables, directory rankings. Rival CEOs become rival managing partners. Promises become public claims about growth, mergers and hires. |
| `regulation/` (regulators, designations, duties, investigations, fines, structural remedies) | 2,650 | **CHANGED** (v2) | The case machinery (visible stages, settle/contest/lobby, fines, odds as ranges, warnings ahead) ports to **bar regulators and disciplinary cases**. Gatekeeper designations and break-ups NOT USED. |
| `rivals/` (incumbents, startups, utility AI, poaching) | 2,582 | **CHANGED** | Utility AI with personalities, key people individually and pools by function, rival founding and failure, poaching both ways all port (ADR-0010). Actions change: rival firms bid for panels, hire laterals, open offices, merge and set rates. Startups become **spin-off boutiques** founded by departing partners. |
| `events/` (director, triggers, effects, modifiers, render, describe, data) | 2,937 | **CHANGED** | The director, slots, severity caps, validation, storylines, relationships and modifiers port (ADR-0005). Triggers, effect types and templates are new. `data.py` hard-codes about 16 tech skill and product names; those become legal ones. |
| `world/` (chain companies, living world, World news, company pages) | 2,882 | **PATTERN** | World news and company pages are reused as a pattern for the legal market's news and rival-firm pages; chain-company logic NOT USED. |
| `geo/` (cities, offices, regional markets) | 570 | **CHANGED** | Cities, HQ, offices, hiring pools by city and regional markets port; adds **bar admission** and **foreign-firm rules** per jurisdiction (v2). |
| `contracts/` | 412 | **NOT USED** | Supply contracts. Panel agreements are new and simpler. |

### 1.4 Industry modules: NOT USED

Each is tech, chain or industry specific; nothing carries over except as examples of "history pinned to 2025, then seeded".

| Module | Lines |
| --- | --- |
| `products/` (dev, markets, churn, pricing) | 1,961 (**PATTERN** for practice-area demand and price score only) |
| `research/` (R&D tree, eras) | 1,681 (**PATTERN** for the legal-tech era table and the first-mover window) |
| `facilities/`, `hardware/`, `chips/`, `fabs/`, `equipment/`, `commodities/`, `exploration/`, `mining/`, `refining/`, `power/`, `platforms/`, `geopolitics/`, `vehicles/`, `robotics/`, `medical/` | together about 36,000 |

---

## 2. Backend outside the core

| Module | Lines | Mark | Notes |
| --- | --- | --- | --- |
| `llm/` (base, anthropic adapter, offline, settings) | 439 | **AS IS** | Adapter protocol, Anthropic, Mock and Template adapters, the $10 a month meter. `TextKind` gains `matter_brief`, `pitch_letter`, `partner_memo`. |
| `events/` (context builder, validator, drafts, service, coo) | 981 | **CHANGED** | Validator and service as is; the context builder reads legal state and keeps ADR-0005 §4's hygiene. |
| `db/session.py`, `migrate.py`, `backup.py`, `saves.py`, `repository.py`, `history.py`, `inbox.py`, `events.py`, `unlocks.py`, `coo.py`, `former.py` | ~3,000 | **AS IS / CHANGED** | One SQLite file per save, WAL pragmas, transactional turns, backups, retention summaries (ADR-0004). `history.py` and `inbox.py` change their KPI and kind lists. |
| `db/models.py`, `mappers.py`, `state_io.py` | ~5,000 | **PATTERN** | New tables and mappers for the new state; same conventions (append-only history, current-state tables). |
| `db/*_io.py` (automation, family, founder, group, mna, regulation, modes, dynasty, investing) | ~2,500 | **CHANGED** | Follow their modules. |
| `db/*_io.py` (commodity, equipment, exploration, fab, geopolitics, medical, mining, platforms, power, refining, robotics, vehicle, world) | ~1,500 | **NOT USED** | |
| `api/app.py`, `deps.py`, `error_log.py`, `interruptions.py`, `howto.py`, `breakdowns.py`, `event_links.py` | ~2,000 | **AS IS / CHANGED** | App factory, dependency wiring, error mapping, blocking rules, how-to and Explain breakdown plumbing. |
| `api/routers/` and `api/schemas/` (game, saves, meta, holiday, history, events, explain, coo, onboarding, mods, profile, modes, campaign, automation, org, founder, family, finance, press, group, mna, regulation, rivals) | ~15,000 | **CHANGED** | Same contract style (OpenAPI is the contract, ADR-0009). People schemas keep the revealed-range rule. |
| `api/routers/` and `api/schemas/` (products, research, hardware, facilities, commodities, contracts, equipment, exploration, fabs, mining, refining, power, platforms, geopolitics, vehicles, robotics, medical, investing-as-company, scaleup, public, living, geo-as-is) | ~15,000 | **NOT USED** (geo CHANGED) | |
| `api/*_views.py` | ~12,000 | same split as routers | |
| `balance/` (runner, scripts, strategies, per-milestone checks) | 17,493 | **PATTERN** | The runner, seeds, strategy-script pattern, printed targets, `known_misses` and the nightly/weekly split are copied as a framework (~1,500 lines); the strategies and checks are new. |
| `advisor/` (chief of staff: driver breakdowns, Ask why) | 3,104 | **CHANGED** | The Explain engine and breakdown format port; the metric list is new (PEP, realisation, utilisation, lockup, matter margin). |
| `mods/` (data editor overlays) | 773 | **AS IS** | |
| `profile/` (achievements across games) | 462 | **AS IS** (achievement list new) | |
| `holiday.py` | — | **AS IS** | Holiday and stop reasons. |
| `ui_settings.py` | — | **AS IS** | Saved column views. |
| `loader.py`, `config.py`, `cli.py` | — | **CHANGED** | Paths and package name; CLI gains `matters`, `vote`, `bill`. |

## 3. Seed data: `backend/data/` (46 files)

| Mark | Files |
| --- | --- |
| **AS IS** | `personality.yaml` (ambition, loyalty, professionalism, temperament, adaptability, risk appetite, ego, integrity, sociability; hidden: consistency, burnout risk, big moments, poachability), `interests.yaml`, `names.yaml` (person pools), `achievements.yaml` (format), `glossary.yaml` (format) |
| **CHANGED** | `skills.yaml` (new legal skill list; leadership group kept, spec §5.1), `roles.yaml` (31 roles → lawyer, paralegal and business-services roles), `tags.yaml` (adds rainmaker, grinder, client whisperer, cowboy, rule-bender), `balance.yaml` (structure kept; keys new), `accounts.yaml` (partnership chart, ADR PT-0003), `regions.yaml`, `cities.yaml` (add bar jurisdictions), `macro_history.yaml` (from 2005; adds M&A, IPO, default rate and litigation indices), `banks.yaml` and `investors.yaml` (lenders to firms and partners), `scenarios.yaml`, `events/` (new templates; format as is), `inbox_templates.yaml`, `exec_voices.yaml`, `advisor.yaml`, `backgrounds.yaml` (lawyer backgrounds) |
| **NOT USED** | `categories.yaml`, `incumbents.yaml` and `entrants.yaml` (replaced by `firms.yaml` and `clients.yaml`), `chain_companies.yaml`, `commodities*.yaml`, `components_history.yaml`, `compute_index.yaml`, `countries.yaml` (blocs), `equipment.yaml`, `eras.yaml` (replaced by `legal_eras.yaml`), `export_controls.yaml`, `geology.yaml`, `medical.yaml`, `nationalization_history.yaml`, `nodes.yaml`, `platforms.yaml`, `power*.yaml`, `regulation.yaml` (replaced by `bar_rules.yaml`), `robotics.yaml`, `suppliers.yaml`, `tariffs.yaml`, `tech_frontier.yaml`, `vehicles.yaml` |

## 4. Front end: `frontend/src/`

| Area | Mark | Notes |
| --- | --- | --- |
| Shell: `App.tsx`, `GameLayout`, `LeftNav`, `TopBar`, `Breadcrumbs`, `CommandPalette`, `ShortcutHelp`, `useGameHotkeys`, `ScreenErrorBoundary`, `ScreenState`, `styles/tokens.css`, fonts | **AS IS** (nav list CHANGED) | Dark, dense, keyboard-first. |
| Tables: `DataTable`, `useTableViews`, `ViewsMenu`, `lib/table.ts` | **AS IS** | Every table (TanStack). |
| Explain and help: `Explain`, `lib/explain.ts`, `hooks/explain.ts`, `Term`, `RoleHelp`, `GuideScreen`, `lib/guides.ts`, glossary | **AS IS** (content new) | |
| Inbox and events: `InboxScreen`, `EventCard`, `lib/inbox.ts`, `ActiveEffects`, `Holiday`, `PreviewDialog` | **AS IS / CHANGED** | Kinds list changes; digest view kept. |
| Automation: `AutomationScreen`, `RunBy`, `OwnerRecord`, `hooks/automation.ts` | **CHANGED** | Area list. |
| People: `PeopleScreen`, `PersonScreen`, `AttributeRange`, `MoraleBar`, `LeadershipFit`, `Relationships`, `PersonOrg`, `RecruitmentScreen`, `HiringPlans`, `ReplacePanel`, `lib/attr.ts` | **CHANGED** | Class year, practice familiarity grid (Football Manager's position grid, spec §5.1), hours and strain. |
| Org: `OrgScreen`, `OrgNode`, `OrgChangeDialog`, `SpanBadge`, `lib/org.ts`, `CeoSeat`, `CooPanel`, `ScaleupPanels` | **CHANGED** | Practice groups, offices, the executive committee, the managing partner. |
| Founder and family: `FounderPanels`, `FamilyScreen`, `FamilyTab`, `InvestmentsTab`, `hooks/founder.ts`, `family.ts`, `investing.ts` | **CHANGED** (light) | |
| Finance: `FinanceScreen`, `finance/StatementsTab`, `DebtTab`, `DivisionsTab` (→ offices and practices), `StatementTable`, `CashChart`, `KpiTile`, `Sparkline`, `lib/finance.ts`, `lib/format.ts` | **CHANGED** | Adds capital accounts, PEP, comp, WIP and lockup. `CapTableTab`, `FundraisingTab`, `BoardTab`, `StockTab`, `DealsTab`, `CapTable`, `DilutionPreview`, `IpoPanel` NOT USED in v1 (`BoardTab` → Partnership tab). |
| Rivals, world, press: `CompetitorsScreen`, `RivalScreen`, `RivalLeaderPanel`, `WorldNewsScreen`, `WorldScreen`, `WorldCompanyPanel`, `PressPanels`, `RankingsScreen`, `MacroStrip`, `EraTimeline` | **CHANGED** | Rival firms, the legal press, rankings tables. |
| Game flow: `MainMenu`, `NewGameScreen`, `SavesScreen`, `SettingsScreen`, `GameOverScreen`, `CampaignEndPanel`, `ModePicker`, `HistoryScreen`, `AchievementsScreen`, `DataEditorScreen`, `OnboardingPanels`, `UnlockToast`, `AchievementToast` | **AS IS / CHANGED** | |
| Industry screens: `Products*`, `Market*`, `Research`, `Hardware`, `Infrastructure`, `Fabs`, `Equipment`, `Exploration`, `Mines`, `Refineries`, `Commodities`, `Power`, `Platforms`, `Vehicles`, `Mobility`, `Robotics`, `Medical`, `Offices`(CHANGED), `Regulation`(CHANGED, v2) and their components and hooks | **NOT USED** | |
| `api/` (generated client) | regenerated | ADR-0009. |

## 5. Tooling, tests and CI

| Item | Mark | Notes |
| --- | --- | --- |
| `Makefile`, `ruff.toml`, `pyproject`, `uv`, `pnpm`, pre-commit, Alembic setup | **AS IS** | |
| `.github/workflows/check.yml`, `e2e.yml`, `determinism.yml`, `nightly.yml`, `weekly.yml`, `tag-milestone.yml` | **AS IS** (paths CHANGED) | Same protected `main`, merge-commit trailer and tagging. |
| `tests/unit/test_sim_purity.py`, `test_turn_order.py`, RNG stream-uniqueness test, ledger property tests, attribute-clamp property tests, hidden-value API tests, migration-chain tests, golden framework, state-cache framework | **AS IS** | These are the most valuable things to carry: they enforce CLAUDE.md's five rules from day one. |
| Domain tests (~1,000 files) | **NOT USED** | |
| `tools/launcher.py`, `dev.py`, `bench.py`, `check_generated.py`, `balance_runner.py`, `quickstart_saves.py` | **AS IS / CHANGED** | Per-milestone `mNN_targets.py` and `e2e_mNN_save.py` are a pattern, not copied. |
| `CLAUDE.md`, `AGENTS.md`, `.cursor/rules` | **CHANGED** | Same five rules and process; repository map, stack note and stream table new. |
| `docs/adr/` | inherited | See `docs/adr/README.md`: 0001–0005, 0007–0010, 0012–0016 inherited; 0006, 0011, 0017–0022 superseded or not applicable. |

## 6. Totals (estimate)

| | Lines in TST | Carried to Partner Track | Of which as is |
| --- | --- | --- | --- |
| `sim/` | ~103,000 | ~35,000 | ~1,500 (kernel) + ~1,200 (people) |
| rest of backend | ~66,000 | ~25,000 | ~6,000 |
| front end (excluding the generated client) | ~45,000 | ~17,000 | ~7,000 |

Roughly a third of Tech Startup Tycoon is useful to Partner Track; about a tenth is usable without edits.

---

## 7. What is new for a law firm

| System | Where it comes from in the spec | Nearest TST analogue |
| --- | --- | --- |
| **Practice areas** with demand cycles, rate cards, leverage norms, margins, task mix and AI exposure | spec §6 | categories and segments (§11) |
| **Clients as relationships**: wallets by practice, panels, RFPs, relationship partners, origination credit, cross-selling, the general counsel as a person, alumni in-house | spec §7.1–7.4 | customers are anonymous in TST: **new** |
| **Matters** as projects: staffing plan, budget, hours by level and task, progress, outcome, WIP, billing, realisation, collection, write-downs; two fidelity tiers | spec §7.5–7.8, ADR PT-0004 | products in development (§11.3) for progress only: **new** |
| **Timekeeping**: capacity, targets, utilisation, hours as tenths | ADR PT-0005 | **new** |
| **Billing models**: hourly, blended, capped, fixed fee, success fee, contingency, retainer | spec §7.7 | **new** |
| **Conflicts of interest** as an engine rule with waivers, ethical walls and lateral/merger conflicts | spec §11.2, ADR PT-0009 | **new** |
| **Partnership economics**: equity and income partners, points, lockstep, modified lockstep, eat-what-you-kill, capital accounts, draws, the year-end true-up, PEP, leverage | spec §8, ADR PT-0003 | cap table (§14) is replaced |
| **The partnership as governor**: confidence, managing-partner elections, admission votes, de-equitisation, merger votes | spec §9.2, ADR PT-0007 | the board (§14.6) |
| **Up-or-out and the annual partnership vote** | spec §5.5 | promotions (§13.8) are a small part |
| **Lockstep associate salary scale** and bonus season | spec §5.4 | **new** |
| **Per-person strain and burnout** from billing pressure | spec §5.6, ADR PT-0006 | founder stress (§32.1), generalised |
| **Practice familiarity** (Football Manager position ratings) | spec §5.1 | **new** |
| **Partner portability and the exodus spiral** | spec §8.7 | poaching (§15.6), extended |
| **Directory rankings and league tables** | spec §12.3 | rankings (§30.4) |
| **Malpractice, insurance and disciplinary cases** | spec §11.3–11.4 | regulation machinery (§48) |
| **Client money** (trust accounts) kept apart from firm cash | ADR PT-0003 | **new** |
| **Ownership rules by jurisdiction and date** (ABS, Arizona, Utah, DC) | spec §11.5, ADR PT-0010 | **new** |
| **Legal technology and AI as task-level eras** | spec §13, ADR PT-0011 | eras (§21, §27.3) |
| **Opposing counsel**: rival firms' teams on the other side of named matters | spec §7.6 | **new** |
