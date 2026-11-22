# PT-M10: History to 2025, seeded to 2034

**Goal:** the world runs on real history from 2005 to December 2025 and on seeded cycles with the same statistics from 2026 to 2034. That covers the economic and legal-demand indices, the associate salary scale, the market's rate rises, real clients' failures and rescues, and the real rivals' paths and dated events. Also: the balance fixes Reece decided on 2026-11-22.

**Spec:** §5.4 (salary history), §6 (demand), §10.3 (history's dated events), §14 (eras to 2034) · **ADRs:** PT-0002 §2 (history pinned to December 2025, then seeded), PT-0008 §2 (the rivals' pin to 2025), PT-0012, PT-0014 (the macro history) · **Depends on:** PT-M7b (`pt-m7b-done`) · **Lane:** A (beside PT-M9 in lane B and PT-M16 in lane C)

## Lane

- **Owns:** `ptk/sim/macro.py`, `macro_data.py`, `macro_history.yaml`, `salary_scale.yaml`, `firms.yaml` and the rivals' pin (`ptk/sim/rivals/` pin and dated-event code), `clients.yaml` failures, `ptk/balance/` (scripts, `known_misses.py`, the runner), `docs/balance-targets.md`, the research dossiers below, RNG ids **65–69**.
- **Must not edit:** `ptk/sim/org/` and any automation package (PT-M9); reputation, press and rankings code (PT-M16). PT-M16 reads rivals through `ptk/sim/interfaces.py`; if it adds a function there, keep it.
- **Shared files:** keep both sides of `balance.yaml`, `CHANGELOG.md`, `docs/data-dictionary.md`, `rng.py` and `interfaces.py`; re-chain migrations if another merged first.

## Reece's decisions on PT-M7b's targets (2026-11-22), applied first (sub-task 0)

- **T2:** the measure is unchanged; the known miss moves to PT-M18.
- **T3 lawyers and T4 steady:** bands unchanged; the known misses move to PT-M16 (reputation that gates the card).
- **T4 pyramid:** a script fix, since a sensible pyramid lays off associates when utilisation stays below a threshold (as TST's §9 rule 2 allows). Band unchanged.
- **T8 corporate-heavy:** −9% is accepted as noise (record it in `balance-targets.md`). **T8 restructuring** is measured only on firms with at least 10 lawyers at December 2008 (update the Measures section).
- **T9 heeded:** a script fix: the heeded rocket asks the CFO's forecast before its first guaranteed lateral and takes none until six months of trend show headroom.

## Sub-tasks (commit after each)

0. **Reece's decisions above:** `known_misses.py` owners and bounds, the two script rules, the two measurement notes; re-read T4 pyramid and T9 heeded on seeds 1-10 and 11-40.
1. **Research dossier** `docs/research/history-2016-2025.md` (sources and S/D/A tags as before): the indices of `v1-macro.md` s2 for 2016-2025 (M&A, PE, issuance, lending, default rate, enforcement, IP, cycle, real estate, lateral heat, collections, rate rises); the pandemic's shape (March–June 2020 shock, then the 2021 boom); the 2022-2023 rate shock and deal slowdown; the salary scale's steps to 2025 (verify the 2021 step: $200,000, $202,500 or $205,000); real clients that failed or were rescued 2016-2025 (for example Sears, Toys "R" Us, PG&E, Hertz, Silicon Valley Bank, Credit Suisse); the rivals' FY2016-FY2025 revenue and lawyers; dated rival events to 2025 (Allen & Overy and Shearman 2024, Herbert Smith Freehills Kramer 2025, McDermott and Schulte 2025, and others).
2. **Macro to 2025:** `macro_history.yaml` extended; the 2020 pandemic as a two-month demand shock in litigation and transactional work, a courts slowdown (judges' docket pace), then the 2021 surge; the 2022-2023 slowdown.
3. **Seeded 2026-2034:** each index follows an AR(1) process fitted to 2005-2025's statistics, with regime switches for recessions (the same frequency and depth distribution as 2005-2025's), on stream `macro_seed` (65) keyed by `(index_number,)`; rate rises and the salary scale's steps seeded likewise (`scale_seed`, 66). Two saves with different seeds diverge from January 2026; the same seed never does (golden).
4. **Salary scale and bonuses to 2025**, then seeded steps (the market leader raises when lateral heat and profits run hot).
5. **Clients' failures and rescues 2016-2025** as in PT-M7 (unpaid bills lost; estates become restructuring work; rescues move work to the buyer's firms).
6. **The rivals' pin to December 2025** (ADR PT-0008 §2): FY2016-FY2025 paths, dated mergers and collapses, conditional on the player as before; from 2026 rivals play freely. Extend T11 to 2020 and 2025 checkpoints.
7. **Balance:** re-read T1-T12 on seeds 1-10 to December 2015 (v1's horizon) and print a 30-year steady run to December 2034 for information (no gate yet; PT-M18 sets 30-year targets). Tune only `macro.*` keys and the new seeded-cycle keys.

## Acceptance criteria

- [ ] Every index has a value for every month 2005-2034; 2005-2025 values match `macro_history.yaml`; 2026-2034 values are seeded and reproducible (golden).
- [ ] T11 passes at 2009, 2015, 2020 and 2025 on seeds 1-10 (0 misses beyond ±15%; at least 8 of history's top 10 by revenue in 2025).
- [ ] The 2020 shock shows in the player's firm: a corporate-heavy firm's April-June 2020 revenue falls 10-30% against January-March, recovering by Q4 2021 (printed, seeds 1-10).
- [ ] T4 pyramid and T9 heeded re-read after the script fixes; T8's measures updated; known misses re-owned (sub-task 0).
- [ ] T12 (≤ 250 ms) holds at December 2025 on the 150-lawyer timing firm.
- [ ] `make check`, `make e2e` and the nightly balance run green with known misses as recorded; `Milestone-Tag: pt-m10-done`.

## Decisions made

Recorded by the PT-M10 session (2026-11-22). Branch `claude/pt-m10-history-156q4l` (the session's assigned branch; the instructions' `pt-m10-history` name could not be pushed from a cloud session).

1. **Sub-task 0: a layoff action.** Partner Track had no way to let anyone go (PT-M1b: "no firing (a follow-up)"), so Reece's pyramid rule needed one: `LayOff` (TST's `Fire`, ADR PT-0015 §6): an associate, counsel or member of staff (never a partner or founder) works a notice month and goes with `pay.severance_months` (2) of salary; everyone remaining loses `morale.layoff_penalty` (-3, TST's). Energy 2. No screen yet (follow-up).
2. **Sub-task 0: the pyramid's rule** (`moves.lay_off_idle`): while three months' utilisation stays below 75%, lay off the lowest-rated associates that bring it back toward 85%, at most 10% of the associates a month (constants in `strategies.py`, as the scripts' other rules).
3. **Sub-task 0: the heeded rocket's rule** (`moves.cfo_clear`): before every guaranteed lateral (the first included) it asks the CFO's forecast, `fx.forecast_breach` as the Finance screen shows it, and takes none until six month ends (`forecast_window` + 1) of trend show headroom now and for `forecast_months`, with no covenant broken and the revolver not called.
4. **Sub-task 0: measures and rows.** T8 restructuring counts firms with 10+ lawyers in December 2008 (`report.T8_MIN_LAWYERS`); T8 corporate's row is "accepted" (Reece), known while the median fall is at least 5%; T2 is owned by PT-M18, T3 lawyers and T4 steady by PT-M16; T4 pyramid's and T8 restructuring's rows are removed (T4 pyramid prints FAIL, a band, not a gate, as it did above its bound in PT-M7b).
5. **Sub-task 0 readings** (standard, 132 turns; `main` = PT-M7b's merge head in a separate worktree):

   | Reading | `main` | PT-M10 rules | Band |
   | --- | --- | --- | --- |
   | T4 pyramid PEP 2015, seeds 1-10 (median) | $3.19M (3/10 dissolved, PT-M7b's run) | $3.95M (1/10 dissolved) | $0.7-1.6M |
   | T4 pyramid PEP 2015, seeds 11-40 | $0.90M (11/30 dissolved; the zeros carry the median) | $2.06M (5/30 dissolved) | $0.7-1.6M |
   | T9 heeded dissolves, seeds 1-10 | 1/10 | 1/10 | <= 1/10 |
   | T9 heeded dissolves, seeds 11-40 | 7/30 (PT-M7b decision 10) | 3/30 | |
   | T8 corporate / restructuring (10+ lawyers), seeds 1-10 | -9.0% / +31.1% (n=2-3) | -11.6% / +9.2% (n=5) | -30 to -10% / -5 to +20% |

   **For Reece:** the layoff rule does what it should (the pyramid survives the crash: 5 of 30 dissolved against 11), and so its PEP rises: a pyramid that sheds idle associates keeps its margin. T4 pyramid misses above its band on both seed sets; `main`'s 11-40 median sits in the band only because a third of the firms are dissolved at $0. No key in PT-M10's lane lowers a surviving firm's PEP (the crisis keys bite in 2009, not 2015). Proposed default: widen T4 pyramid to $1.0-4.0M (PT-M7b's proposal was $1.0-3.5M), or own it in PT-M16 with T4 steady (the card).
6. **Sub-task 1: the dossier** (`docs/research/history-2016-2025.md`, s2-s8): every figure tagged [S]/[D]/[A] with its source; gaps listed in each part (for example Thomson Reuters' all-firm worked-rate growth for 2016-2018 and 2020, lockup in days, Boies Schiller's and Cadwalader's FY2025 revenue). **The 2021 step was $205,000** (Davis Polk, 11 June 2021, for first-years on payroll from July; its incoming class $202,500 until January; Milbank's $200,000 was superseded within days); $215,000 came in January 2022, not November 2021.
7. **Sub-task 2: history's corrections before 2016.** The research moved PT-M1b's 2006 scale step to February 2006 (S&C's +$20k; the 8th year $240k, not $245k) and replaced the 2008-2015 bonuses with Cravath's and Davis Polk's [S] rows (2015's was too high). The last macro point (July 2015) used to hold; with 2016's point after it, August-December 2015 interpolate toward 2016. Both move v1's readings slightly (T3.revenue, below).
8. **Sub-task 2: the pandemic** is a dated shock (`macro_history.yaml` `shocks`, ADR PT-0015 §5), not only index points, because litigation reads a counter-cyclical `cycle` index that would rise in a recession. April-May 2020: litigation 35%, white collar 25%, IP 20%, employment 15% of demand lost; courts' cases pause 5-15% of their planned hours and their planned months grow one a month; deals' fall comes from the `ma` and `pe` indices' monthly points. **Tuning** (my keys, seeds 1-10, steady to December 2021; T8.2020's median Q2/Q1 of corporate-heavy firms): deal and case hours paused 0.30 (cases 0.30): -41.1%, 8 of 9 back by Q4 2021; halved: -35.8%, 7 of 9; deals 0, cases 0.15: **-23.3%, 7 of 9** (kept). "Recovering by Q4 2021" is read as most firms back to Q1 2020's revenue (a quarter's revenue is lumpy: seeds 1 and 6 rose in Q2 2020 on closings).
9. **Sub-task 3: the seeded world** (ADR PT-0015): fitted at load from the history itself (no fitted numbers in `balance.yaml`; only the fit's choices: years, mean years, the trend series, the AR range, history's two recession episodes, the gap between recessions, the rate range and the scale rule). `world_data` returns a save's own `GameData`, memoised; it is applied at the sim's entry points, so modules keep reading `data.macro`. Stream `macro_law` (32, reserved by PT-0012) stays unused: the brief's lane is 65-69.
10. **Sub-task 4: the scale rule's keys** are mine (the brief names the trigger, not the numbers): June, lateral heat >= 1.1 over the past year, the year's rate rise >= 4%, two years since the last step, 50% chance, a step drawn from history's first-year steps since 2016 (12.5%, 5.6%, 7.9%, 4.9%, 4.7%). On seeds 0-29 the market steps on most seeds, 2-3 times by 2034.
11. **Sub-task 5: failures.** Toys R Us, Sears Holdings, J.C. Penney and Rite Aid fail as bankruptcies; Credit Suisse is rescued (UBS). PG&E is left out (it filed but paid its unsecured creditors and kept operating: ADR PT-0014 §5's rule); subsidiaries' filings are not their parents' failures. One `fails` per client: Rite Aid's two filings are covered by its first's estate months.
12. **Sub-task 6: the rivals' pin.** Only [S], [S·snip] and [D] points enter `firms.yaml`, never the dossier's interpolations; Baker McKenzie's FY2016 and FY2018-2019 are left out (its June year-end and the Global series' one-year lead, dossier s6 note 3); DLA Piper keeps its US basis to 2009; A&O Shearman (May 2024) is an outside merger with Shearman's path stepping to the global firm. Hogan Lovells Cadwalader (July 2026) is after the pin and not scripted (rivals play freely from 2026). `rivals.market_growth` 2016-2025 takes the researched Am Law 100 growth. PT-M5's dated-history test now plays past the last event (2024).
13. **Sub-task 7: T12** is timed at December 2025 (`make check-timing`, alone): **138 ms** (PT-M7b's 2015 reading: 159 ms; the bisected index lookup keeps 2025's 36 points cheap). The runner's printed T12 (641 ms on CI, workers sharing cores) is not the gate.

14. **T12 on `main` after the merge** read 255 ms on `check`'s runner (the PR's runs passed with the same code). By rule 6, no retry or looser check: the December 2025 turn was profiled and three steps made proportional with identical results (CHANGELOG): `month_hours`' per-earner record filter (3.2M calls in 12 turns), `org_view` rebuilt for every person's morale, and `staff_ids`. Profiled 383 -> 311 ms; `make check-timing` 130-134 ms. `org/rules.py` is PT-M9's lane, whose ownership lapsed when it merged (rule 8). The fix's merge commit carries `Milestone-Tag: pt-m10-done`.

**Sub-task 7 readings** (`make balance --long` on CI: nightly run 8 on `8f1e4c1`, and run 11 on the merge head `be0cb32` after PT-M9 with the same readings except the 30-year print; seeds 1-10, 132 turns, plus steady to December 2034; T8.2020 from the tuned shock, seeds 1-10 to December 2021):

| Target | Band | PT-M7b | PT-M10 | |
| --- | --- | --- | --- | --- |
| T1 do-nothing fails | >= 9/10 | 9/10 | 9/10 (7 nominal) | pass |
| T2 no dominant strategy | <= 6/10 | steady 9, boutique 1 | **steady 6, pyramid 4** | pass (row kept, owned by PT-M18, unused) |
| T3 steady lawyers | 100-250 | 50 | 45.5 | known miss (PT-M16) |
| T3 steady revenue | $60-150M | $57.3M | $51.6M | miss (a band; history's 2015 changes) |
| T4 PEP steady / boutique / pyramid | | $4.02M / $2.00M / $3.19M | $3.60M / $1.95M / $3.21M | known miss (PT-M16) / pass / miss, for Reece (decision 5) |
| T5 easy / standard / hard | 0-10 / 5-20 / 20-45% | 20 / 10 / 30% | 20 / 10 / 30% | easy: PT-M7b's seed variance |
| T6 attrition / class | 15-25% / 8-15% | 20.5% / 0% | 24.1% / 0% | pass / PT-M7's noise |
| T7 realisation / collection / utilisation / lockup | | 84.4 / 96.5 / 83.6 / 126 | 84.6 / 96.5 / 84.2 / 125 | pass |
| T8 corporate / restructuring (10+ lawyers) | | -9.0% / +31.1% | -12.6% (n=41) / -2.3% (n=5) | pass |
| T9 rocket / heeded | 3-6 / <= 1 | 3 / 1 | 4 / 1 | pass |
| T10 ratio / steady | >= 2x / <= 5% | 10.98x / 0.7% | 11.20x / 0.6% | pass |
| T11 at 2009, 2015 | 0 misses, >= 8 kept | 0, 10 (5.7%) | 0, 10 (5.7%) | pass |
| T11 at 2009-2025 (steady to 2034) | 0 misses, >= 8 kept | | **0, 8 (worst 7.5%)** | pass |
| T8.2020 shock (corporate-heavy, Q2/Q1 2020) | -30% to -10%, back by Q4 2021 | | **-23.3%, 7 of 9 back** | pass |
| T12 at December 2025 | <= 250 ms | 159 ms (2015) | **138 ms** | pass |
| 30-year steady, December 2034 (information) | PT-M18 | | 70.5 lawyers, $233.3M, PEP $10.10M, 1/10 dissolved (run 11; run 8 before the shock's tuning: 38.5, $102.7M, $7.20M) | printed |

PT-M5's T11 test (`make check`, unmanaged player): seeds 1-10 at 2009, 2015, 2020 and 2025, worst gaps 5.1-7.2%, top 10 kept 8-10, no misses.

**The 2020 shock, seed by seed** (steady to December 2021, corporate-heavy in 2019; $M a quarter):

| Seed | 2020 Q1 | 2020 Q2 | Q2/Q1 | 2021 Q4 | Back |
| --- | --- | --- | --- | --- | --- |
| 1 | 15.53 | 19.97 | +28.6% | 20.19 | yes |
| 2 | 20.94 | 19.07 | -8.9% | 28.04 | yes |
| 3 | 28.60 | 28.08 | -1.8% | 27.18 | no |
| 4 | 27.51 | 18.68 | -32.1% | 24.68 | no |
| 5 | 14.88 | 11.41 | -23.3% | 19.23 | yes |
| 6 | 2.40 | 2.83 | +17.8% | 3.63 | yes |
| 7 | dissolved in 2009 | | | | |
| 8 | 25.66 | 16.58 | -35.4% | 29.68 | yes |
| 9 | 1.76 | 0.66 | -62.4% | 4.15 | yes |
| 10 | 11.80 | 7.35 | -37.7% | 14.69 | yes |

## Follow-ups

- A screen for the layoff action (the API and the People screen); automation's staffing area (PT-M9) may want it as a one-off.
- PG&E-style filings (a Chapter 11 that pays its creditors and keeps operating) as a third failure kind that brings restructuring work without ending the wallet; subsidiaries' filings as large restructuring mandates.
- Hogan Lovells Cadwalader (July 2026) and other post-2025 events as seeded possibilities rather than history.
- The seeded world on the Overview or History screen (the indices and the scale's steps after 2025).
- Baker McKenzie's FY2015 point may be its year to June 2016 (dossier s6 note 3); T11 passes either way.
- T2 now passes on seeds 1-10 (steady 6, pyramid 4); its known-miss row (PT-M18) can go when PT-M18 confirms on 11-40.
