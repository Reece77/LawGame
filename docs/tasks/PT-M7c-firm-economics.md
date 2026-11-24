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

- [x] The decomposition table (sub-task 2) is in the brief's "Decisions made", before and after, against the benchmarks.
- [x] T3 steady lawyers and revenue, T4 steady, boutique and pyramid inside their bands on seeds 1-10, or a seed table showing how close and why, for Reece.
- [ ] T1, T2 and T5-T12 hold (known misses as recorded).
- [ ] `make check`, `make e2e` and the nightly run green; `Milestone-Tag: pt-m7c-done`.

## Decisions made

Recorded by the PT-M7c session (2026-11-23). "main" is `f8deff3`; readings are December 2015 (132 turns of `biglaw_spinout`, standard), seeds 1-10 unless stated; the decomposition is `tools/firm_economics.py` (`ptk/balance/economics.py`), the targets `make balance` in the nightly on the branch.

1. **Benchmarks** (sub-task 1): `docs/research/firm-economics.md`. The bands match a **Second Hundred** firm in 2015: RPL $649k [S], PEP $737k [S], margin about 36% [S, 2009], equity partners about 29% of lawyers [D]; equity partners' standard rate $650 an hour (Am Law 100 $875) [S]; associates bill about 85% of the hours they work (1,873 of 2,199) [S]; overhead per lawyer $150-270k [A]; equity-partner attrition about 5% a year [A]; elite start-ups grew 15-25% a year in their first 10-15 years (Wachtell, Wilson Sonsini, Quinn Emanuel) [D].

2. **The decomposition, before and after** (sub-task 2; medians of the surviving runs; "Other costs/L" is every expense but lawyers' pay, per lawyer; hours are billable per lawyer; rate is standard value per billable hour; share is the year's worked value over New York's demand):

| Run | Dissolved | Lawyers | Revenue $M | PEP $k | RPL $k | Margin | Lawyers/EP | EP share | Hours | Rate $ | Realis. | Collect. | Lawyer pay/L $k | Other costs/L $k | Hires/yr | Leavers/yr | Admits/yr | Share of NY demand |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| steady (before) | 2/10 | 64 | 72 | 3794 | 1186 | 55% | 5.74 | 17% | 2050 | 778 | 75% | 96% | 237 | 262 | 24 | 16 | 3.5 | 0.6% |
| boutique (before) | 0/10 | 8 | 9 | 2266 | 1313 | 64% | 2.72 | 37% | 2009 | 766 | 88% | 96% | 125 | 280 | 1 | 1 | 0.0 | 0.1% |
| pyramid (before) | 1/10 | 24 | 23 | 2571 | 894 | 37% | 7.92 | 13% | 1946 | 614 | 83% | 96% | 258 | 261 | 7 | 7 | 1.0 | 0.2% |
| steady (after) | 2/10 | 72 | 81 | 2837 | 1189 | 57% | 4.36 | 23% | 1900 | 802 | 82% | 97% | 235 | 255 | 22 | 14 | 1.8 | 0.7% |
| boutique (after) | 0/10 | 8 | 9 | 2266 | 1313 | 64% | 2.72 | 37% | 2009 | 766 | 88% | 96% | 125 | 280 | 1 | 1 | 0.0 | 0.1% |
| pyramid (after) | 0/10 | 29 | 26 | 1655 | 1021 | 51% | 3.08 | 32% | 1895 | 656 | 86% | 96% | 209 | 235 | 8 | 7 | 1.0 | 0.2% |
| **Benchmark** (Second Hundred, 2015) | | 100-250 (T3) | 60-150 (T3) | 737 | 649 | ~36% | ~3.4 | ~29% | ~1,750 | ~440 (partners 650) | ~84% collected | | | ~270 | | ~5% of partners | | |

**Which term was off, and by how much (steady, before):** leverage 5.74 lawyers per equity partner against about 3.4 (+70%), from the equity partners' **attrition** (decision 3); RPL $1,186k against $649k (+83%), from the **rate** ($778 against about $440 blended, +75%; partners about $1,075 against $650) with hours +17% and realisation and collection -10%; margin 55% against about 36% (+19 points), which is RPL's excess over a cost base that is already a large firm's (lawyers' pay $237k and other costs $262k a lawyer, against the Am Law 100's $541k in all [D]). PEP = RPL x margin x leverage = 5.1 times the benchmark: 1.8 (RPL) x 1.5 (margin) x 1.7 (leverage). **Growth** is not capped by demand (the firm works 0.6% of New York's demand; utilisation 90%): it is the hiring rule's 80% utilisation gate and two-at-a-time hiring plans, and the 4-to-64 path (30% a year) is already faster than the dossier's elite start-ups.

3. **The fix: a December admission keeps its budget** (`ptk/sim/partnership/comp.py`, lane A's comp rules). December's allocation gave a partner voted in that December (admitted from January) their zero share of the closing year and set their budget to it, so in their first year `flight.firm_comp_cents` read their comp as nothing: the comp gap capped p_leave at 15% a month and stay probability near 1%. Steady seed 1 lost 28 equity partners in 11 years (seed 5: 30), nearly every homegrown partner within a year of admission; after the fix 6 and 3 (about 3-5% a year, the benchmark's 5%). Their budget is now their points' share of the year's pool, as `effects.admit` intended. Unit test `test_a_december_admission_keeps_its_budget` (fails before the fix). Leverage 5.74 -> 4.36 (equity partners 17% -> 23%), steady PEP (survivors) $3.79M -> $2.84M, pyramid $2.57M -> $1.66M; boutique unchanged (no admissions in 2005-2015).

4. **Tried and not kept** (tuning copies of `balance.yaml`, seeds 1-10, with the fix unless stated):

| Change | Steady lawyers / PEP (survivors) | Dissolved (steady, pyramid) | Why not kept |
| --- | --- | --- | --- |
| Overhead indexed to the market's rate index (a new `pay.overhead_index_bp`), before the fix | 52 / $4.25M | - | 2015's other costs ($262k a lawyer) are already inside the benchmark ($150-270k); indexing takes them to $335k |
| Fill 0.85 (`staffing.plan_fill`, `matters.flow_fill`: associates bill 85% of hours worked), dilution weight 2, before the fix | 24 / $3.00M | - | steady's 80% utilisation gate then rarely opens: growth stops |
| Card 75% (`rates.card.start_bp`), before the fix | 57 / $2.75M | 6, 8 | first-year insolvency |
| Card 80% and pay 80% of the scale (spec 5.4's below-scale firm, a script policy), before the fix | 53 / $2.77M | 2 of 20 | margin 55%: PEP unchanged |
| Card 65% / 75% with pay 70% / 75% and admission frictions (dilution 2, proposal energy 2) | 11 / $0.36M; 79 / $3.56M | 15 of 20; 6 of 20 | the founders' overhead and draws outrun the revenue |
| Card 80% | 86 / $2.19M | 6, 2 (boutique 3) | T5 standard (5-20%) broken: the co-founder is poached in 2006 at the lower comp, the departures covenant breaks and the bank calls the revolver (seed 4, month 23) |
| Card 80%, steady hires only with a month's costs in cash (a script rule) | 58 / $2.56M | 4 | still dissolves; growth falls |
| Hiring plans sized to the need (script) | 74 / $3.19M | 2, 0 | no gain alone; pyramid PEP $2.21M |
| Admission frictions (dilution 2, proposal energy 2) | 96 / $3.17M | 2, 0 | equity share unchanged (23%): no benchmark mechanism; pyramid $2.06M |
| Both of the last two | 116 / $2.81M | 2, 0 | T3 lawyers in band but PEP unchanged and pyramid $2.24M; seed noise as large as the effect |

5. **The term left is the rate, and it is a design question (for Reece).** With leverage fixed, steady's PEP is RPL ($1.19M, +83%) over a large firm's cost base. Every in-lane key that lowers RPL or raises costs dissolves the young firm first: its first two years run on the founders' books at the founders' rates, with the revolver drawn, and a lower card makes the co-founder poachable and the bank nervous. The rate card is not one of this brief's keys, and PT-M7b's design (Reece, 2026-11-21) has a new firm's card rise from its start with reputation. **Proposed options:** (a) a card that starts at the founders' rates (9850) and drifts each January toward a reputation target with a lower floor (for example 60% of the top card, a step of 3 points a year), so that a firm without the market's top reputation bills like the Second Hundred by 2015; (b) a new firm's costs follow its card (PT-M7b's proposal); (c) T4 steady's band moved to the benchmark of what steady is (an elite spin-out of 50-120 lawyers: $2-4M, the Am Law 50). **T3 lawyers:** the dossier's young firms grew 15-25% a year; steady's 30% a year (4 to 72, survivors) is already faster, and 100-250 lawyers needs 35-45% a year. Proposed: keep the band and let growth come from the hiring plans sized to the need (decision 4) once the rate question is settled, or lower the band to 50-150.

6. **Seed tables** (T3's and T4's measures: lawyers on the books in December 2015, a dissolved firm's PEP counting $0; main and branch on the same machine):

Seeds 1-10
| Seed | steady lawyers main | branch | steady PEP main | branch | boutique PEP main | branch | pyramid PEP main | branch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 84 | 17 | $3.43M | $3.31M | $2.26M | $2.26M | $2.57M | $2.08M |
| 2 | 60 | 15 (d) | $4.69M | $0.00M | $2.86M | $2.86M | $0.00M | $1.58M |
| 3 | 22 (d) | 78 | $0.00M | $2.94M | $2.11M | $2.11M | $2.82M | $2.20M |
| 4 | 43 | 20 | $3.24M | $1.50M | $2.51M | $2.51M | $2.15M | $1.23M |
| 5 | 94 | 116 | $3.34M | $3.50M | $2.27M | $2.27M | $1.95M | $1.18M |
| 6 | 67 | 78 | $4.38M | $3.62M | $1.82M | $1.82M | $4.12M | $3.13M |
| 7 | 42 | 26 | $5.08M | $1.65M | $2.53M | $2.53M | $3.60M | $1.73M |
| 8 | 82 | 83 | $4.15M | $2.72M | $1.49M | $1.48M | $0.80M | $1.10M |
| 9 | 13 (d) | 21 (d) | $0.00M | $0.00M | $2.50M | $2.50M | $4.07M | $3.06M |
| 10 | 50 | 66 | $3.00M | $2.73M | $2.15M | $2.15M | $0.71M | $1.57M |

Seeds 11-40: steady lawyers 56 -> 83.5, steady PEP $3.90M -> $3.01M, boutique $1.86M -> $1.86M, pyramid $3.46M -> $2.07M; dissolved steady 2 -> 3, boutique 4 -> 4, pyramid 2 -> 1. Seeds 1-10's steady lawyers median falls (55 -> 46) because seeds 1, 4 and 7 take other paths (17, 20, 26 lawyers) and seed 2 dissolves (seed 3 survives); on 30 seeds it rises by 28. Rule 4: seed variance on 1-10, a real gain on 30.

7. **Streams:** none added (ids 80-84 unused). **Schema:** no change. **Strategies:** unchanged (no rule-2 script change was needed). PT-M11 and PT-M14 registered no strategy and asked no re-read before this merge.

8. **State cache re-recorded** (the fix changes results from the first December admission). Golden snapshots unchanged.

9. **T1-T12** (`make balance` in the nightly on the branch, run 45112447547, seeds 1-10; "main" is PT-M16's last nightly, run 45082072583 on `fdd6da4`, main's code):

| Target | Band | main | PT-M7c | Row |
| --- | --- | --- | --- | --- |
| T1 do-nothing fails | >= 9/10 | 8/10 | 8/10 | known (PT-M18), unchanged |
| T2 no dominant strategy | <= 6/10 | steady 8, pyramid 2 | steady 6, pyramid 4 | **passes: row removed** |
| T3 steady lawyers | 100-250 | 55.0 | 46.0 (11-40: 83.5, main 56) | known, now Reece's (decision 5) |
| T3 steady revenue | $60-150M | $56.95M | $44.39M (11-40: $95.7M, main $63.6M) | printed, no row |
| T4 steady PEP | $0.5-1.2M | $3.39M | $2.72M | known, now Reece's (decision 5) |
| T4 boutique PEP | $1.0-2.5M | $2.27M | $2.27M | ok |
| T4 pyramid PEP | $0.7-1.6M | $2.36M | $1.65M | known, now Reece's (decision 5) |
| T5 easy / standard / hard | 0-10 / 5-20 / 20-45% | 10 / 20 / 50% | 10 / 20 / 50% | hard printed (as main) |
| T6 attrition / partners | 15-25% / 8-15% | 23.5% / 0.0% | 23.0% / 6.2% | partners printed (better) |
| T7 realisation / collection / utilisation / lockup | 84-92 / 93-98 / 75-90% / 90-150 d | 84.5 / 96.3 / 84.1 / 128 | 85.1 / 96.4 / 83.1 / 126 | ok |
| T8 corporate / restructuring | -30 to -10% / -5 to +20% | -5.5% / -16.6% (n=3) | -5.9% / -17.5% (n=4) | corporate accepted; restructuring printed (as main) |
| T9 rocket / heeded | 3-6 / <= 1 | 2 / 2 | 2 / 2 | printed (as main) |
| T10 ratio / steady | >= 2x / <= 5% | 7.93x / 1.0% | 12.43x / 0.7% | ok |
| T11 / T11.2025 | +-15%, 0, >= 8 | 5.6%, 0, 10 / 7.1%, 0, 8 | 5.7%, 0, 10 / 7.1%, 0, 9 | ok |
| T12 | <= 250 ms | 920 ms on the runner | 845 ms on the runner | the gate is `make check-timing` (check) |
| T8.2020 | -30 to -10%, most back | -15.5%, 6/8 | -22.1%, 8/8 | ok |
| 30y steady (information) | - | 120 lawyers, $329M, $9.66M | 174 lawyers, $493M, $8.63M | printed |

10. **PT-M9's guard** (`tests/balance/test_pt_m9.py::test_steady_automated_is_within_20_percent_of_steady`, nightly: 2015 revenue and PEP of `steady-automated` within 20% of steady's, seeds 1-10) **misses on seeds 1-10 on the branch and passes on 11-40 on both** (rule 4: seed variance, treated as rule 3; locally, the same machine):

| Seeds | main revenue gap | main PEP gap | PT-M7c revenue gap | PT-M7c PEP gap |
| --- | --- | --- | --- | --- |
| 1-10 | within 20% (PT-M16's nightly passed) | within 20% | +67.2% (steady $44.39M, automated $74.21M) | +20.5% ($2.72M, $3.28M) |
| 11-40 | -15.3% ($63.57M, $53.84M) | -10.1% ($3.90M, $3.51M) | -3.8% ($95.68M, $92.06M) | +7.6% ($3.01M, $3.24M) |

On 30 seeds the branch is closer to steady than main; on seeds 1-10 steady's own median falls (seeds 1, 4 and 7 take small paths, decision 6). Not added to `known_misses.py` (rule 3) and the test is unchanged: **for Reece or the product manager** (the guard's owner is PT-M18's balance pass by PT-M16's precedent for PT-M8's guard).

### Client-tier pricing (Reece's decision on the rate card, via the product manager, 2026-11-23)

Reece: (1) client tiers: mid-market clients pay at most 55-60% of the top card, only large clients pay the top card, and only to a firm in the practice's top decile; (2) the card's reputation curve reads the firm's percentile among all firms in the practice and region; (3) the founders' book clients keep the founders' rates so the first two years survive. PT-M16 has merged, so its reputation and card code is lane A's to change. "Before" below is the branch after merging PT-M11 (`8bd506e`: the admission fix, no tiers); "after" is `46fdb24`.

11. **The mechanism** (`ptk/sim/matters/rates.py` `ClientCards`, `client_indexes`): a client's share of a practice's top card is: the founders' book clients (on the panel since the setup, `since_turn` 0; no schema change) `rates.card.book_bp` 9850; large clients (`size_class` large) the practice's card (`firm.rate_card`, from `start_bp` moving at most `step_bp` a January toward `start + (1 - start) x min(1, percentile / top_quantile)^curve`, so the full card only at the top decile); mid-market clients the practice's card capped at `mid_max_bp`. Hours' standard value (the staffing rule), new matters' expected fees (intake), blended engagements (billing) and RFP matters read it. The appeal's price term is `1 - the client's index / (the market's index x the tier's reference)`, the reference being the mid cap for mid-market clients, the full card for large ones and the founders' rates for the book, so a firm priced at its tier is priced as its market is. `reputation.formulas.percentile`: the share of the other seeded firms in the practice and region below the firm's reputation (ties half); `card_progress` = min(1, percentile / 0.9); `reputation.card.full_share` removed. Unit and Hypothesis tests: `tests/unit/test_client_tiers.py`; PT-M3b's WIP property test reads the client's card (the identity it checks is unchanged).
12. **The book's rates are time-limited** (my reading of "so the first two years survive"): `book_months` 24, then the book's share falls linearly to its tier's card over `book_fade_months` 60 (to January 2012). Permanent founders' rates left the founders' clients 40% of steady's 2015 work at 98.5% of the top card; a cliff at month 24 (tried: book 24, fade 0) cut 2007's profit below zero, zero allocations sent every partner's flight to its cap (seed 3: three of five equity partners left in 2008, their clients followed) and steady dissolved on 7 of 10.
13. **Keys and tuning** (seeds 1-10, T3's and T4's measures, a dissolved firm's PEP $0):

| Run | Steady lawyers / revenue | Steady PEP | Boutique PEP | Pyramid PEP | Steady dissolved (std) |
| --- | --- | --- | --- | --- | --- |
| before (no tiers) | 46 / $46.6M | $2.40M | $2.17M | $1.59M | 3 |
| A: tiers, start 9850, step 50, permanent book | 29.5 / $20.8M | $1.56M | $2.14M | $1.79M | 4 |
| B: start 7000, step 400, book 24 months, cliff | 23.5 / $9.8M | $0 | $1.26M | $0.76M | 7 |
| C: B with a 36-month fade | 24.5 / $8.6M | $0 | $1.31M | $0.56M | 7 |
| D: start 8000, step 400, mid 6000, fade 60 | 47 / $29.1M | $1.22M | $1.79M | $0.83M | 3 |
| D, the nightly (T5 easy / standard / hard) | 47 / $29.08M | $1.22M | $1.79M | $1.32M (pyramid at 80% pay) | 40% / 30% / 70% |
| D + steady's layoff rule (decision 14), curve 2 | 55 / $43.9M | $1.66M | - | - | 0 / 2 / 5 of 10 |
| ... curve 3 (**final**) | 60 / $47.2M | $1.31M | $1.49M | $0.98M | 0 / 2 / 5 of 10 |
| ... curve 3, start 7500 | 43.5 / $32.0M | $1.25M | - | - | 0 / 1 / 5 |
| ... curve 4 | 59 / $49.9M | $1.30M | - | - | 0 / 2 / 6 |
| D, start 7500 (no layoff) | 63 / $49.7M | $1.53M | - | - | 2 (11-40: 8 of 30) |

Final keys: `rates.card` start_bp 9850 -> 8000, step_bp 50 -> 400, mid_max_bp 6000 (Reece's 55-60%, the top), book_bp 9850, book_months 24, book_fade_months 60; `reputation.card` curve 2 -> 3, full_share removed, top_quantile 0.9.
14. **Two script rules (CLAUDE.md 9 rule 2), for Reece's review:** the **pyramid pays 80% of the scale** (`PYRAMID_PAY_BP`): billing mid-market clients below the market's rates at the full New York scale it dissolved on 13 of seeds 11-40 (at 80%: 6, median PEP $0.94M); mid-size firms pay 65-72% of the scale (dossier s5). **Steady lays off associates while utilisation stays below 70%** (`STEADY_LAYOFF_*`: three months below 70%, back toward 80%, at most 10% of associates a month; the pyramid's PT-M10 rule, more patient): with the tiers every easy-difficulty steady death came in 2009 (a loss year zeroes the partners' allocations and flight takes them), T5 read 40% / 30% / 70%; with the rule 0% / 20% / 50% (main 10% / 20% / 50%).
15. **Guards:** PT-M4's exodus guard heeded 1 of 10 dissolved, ignored 5 of 10 (main 1 and 3+); T5 easy 0% (band 0-10), standard 20% (5-20), hard 50% (20-45; main 50%, printed, not a gate) on seeds 1-10 (`/tmp` reading, the nightly below confirms).
16. **The decomposition, before and after the tiers** (seeds 1-10, medians of the surviving runs; "Founders' clients %" is the share of the year's worked value from the setup's book clients, who by 2015 pay their tier's card; large and mid as the other shares):

| Run | Dissolved | Lawyers | Revenue $M | PEP $k | RPL $k | Margin | Lawyers/EP | EP share | Hours | Rate $ | Realis. | Collect. | Lawyer pay/L $k | Other costs/L $k | Hires/yr | Leavers/yr | Admits/yr | Share of NY demand | Founders' clients % | Large % | Mid % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| steady (before tiers) | 3/10 | 68 | 83 | 2852 | 1235 | 59% | 4.23 | 24% | 1936 | 802 | 82% | 97% | 223 | 245 | 21 | 14 | 2.0 | 0.6% | - | - | - |
| boutique (before tiers) | 1/10 | 8 | 9 | 2199 | 1322 | 64% | 2.79 | 36% | 2007 | 800 | 90% | 97% | 124 | 282 | 1 | 1 | 0.0 | 0.1% | - | - | - |
| pyramid (before tiers) | 0/10 | 32 | 24 | 1595 | 992 | 50% | 3.06 | 33% | 1721 | 654 | 86% | 96% | 225 | 234 | 7 | 6 | 1.0 | 0.2% | - | - | - |
| steady (after tiers) | 2/10 | 78 | 65 | 1593 | 882 | 41% | 4.28 | 23% | 1945 | 627 | 82% | 96% | 236 | 256 | 27 | 21 | 2.2 | 0.5% | 10% | 34% | 30% |
| boutique (after tiers) | 0/10 | 6 | 6 | 1494 | 1114 | 58% | 2.46 | 41% | 1942 | 714 | 84% | 97% | 127 | 324 | 1 | 1 | 0.0 | 0.0% | 24% | 76% | 0% |
| pyramid (after tiers) | 1/10 | 28 | 19 | 1061 | 868 | 49% | 2.68 | 37% | 1913 | 552 | 83% | 97% | 170 | 206 | 7 | 6 | 0.8 | 0.1% | 54% | 41% | 0% |

| **Benchmark** (Second Hundred, 2015) | | 100-250 (T3) | 60-150 (T3) | 737 | 649 | ~36% | ~3.4 | ~29% | ~1,750 | ~440 (partners 650) | ~84% collected | | | ~270 | | | | | | | | |

**What moved:** steady's RPL $1,235k -> $882k (rate $802 -> $627, -22%), margin 59% -> 41%, leverage unchanged (4.2-4.3): PEP $2.85M -> $1.59M among survivors. **What is still off:** RPL is 36% above the Second Hundred because 34% of steady's work is for large clients and its practices reach the top decile (and the full card) within the decade; mid-market clients are 30%. Margin 41% against 36%. Growth: 78 lawyers among survivors (60 with the dissolved), revenue $47.2M median.

17. **Seed tables** (T3's and T4's measures, seeds 1-10, before and after the tiers):

| Seed | Steady lawyers before | after | Steady revenue before | after | Steady PEP before | after | Boutique PEP before | after | Pyramid PEP before | after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 21 (d) | 82 | $4.7M | $81.3M | $0.00M | $1.84M | $1.31M | $1.48M | $1.66M | $1.54M |
| 2 | 15 (d) | 46 | $0.5M | $37.2M | $0.00M | $1.76M | $2.80M | $2.43M | $1.84M | $0.00M |
| 3 | 68 | 74 | $83.3M | $57.2M | $2.51M | $1.20M | $2.59M | $1.45M | $1.66M | $0.90M |
| 4 | 19 | 12 (d) | $24.1M | $5.2M | $2.29M | $0.00M | $0.00M | $1.51M | $1.43M | $1.06M |
| 5 | 119 | 98 | $139.3M | $96.7M | $3.37M | $2.00M | $2.29M | $0.70M | $1.41M | $1.35M |
| 6 | 82 | 95 | $98.1M | $99.8M | $3.39M | $3.15M | $1.94M | $0.92M | $2.20M | $2.86M |
| 7 | 26 | 21 | $18.4M | $14.8M | $0.83M | $0.59M | $2.20M | $2.27M | $1.53M | $0.70M |
| 8 | 76 | 90 | $85.2M | $72.1M | $2.85M | $1.42M | $1.53M | $0.98M | $1.06M | $0.45M |
| 9 | 21 (d) | 10 (d) | $7.1M | $3.5M | $0.00M | $0.00M | $2.42M | $1.81M | $1.70M | $1.63M |
| 10 | 66 | 37 | $69.2M | $30.0M | $3.05M | $0.46M | $2.15M | $1.55M | $1.03M | $0.80M |
| **Median** | 46.0 | 60.0 | $46.6M | $47.2M | $2.40M | $1.31M | $2.17M | $1.49M | $1.59M | $0.98M |

Seeds 11-40 (before -> after): steady lawyers 72.5 -> 71.5, revenue $84.9M -> $63.3M, PEP $3.09M -> $1.65M, dissolved 3 -> 2 of 30; boutique PEP $1.85M -> $1.30M (dissolved 4 -> 6); pyramid $2.22M -> $1.18M (1 -> 4).

**For Reece (T3 and T4 steady still miss):** T4 steady $1.31M on seeds 1-10 ($0.11M above its band; 11-40 $1.65M): what remains is steady's large clients at a top-decile card, which decision 1 of Reece's rule intends. T3: 60 lawyers and $47.2M (11-40: 71.5 and $63.3M); steady's growth (30% a year among survivors) is already above the dossier's young firms. Proposed: keep the rows as known misses with these readings (their bounds unchanged), or a T4 steady band of $0.5-1.6M (the Am Law 100's $1.61M at the top) and T3 50-150 lawyers.

18. **T1-T12 after the tiers** (`make balance` in the nightly on `46fdb24`, run 45299253405, seeds 1-10; "main" is PT-M11's last nightly, run 45129354271):

| Target | Band | main (PT-M11) | before tiers (PT-M7c, `bbac756`) | after tiers |
| --- | --- | --- | --- | --- |
| T1 | >= 9/10 | known miss | 8/10 | **10/10 ok** |
| T2 | <= 6/10 | known miss | steady 6, pyramid 4 | steady 5, pyramid 4, boutique 1 ok |
| T3 lawyers / revenue | 100-250 / $60-150M | 60 / $70.21M | 46 / $44.39M | 60 / $47.21M (miss) |
| T4 steady / boutique / pyramid | $0.5-1.2 / 1.0-2.5 / 0.7-1.6M | $4.37M / $2.17M / $2.08M | $2.72M / $2.27M / $1.65M | **$1.31M** / $1.49M ok / **$0.98M ok** |
| T5 easy / standard / hard | 0-10 / 5-20 / 20-45% | 10 / 20 / 50% | 10 / 20 / 50% | 0 / 20 / 50% |
| T6 attrition / partners | 15-25% / 8-15% | 24.2% / 0.0% | 23.0% / 6.2% | **27.3% (new miss)** / 7.1% |
| T7 | in bands | ok | ok | ok (84.9 / 96.4 / 84.4 / 125) |
| T8 corporate / restructuring | -30 to -10% / -5 to +20% | -5.5% / -16.6% | -5.9% / -17.5% | **-14.4% ok** / -17.2% |
| T9 rocket / heeded | 3-6 / <= 1 | 2 / 2 | 2 / 2 | **5 ok** / 2 |
| T10 | >= 2x / <= 5% | ok | ok | 12.79x / 0.6% ok |
| T11 / T11.2025 | gates | ok | ok | ok (6.9%, 0, 9 / 7.1%, 0, 8) |
| T12 (runner; the gate is check-timing) | <= 250 ms | 1033 ms | 845 ms | 998 ms |
| T8.2020 | -30 to -10% | -11.2%, 6/8 | -22.1%, 8/8 | **-8.8% (new miss)**, 8/8 |

19. **What still misses, for Reece:**
    - **T6 attrition 27.3%** (main 24.2%): steady's layoff rule (decision 14) counts in "associates who left": steady's own attrition 34.6% with it, 25.0% without (and without it T5 reads 40 / 30 / 70%). Tried: below 60% to 75% at 5% a month (T6 24.5%, T5 40 / 30 / 70%); 65/75/10 and 70/75/10 (T6 27.3%, T5 0-20-50/60); layoffs only below a 15% or 5% trailing margin (steady's attrition 27.4% / 25.8%, T5 hard 70%); the pyramid at 90% or 100% pay (T6 26.9% / 27.3%). T5 and T6 pull against each other through the layoffs: a firm thin enough to bill Second Hundred rates needs to shed associates in 2009, and the measure counts them.
    - **T8.2020 -8.8%** against -10% (main -11.2%): steady-30y's corporate-heavy firms fall less in 2020 Q2 (smaller, with mid-market work).
    - **PT-M9's guard** (`test_steady_automated_is_within_20_percent_of_steady`): automated steady $13.48M against steady $47.21M (-71%): `steady_automated` (PT-M9's script) has no layoff rule, so it no longer tracks steady; a rule-2 fix (giving it the same rule) is mine to make if you keep the layoff rule.
    - **T3 and T4 steady** as decision 17 (known-miss rows, bounds unchanged).
    **Proposed:** accept the layoff rule and T6's band reading 15-30% for years with a crisis, or keep steady without layoffs and T5 at 40 / 30 / 70%; the PT-M9 guard follows whichever you choose.

## Follow-ups

- Reece's decision on the rate card (decision 5); then T3 lawyers through hiring plans sized to the need (decision 4).
- The pyramid's two-tier vote is proposed once, before the firm reaches stage 2, and never again (`moves.comp_system` marks it proposed when the action is refused), so a pyramid has no income partners and admits equity partners (32% of its lawyers): a script fix that raises pyramid's PEP, left for the rate-card pass.
- The boutique stays at 8 lawyers against its 25 (its hiring rule needs 80% utilisation and a quiet bank).
- Up or out leaves many class-8 associates on the books (steady seed 5: 36 of 117 lawyers in 2015).
- `pay.overhead_per_lawyer_cents` is flat in nominal dollars to 2034: inside the 2015 benchmark, but by 2025 it will be low against rates (PT-M18's 30-year targets).
