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

## Follow-ups

(The session records follow-ups here, for v3.)
