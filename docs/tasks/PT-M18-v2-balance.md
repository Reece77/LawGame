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

(The session records its decisions here.)

## Follow-ups

(The session records follow-ups here, for v3.)
