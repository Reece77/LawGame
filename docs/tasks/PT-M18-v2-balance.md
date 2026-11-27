# PT-M18: v2 balance

**Goal:** close v2 with a game whose numbers hold up over the whole campaign. Every target and guard is judged on seeds 1-40, not 1-10, so a one-seed swing no longer decides a pass. Every known miss and expected failure carried by PT-M7b to PT-M15 is traced to its cause and fixed or brought back. The thirty-year campaign gets targets of its own for 2016-2034. Turn time regains its headroom, and the nightly run is sharded so its limits stop blocking merges.

**Spec:** §17 (balance), §20 (the v2 scope) · **ADRs:** PT-0012, PT-0014 (macro history), PT-0015 (the seeded world) · **Rules:** CLAUDE.md §12 (Reece, 2026-11-25) · **Depends on:** PT-M12 (`pt-m12-done`), the last of v2's feature milestones · **Lane:** runs alone. No other session changes the simulation while PT-M18 is open; front-end and docs work may run beside it.

## Lane

- **Owns:** every key in `balance.yaml` and every simulated system's data (CLAUDE.md §12 rule 6: each passed to the balance milestone when its builder merged), `ptk/balance/`, `tests/balance/`, `known_misses.py`, `docs/balance-targets.md`, `.github/workflows/nightly.yml`, the strategy scripts, performance work anywhere in `ptk/sim/` that leaves results identical. RNG ids: none expected; **150-159** if a fix needs one.
- **Must not:** add systems or features (follow-ups go to v3's roadmap); widen a target's band without Reece's decision; change a test's assertion to make it pass (CLAUDE.md §10).

## Sub-tasks (commit after each)

1. **Forty seeds.** The balance runner and every nightly guard read seeds 1-40, with thresholds as shares of seeds (6 of 10 becomes at most 60%; 9 of 10 becomes at least 90%; a median stays a median). Record each target's old and new measure in `balance-targets.md` with this brief's date.
2. **A sharded nightly.** Split the nightly's tests and the balance run by seed range across parallel jobs, as `check` is sharded, so the nightly finishes within its 120-minute limit with 40 seeds. Restore the 120-minute limit (PT-M12 raised it to 180). The summary job prints every target over all 40 seeds.
3. **The baseline.** Read every target (T1-T14) and every guard on `main` at 40 seeds, with each known miss's and expected failure's reading, in a table in "Decisions made". Rows and markers that pass at 40 seeds are removed here.
4. **The known misses and expected failures.** For each that is left, trace the cause (a decomposition as PT-M7c's for T3/T4), then fix it with keys or script rules (TST's rule 2), or bring it back with the table. The list on `main` when this brief was written, to be confirmed in sub-task 3:
   - **T2,** steady dominant (9 of 10 on PT-M15's branch; 16-21 of 30 on seeds 11-40);
   - **T3** lawyers and revenue, steady too small (60 lawyers against 100-250; PT-M12 and PT-M13 add growth routes);
   - **T4 steady,** PEP $1.31M against $0.5-1.2M;
   - **T5** hard (50-60%) and standard (seed variance);
   - **T6** partners, 7.1% against 8-15%;
   - **T9 heeded,** the warned firm still dissolves;
   - **PT-M14.fixed_fees,** fixed fees beat hourly on 4 of 10 (needed 7);
   - **T13** and **T14,** if PT-M12 records them;
   - **expected failures:** PT-M9's automated steady (delegated hiring grows the firm more slowly), the cowboy's lower PEP (fails on `main` at 11-40) and the heeded exodus.
5. **Thirty-year targets.** Propose T15-T18 for 2016-2034, each with a dossier source or a stated reason, for the product manager's approval before tuning: rivals' revenue growth after 2025 inside history's 2005-2025 range; dissolutions a decade in a believable band; no strategy dominant at year 30; and the AI era's (PT-M14 criterion 2's 40-70% fewer hours on exposed tasks by 2030, and juniors' growth with training). Read them on seeds 1-40.
6. **Turn time.** PT-M12 left the branch about 30% slower than `main` (firms carry about 2.4 times as many matters; staffing's re-plan was quadratic). Make the slow steps proportional, with results identical (golden snapshots and the state cache replay unchanged). Add a December 2034 timing case beside December 2025's.
7. **The close.** Re-read T1-T18 on seeds 1-40 with before and after values; regenerate golden snapshots once at the end with the reasons in `CHANGELOG.md`.

## Acceptance criteria

- [ ] Every target and guard is judged on seeds 1-40 (test of the runner's seed list), and the nightly finishes within 120 minutes (two consecutive runs).
- [ ] Every target T1-T14 passes on seeds 1-40, or has a known-miss row that Reece approved after the session brought it back with the table.
- [ ] No expected failure owned by PT-M18 remains in `tests/balance/`.
- [ ] T15-T18 approved by the product manager and passing on seeds 1-40.
- [ ] T12: the median of five runs at most 200 ms on CI's runner in December 2025 (20% headroom on the 250 ms budget), and at most 250 ms in December 2034.
- [ ] Golden snapshots regenerated with reasons; no band widened without Reece's decision (recorded in `balance-targets.md`).
- [ ] `make check`, `make e2e` and the nightly green; `Milestone-Tag: pt-m18-done`. This closes v2.

## Manual check (Reece)

Start a fresh standard game, play 2005-2008 yourself, delegate everything to the executive committee, and let it run to December 2034; read the campaign's ending.

## Decisions made

1. **Order of the sub-tasks** (the product manager, Reece, 2026-11-26): `pt-m12-done` was never created because main's `check` read T12 at 251 ms (the minimum of five) against 250, so PT-M18 starts without waiting for it and takes the sub-tasks in the order **6, 2, 1, 3, 4, 5, 7**. Sub-task 6 goes first as its own pull request, whose merge commit carries `Milestone-Tag: pt-m12-done` (it closes PT-M12's red `check`); the milestone merges later with `Milestone-Tag: pt-m18-done`.
2. **Sub-task 6, turn time, with identical results** (golden snapshots and the state cache replay unchanged; no balance key moved, so the matter volume is untouched). Profiled on T12's merged-firm case (py-spy and per-phase timers); each change is proportional to what changes and gives the same values:
   - **The cyclic collector** is paused for a turn (`turn.advance_turn`): a turn builds no reference cycles (a collection after a turn frees none), but every gen-2 pass walked the whole live game. On resuming, the turn's survivors are moved to the oldest generation with `gc.freeze()` and `gc.unfreeze()` (a list splice; skipped if a caller has frozen objects), instead of a young-generation pass over everything the new state holds. A 132-turn steady run: 37 s -> 23 s, peak memory 290 -> 305 MB.
   - **Lookups** on the state's tuples (`person`, `employment_of`, `employer_of`, `person_state`, `reveal`) are indexed on a tuple's eighth lookup, memoised on the tuple's identity (first match wins, as the scans).
   - **`ptk.sim.fastcopy.replace`**, a cached positional `dataclasses.replace` (same `__init__` and `__post_init__`; unknown names raise), in the turn's hot modules; a test checks every sim dataclass has only init fields.
   - **RNG streams** pass the seed's and key's 32-bit words as `SeedSequence`'s entropy, which is the pool `spawn_key` assembles (a Hypothesis test against the documented call; parts of 32 bits or more take the documented path).
   - Staffing: a fee earner's per-person core and the fee earner itself memoised on the person; flow demand grouped by practice once. Growth: skill-independent terms once, noise as one array, one copy of the person. Rivals: action noise as one array, the month's time and each real firm's path once. Reputation: `means` inlines `long_run_mean` (a test checks equality). Relationships' monthly moves applied in one pass. Billing: a sector's shortfall memoised per month. The directory builds only notables' views. `AttrSet.updated` clamps only changed values.
   - **Readings** (CI's `check` on PR #36, run 45918508384; `make check-timing` now prints each case's five runs, the gate's minimum and the median of five, and the gate is unchanged), ms:

     | Case | main (gate) | gate (minimum) | median of five |
     | --- | --- | --- | --- |
     | two offices, December 2025 | 251 | 131 | 135 |
     | merged firm and verein, December 2025 | 251 | 134 | 140 |
     | 150 lawyers, December 2025 | — | 110 | 115 |
     | 150 lawyers, **December 2034** (new case) | — | 103 | 105 |
     | a merger closed in 2025 (reading, nightly) | — | 201 | 207 |

     PR #36 merged as `0e13dca` with `Milestone-Tag: pt-m12-done`; `check` passed on main and `tag-milestone` created `pt-m12-done` on `0e13dca` (confirmed with `git ls-remote --tags origin pt-m12-done`).
3. **Sub-task 2, the sharded nightly** (`.github/workflows/nightly.yml`): 8 `balance` jobs, each a contiguous seed range (`make balance-shard`; `tools/balance_runner.py --shard K/N --save`), then `balance-summary`, which reads every shard's runs, prints every target over every seed (`--summary`) and runs `test_pt_m7::test_balance_targets` on them (`PTK_BALANCE_RESULTS`): the same gates, no second play of the runs. 6 `nightly` test jobs (`make nightly-shard`): the tests dealt by recorded duration, longest first, each to the least loaded shard, `xdist_group`s together (`tests/nightly_shards.py`); a check that every test is in one shard; each job uploads its tests' durations and `durations` merges them for `tests/nightly_durations.json`. A job `nightly` passes only if every shard and the summary did. Every job's limit is 120 minutes (PT-M12 had 180 for the whole run). Engineering choices: 8 and 6 shards (GitHub's 20 concurrent jobs), seed ranges rather than strategies (a seed's runs cost alike), pickled results between jobs (the same code writes and reads them).
4. **Sub-task 1, forty seeds**: `ptk/balance/seeds.py` (`SEEDS` 1-40, `at_least`, `at_most`) read by the runner, the tools and every nightly guard; old and new measures in `docs/balance-targets.md` ("Forty seeds"). Counts of seeds in scores became shares (T1, T2, T9), so T2's known miss "at most 9 of 10" reads 0.9. Guards that looped seeds one at a time (PT-M5's conditional history, PT-M7a, PT-M8) run them in a process pool. PT-M13's separate seeds 11-40 test folds into its seeds 1-40 test (it only printed what the latter now prints). PT-M7a's acceptance firm moves from seeds 1-5 to 1-40 (rule 1: every guard).

5. **Two crashes found by the first 40-seed nightly** (run 45921178345; its jobs took 9-27 minutes, the whole run 27):
   - **Rivals' free play (P1; the product manager chose "relative to the market", 2026-11-27).** A history-following rival's rate index carries the market's rate rises after the pin (its capacity per lawyer stays at 2005's while pinned), and from 2026 the rate elasticity read that as overpricing: demand about -50% a year on every seed, and seed 36's `steady-30y` stopped (a boutique's bias below -1). Fix: such a rival is read against its region's history-following rivals' mean index, every other firm against 1 (no change before 2026: state cache identical); the bias has a floor, `rivals.growth_bias_floor` -0.5 (a new key). Refinement of the option as worded: the mean is over history-following rivals, not every firm, because generated firms carry the rate rises in their capacity instead (US 2025 medians 0.86 generated against 1.91 real; a mean over both would leave the premium firms collapsing and would move generated firms from 2005). Seed 1, 2025-2034: real rivals' growth median 3.8% a year (min -4.0%, max 8.2%; before the fix -5.5% to 8.2%, median 3.0%, with the top US firms collapsing); history 2005-2025: 3.1-14.2% (median 6.2%; ten-year windows -0.4% to 18.3%). T15 will measure it.
   - **Discipline** (PT-M15's files, rule 8): a disbarred lawyer at a partner level who is not on the partnership's record went through partner departure and raised `PartnershipError`; such a lawyer now leaves as an employee. Regression test.
6. **Sub-task 3, the baseline at 40 seeds** (nightly runs 45952995537 and 45957902516 on this branch: the sim is main's, `0e13dca`, plus decision 5's two fixes, which change nothing before 2026 apart from the crashes). Readings:

   | Target or guard | 40-seed reading | Band | Verdict |
   | --- | --- | --- | --- |
   | T1 | 39/40 | >= 36/40 | ok |
   | T2 | steady 29, pyramid 8, boutique 1, do-nothing 1, rocket 1 | <= 24/40 | known miss (0.725 within 0.9) |
   | T2.specialist | steady 25, pyramid 8, specialist 4 | <= 24/40 | fail (printed row) |
   | T3.lawyers | 66.5 | 100-250 | known miss |
   | T3.revenue | $70.91M | $60-150M | **ok: row removed** |
   | T4 steady / boutique / pyramid | $1.65M / $1.67M / $1.21M | $0.5-1.2M / $1-2.5M / $0.7-1.6M | known miss / ok / ok |
   | T5 easy / standard / hard | 5.0% / 15.0% / 35.0% | 0-10% / 5-20% / 20-45% | ok / **ok: row removed** / ok |
   | T6 attrition / partners | 21.9% / 1.9% | 15-25% / 8-15% | ok / fail (no row) |
   | T7 realisation, collection, utilisation, lockup | 84.3%, 96.4%, 85.8%, 121 days | bands | ok |
   | T8 corporate / restructuring | -12.2% (n=230) / +1.4% (n=32) | -30 to -10% / -5 to +20% | **ok: "accepted" row removed** / ok |
   | T8.2020 | -14.2%, 29/34 back | -30 to -10%, most back | ok |
   | T9 rocket / heeded | 20/40 / 10/40 | 12-24 / <= 4 | ok / fail |
   | T10 ratio / steady | 11.98x / 0.7% | >= 2x / <= 5% | ok |
   | T11 / T11.2025 | 7.7%, 0, 9 / 9.5%, 0, 8 | ±15%, 0, >= 8 | ok (every seed's T11 and UK T11 tests pass) |
   | T12 (gate: `check-timing`) | see decision 2 | <= 250 ms | ok |
   | T13 | 25.2% (22 of 40 merged) | 10-20% | known miss (within 28%) |
   | T14 | 1.50; premium $9,891 | 1.5-5.0; $5-10k | on the edge (the test passes; row kept until sub-task 4 reads it to more places) |
   | PT-M12.specialist / specialist_2009 | 29/40 / -30.6% vs -51.6% | >= 28/40 / falls less | ok |
   | PT-M5 conditional history | 38/40 | >= 28/40 | ok |
   | PT-M11 London lift | 39/40 within 36 months; seed 11 dissolved before 2007 (never opened) | every seed opens; >= 24/40 | fail on `all(opened)`: a question for the product manager |
   | PT-M8 pitches | median 2.0 a quarter | 2-6 | ok |
   | PT-M7a, PT-M16 pace, state cache, golden, real people | pass | | ok |
   | Expected failures: PT-M9 automated steady (non-strict), PT-M8 strong leader (strict), PT-M15 cowboy PEP (non-strict), PT-M12 heeded exodus (non-strict) | still fail (xfail) | | owned by PT-M18: sub-task 4 |
   | PT-M14.fixed_fees (`tools/tech_readings.py`) | to read in sub-task 4 | >= 70% | known miss |

   The nightly took 26 and 39 minutes (every job under 120).
7. **The product manager's decisions of 2026-11-27:** (a) T15-T18 approved as proposed (T16 counts real rivals' collapses; T17 plays every strategy to 2034); built as rows T15-T17 of the balance run (`report._t15`, `_t16`, `_t17`; the long runs record their rivals' growth and collapses; `<strategy>-30y` variants) and T18 as `tests/balance/test_pt_m18.py` (PT-M14's criteria 2 and 4 without criterion 3's branches: the same numbers as `tools/tech_readings.py run_seed`, checked on seed 1). (b) PT-M11's London lift is judged on the seeds whose firm is alive in January 2007 (`OfficeRun.reached`); seed 11, dissolved before 2007, is printed and not judged.
8. **Sub-task 4, T15 and T16 (rivals after history; my keys as the balance owner, rule 6).** The fourth nightly (run 46003730538, on `4ea2865`) read T15 at -5.0%, 4.3%, 20.4% (min, median, max), with 274 of 1,835 rival-seeds outside -0.4% to 18.3%, and T16 at 0 collapses on 0 of 34 seeds. Causes, from seeds 1 and 2 played to 2034: (a) every rival outside the range was a premium US firm (Kirkland, Latham, Ropes, Quinn, Cooley, Morgan Lewis, Paul Weiss, Proskauer: rate index 1.75-1.93 against a regional mean of about 1.55), shrinking 1-5% a year, because decision 5's regional mean read their 2005-2025 rise in revenue per lawyer (history's, not a price rise) as overpricing; (b) the collapse hazard of a firm without departures or a dated collapse is `base_bp` 0 times `other_mult`, so nothing could collapse after 2025. Fixes: (a) a history-following rival's market level is the index its own path needed in December 2025 (`rivals.economy.reference_index`: the path's revenue per lawyer then over its 2005 capacity per lawyer at its personality's utilisation; its capacity rises with `rate_inflation` from 2026). This is a refinement of the product manager's "relative to the market": the market price for such a firm is its own at history's end, and the market's later rises are in its capacity, as for every free firm. (b) After the pin, a history firm carries `rivals.collapse.free_play_bp` 4.0 bp a month times its personality's fragility (a new key: history's own rate, 4 collapses among 43 firms in 2005-2025, 3.9 bp a firm-month; expected about 2 a decade a seed, at least one on about 80% of seeds). Before the pin nothing changes (state cache identical; `rivals.collapse.hazard` extracted for its unit test). Seeds 1, 2, 4 and 5 to 2034 after (a): every real rival grows 3.4-15.7% a year, median 6.2% (T15: each -0.4% to 18.3%, median 3.6-9.2%). Golden snapshots regenerated (CHANGELOG).
9. **Sub-task 4, T9.heeded, T6.partners and PT-M4's exodus guard.**
   - **T9.heeded** (10 of 40 at baseline, at most 4): the warned rockets that dissolved were 3-6 lawyers at no cash for months, still hiring associates and campus classes, and their one $1M capital call (two to three years of a five-lawyer rocket's capital) was voted down by the guaranteed laterals (seed 7: `capital_call` failed in July 2006, insolvent from August). Script rules (rule 2, `strategies.lateral_rocket` and `moves.heed_warning`): once warned, hire associates and campus classes only with cash headroom (`bank_quiet`) and lay idle associates off by steady's rule; the capital call is three months of costs (at least $100k), called again each quarter while cash is under two months of costs. Seeds 1-40 to 2015, played locally: 11 -> 7 (hiring rule) -> **4** dissolved (both); the unheeded rocket is unchanged.
   - **T6.partners** (1.9% against 8-15%): not an admissions question. Steady's September 2006 class is 0-2 people a seed (a 10-lawyer firm's campus class), and on 7 of seeds 1-8 all of them have left by December 2012, before they are eligible (`track_years` 8). With an admission every December at least (`max(1, _admissions)`), seeds 1-8 read the same: one of 12 made equity (seed 8, December 2014). The share is set by the class's survival to year 8 (22% attrition a year leaves about 13%), so it goes back to the product manager with the table.
   - **PT-M4's exodus guard** (`tests/unit/test_partnership_flight.py`, nightly) still read seeds 1-10: now seeds 1-40 with shares (untended at least 30%, heeded at most 10%: 12 and 4 of 40), in a process pool, and pinned by the seed-list test. At 40 seeds a dissolved seed raised `GameOverError` in the fixture (it acted on an ended game); the loop now stops when the game has ended (rule 5: the fixture, not the check). Reading: untended 19 of 40, heeded **5 of 40**, which is main's own 1/10 + 4/30 (decision 6's source). A call of three months' costs, or the larger of that and $1M, repeated each quarter, also reads 5 of 40, so the guard's response is left as it was. Inherited (rule 3); a PT-M18 expected failure: back to the product manager.
10. **Sub-task 4, T2, T4 steady and T17: steady's equity ratio (rule 2), and T15's one outlier.**
   - The fifth nightly (run 46016396663 on `00e7eef`, 35 minutes, every job under 30) read T15 at 1 of 1,792 outside (seed 6's DLA Piper, 20.5% a year in every strategy), T16 1.1 a decade on 26 of 34 seeds (ok), T17 steady 29 (at most 24), T18 ok (saving 51.0-56.5% on 40 of 40; loss 0.858; restored 0.98 over 25 seeds).
   - **T15's outlier:** a free-play rival merger in 2032 (DLA Piper $4.1bn -> $10.3bn) took a firm with half the buyer's lawyers but 1.5 times its fees. The target must now be at most `mergers.rival.free_max_ratio` (0.5) of the buyer's last 12 months' fees as well as its lawyers (`rivals.mergers.free_targets`), so no deal makes a firm more than 1.5 times its size: "the smaller firm" by fees too. After 2026 only.
   - **Steady's equity ratio:** steady's script admitted one equity partner per 4 lawyers and bought laterals above 5, where the dossier's 50-150-lawyer firm keeps 2.5-3.5 lawyers per equity partner (30-40% of its lawyers in the equity, `docs/research/firm-economics.md` s10). With the script at the dossier's figure, its PEP falls into T4's band and T2's dominance goes. Seeds 1-40, every strategy to 2015 (`STEADY_PER_EQUITY` / `STEADY_LATERAL_PER_EQUITY`):

     | Ratio (admit / lateral above) | T2 (steady wins) | T4 steady PEP | T3 lawyers / revenue | T6 attrition | T7, T10 |
     | --- | --- | --- | --- | --- | --- |
     | 4 / 5 (before) | 29 | $1.65M | 66.5 / $70.91M | 21.9% | ok |
     | 3 / 4 | 21 | $1.37M | 69.0 / $67.19M | 22.1% | ok |
     | **2.5 / 3.5 (chosen)** | **22** | **$1.19M** | 70.0 / $66.93M | 22.8% | ok |

     2.5 is the dossier's low end; steady automated and the practice strategies read the same constants. The state cache is re-recorded (steady plays differently from 2005) and the golden snapshots regenerated (CHANGELOG).
11. **Sub-task 4, T14 after decision 10, and the cowboy's PEP.** The sixth nightly (run 46027421962 on `624da9a`, 36 minutes, every job under 35) read every T1-T18 row ok but T3.lawyers (70.0, known), T6.partners (1.9%) and T12's runner row (334 ms; the gate is `check-timing`): T2 steady 22, T2.specialist steady 20, T4 steady $1.19M, T9.heeded 4/40, T15 0 of 1,959 outside (max 13.8%), T16 1.1 a decade on 29 of 37, T17 steady 18, T18 ok. T2's and T4.steady's known-miss rows are removed. One nightly test failed: **T14** 1.342 (bound 1.495), because steady's larger equity tier lets fewer errors escape. `risk.claims.from_error_bp` (mine, rule 6) moves it, seeds 1-40 (T14 median; December 2015 premium a lawyer; cowboy lower PEP than steady):

    | `from_error_bp` | T14 (1.5-5.0) | Premium ($5-10k) | Cowboy lower PEP (>= 24) |
    | --- | --- | --- | --- |
    | 800 (before) | 1.34 | - | - |
    | 1000 | 1.43 | $9,538 | 24 |
    | **1070 (chosen)** | **1.50** | **$9,686** | **24** |
    | 1300 | 1.87 | $11,036 | - |

   Both bands hold only between about 1,050 and 1,090: T14 stays at its band's edge (its known-miss row stays, bound unchanged), and the premium near its top. The cowboy's lower PEP now passes on seeds 1-40 (24 of 40): its expected failure is removed and the guard asserts. State cache re-recorded and golden snapshots regenerated (CHANGELOG).
12. **The seventh nightly** (run 46039759484 on `4d91fac`, 38 minutes, green): every row as decision 11 but **T4.steady $1.32M** ($0.5-1.2M): T14's claim rate lifts steady's PEP back from $1.19M. Steady is already at the dossier's lowest ratio (2.5 lawyers per equity partner), and laterals above 3.0 instead of 3.5 leave it at $1.32M (seeds 1-40: T2 steady 21, T3 67.5 lawyers / $70.12M), so my keys cannot hold T4 and T14 together. T4.steady's known-miss row returns, bounded at the 40-seed reading ($1.33M; CLAUDE.md 12.5), for the product manager. T6.partners reads 0.0% (no 2006-class member is an equity partner in December 2015).
13. **The product manager's decisions on what keys and script rules cannot fix (2026-11-27, on the table of decisions 9-12; all four as recommended):**
   - **T4.steady against T14:** T14 keeps `risk.claims.from_error_bp` 1070 (1.50, premium $9,686); T4.steady stays a known miss, bounded at its 40-seed reading ($1.3168M; baseline $1.65M).
   - **T3.lawyers, T6.partners, T13:** known misses carried to v3, owned by PT-M23 (the next balance milestone, `docs/v3-outline.md`), each bounded at its 40-seed reading: T3.lawyers 73.5 (revenue $70.6M is inside), T6.partners 0.0% (a new row; the report's row now carries a score), T13 23.1% on the 23 seeds that merge (bound tightened from 28%). Causes in decisions 9 and 12; follow-ups below.
   - **Expected failures:** PT-M8's strong leader (utilisation gap 2.8 points against 3.0; morale gap 7.3, passes), PT-M9's automated steady (revenue -19.7%, passes; PEP +32.9% against 20%) and PT-M4's heeded exodus (5 of 40 against at most 4; main the same) are non-strict, owned by PT-M23, with both readings in each reason. PT-M8's was strict. PT-M18 now owns no expected failure.
   - **PT-M14.fixed_fees:** the row stays, owned by PT-M23, bounded at the 40-seed reading: 24 of 40 (score -0.6; the measure is a share of seeds, CLAUDE.md 12.1).
   - T14: see decision 15 (it reads 1.4951, not 1.50, and keeps its row).
14. **Sub-task 7, the close: T1-T18 on seeds 1-40, before and after.** Before: decision 6's baseline (nightly runs 45952995537 and 45957902516; T15-T17 from run 46003730538, the first that read them). After: the seventh nightly (run 46039759484 on `4d91fac`; the commits since change no result). T12: `make check-timing` on CI (check run 46047551108).

    | Target | Before | After | Band | After's verdict |
    | --- | --- | --- | --- | --- |
    | T1 | 39/40 | 39/40 | >= 36/40 | ok |
    | T2 | steady 29 | steady 22 | <= 24/40 | ok (row removed) |
    | T2.specialist | steady 25 | steady 21 | <= 24/40 | ok |
    | T3 lawyers / revenue | 66.5 / $70.91M | 73.5 / $70.58M | 100-250 / $60-150M | known (PT-M23) / ok |
    | T4 steady / boutique / pyramid | $1.65M / $1.67M / $1.21M | $1.32M / $1.71M / $1.12M | $0.5-1.2M / $1-2.5M / $0.7-1.6M | known (PT-M23) / ok / ok |
    | T5 easy / standard / hard | 5.0% / 15.0% / 35.0% | 2.5% / 7.5% / 35.0% | 0-10% / 5-20% / 20-45% | ok |
    | T6 attrition / partners | 21.9% / 1.9% | 23.0% / 0.0% | 15-25% / 8-15% | ok / known (PT-M23) |
    | T7 realisation, collection, utilisation, lockup | 84.3%, 96.4%, 85.8%, 121 | 84.3%, 96.3%, 85.4%, 120 | bands | ok |
    | T8 corporate / restructuring | -12.2% / +1.4% | -10.4% / +6.4% | -30 to -10% / -5 to +20% | ok |
    | T8.2020 | -14.2%, 29/34 | -23.8%, 31/35 | -30 to -10%, most back | ok |
    | T9 rocket / heeded | 20/40 / 10/40 | 22/40 / 4/40 | 12-24 / <= 4 | ok |
    | T10 ratio / steady | 11.98x / 0.7% | 12.65x / 0.6% | >= 2x / <= 5% | ok |
    | T11 / T11.2025 | 7.7%, 0, 9 / 9.5%, 0, 8 | the same | ±15%, 0, >= 8 | ok |
    | T12 (median of five, CI) | 251 ms (the minimum on main) | 162 ms December 2025, 157 ms December 2034 | <= 200 / <= 250 | ok |
    | T13 | 25.2% | 23.1% | 10-20% | known (PT-M23) |
    | T14 | 1.495 | 1.4951 | 1.5-5.0 | known (PT-M23; decision 15) |
    | T15 | -5.0%, 4.3%, 20.4%; 274/1,835 outside | 3.3%, 6.2%, 13.1%; 0/1,906 | each -0.4-18.3%, median 3.6-9.2% | ok |
    | T16 | 0.0; 0/34 | 1.1; 28/36 | 0-4; >= 20% of seeds | ok |
    | T17 | steady 25 | steady 19 | <= 24/40 | ok |
    | T18 | (the test ran past its shard's limit) | saving 51.0-56.5% on 40/40; loss 0.994; restored 0.96 over 23 seeds | 40-70% every seed; > 0; >= 0.5 | ok |
    | PT-M14.fixed_fees | 4/10, 9/30 | 24/40 | >= 70% | known (PT-M23) |

   Guards at 40 seeds: PT-M12 specialist 29/40 (>= 28), PT-M5 conditional history, PT-M7a, PT-M11 London (seeds reaching 2007), PT-M8 pitches, PT-M15 cowboy (2x on 36, lower PEP on 24 of 40), PT-M16 pace, real people, the state cache and the golden snapshots pass; PT-M8's leader, PT-M9's automated steady and PT-M4's heeded exodus are PT-M23's non-strict expected failures (decision 13). The golden snapshots were last regenerated on `4d91fac` (decision 11's claim rate) and are current: nothing since changes a result. The nightly finished within 120 minutes on every run from the fourth (35, 36 and 38 minutes on the last three).
15. **A correction: T14 reads 1.4951, not 1.50.** The nightly on `56fa6b8` (run 46063047010) failed T14 at 1.4951 after decision 13 removed its row: my local readings printed the median rounded to two places (1.50) and I read that as inside the band. With `from_error_bp` 1070 the 40-seed median is 1.4951, just under 1.5 and within the bound Reece authorised on 2026-11-25 (1.495). Its known-miss row returns at that bound, owned by PT-M23 with the other carried misses; decision 11's choice (1070) and the cowboy guard (24 of 40) stand. So T4.steady and T14 are both known misses: the trade decision 13 settled holds T14 at its old bound rather than inside the band. For the product manager to note.

## Follow-ups

- **T3.lawyers (v3, PT-M23):** steady grows only while utilisation is at least 80% (a sixth to an eighth of its lawyers a year); a growth rule that hires ahead of demand, or the v3 world's larger markets, would carry it to 100-250.
- **T6.partners:** the 2006 class is 0-2 people a seed. Retention of strong associates (attrition falling on the weakest), or measuring the classes of 2006-2008 together (a change of measure: Reece's), would make the share readable.
- **T13:** partners' ordinary flight over 24 months is about 21.7% at steady's firm size; the base rate of partner flight, or measuring the loss above the firm's own rate before the merger (Reece's), decides it.
- **T4.steady and T14** move against each other through steady's equity tier; a v3 retune of overhead per lawyer or the comp round could hold both.
- **PT-M9:** automated steady's delegated admissions keep a smaller equity tier than steady's script (PEP +32.9%).
- **The nightly's T12 row** reads the runner's loaded machine (334-414 ms); the gate is `make check-timing` alone.
