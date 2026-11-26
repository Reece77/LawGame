# Task briefs

Each brief is a self-contained prompt for a coding agent, in Tech Startup Tycoon's format. Hand one brief to one Claude Code session in its own clone or worktree.

## How to run a brief

1. Start a fresh session in the `partner-track` repository root (it reads `CLAUDE.md`).
2. Paste: `Read docs/tasks/<brief>.md and implement it. Follow CLAUDE.md. Work through the sub-tasks in order, committing after each. Stop and ask if anything in the brief conflicts with the spec or ADRs.`
3. The session merges through a pull request when `make check`, `make e2e` and CI are green, with the trailer `Milestone-Tag: pt-mX-done`.
4. **Tech Startup Tycoon is read-only** for every Partner Track session: clone it to read and copy; never commit, push, open pull requests or run workflows there (Reece, 2026-11-17).

## Order (v1)

| Brief | Milestone | Depends on |
| --- | --- | --- |
| [PT-M0-foundation.md](PT-M0-foundation.md) | Repository, vendored kernel, guards, schema v1, turn runner, API and shell | — |
| [PT-M1a-lawyers.md](PT-M1a-lawyers.md) | Lawyers: skills, levels, familiarity, generation, growth, reveal, strain | PT-M0 |
| [PT-M1b-hiring-and-pay.md](PT-M1b-hiring-and-pay.md) | Campus, laterals, salary scale, payroll, morale, resignations, screens | PT-M1a |
| [PT-M2-org-and-practice-groups.md](PT-M2-org-and-practice-groups.md) | Practice groups, supervision, delegated hiring | PT-M1a |
| [PT-M3a-clients-and-matters.md](PT-M3a-clients-and-matters.md) | Practices, demand, clients, conflicts, matters, staffing, outcomes | PT-M1b, PT-M2 |
| [PT-M3b-billing-and-collections.md](PT-M3b-billing-and-collections.md) | Billing models, WIP, bills, collections, write-downs | PT-M3a sub-task 4 |
| [PT-M3c-screens.md](PT-M3c-screens.md) | Matters, Clients and Practices screens | PT-M3a |
| [PT-M4-the-partnership.md](PT-M4-the-partnership.md) | Capital, comp, PEP, votes, elections, laterals, flight | PT-M3b |
| [PT-M5-rival-firms.md](PT-M5-rival-firms.md) | Real rivals, utility AI, RFPs, poaching, history pin | PT-M3a |
| [PT-M6-events.md](PT-M6-events.md) | Events and the LLM | PT-M3a |
| [PT-M7a-v1-gaps.md](PT-M7a-v1-gaps.md) | Scenario fix, staffing for expected output, pro bono, early case assessment, rate rises, Holiday stops | PT-M3a–PT-M6 |
| [PT-M7-balance-and-v1-close.md](PT-M7-balance-and-v1-close.md) | Strategies, macro history, balance, Holiday, History | all |
| [PT-M7b-pressure-and-balance.md](PT-M7b-pressure-and-balance.md) | A new firm's card, difficulty teeth, crisis discounts, an earlier CFO warning, an hours policy; T2 re-read | PT-M7 |

## v2, first wave (2026-11-21)

| Brief | Milestone | Depends on |
| --- | --- | --- |
| [PT-M7b-pressure-and-balance.md](PT-M7b-pressure-and-balance.md) | Pressure and balance (v1's known misses) | PT-M7 |
| [PT-M8-seats-authority-pitches.md](PT-M8-seats-authority-pitches.md) | Seats, authority, pitches, reports | PT-M7 (wires CFO, pricing and COO effects after PT-M7b) |
| [PT-M17-founder-life-and-succession.md](PT-M17-founder-life-and-succession.md) | The founding partner's life, family and succession | PT-M7 |

RNG ids by lane: PT-M7b 42-44, PT-M8 45-49, PT-M17 50-59.

## v2, second wave (2026-11-22)

| Brief | Milestone | Depends on |
| --- | --- | --- |
| [PT-M10-history-to-2025.md](PT-M10-history-to-2025.md) | History to 2025, seeded to 2034; Reece's decisions on PT-M7b's targets | PT-M7b |
| [PT-M9-automation.md](PT-M9-automation.md) | Automation everywhere | PT-M8 |
| [PT-M16-reputation-press-rankings.md](PT-M16-reputation-press-rankings.md) | Reputation, press and rankings | PT-M7b |

RNG ids by lane: PT-M9 60-64, PT-M10 65-69, PT-M16 70-79.

## v2, third wave (2026-11-22)

| Brief | Milestone | Depends on |
| --- | --- | --- |
| [PT-M7c-firm-economics.md](PT-M7c-firm-economics.md) | Firm economics audit (T3, T4) | PT-M16 |
| [PT-M11-offices-and-london.md](PT-M11-offices-and-london.md) | Offices, cities and London | PT-M10 |
| [PT-M14-legal-tech-and-ai.md](PT-M14-legal-tech-and-ai.md) | Legal technology and AI | PT-M10 |

RNG ids by lane: PT-M7c 80-84, PT-M11 100-109, PT-M14 110-119 (99 stays tests-only).

## v2, fourth wave (2026-11-24)

| Brief | Milestone | Depends on |
| --- | --- | --- |
| [PT-M12-all-twenty-practices.md](PT-M12-all-twenty-practices.md) | All twenty practices, contingency and litigation funding | PT-M7c |
| [PT-M13-mergers-and-the-verein.md](PT-M13-mergers-and-the-verein.md) | Mergers and the verein | PT-M7c (uses PT-M11's offices) |
| [PT-M15-risk-and-ethics.md](PT-M15-risk-and-ethics.md) | Malpractice, insurance, discipline, trust accounts, billing audits | PT-M7c |

Lanes: PT-M12 A (owns `ptk/balance/` and re-reads for every lane), PT-M13 B, PT-M15 C. RNG ids by lane: PT-M12 120-129, PT-M13 130-139, PT-M15 140-149. ADRs reserved: PT-0016 (PT-M13), PT-0017 (PT-M15). PT-M18 (v2 balance) follows all three.

## v2, closing (2026-11-25)

| Brief | Milestone | Depends on |
| --- | --- | --- |
| [PT-M18-v2-balance.md](PT-M18-v2-balance.md) | v2 balance: seeds 1-40, every known miss, 30-year targets, turn time, a sharded nightly | PT-M12 (runs alone) |

From 2026-11-25, sessions settle seed variance and inherited misses themselves under CLAUDE.md §12, and stop only on real regressions.
