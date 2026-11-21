# Balance targets (v1)

**Status: DRAFT for Reece's approval.** As in TST: the balance runner plays every strategy on the same seeds, prints every target, and fails the nightly run on pass/fail targets; bands are tuned with `balance.yaml` keys only, or brought back to Reece.

## Setup

| | |
| --- | --- |
| Seeds | 1–10 (nightly); 11–40 for seed-luck checks (CLAUDE.md §9 rule 4) |
| Turns | 132 (January 2005 to December 2015) |
| Scenario | `biglaw_spinout`: an M&A partner and a litigator found a firm in New York with two associates, $600,000 of partners' capital and a $1M revolver, books of $2.5M and $1.5M |
| Difficulty | standard; T5 also easy and hard |
| Events | on, `MockLLMAdapter`; first choice |

## Strategies

| Strategy | People | Work | Money | Partnership |
| --- | --- | --- | --- | --- |
| **do-nothing** | founders only | flow work only, no BD | no revolver use | no votes |
| **boutique** | grow to 25 lawyers, leverage ≤ 2 | two practices, high rates, premium clients | conservative | pure lockstep; admit one partner every two years |
| **steady** | grow while utilisation ≥ 80%; campus class each year | add a practice at each 30 lawyers; cross-sell | revolver ≤ 1 × monthly fees | modified lockstep; admit by business case |
| **lateral rocket** | lateral partners whenever a book of $2M+ is available, with guarantees | follow laterals' books | revolver to its covenant limit | eat what you kill |
| **pyramid** | leverage 5+, utilisation targets 2,100 hours (PT-M7b: an hours policy of 2,300) | volume work, fixed fees | moderate | two-tier; few equity admissions |

All strategies staff named matters by the default rule, bill monthly, accept the first settlement offer above the expected value and never de-equitise (except pyramid).

## Targets

| # | Target | Kind |
| --- | --- | --- |
| T1 | **Do-nothing fails:** revenue below $3M and falling at year 5 on ≥ 9 of 10 seeds, or dissolved | pass/fail |
| T2 | **No dominant strategy:** no strategy has the best firm score at year 11 on more than 6 of 10 seeds | pass/fail |
| T3 | **Growth is possible:** steady reaches 100–250 lawyers and $60M–$150M revenue (nominal) by December 2015, median | band |
| T4 | **PEP is believable:** at year 11, median PEP $500k–$1.2M for steady, $1.0M–$2.5M for boutique, $0.7M–$1.6M for pyramid | band |
| T5 | **Difficulty matters:** steady's dissolution rate easy 0–10%, standard 5–20%, hard 20–45% | band |
| T6 | **Associate attrition** 15–25% a year (median across years and strategies); 8–15% of a September class make equity partner within 10 years in steady | band |
| T7 | **Real ratios:** median realisation 84–92%, collection 93–98%, utilisation 75–90%, lockup 90–150 days | band |
| T8 | **The crash bites:** 2009 revenue against 2008, a corporate-heavy firm −10% to −30%; a firm with a restructuring practice above 20% of revenue −5% to +20% | band |
| T9 | **The spiral is real but survivable:** lateral rocket dissolves on 3–6 of 10 seeds by 2015; the same strategy with the CFO's warnings heeded (a script rule: stop guarantees and repay the revolver when the warning comes) dissolves on at most 1 | band |
| T10 | **Strain matters:** pyramid's associates burn out at least twice as often as steady's; steady's at most 5% a year | band |
| T11 | **Rivals hold history:** each pinned rival's revenue within ±15% of its path in December 2009 and December 2015; the top 10 by revenue in 2015 contains at least 8 of history's | pass/fail |
| T12 | **Turn time:** median turn ≤ 250 ms at December 2015 on the steady save | pass/fail |

## Known misses

Recorded in `backend/ptk/balance/known_misses.py` by Reece's decision on PT-M7 (2026-11-21), each owned by PT-M7b (`docs/tasks/PT-M7b-pressure-and-balance.md`): T2, T3 (lawyers), T4 (steady and pyramid), T5 (standard and hard), T8, T9 and T10. T6's class reading (7.7% against 8%) is accepted as sampling noise.

PT-M7b (2026-11-21) removed T5 (standard and hard), T8 (corporate), T9 (the unchecked rocket) and T10 (the ratio), which now pass on seeds 1-10, and carries T2, T3 (lawyers), T4 (steady and pyramid), T8 (restructuring) and T9 (heeded) with its readings back to Reece (the brief's "Decisions made").

## Measures (PT-M7)

How `ptk/balance/report.py` reads each target (`make balance`; `tools/balance_runner.py --runs` prints one line per run). Year 1 is 2005, year 5 2009, year 11 2015; a run is 132 turns of `biglaw_spinout` over the pure sim, critical events answered with their first choice, events written by `MockLLMAdapter`.

| # | Measure |
| --- | --- |
| T1 | do-nothing runs where the firm dissolved, or 2009's revenue (the year's fees) is below 2008's and below $3M **in 2005 dollars**: deflated by the game's market rate index for 2009 (the macro history's January rises; Reece, 2026-11-21). The nominal count is printed beside it |
| T2 | the score at December 2015 = the founding partner's earnings: the December allocations of the partner the player plays, summed over 2005-2015 (TST's founder value, for a partnership; 0 if the firm dissolved); a strategy wins a seed with the best score (a tie wins nobody) |
| T3 | steady's lawyers on the books in December 2015 and its 2015 revenue, medians over seeds |
| T4 | PEP (trailing 12 months) in December 2015, a dissolved firm counting 0, medians |
| T5 | steady's share of seeds dissolved by December 2015 at each difficulty |
| T6 | attrition: associates who left in a year / the year's average associates, for each full year 2006-2015 with two or more associates, median over years and the four active strategies; partners: steady's September 2006 class (the first class a January 2005 firm can hire) made equity partner by December 2015 (track 8: eligible from December 2014) |
| T7 | utilisation: monthly, 2006-2015; realisation, collection and lockup: December's trailing-12-month values; medians over the five strategies' standard runs |
| T8 | 2009's revenue over 2008's: "corporate-heavy" = M&A, PE, capital markets and banking at least half of 2008's revenue; "restructuring" = restructuring above 20% of 2009's; every standard run that qualifies (the `restructuring` variant, steady with a restructuring lateral from 2005, makes sure some do) |
| T9 | lateral rocket's dissolutions by December 2015; the `lateral-rocket-heeded` variant: when the CFO warns (or a covenant breaks), it stops new laterals, suspends draws, calls $1M of capital and repays the revolver from spare cash |
| T10 | burnout starts among associates / associate-years, pooled over each strategy's runs |
| T11 | PT-M5's measure (`tests/balance/test_pt_m5.py`), read from the steady runs' rivals |
| T12 | printed: the steady runs' median turn in 2015 (pure sim, on the runner's machine with its workers sharing cores); the gate is `make check-timing`'s test (PT-M5's, run alone, CLAUDE.md §9 rule 6) |
