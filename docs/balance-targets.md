# Balance targets (v1)

**Status: DRAFT for Reece's approval.** As in TST: the balance runner plays every strategy on the same seeds, prints every target, and fails the nightly run on pass/fail targets; bands are tuned with `balance.yaml` keys only, or brought back to Reece.

## Setup

| | |
| --- | --- |
| Seeds | **1–40 for every target and guard (PT-M18, 2026-11-27; Reece's rule of 2026-11-25, CLAUDE.md §12.1), with thresholds as shares of seeds** (6 of 10 becomes at most 60%, 9 of 10 at least 90%; a median stays a median): `ptk/balance/seeds.py`. Before PT-M18: seeds 1–10, with 11–40 for seed-luck checks |
| Turns | 132 (January 2005 to December 2015) |
| Scenario | `biglaw_spinout`: an M&A partner and a litigator found a firm in New York with two associates, $600,000 of partners' capital and a $1M revolver, books of $2.5M and $1.5M |
| Difficulty | standard; T5 also easy and hard |
| Events | on, `MockLLMAdapter`; first choice |

## Strategies

| Strategy | People | Work | Money | Partnership |
| --- | --- | --- | --- | --- |
| **do-nothing** | founders only | flow work only, no BD | no revolver use | no votes |
| **boutique** | grow to 25 lawyers, leverage ≤ 2 | two practices, high rates, premium clients | conservative | pure lockstep; admit one partner every two years |
| **steady** | grow while utilisation ≥ 80%; campus class each year; PT-M7c: lays off associates while utilisation stays below 70% | add a practice at each 30 lawyers; cross-sell | revolver ≤ 1 × monthly fees | modified lockstep; admit by business case |
| **lateral rocket** | lateral partners whenever a book of $2M+ is available, with guarantees | follow laterals' books | revolver to its covenant limit | eat what you kill |
| **pyramid** | leverage 5+, utilisation targets 2,100 hours (PT-M7b: an hours policy of 2,300); PT-M10: lays off associates while utilisation stays below 75%; PT-M7c: pays 80% of the scale | volume work, fixed fees | moderate | two-tier; few equity admissions |

All strategies staff named matters by the default rule, bill monthly, accept the first settlement offer above the expected value and never de-equitise (except pyramid).

## Targets

| # | Target | Kind |
| --- | --- | --- |
| T1 | **Do-nothing fails:** revenue below $3M and falling at year 5, or dissolved, on at least 90% of seeds (PT-M18; before: ≥ 9 of 10) | pass/fail |
| T2 | **No dominant strategy:** no strategy has the best firm score at year 11 on more than 60% of seeds (PT-M18; before: more than 6 of 10) | pass/fail |
| T3 | **Growth is possible:** steady reaches 100–250 lawyers and $60M–$150M revenue (nominal) by December 2015, median | band |
| T4 | **PEP is believable:** at year 11, median PEP $500k–$1.2M for steady, $1.0M–$2.5M for boutique, $0.7M–$1.6M for pyramid | band |
| T5 | **Difficulty matters:** steady's dissolution rate easy 0–10%, standard 5–20%, hard 20–45% | band |
| T6 | **Associate attrition** 15–25% a year (median across years and strategies); 8–15% of a September class make equity partner within 10 years in steady | band |
| T7 | **Real ratios:** median realisation 84–92%, collection 93–98%, utilisation 75–90%, lockup 90–150 days | band |
| T8 | **The crash bites:** 2009 revenue against 2008, a corporate-heavy firm −10% to −30%; a firm with a restructuring practice above 20% of revenue −5% to +20% | band |
| T9 | **The spiral is real but survivable:** lateral rocket dissolves on 30–60% of seeds by 2015 (PT-M18; before: 3–6 of 10); the same strategy with the CFO's warnings heeded (a script rule: stop guarantees and repay the revolver when the warning comes) dissolves on at most 10% (before: at most 1 of 10) | band |
| T10 | **Strain matters:** pyramid's associates burn out at least twice as often as steady's; steady's at most 5% a year | band |
| T11 | **Rivals hold history:** each pinned rival's revenue within ±15% of its path in December 2009, 2015, 2020 and 2025 (PT-M10); the top 10 by revenue in 2015 (and in 2025 on the long runs) contains at least 8 of history's | pass/fail |
| T12 | **Turn time:** median turn ≤ 250 ms at December 2025 (PT-M10; PT-M5: 2015) on the steady save | pass/fail |
| T14 | **Claims are believable (PT-M15, proposed for the product manager's approval):** steady's malpractice claim notices 2006-2015, per 100 lawyer-years, median of seeds 1-40 (PT-M18; before: 1-10), within 1.5-5.0 (the dossier's 2-4 notices a 100 lawyers a year, widened for a small firm's sampling); steady's premium a lawyer in December 2015 within $5k-$10k | band |
| T13 | **Integration costs partners (PT-M13, proposed for the product manager's approval):** of the combined equity partnership at closing, 10-20% gone within 24 months (every exit), median over the `merger` strategy's mergers on seeds 1-40 (PT-M18; before: 1-10) (docs/research/law-firm-mergers.md s4: A&O Shearman ~17% in 17 months with a planned cut; ~4% before go-live; 8-12% background turnover) | band |
| T15 | **Rivals grow as history did (PT-M18, approved by the product manager, 2026-11-27):** each real rival's revenue growth a year, FY2025 to FY2034, within history's ten-year range of the modelled rivals' sourced paths (-0.4% to +18.3%), and the median within history's twenty-year p10-p90 (3.6%-9.2%; 43 firms 2005-2025, median 6.2%) | band |
| T16 | **Dissolutions are believable (PT-M18, approved):** collapses of the real rivals active in December 2025, 2026-2034, scaled to a decade: median 0-4, and at least one on at least 20% of seeds (history: 4 of 43 in 2005-2015, 0 of 38 in 2016-2025; docs/research/rivals-2005.md, history-2016-2025.md) | band |
| T17 | **No dominant strategy at year 30 (PT-M18, approved):** T2's measure to December 2034 (the founding partner's allocations 2005-2034, 0 if dissolved), every strategy played to 2034: no strategy best on more than 60% of seeds | pass/fail |
| T18 | **The AI era (PT-M18, approved; PT-M14's criteria 2 and 4):** a fully adopted firm's AI-exposed tasks take 40-70% fewer hours by December 2030 on every seed; the 2030 junior cohort's growth falls without training (median) and training restores at least half of it (median) | band |
| T8.2020 | **The pandemic bites (PT-M10):** a corporate-heavy firm's April-June 2020 revenue falls 10-30% against January-March, recovering by Q4 2021 | band |

## Forty seeds (PT-M18 sub-task 1, 2026-11-27)

Every target and guard reads `ptk.balance.seeds.SEEDS` (1-40); counts of seeds become shares (`at_least`, `at_most`). The bands are unchanged; a known miss's score that counted seeds is now the same count as a share.

| Target or guard | Before PT-M18 | From PT-M18 |
| --- | --- | --- |
| T1 | do-nothing fails on ≥ 9 of seeds 1-10 | on ≥ 90% of seeds 1-40 (36 of 40); score: minus the share |
| T2, T2.specialist | no strategy best on more than 6 of 10 | on more than 60% (24 of 40); score: the most wins as a share (T2's known miss: 9 of 10 read as 0.9) |
| T3, T4, T5, T6, T7, T8, T10, T8.2020, 30y | medians / rates over seeds 1-10 | the same over seeds 1-40 |
| T9 rocket / heeded | 3-6 of 10 / at most 1 of 10 | 30-60% (12-24 of 40) / at most 10% (4 of 40); scores as shares |
| T11 | every pinned rival on each of seeds 1-10 | on each of seeds 1-40 (seed 1 in `check`, as before) |
| T12 | the runner's steady runs (printed) | unchanged (the gate is `check-timing`) |
| T13, T14 | medians, seeds 1-10 (seeds 11-40 printed) | medians, seeds 1-40 (the separate 11-40 readings fold in) |
| PT-M12.specialist | survives on ≥ 7 of 10 | on ≥ 70% |
| PT-M5 conditional history | Howrey early on ≥ 7 of 10 | on ≥ 70% |
| PT-M11 London lift | pays within 3 years on ≥ 6 of 10 | on ≥ 60% of the seeds whose firm is alive in January 2007, and opens on every such seed (the product manager's decision, 2026-11-27) |
| PT-M15 cowboy | 2x claims on ≥ 8 of 10; lower PEP on ≥ 6 of 10 | on ≥ 80%; on ≥ 60% |
| PT-M7a acceptance firm, PT-M8 leaders and pitches, PT-M9 automated, PT-M16 pace | medians / all over seeds 1-5 (PT-M7a) or 1-10 | the same over seeds 1-40 |
| PT-M14 criterion 3 (`tools/tech_readings.py`) | 7 of 10 | at least 70% |

## Known misses

Recorded in `backend/ptk/balance/known_misses.py` by Reece's decision on PT-M7 (2026-11-21), each owned by PT-M7b (`docs/tasks/PT-M7b-pressure-and-balance.md`): T2, T3 (lawyers), T4 (steady and pyramid), T5 (standard and hard), T8, T9 and T10. T6's class reading (7.7% against 8%) is accepted as sampling noise.

PT-M7b (2026-11-21) removed T5 (standard and hard), T9 (the rocket and the heeded rocket) and T10 (the ratio), which now pass on seeds 1-10, and carries T2, T3 (lawyers), T4 (steady and pyramid) and T8 (corporate and restructuring) with its readings back to Reece (the brief's "Decisions made").

**Reece's decisions on PT-M7b's targets (2026-11-22), applied by PT-M10 (sub-task 0):**

- **T2:** the measure is unchanged; the known miss is owned by PT-M18.
- **T3 lawyers and T4 steady:** bands unchanged; the known misses are owned by PT-M16 (reputation that gates the card).
- **T4 pyramid:** band unchanged; the pyramid script lays off associates while its utilisation stays below a threshold (a script fix, TST's §9 rule 2). Its row is no longer a known miss (PT-M10's reading is in its brief).
- **T8 corporate-heavy:** PT-M7b's −9.0% is **accepted as noise** against the −10% edge: its known-miss row (owner "accepted") holds while the median fall is at least 5%.
- **T8 restructuring** is measured only on firms with at least 10 lawyers in December 2008 (Measures).
- **T9 heeded:** the heeded rocket asks the CFO's forecast before a guaranteed lateral and takes none until six months of trend show headroom (Measures).

**Reece's decisions on PT-M7c's open items (2026-11-24):** steady keeps its layoff rule and T6 counts departures other than layoffs (layoffs print as `T6.layoffs`; band unchanged); steady-automated takes the same layoff rule; T3 (lawyers and revenue) and T4 steady are known misses owned by PT-M18 (growth from PT-M12 and PT-M13); the pyramid's 80% pay and the book's 24-month hold and 60-month fade are approved. T1 and T4 pyramid pass after the client tiers and their rows are removed.

**PT-M15 (2026-11-25), the product manager's decisions:** T2 (steady 9 of seeds 1-10; seeds 11-40 16/30 on the branch, 19/30 on main) and T5.standard (seed variance: 0/10; 2/30 on both) are known misses owned by PT-M18 (`docs/tasks/PT-M15-risk-and-ethics.md`, decision 15).

**PT-M18 (2026-11-27), the product manager's decisions on seeds 1-40** (`docs/tasks/PT-M18-v2-balance.md`, decision 13): T2, T3.revenue, T5.standard and T8.corporate pass and their rows are removed; T14 reads 1.4951 and keeps its row at Reece's 1.495 bound (decision 15). T3.lawyers (73.5), T4.steady ($1.3168M), T6.partners (0.0%, a new row) and T13 (23.1%) are carried to v3, owned by PT-M23 (`docs/v3-outline.md`), each bounded at its 40-seed reading; PT-M14.fixed_fees stays, bounded at 24 of 40 (60%), owned by PT-M23. T4.steady gives way to T14: the claim rate that holds T14 at 1.4951 (its known-miss bound) lifts steady's PEP from $1.19M. The expected failures PT-M8 (a strong leader's utilisation gap 2.8 points, needs 3.0), PT-M9 (automated steady's PEP +32.9%, band 20%) and PT-M4's heeded exodus (5 of 40, at most 4; main the same) are non-strict and owned by PT-M23. No band is widened and no measure changed.

**PT-M7c (2026-11-23), the firm economics audit** (`docs/tasks/PT-M7c-firm-economics.md`, benchmarks in `docs/research/firm-economics.md`): a partner admitted in December now keeps a budget through December's allocation (homegrown equity partners had been poached within a year, holding leverage at 5.7 lawyers per equity partner). T2 passes on seeds 1-10 (steady 6, pyramid 4) and its row is removed; T3.lawyers (46; seeds 11-40 83.5), T4.steady ($2.72M) and T4.pyramid ($1.65M) keep their bounds, owned by Reece's decision on the rate card (the brief's decision 5: RPL is 83% above the Second Hundred's, from the rate).

## Measures (PT-M7)

How `ptk/balance/report.py` reads each target (`make balance`; `tools/balance_runner.py --runs` prints one line per run). Year 1 is 2005, year 5 2009, year 11 2015; a run is 132 turns of `biglaw_spinout` over the pure sim, critical events answered with their first choice, events written by `MockLLMAdapter`.

| # | Measure |
| --- | --- |
| T1 | do-nothing runs where the firm dissolved, or 2009's revenue (the year's fees) is below 2008's and below $3M **in 2005 dollars**: deflated by the game's market rate index for 2009 (the macro history's January rises; Reece, 2026-11-21). The nominal count is printed beside it |
| T2 | the score at December 2015 = the founding partner's earnings: the December allocations of the partner the player plays, summed over 2005-2015 (TST's founder value, for a partnership; 0 if the firm dissolved); a strategy wins a seed with the best score (a tie wins nobody) |
| T3 | steady's lawyers on the books in December 2015 and its 2015 revenue, medians over seeds |
| T4 | PEP (trailing 12 months) in December 2015, a dissolved firm counting 0, medians |
| T5 | steady's share of seeds dissolved by December 2015 at each difficulty |
| T6 | attrition (**Reece, 2026-11-24:** departures other than layoffs; layoffs print as their own line, `T6.layoffs`, pooled layoffs over associate-years 2006-2015; the band is unchanged at 15-25%): associates who left in a year / the year's average associates, for each full year 2006-2015 with two or more associates, median over years and the four active strategies; partners: steady's September 2006 class (the first class a January 2005 firm can hire) made equity partner by December 2015 (track 8: eligible from December 2014) |
| T7 | utilisation: monthly, 2006-2015; realisation, collection and lockup: December's trailing-12-month values; medians over the five strategies' standard runs |
| T8 | 2009's revenue over 2008's: "corporate-heavy" = M&A, PE, capital markets and banking at least half of 2008's revenue; "restructuring" = restructuring above 20% of 2009's, **on firms with at least 10 lawyers in December 2008** (Reece, 2026-11-22); every standard run that qualifies (the `restructuring` variant, steady with a restructuring lateral from 2005, makes sure some do). Corporate-heavy's −9% (PT-M7b) is accepted as noise |
| T9 | lateral rocket's dissolutions by December 2015; the `lateral-rocket-heeded` variant: when the CFO warns (or a covenant breaks), it stops new laterals, suspends draws, calls $1M of capital and repays the revolver from spare cash; and (Reece, 2026-11-22) before any guaranteed lateral it asks the CFO's forecast (the Finance screen's): none until six months of trend (`forecast_window` + 1 month ends) show headroom on every covenant now and for `forecast_months` |
| T10 | burnout starts among associates / associate-years, pooled over each strategy's runs |
| T11 | PT-M5's measure (`tests/balance/test_pt_m5.py`), read from the steady runs' rivals at 2009 and 2015 (top 10 at 2015), and (PT-M10) from `steady-30y`'s rivals, steady played to December 2034, at 2009, 2015, 2020 and 2025 (top 10 at 2025): row `T11.2025` |
| T12 | printed: the steady runs' median turn in 2015 (pure sim, on the runner's machine with its workers sharing cores); the gate is `make check-timing`'s test (PT-M5's, run alone, CLAUDE.md §9 rule 6), timing 2025's turns from PT-M10. **Measure from 2026-11-25** (Reece's decision on PT-M12): each case's last 12 turns of 2025 are replayed from their own states and timed five times; the gate reads the median of the five runs' medians, budget unchanged at 250 ms. **Measure from 2026-11-26** (Reece's decision, after main's `check` read 256 and 261 ms on the median): the gate reads the **minimum** of the five runs' median turns (`tests/balance/test_pt_m5.py` `t12_ms`), budget unchanged at 250 ms. PT-M18's criterion is unchanged: the median of five, at most 200 ms on CI's runner in December 2025 |
| T8.2020 | `steady-30y` runs with M&A, PE, capital markets and banking at least half of 2019's revenue: the median of 2020 Q2's revenue over Q1's; recovered when most of them have Q4 2021's revenue at least Q1 2020's (PT-M10) |
| T14 | `tests/balance/test_pt_m15.py` (nightly): claims noticed 2006-2015 over lawyer-months / 12 from 2006, per seed, the median; the premium a lawyer is the policy in force in December 2015 over lawyers on the books. PT-M15's reading: median 1.69 (seeds 1-10), premium median $7.0k |
| T13 | `tests/balance/test_pt_m13.py` (nightly): `mergers.integration.partners_lost_share` over each `merger` run's integration (`lost_partners` / the partnership at closing, within 24 months), median; seeds 11-40 printed beside steady |
| T15 | `steady-30y` runs that reach December 2034: every real rival with FY2025 and FY2034 records, (FY2034 / FY2025)^(1/9) - 1; each within the range, the median of all firm-seeds within the median band |
| T16 | `steady-30y` runs that reach December 2034: real rivals with an FY2025 record still active in January 2026 that end `collapsed` or `failed` by December 2034, x 10/9; the median over runs, and the share of runs with at least one |
| T17 | `<strategy>-30y` (every strategy, 360 turns): wins on each seed by `RunResult.score_30y`, as T2 |
| T18 | row T18 of the balance run (`report._t18`; each nightly balance shard plays its seeds' `ptk.balance.ai_era.read_seed`, `tools/tech_readings.py`'s criterion 2 (every seed) and criterion 4 (the restored share (trained - untrained) / (off - untrained) over seeds with a cohort that lost)) |
| 30y | printed for information: `steady-30y` at December 2034 (lawyers, revenue, PEP medians, dissolved); PT-M18 sets the 30-year targets |

- **PT-M14 criterion 3 (fixed fees against hourly, 2026-2030 PEP):** a known miss owned by PT-M18 (row `PT-M14.fixed_fees`, authorised by the product manager on Reece's decision of 2026-11-23): 4 of 10 on seeds 1-10, 9 of 30 on seeds 11-40 (`tools/tech_readings.py --criterion3`).
