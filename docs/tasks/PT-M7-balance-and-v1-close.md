# PT-M7: Balance and v1 close

**Goal:** v1 is a game: the macro history from 2005 to 2015 drives demand (the crash included); five strategies play ten years on ten seeds against `docs/balance-targets.md`; Holiday, History and onboarding make it playable for a decade.

**Spec:** §14 (to 2015), §17 · **Depends on:** all v1 milestones · **Lane:** A (closes v1)

## Sub-tasks (commit after each)

1. **Macro and legal indices 2005–2015** (`macro_history.yaml` extended): M&A, PE, IPO, default rate, litigation, enforcement, lateral heat, rate inflation; a dossier with sources; connect to demand, collections stress and lateral heat.
2. **Strategy scripts** for the five strategies; the runner (TST's framework), nightly workflow, `known_misses.py`.
3. **Tune** to T1–T12, recording before and after values in "Decisions made".
4. **History** (firm timeline, rankings by year), **onboarding** (TST M29's guided first year and What next). Holiday with its stop reasons came early, in PT-M7a.
5. **The 10-year run** printed; a practice save `pt-2008` (a 60-lawyer firm in June 2008).

## Acceptance criteria

- [ ] T1, T2, T11 and T12 pass; the bands pass or are carried with a recorded decision for Reece.
- [ ] Golden snapshots and the state cache recorded for v1.
- [ ] `make check`, e2e and nightly green; `Milestone-Tag: pt-m7-done`.

## Manual check (Reece)

Load `pt-2008` and get the firm through the crash. Then start a fresh campaign and play to 2015.

## Decisions made

Recorded by the PT-M7 session (2026-11-21). The runner's table is `make balance` (seeds 1-10, 132 turns, 90 runs; about five minutes on four cores); "before" is the first full run with the scripts and no tuning (sub-task 2's head plus the flight fix in decision 13), "after" the final run.

1. **The macro history as dated points** (ADR PT-0014; `macro_history.yaml`, dossier `docs/research/v1-macro.md`): mid-year points from the dossier's annual series (damped: about the square root of a dollar volume's ratio, since legal work follows counts and hours), with October 2008 and April 2009 points for the crash's timing. Counter-cyclical practices (beta < 0) read a pro-cyclical index so the spec's sign holds: restructuring reads `credit` (sqrt of 2005's default rate over the year's), litigation and employment `cycle`. White collar's beta 0.0 -> 0.6 (the enforcement index; it was 0 only while indices were flat).
2. **History's failures are data, not draws** (`clients.yaml` `fails`): twelve bankruptcies (Lehman, WaMu, GM, Chrysler, General Growth, Visteon, Lear, Delphi, Delta, Northwest, Dana, AMR) and six rescues (Bear Stearns, Merrill Lynch, Wachovia, Countrywide, National City, HBOS). A bankruptcy stops the client's work outside restructuring, writes its open bills off every month from the filing (final bills too) and gives its estate restructuring work (`macro.estate_mult` 25 for `estate_months` 24) to a firm that has it on its books and a restructuring lawyer; a rescue pays and its wallet ends `rescue_months` (3) later. Fannie, Freddie and AIG kept operating and paying, so they do not fail; UAL was already in Chapter 11 in 2005. Chrysler is appended to `clients.yaml` (generated clients' ids move by one, so seeded fixtures were re-picked: decision 15).
3. **Rate inflation reaches revenue through the rate index**: the market's January rise is the dossier's worked-rate growth (6.5% in 2006 and 2007, 6% 2008, 2.5% 2009, 3-4% after); demand stays work at the 2005 cards (hours). This closes PT-M7a's follow-up: the default firm's revenue no longer rises a fixed 3% a year for free but with history.
4. **Overhead per lawyer** (`pay.overhead_per_lawyer_cents`, new): support staff $7,000, technology $1,500, insurance $800, general and administrative $4,000 a month per lawyer on the books (NY band), charged to the chart's accounts that had no costs (5100, 6100, 6300, 6900). Before: margins of 85-97% against spec 6's norms of 30-45%. Tried $17,300 a month (9 of 10 restructuring runs dissolved) and $9,000 (T1 fell to 8 of 10, steady never dissolved); kept $13,300. **For Reece:** a new firm now has to finance its lockup, and an untouched group lift dissolves on 4 of 12 seeds in its first two years (main: none); a smaller first year's draw budget (`partnership.budget.first_year_margin_bp` 3000 -> 2000) would save it but costs T1 its 9 of 10.
5. **Tuning keys and values** (before -> after): `macro.beta_scale` 1.0 -> 1.3 (T1, T8); `billing.overrun_writedown` 0.60 -> 0.40 (T7 realisation; PT-M3b's guard read 83.4% on seeds 1-10 with the macro, 84.0% on main; seeds 11-40 read 84.65% branch, 84.0% main, seed variance, but realisation is T7's: 84.5% at 0.40; 0.35 gave 85.0% but steady never dissolved and won 9 of 10); difficulty `hard` `capital_mult_bp` 6000 -> 8000 (T5: 7 of 10 dissolved at 6000 with $17,300 of overhead); the new `macro.*` and `pay.overhead_per_lawyer_cents`. Tried and reverted: `strain.comfort_base` 1.0 -> 0.92 (T10: steady's own burnout rose to 18.7%), `rivals.rfp.w_incumbent` 0.8 -> 0.3 (T1: no effect), `beta_scale` 1.6 (T1: seeds 3 and 10 stay above $3M), `first_year_margin_bp` 3000 -> 2000 (decision 4).
6. **T1 in 2005 dollars.** T3 says "nominal"; T1 does not. Two partners at capacity bill about $3.2-3.5M nominal in 2009 because the market's rates rose about 27% in 2006-2009 (decision 3). T1 is read with 2009's revenue deflated by the market's rate index: 9 of 10 (7 of 10 nominal). Both are printed. **For Reece:** confirm the reading, or say T1 is nominal (then it misses on 2-3 seeds: the founders stay capacity-bound because their clients' wallets exceed two partners' hours even after the crash).
7. **T2's score** is the founding partner's earnings, 2005-2015: the December allocations of the partner the player plays, summed (TST's founder value, for a partnership; 0 if the firm dissolved). A first reading, PEP x sqrt(equity partners), rewarded size the same way (steady 8 of 10 before the scripts' fixes, 9 after). **T2 fails: steady has the best score on 9 of 10 seeds** (pyramid 1). See the table below.
8. **Scripts** (sensible play, not tuning): every active strategy answers a lost MP election by handing over to the winner (it then keeps its levers; before, steady lost its laterals and proposals for the rest of the game on some seeds); holds December's vote first in the month; defers a candidate once in their first eligible year, then leaves them to up or out; group leaders who left are replaced. The rocket borrows to its covenant limit, not past it: a lateral only while the bank has not warned for six months and cash covers two months' costs; the heeded rocket, at the first warning, stops laterals, suspends draws, calls $1M of capital and repays the revolver from spare cash. Pyramid plans 175 hours a month for every associate (2,100 a year) and hires laterals only at 90% utilisation. Boutique grows whenever its people are busy (80%): associates while leverage is under 2, a lateral partner with a $2M book when it reaches 2, two pitches a month, rates the market's plus 1 point (before: it stayed at 5-8 lawyers).
9. **T12 in the runner is printed, not a gate**: four workers share the cores, so its 2015 turn reads 197-313 ms; the gate is PT-M5's `make check-timing` test, run alone: **148 ms** at December 2015 with 150 lawyers (rule 6).
10. **PT-M4's exodus guard** (`test_the_exodus_spiral`) passes again: 3 of 10 unmanaged firms dissolve, 1 of 10 with the response (seeds 11-40: 7 of 30 and 3 of 30; main 5 of 30); its strict xfail is removed (PT-M7a's follow-up).

**Targets after tuning (seeds 1-10):**

| Target | Band | Before | After | |
| --- | --- | --- | --- | --- |
| T1 do-nothing fails | >= 9/10 | 7/10 | 9/10 (7 nominal) | pass (decision 6) |
| T2 no dominant strategy | <= 6/10 | steady 8 | steady 9, pyramid 1 | **FAIL: a gate, for Reece** |
| T3 steady lawyers | 100-250 | 60.5 | 53 | **for Reece** |
| T3 steady revenue | $60-150M | $75.1M | $63.9M | pass |
| T4 PEP steady | $0.5-1.2M | $5.33M | $4.07M | **for Reece** |
| T4 PEP boutique | $1.0-2.5M | $3.45M | $2.24M | pass |
| T4 PEP pyramid | $0.7-1.6M | $2.03M | $1.80M | **for Reece** |
| T5 steady dissolves easy / standard / hard | 0-10% / 5-20% / 20-45% | 0 / 0 / 0% | 0 / 0 / 0% | easy passes; **for Reece** |
| T6 attrition | 15-25% | 23.7% | 19.9% | pass |
| T6 class of 2006 to equity | 8-15% | 0.0% | 7.7% | **for Reece** (one partner short) |
| T7 realisation / collection / utilisation / lockup | 84-92% / 93-98% / 75-90% / 90-150 d | 86.7 / 96.6 / 81.3% / 121 | 87.4 / 96.5 / 84.9% / 123 | pass |
| T8 corporate-heavy 2009/2008 | -30% to -10% | -3.6% (n=32) | -1.3% (n=32) | **for Reece** |
| T8 restructuring > 20% | -5% to +20% | none | +40.7% (n=3) | **for Reece** |
| T9 rocket dissolves | 3-6/10 | 8/10 | 8/10 | **for Reece** |
| T9 heeded dissolves | <= 1/10 | 5/10 | 6/10 | **for Reece** |
| T10 pyramid / steady burnout | >= 2x | 0.51x | 0.88x | **for Reece** |
| T10 steady burnout | <= 5% | 0.6% | 0.6% | pass |
| T11 rivals hold history | 0 misses, >= 8 kept | 0, 10 | 0, 10 (worst 5.7%) | pass |
| T12 turn time | <= 250 ms | — | 148 ms (`make check-timing`) | pass |

During tuning one intermediate configuration (overhead $13,300, write-down 0.50) passed T2 (steady 6, pyramid 3) and T5 standard and hard (10% and 20%): only because steady dissolved on one seed in ten. It did not survive the realisation fix PT-M3b's guard needs, so it is not offered as a pass. The full printed run is `docs/balance-run.md`.

**The gate and the bands carried to Reece, with why the keys cannot reach them:**

- **T2 (a pass/fail gate)**: steady is the strongest strategy in v1's engine. It grows with its demand and laterals, keeps leverage at 4-5 lawyers per equity partner and rarely dissolves, so whatever the score reads (the founder's earnings, or PEP x sqrt(equity partners)), it wins wherever it survives; the other strategies win only on seeds where it dies. No tuning key separates them without breaking another target or an earlier guard. Proposed default: make the strategies' risks real, which is what T5 and T9 measure (decisions 4 and 5), and read T2 again; or define the score as PEP alone (boutique wins on PEP once T4's bands hold). **The branch is not merged while T2 fails** (CLAUDE.md section 9: a guard rules 1-4 cannot resolve).
- **T5**: steady dissolves on no seed at any difficulty, because the difficulty only scales the starting capital (`capital_mult_bp`) and steady never draws its revolver hard. Proposed default: hard also cuts the revolver and the founders' books (two new difficulty fields), or T5 measures the pyramid or the rocket.
- **T3 lawyers and T4 PEP** ask for a firm of 100-250 lawyers at about $600k revenue per lawyer (T3's $60-150M) and PEPs of an Am Law mid-table firm. v1's rate cards are a top New York firm's 2005 card (`practices.yaml`, dossier v1-market s5), and with history's rate rises a lawyer bills about $1.2M in 2015: steady reaches T3's revenue with half T3's lawyers, and PEP is RPL x margin x leverage = about 3x the band. Proposed default: keep the cards and move T3 to 50-120 lawyers and T4 to steady $2-5M, boutique $2.5-5M, pyramid $1.5-3.5M (Am Law 50's 2015 range); or give a new firm a lower card (a rate index below 1 at the start).
- **T8**: a two-practice or small firm is capacity-bound: its clients' wallets exceed its hours even after a 45% fall in corporate demand, so its revenue barely moves. 2009's real declines came with clients' discounts and write-downs (spec 14: "rates frozen; clients demand discounts"), which v1 does not model. Proposed default: a crisis discount (the macro's `collections` stress also raising clients' discounts and short payments in 2009-2010), a small rule for PT-M7b. The restructuring reading is 3 runs, 5 points above the band.
- **T9**: the scenario's $600,000 of capital and $1M revolver cannot carry a guaranteed lateral with a $2M+ book until it has grown; the rocket either waits (and is not a rocket) or breaches in its first year, and heeding the warning then is too late on 6 of 10 seeds. Proposed default: measure T9 from a capitalised start (the rocket from 2007, or the scenario's capital x 3), or accept 8/10 and 6/10.
- **T10**: the default staffing rule plans at most 95% of capacity (PT-M7a's `staffing.plan_fill`) and strain starts above 100% (`strain.comfort_base`), so a planned 2,100-hour year does not become strain; lowering the comfort point burns steady out too. Proposed default: overtime as a player policy (a firm-wide hours target the staffing rule plans to), PT-M7b.
- **T6 partners**: 7.7% against 8% (1 of 13 in the class): seed variance over a small class; carried rather than bending steady's admission rule.

11. **The state cache** (TST M30's framework, ported: `ptk/balance/state_cache.py`, `tests/fixtures/state_hashes.json`) is recorded for v1 on steady, pyramid and boutique, seeds 1-3, 132 months; the nightly compares every month.
12. **History and onboarding** read only stored facts: History's years come from the turn snapshots (rank among rivals by the year's revenue, a year with all twelve months); its timeline is the inbox's milestone templates and the market's dated events. Getting started's six steps tick from state; the checklist shows for at most two years or until done, and dismissing it is a browser setting (`localStorage`), as table views are. No schema change.
13. **Engine fixes the scripts found** (each with a test in `tests/unit/test_pt_m7_fixes.py`): a vote on someone who has left is withdrawn (an assertion before); the no-confidence petition queues its template's id (`no_confidence_petition`, not the trigger's name: the director raised); an approach to a partner whose employment ended another way is withdrawn (raised `not on a firm's books`).
14. **pt-2008** (`ptk/practice.py`) is built, not hand-written: the spin-out plays January 2005 to June 2008 over the pure sim, then grows at once to 60 lawyers (14 equity partners through PT-M4's arrival hook, 7 income partners, 39 associates, 31 clients worth the firm's capacity, $15M of capital). The candidate is a corporate seventh-year (eighth from September, eligible at track 8). History's failing clients are left out of its panels. `ptk practice-save`, `POST /api/practice/{key}`, the Main menu's Practice button.
15. **Fixtures re-picked** because Chrysler's row shifts generated clients (decision 2), each asserting the precondition it needs: PT-M3b's retainer test (seed 3: seed 2 now has a retainer), PT-M6's event property test (seed 8: seed 7 has no open matter at turn 8), its write-down test (seed 4), PT-M7a's assessment tests (seed 4: no case in three years on seed 3), the CLI matters test (seed 40), PT-M4's true-up test (seed 3: with overhead, seed 2's founders drew more than the first year's cash profit), PT-M4's partnership API round trip (seed 5: the untouched group lift on seed 4 dissolves in its fourteenth month); PT-M1b's hiring round trip runs under `solvent(balance)` on both sides (it hires two people a month from $600k of capital and now dissolves by month 6; it tests the round trip, PT-M4's pattern); the golden seeds play until the campaign ends or the firm dissolves (seed 2's unmanaged firm now dissolves before 2034). No assertion was loosened.

## Follow-ups

- **PT-M7b (proposed):** Reece's answers on the bands above (T3, T4, T6 partners, T8, T9, T10), then the small rules they need (a crisis discount, an hours policy, a capitalised T9 start).
- Steady's partners leave when underpaid against their market value: a December comp round in the scripts (`CompRound`) would keep more of them; the engine has it, the scripts do not use it.
- A client's GC change and panel churn for a firm that does no BD (do-nothing's clients are sticky; T1 then needs no deflation).
- History: a rankings tab by PEP and RPL, and the timeline's events linked to their screens.
- Holiday's stop reasons for a client's failure (`client_failed`), so a player on holiday sees Lehman.
