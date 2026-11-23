# PT-M7c: Firm economics audit

**Goal:** a growing firm's economics look like a real firm's. After PT-M16, steady reaches 55 lawyers and $3.39M PEP in 2015, and pyramid $2.36M, against bands of 100-250 lawyers and $0.5-1.6M. Reputation was not the whole cause. Find which term of the PEP identity (spec §8.1: revenue per lawyer × margin × leverage) and which growth limit are wrong against real benchmarks, fix the model (not the bands), and bring T3 and T4 into their bands without breaking T1-T12.

**Spec:** §5.4 (pay, including below-scale firms), §5.5 (admissions), §8.1-§8.5 (the identity, KPIs, costs, comp), §17 · **ADRs:** PT-0003, PT-0007 · **Targets:** `docs/balance-targets.md` T3, T4 (known misses owned by PT-M16 and PT-M18; this milestone takes them over) · **Depends on:** PT-M16 (`pt-m16-done`) · **Lane:** A (beside PT-M11 in lane B and PT-M14 in lane C)

## Lane

- **Owns:** `ptk/balance/` and `docs/balance-targets.md` (lane A), partnership admission and comp rules (`ptk/sim/partnership/careers.py`, `comp.py`), payroll and overhead (`pay.*`, `staffing.*` and the overhead keys), hiring rates for growth, RNG ids **80-84**.
- **Must not edit:** offices, regions, bar rules and UK hiring (PT-M11), task mixes, eras, adoption and AI pricing (PT-M14).
- **Shared files:** keep both sides; re-chain migrations if another merged first. PT-M11 and PT-M14 may register strategies or ask for re-reads: accept them.

## Sub-tasks (commit after each)

1. **Benchmarks dossier** `docs/research/firm-economics.md` (sources, S/D/A tags): for 2005, 2009 and 2015, for the Am Law 100, the second hundred and firms of 50-150 lawyers where available: revenue per lawyer, PEP, profit margin, leverage (lawyers per equity partner), equity partners as a share of lawyers, associates' salary scale share at mid-size firms, overhead per lawyer, realisation. Also how fast real young firms grew (for example Quinn Emanuel, Boies Schiller, Wilson Sonsini in their first 10-15 years).
2. **Decompose** steady, boutique and pyramid at December 2015, seeds 1-10, into the identity's terms (RPL, margin, leverage, equity partners per lawyer) and the growth terms (hiring a year, attrition, admissions, demand won against demand available). Print the table against the benchmarks: which term is off, by how much.
3. **Fix the terms that are off**, in the model, with the keys you own (for example: admissions too rare, so leverage too high; salaries or overhead below a real firm's of that size; a firm's growth capped by hiring rules rather than by demand). Record each change with the benchmark it targets. Strategy scripts may change only where a sensible player would act differently (rule 2).
4. **Re-read T1-T12** on seeds 1-10 and 11-40; T3 and T4 into their bands; remove the rows you fix.

## Acceptance criteria

- [ ] The decomposition table (sub-task 2) is in the brief's "Decisions made", before and after, against the benchmarks.
- [ ] T3 steady lawyers and revenue, T4 steady, boutique and pyramid inside their bands on seeds 1-10, or a seed table showing how close and why, for Reece.
- [ ] T1, T2 and T5-T12 hold (known misses as recorded).
- [ ] `make check`, `make e2e` and the nightly run green; `Milestone-Tag: pt-m7c-done`.

## Decisions made

## Follow-ups
