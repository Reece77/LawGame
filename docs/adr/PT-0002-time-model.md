# ADR PT-0002: Time model: January 2005 start, monthly turns, firm-year cycles

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Supersedes for Partner Track: TST ADR-0006 (turn 0 = January 2010) and ADR-0011's start year
- Inherits: ADR-0006's monthly turn, the 12-phase order, `birth_turn`, no weekly sub-turns in v1

## Context

Reece asked for a start in 2005 or 2010 with the 2008 crisis, the 2020 pandemic, the 2021 deal boom and generative AI from 2023. A 2010 start misses the crash and the 2005–2007 boom (the lateral-partner wars, the Dewey & LeBoeuf merger of 2007, record private-equity activity), and leaves the 2012 Dewey collapse with no build-up. TST hard-codes turn 0 as January 2010 in `calendar.py`.

## Decision

1. **Turn 0 = January 2005 by default**; a standard campaign is 360 turns, ending December 2034. The base year is a field of the scenario (`scenarios.yaml: start_ym`), read by `calendar.turn_to_ym` through `GameData`, never a constant. A **2010 "after the crash" scenario** is a separate seed pack (rivals, clients, rates, salaries at 2010 values) delivered in v2.
2. **History is pinned to December 2025, then seeded** (TST ADR-0019 §9, §15): macro indicators, deal and litigation volumes, the associate salary scale, real firms' headline numbers, regulatory changes. From 2026 every series follows seeded cycles within published bands.
3. **Firm-year cycles** run inside monthly turns and are fixed in data:

| Month | What happens |
| --- | --- |
| January | New rate cards take effect; partner points for the year are set; compensation for the prior year is finalised |
| March–April | Directory research submissions due (v2); league tables for the prior year published |
| May–June | Summer associates arrive (US); trainee seats rotate (UK) |
| August | Campus interviewing (US); offers to summer associates |
| September | The new associate class starts; NQ qualification (UK) |
| October | Directory rankings published (v2) |
| November | Year-end bonus announcements (market-wide, then the firm's); budget for next year |
| December | Partnership admission vote; de-equitisation decisions; year-end collections push; profit true-up and distribution |

4. **No weekly sub-turns in v1.** v2 may add **trial weeks**: a critical named matter in trial opens up to four weekly sub-turns (ADR-0006's original design), which TST deferred.

## Consequences

- The 2008 crisis lands in year 4, after the player has built something worth protecting: the right time for the game's first great test.
- The year has a rhythm the player plans around (Football Manager's season), which a tech startup lacked.
- Seeding beyond 2025 begins in year 21 of 30, so the last third is the player's own future, with AI as its main force (ADR PT-0011).
