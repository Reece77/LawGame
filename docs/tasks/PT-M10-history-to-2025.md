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

## Follow-ups
