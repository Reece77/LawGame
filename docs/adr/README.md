# Architecture decision records

Partner Track inherits Tech Startup Tycoon's ADRs by reference where they apply. Its own ADRs are numbered `PT-NNNN`. To change a decision, write a new ADR that supersedes the old one.

## Inherited from Tech Startup Tycoon

| TST ADR | Decision | In Partner Track |
| --- | --- | --- |
| 0001 | Stack and fixed dependency list | **Inherited** unchanged (Python 3.12, FastAPI, SQLite, React, Mantine, TanStack) |
| 0002 | Pure core, seeded derived streams | **Inherited** |
| 0003 | Integer cents, double entry | **Inherited**, extended by PT-0003 and PT-0005 |
| 0004 | One SQLite file per save, one transaction per turn, backups, history | **Inherited** (file suffix `.ptk.sqlite`) |
| 0005 | The LLM proposes, the engine disposes | **Inherited** |
| 0006 | Time model, 2010 start | **Superseded** by PT-0002 (2005 start); the 12-phase order is kept with new phase bodies |
| 0007 | Hidden values and revealed ranges | **Inherited**, extended by PT-0006 §5 |
| 0008 | Tunables and seed data in YAML | **Inherited** |
| 0009 | OpenAPI contract, generated client | **Inherited** |
| 0010 | Rivals as full entities | **Inherited**, extended by PT-0008 |
| 0011 | Game-setting decisions | **Superseded** by PT-0013 |
| 0012 | `advance_turn` signature | **Inherited** |
| 0013 | One stream per use, entity keys | **Inherited**; table in PT-0012 |
| 0014 | Immediate actions and pending items | **Inherited** |
| 0015 | Delegates act in phase 2 | **Inherited** |
| 0016 | Offers need an interview | **Inherited** (laterals need a meeting with the MP or a practice leader) |
| 0017 | Static incumbents and product phases | Not applicable |
| 0018 | Shares and game over | **Replaced** by PT-0003 and PT-0007; shares only inside an ABS (PT-0010) |
| 0019 | v2 scope | Not applicable |
| 0020 | Per-company everything | **Inherited** as a principle (every entity has a `firm_id`; member firms of a verein are firms) |
| 0021, 0022 | Platforms, power | Not applicable |

## Partner Track's own

| ADR | Decision | Status |
| --- | --- | --- |
| [PT-0001](PT-0001-code-sharing.md) | Selective transplant now; extract `sim-core` from two working games later | Accepted |
| [PT-0002](PT-0002-time-model.md) | January 2005 start; firm-year cycles; history to 2025 | Accepted |
| [PT-0003](PT-0003-partnership-accounting.md) | Partnership accounting; WIP, bills, collections; client money in its own book | Accepted |
| [PT-0004](PT-0004-matters-two-tiers.md) | Named matters and flow work | Accepted |
| [PT-0005](PT-0005-hours.md) | Hours as integer tenths; rate cards | Accepted |
| [PT-0006](PT-0006-people-for-law.md) | Class years, practice familiarity, strain for everyone | Accepted |
| [PT-0007](PT-0007-partnership-governance.md) | The partnership governs: confidence, votes, elections | Accepted |
| [PT-0008](PT-0008-rivals-real-scale.md) | Rivals at real scale; history pin to 2025 | Accepted |
| [PT-0009](PT-0009-conflicts.md) | Conflicts of interest as an engine rule | Accepted |
| [PT-0010](PT-0010-ownership-by-jurisdiction.md) | Ownership rules by jurisdiction and date (ABS) | Accepted |
| [PT-0011](PT-0011-legal-ai-era.md) | Legal tech and AI act on tasks | Accepted |
| [PT-0012](PT-0012-rng-streams.md) | Stream table; kernel ids reserved | Accepted |
| [PT-0013](PT-0013-game-setting-decisions.md) | Reece's game-setting decisions; real lawyers and judges and their rules | Accepted |
| [PT-0014](PT-0014-macro-history.md) | The macro history to 2015 as dated indices; history's client failures as data | Accepted |
