# Partner Track roadmap

**Status: DRAFT for Reece's review (2026-11-17).** Same process as Tech Startup Tycoon: one brief per milestone in `docs/tasks/`, up to three lanes at once under CLAUDE.md §9's decision rules, one named session merges each milestone through a pull request with a `Milestone-Tag:` trailer, a Codex review every five to six milestones, and a playtest on a played save every second one.

Milestone ids are prefixed `PT-` so they never collide with TST's in conversation or in tags (`pt-m3a-done`).

## v1: the playable core (2005–2015, one country)

Goal: a founding partner can start a firm in January 2005, staff and bill matters for real clients, survive 2008, hold a partnership vote, and play ten years to December 2015 with rivals that behave like real firms.

| Milestone | Lane | What | Depends on | Brief |
| --- | --- | --- | --- | --- |
| **PT-M0, foundation** | A | new repository; vendored kernel with provenance (ADR PT-0001); guard tests; calendar from 2005; schema v1; the 12-phase runner; API and UI shell; CI | — | `PT-M0-foundation.md` |
| **PT-M1a, lawyers** | A | skills, levels, practice familiarity, generation with school tiers, growth with learning, reveal, strain | PT-M0 | `PT-M1a-lawyers.md` |
| **PT-M1b, hiring and pay** | A | campus cycle, lateral associates, the salary scale and bonuses, payroll, morale with the new terms, resignations | PT-M1a | `PT-M1b-hiring-and-pay.md` |
| **PT-M2, org and practice groups** | B, beside PT-M1b | practice groups and teams, supervision span, manager quality and mentoring on matters, delegated hiring | PT-M1a | `PT-M2-org-and-practice-groups.md` |
| **PT-M3a, clients and matters: rules** | A | practices data, demand, clients and wallets, relationships, intake, conflicts, named matters and flow work, staffing, hours, progress, outcomes | PT-M1b, PT-M2 | `PT-M3a-clients-and-matters.md` |
| **PT-M3b, billing and collections** | B | billing models, WIP to bills to cash, realisation, write-downs, collections, disputes; the ledger chain (ADR PT-0003, 0005) | PT-M3a's sub-task 4 | `PT-M3b-billing-and-collections.md` |
| **PT-M3c, matters and clients screens** | C | Matters, Matter, Clients, Client, Practices screens; staffing board | PT-M3a | `PT-M3c-screens.md` |
| **PT-M4, the partnership** | A | capital, draws, true-up, the revolver and covenants; comp systems; PEP; partner confidence; the December vote and up-or-out; the MP election; laterals with books and guarantees; partner flight; dissolution | PT-M3b | `PT-M4-the-partnership.md` |
| **PT-M5, rival firms** | B | 40 real firms at 2005 values, generated firms, personalities and utility AI, panels and RFPs, poaching both ways, spin-off boutiques, the history pin to 2015 | PT-M3a | `PT-M5-rival-firms.md` |
| **PT-M6, events and the LLM** | C | legal templates, the context builder, critical events, storylines, opposing counsel in events, the year-end letter | PT-M3a | `PT-M6-events.md` |
| **PT-M7, balance and v1 close** | A | strategy scripts, the runner, macro history 2005–2015, the 2008 crisis checks, Holiday, History, onboarding, the 10-year run | all of v1 | `PT-M7-balance-and-v1-close.md` |
| **PT-M7b, pressure and balance** | A | a new firm's rate card, difficulty teeth, crisis discounts, an earlier CFO warning, an hours policy; T2 re-read (Reece's decisions on PT-M7, 2026-11-21) | PT-M7 | `PT-M7b-pressure-and-balance.md` |

**Lanes.** Lane A carries the spine (people → matters → partnership → balance). Lane B joins at PT-M2 and stays on systems that touch few shared files. Lane C does screens and events. PT-M3a and PT-M5 are the riskiest; they start as early as their dependencies allow.

**Size.** Each milestone is TST-sized (a few thousand lines plus tests). With TST's observed pace (several milestones a week across lanes), v1 is roughly three to four weeks of agent time; Reece's first full playtest follows PT-M4.

## v2: depth (to 2034, the US and London)

| Milestone | What | Brief (outline) |
| --- | --- | --- |
| PT-M8, seats, authority and pitches | seats (§9.1), the executive committee, practice group leaders, authority with guardrails, pitches, reports with a voice | ports TST M8, M10c, M13b |
| PT-M9, automation everywhere | §9.4's areas, money limits, one-offs, digest, Automation screen | ports TST M27a |
| PT-M10, history to 2025, then seeded | macro and legal indices to 2025; salary scale; rivals' history pin to 2025; seeded cycles to 2034 | |
| PT-M11, offices, cities and London | offices and leases, bar admissions, pro hac vice, the UK's rules, trainees and NQs | ports TST M9 |
| PT-M12, all twenty practices | the remaining practices, cross-sell affinities, contingency and litigation funding | |
| PT-M13, mergers and the verein | combinations voted by both firms, points ratio, conflicts clearance, integration, the verein | ports TST M14, M16 |
| PT-M14, legal technology and AI | task mixes, eras, adoption, client expectations, training, fixed-fee products | |
| PT-M15, risk and ethics | malpractice and insurance, discipline, trust accounts, billing audits | ports TST M34's case machinery |
| PT-M16, reputation, press and rankings | reputation, legal press, public claims, revenue tables, league tables, directories | ports TST M14b, M15b |
| PT-M17, the founding partner's life and succession | stress (already), persona, personal account, foundation, family, succession by election | ports TST M24, M26, M36 |
| PT-M18, v2 balance | seeds 1-40, every known miss and expected failure, 30-year targets, turn time, a sharded nightly | runs alone, after PT-M12 |

## v3: the world

Foreign offices under local rules (Asia, Europe, the Gulf); ABS entities, outside capital and listing; Big Four and ALSPs as rivals; a 2010 scenario pack; dynasty mode.

**Outline (2026-11-26):** `docs/v3-outline.md` (PT-M19 to PT-M32, in five phases, each followed by a balance pass), for Reece's decisions. The `sim-core` checkpoint below is now due: TST closed v5 on 2026-11-21.

## The `sim-core` checkpoint

Per ADR PT-0001 §5: when TST v5 closes **and** PT-M7 has merged, the product manager writes a short plan for extracting `sim-core` from both codebases, for Reece's decision. Until then the vendoring check keeps the copies honest.

**Plan accepted (Reece, 2026-11-26):** `docs/sim-core-plan.md`, every default; `Reece77/sim-core` created. Next: SC-1 (beside PT-M18), then SC-2 as PT-M19a, alone, before PT-M19's world framework. Plaza's route (SC-1 and SC-2) costs two milestones; moving TST as well costs about five in all.
