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
