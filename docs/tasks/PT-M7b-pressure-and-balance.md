# PT-M7b: Pressure and balance

**Goal:** close the balance targets PT-M7 carried as known misses (Reece's decisions on PT-M7, via the product manager, 2026-11-21): a new firm bills below the top card until it earns its reputation, difficulty has teeth, the 2008 crisis brings discounts and collapsed deals, the CFO warns early enough to act on, and a firm can set its billable hours. Then re-read T2.

**Spec:** §6 (rates, demand), §7.1 (the price term), §7.7 (billing), §8.4 (the revolver and covenants), §8.7 (the CFO's warning), §14 (2008-2009: "rates frozen; clients demand discounts and alternative fees"), §17 · **ADRs:** PT-0003, PT-0005, PT-0007, PT-0012 (streams), PT-0014 (the macro history) · **Targets:** `docs/balance-targets.md` T2, T3, T4, T5, T8, T9, T10 (the known misses in `backend/ptk/balance/known_misses.py`, each owned by PT-M7b) · **Depends on:** PT-M7 (`pt-m7-done`) · **Lane:** A

## Out of scope

Any change to how a target is measured or to its band (T3 and T4's bands stay; T2's score stays the founding partner's earnings, 2005-2015; T1 stays in 2005 dollars); first-year draws (`partnership.budget.first_year_margin_bp` stays 3000: an untouched group lift that dissolves is accepted, Reece 2026-11-21); the seeded macro cycles after 2015 (PT-M10); v2's reputation and rankings (PT-M16: sub-task 1's reputation is the existing stand-in, `matters.market.firm_reputation`); Tech Startup Tycoon is read-only (CLAUDE.md §3).

## Sub-tasks (commit after each)

1. **A new firm's rate card.** A firm starts each practice at 65% of the top card (`practices.yaml`'s 2005 cards) and rises toward the full card as its reputation in that practice grows (keys in `balance.yaml`: the starting share, the reputation at which the full card is reached, and the curve between). Every hour's standard value, blended rates and new matters' expected fees use the practice's card times the firm's rate index; the appeal's price term reads the practice's card against the market's. Rivals keep their own rates. The card by practice on the Practices screen. **Targets:** T3 (steady lawyers 100-250), T4 (PEP steady $0.5-1.2M, pyramid $0.7-1.6M); the bands are unchanged.
2. **Difficulty teeth.** `hard` multiplies the founders' books by 0.7, the revolver by 0.5, clients' starting loyalty by -10 points and the starting card by 0.9 (on top of sub-task 1's); `easy` is the mirror image, softer (books x 1.2, the revolver x 1.5, loyalty +5, the card x 1.05: the brief's proposal; tune within these directions). New difficulty fields in `scenarios.yaml`, validated at load; `standard` is unchanged. **Target:** T5 (steady dissolves easy 0-10%, standard 5-20%, hard 20-45%).
3. **Crisis discounts.** From late 2008, clients ask for discounts on new engagements and write-downs on bills, tied to the macro indices (the `collections` and `credit` stress; more for price-sensitive clients and clients whose sector is stressed), easing as the indices recover; and more deals collapse in progress (a deal's chance to close falls with its practice's driver index). Restructuring's 2009 growth comes back under +20% (the estate multiplier, the credit index's transform or the restructuring beta). New randomness from a new stream (ADR PT-0012's table). **Target:** T8 (corporate-heavy firms -30% to -10% in 2009 against 2008; restructuring-heavy -5% to +20%).
4. **An earlier CFO warning.** A forecast covenant warning 3-6 months ahead (the covenants projected from the trailing trend of revenue, cash and drawn balance), as an inbox item and on the Finance screen, beside today's headroom warning. Tune lateral partners' guarantees (and, if needed, books' arrival and the lateral market's costs) so the unchecked lateral rocket dissolves on 3-6 of 10 seeds and the rocket that heeds the warning (the `lateral-rocket-heeded` script, which reads the new warning) on at most 1. **Target:** T9; PT-M4's exodus guard (`test_the_exodus_spiral`) stays green.
5. **An hours policy.** A firm-wide billable target (hours a year, an action and an Org-screen setting, default the levels' `billable_target_hours`) that the default staffing rule plans toward: `staffing.plan_fill` may exceed 95% of capacity when the policy asks for more hours than that allows, so strain follows. The pyramid script sets 2,300-2,400 hours; the other scripts keep the default. **Target:** T10 (pyramid's associates burn out at least twice as often as steady's; steady's at most 5% a year).
6. **Re-read T2** after sub-tasks 1-5 with the runner (`make balance`), and add a **December comp round** to the strategy scripts (`CompRound`: the partners a strategy would keep, by its comp system). Report to Reece with the seed table (each strategy's score by seed, the winner, and every target's before and after); T2's measure is unchanged. Remove each known miss whose target now passes; a target that still misses keeps its row with the new reading, or comes back to Reece.

## Acceptance criteria

- [ ] T3 (lawyers), T4 (steady, pyramid), T5 (standard, hard), T8, T9 and T10 pass on seeds 1-10, or are carried with a recorded decision for Reece; their known misses are removed when they pass.
- [ ] T1, T11 and T12 still pass; T2 re-read and reported to Reece with the seed table.
- [ ] Earlier guards green (PT-M3b's realisation guard, PT-M4's exodus spiral, PT-M7a's acceptance firm, PT-M5's T11 test); `make check-timing` green.
- [ ] New mechanisms have unit tests, their randomness a seeded test, and money and hours invariants Hypothesis property tests; any new stream is in `STREAM_IDS` and ADR PT-0012's table.
- [ ] Schema migration and `docs/data-dictionary.md` for any new persisted field (the rate card by practice, the hours policy, the difficulty fields if stored); `balance.yaml` keys with unit and intent.
- [ ] Golden snapshots and the state cache re-recorded, the reason in `CHANGELOG.md`.
- [ ] `make check`, `make e2e` and the nightly (`nightly.yml`, dispatched on the branch) green; merged with `Milestone-Tag: pt-m7b-done`.

## Manual check (Reece)

Start a hard game and play to 2010: the firm's card should start below the market's, the bank should warn months before a covenant breaks, and 2009 should cost a corporate-heavy firm real revenue.

## Decisions made

Recorded by the PT-M7b session (2026-11-21). "PT-M7" is PT-M7's recorded run (`docs/balance-run.md`); "brief values" is the first full run with every mechanism at the brief's numbers (a 65% card, hard at 0.7/0.5/-10/0.9, the pyramid at 2,400 hours); "PT-M7b" is `make balance` on the merge head (seeds 1-10, 132 turns, 90 runs), after merging PT-M17.

1. **The card's mechanism.** `firm.rate_card` holds each practice's share of the top card (bp). A new firm starts every practice at `rates.card.start_bp` times the difficulty's `card_mult_bp` (capped at the full card); each January (with the rate rise) a practice moves at most `step_bp` toward its target, `start + (1 - start) x min(1, rep / full_reputation)^curve`, where `rep` is the existing stand-in (`firm_reputation`, the best partner's familiarity). A practice's index is the rate index times its share; hours, blended rates, new matters' fees (RFP matters too, which had no index before) and the price term (`price_term(..., practice)`) read it. A save from before PT-M7b has an empty card and keeps the full card. **The fourth key** (`step_bp`, the most a share moves a year) is mine: the stand-in reputation saturates within about two years of work (familiarity tapers to 20), so a card that followed reputation alone would be back at the full card by 2007.
2. **The card cannot reach T3 or T4.** At the brief's 65% start, steady dissolved on 9 of 10 seeds within its first year (8 of 10 at easy, 10 of 10 at hard): with PT-M7's overhead ($13,300 a month a lawyer) an associate at 65% of the card costs more than they bill, so steady's growth rule spirals into its lockup. Starting share against steady (standard, seeds 1-10; the crisis and other mechanisms on): 6500: 90% dissolved, 11 lawyers median; 7500 (4 seeds): 50%, 41; 8500: 40%, 39.5, PEP $3.22M; 9000: 30%, 37.5, $3.08M; 9500: 10%, 52, $3.58M; 10000 (no card): 20%, 44.5, $3.40M. **A lower card makes a firm poorer, not bigger**: the price term's extra demand does not outrun the costs. Tuned `start_bp` 6500 -> 9850 and `step_bp` 250 -> 50 (T5 and PT-M4's exodus guard, decision 8); `full_reputation` 0.95 and `curve` 2.0 kept. **For Reece:** T3 (lawyers) and T4 (steady) stay known misses (proposed defaults below).
3. **Difficulty teeth** (`scenarios.yaml`, validated by `Difficulty`; standard has none). "Clients' starting loyalty" is read as the founders' clients' starting relationship scores (0-100, `books.start_relationship`), since the clients' 1-20 loyalty only sets drift. The brief's hard (books 0.7, revolver 0.5, loyalty -10, card 0.9) dissolved steady on 10 of 10 seeds, nearly all in its first year; tuned within the brief's directions to books 8500, revolver 7500, loyalty -5, card 9500. Easy books 12000 -> 11000 (larger books mean larger first-year budgets and draws: easy dissolved more than standard at 12000); revolver 15000, loyalty +5, card 10500 kept.
4. **The crisis** (`macro.crisis`; streams `crisis` 42 and `deal_collapse` 43, ADR PT-0012). Stress 0-1 is the larger of the collections index's rise above 1.05 (1 at 1.20) and the credit index's fall below 0.80 (1 at 0.35): October 2008 0.56, April 2009 1, July 2010 0.33, 2011 on 0. A client's factor is its price sensitivity / 10 x (1 + its sector's mix-weighted pro-cyclical shortfall). New engagements and each month's flow bill take `discount_bp` x stress x factor more discount (at most `discount_max_bp`); each matter or flow bill meets a write-down request with chance `ask_bp` x stress x factor (its size uniform in `writedown_bp`); a deal's p_close loses `close_k` logit points per unit of its driver's shortfall, and an open deal collapses in progress with chance `collapse_month_bp` per unit a month (a pulled deal: the relationship does not move). Tuning: discount 1200 -> 1000, ask 3000 -> 2500, collapse 2500 -> 300, close_k 2.0 -> 0.3 (at 1250-2500 bp of collapse pyramid and steady died in the crash on most seeds; at discount 1300 realisation fell to 83.8%, under T7, and easy dissolved on 2 of 10). Restructuring: `macro.estate_mult` 25 -> 15 and restructuring's beta -1.2 -> -0.8 (the brief's named levers; restructuring-heavy firms grew +40-70% in 2009 at -1.2).
5. **The CFO's forecast** (spec 8.7). Each month end records the drawn balance, partners' capital and cash on the P&L point; `fx.forecast_breach` fits the last `forecast_window` (6) months' trends (monthly fees, drawn less cash, drawn, capital), rolls the trailing 12 months' fees forward and returns the first covenant broken within `forecast_months` (6), or none (a covenant broken now is the headroom warning's). The inbox's `cfo_forecast` comes at most once a `cfo_warning_cooldown`; the Finance screen's revolver card shows it live; What next lists it; the scripts' bank rule (`BANK_WARNINGS`) and the heeded rocket read it. A firm with cash falling and nothing drawn is forecast to draw (the drawn-less-cash trend), which is the earlier warning a firm living off its capital needs.
6. **T9's keys:** `partnership.lateral.comp_of_book_bp` 3500 -> 2500 (a guarantee pays the full ask while only the portable share of the book arrives over 12-24 months; the rocket's three guaranteed laterals ate $4M a year). Tried and reverted: `arrival_months` [6, 12] (the rocket grew faster and dissolved on 7 of 10), `fee_bp` 1500 (no change to the heeded rocket), `forecast_window` 3 (no change).
7. **The hours policy.** `firm.billable_target_hours` (null: the levels' targets); each fee earner's fill is max(`plan_fill`, policy / their capacity) up to `staffing.policy_fill_max` (1.2), for the default rule's named plans and for flow. The pyramid's 2,400 hours dissolved it on 9 of 10 seeds (strain, errors and lost clients by 2011); it sets 2,300 (the brief's floor). It keeps PT-M7's 2,100-hour plan push as well.
8. **PT-M4's exodus guard** (`test_the_exodus_spiral`, heeded at most 1 of 10) read 3 of 10 at a 9500 card (main: 1). Rule 2: the guard's scripted response is "the CFO's warning heeded, as T9's script rule", and T9's rule now heeds the forecast, so the response reads `cfo_forecast` too (no change alone: 3 of 10); then my key: `start_bp` 9500 -> 9750 gave 2 of 10, 9850 gives 1 of 10 (the step and `full_reputation` did not move it: the guard's damage is in its first year, before any January step). PT-M3b's realisation guard and PT-M7a's acceptance firm pass; T12 (`make check-timing`) 159 ms.
9. **December comp rounds** (`moves.comp_round`): under modified lockstep (steady, pyramid, restructuring) an equity partner other than the founder whose market value is above what the firm pays them moves up the gate (two steps when 25% or more under); under committee their share moves up by the gap (at most the round's cap); pure lockstep (boutique) and eat what you kill (the rocket) have no lever.
10. **Seeds 11-40** (rule 4, the merge head): steady easy 1 of 30 (3%), standard 7 of 30 (23%), hard 8 of 30 (27%); the rocket 11 of 30 (37%), heeded 7 of 30 (23%). T5.easy's 2 of 10 on seeds 1-10 is seed variance (1 of 30); T9.heeded passes seeds 1-10 (1 of 10) but reads 23% on 11-40: its year-one deaths (decision 11) are structural.
11. **T9.heeded for Reece** (passes on 1-10, its row removed, but not robust): the rocket's first guaranteed lateral sinks it in months 4-6, before six months of trend exist to forecast, and its $1M capital call fails the partners' vote (a $1M call against founders' $300k capital accounts costs each voter more utility than the stress bonus gives; PT-M4's keys and T9's measure). Proposed default: the heeded rule asks the CFO before its first guaranteed lateral (no guarantee until the forecast is clear with six months of trend), or a call sized to pass.

**Targets (seeds 1-10):**

| Target | Band | PT-M7 | Brief values | PT-M7b | |
| --- | --- | --- | --- | --- | --- |
| T1 do-nothing fails | >= 9/10 | 9/10 | 9/10 | 9/10 (7 nominal) | pass |
| T2 no dominant strategy | <= 6/10 | steady 9, pyramid 1 | do-nothing 6 (most others dissolved) | steady 9, boutique 1 | **known miss, for Reece** |
| T3 steady lawyers | 100-250 | 53 | 11 | 50 | **known miss, for Reece** |
| T3 steady revenue | $60-150M | $63.9M | $0 | $57.3M | miss (not a known miss; $65.7M before merging PT-M17) |
| T4 PEP steady | $0.5-1.2M | $4.07M | $0 | $4.02M | **known miss, for Reece** |
| T4 PEP boutique | $1.0-2.5M | $2.24M | $0 | $2.00M | pass |
| T4 PEP pyramid | $0.7-1.6M | $1.80M | $0 | $3.19M | **known miss (above its bound), for Reece** |
| T5 steady dissolves easy / standard / hard | 0-10 / 5-20 / 20-45% | 0 / 0 / 0% | 80 / 90 / 100% | 20 / 10 / 30% | standard, hard pass; easy seed variance (decision 10) |
| T6 attrition | 15-25% | 19.9% | 26.5% | 20.5% | pass |
| T6 class to equity | 8-15% | 7.7% | 0% | 0% | accepted as noise in PT-M7 (one partner in a class of about 12; 8-9% on several tuning runs) |
| T7 realisation / collection / utilisation / lockup | 84-92 / 93-98 / 75-90% / 90-150 d | 87.4 / 96.5 / 84.9 / 123 | 87.0 / 96.4 / 81.9 / 117 | 84.4 / 96.5 / 83.6 / 126 | pass |
| T8 corporate-heavy 2009/2008 | -30% to -10% | -1.3% | -19.0% | -9.0% | **known miss (-11.1% at a 9500 card), for Reece** |
| T8 restructuring > 20% | -5% to +20% | +40.7% (n=3) | none | +31.1% (n=2-3) | **known miss, for Reece** |
| T9 rocket dissolves | 3-6/10 | 8/10 | 10/10 | 3/10 | pass |
| T9 heeded dissolves | <= 1/10 | 6/10 | 6/10 | 1/10 | pass on 1-10; 7/30 on 11-40 (decision 11) |
| T10 pyramid / steady burnout | >= 2x | 0.88x | 29.6x | 10.98x | pass |
| T10 steady burnout | <= 5% | 0.6% | 0.8% | 0.7% | pass |
| T11 rivals hold history | 0 misses, >= 8 kept | 0, 10 | 0, 10 | 0, 10 (worst 5.7%) | pass |
| T12 turn time | <= 250 ms | 148 ms | | 159 ms (`make check-timing`) | pass |

**For Reece (proposed defaults):**

- **T3 lawyers and T4 steady:** the card cannot get there with PT-M7's overhead (decision 2). Proposed default: keep the card near the full card and move T3 to 40-120 lawyers and T4 steady to $2.5-5M (Am Law 50 in 2015), as PT-M7 proposed; or give a new firm's costs a card too (overhead and salaries at the market's share a new firm can bill), which is a design change.
- **T2:** steady still wins 9 of 10 seeds (seed table below): it grows with its demand, keeps leverage at 4-5 lawyers an equity partner and now survives the crisis on 9 of 10 seeds. Proposed default: score T2 by PEP alone (boutique leads on PEP), or accept steady as v1's best strategy.
- **T4 pyramid:** $3.19M, above its band and above the row's bound (the 2,300-hour policy bills more; it printed FAIL, not a gate). At stronger crisis settings 6 of 10 pyramids dissolved in 2009-2010 and the median was $0. Proposed default: widen T4 pyramid to $1.0-3.5M, or a pyramid that lays off associates when its utilisation falls (a script rule).
- **T8:** corporate-heavy firms fall 9% (11% at a 9500 card, which broke PT-M4's exodus guard); a stronger discount pushes realisation under T7. Restructuring's reading is 2-3 small firms that caught an estate. Proposed default: accept -9% as within noise of the band, and measure T8 restructuring on firms with at least 10 lawyers.
- **T9 heeded:** decision 11.

**T2's seed table** (the founding partner's earnings, the December allocations summed over 2005-2015; $0 if dissolved), the merge head:

| Seed | do-nothing | boutique | steady | lateral-rocket | pyramid | Winner |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | $12.70M | $13.62M | $25.82M | $11.70M | $21.09M | steady |
| 2 | dissolved $0 | $11.53M | $47.91M | dissolved $0 | $34.16M | steady |
| 3 | $14.85M | $18.01M | $54.44M | $16.36M | $25.10M | steady |
| 4 | dissolved $0 | dissolved $0 | $32.38M | dissolved $0 | $30.27M | steady |
| 5 | $12.19M | $17.56M | $36.32M | $16.43M | $7.01M | steady |
| 6 | $11.87M | $15.20M | $42.34M | $9.58M | dissolved $0 | steady |
| 7 | $10.33M | $13.96M | dissolved $0 | $8.65M | dissolved $0 | boutique |
| 8 | $13.14M | $14.74M | $34.65M | $6.37M | $28.00M | steady |
| 9 | $12.35M | $14.02M | $28.94M | dissolved $0 | dissolved $0 | steady |
| 10 | $14.26M | $13.76M | $41.58M | $6.35M | $28.14M | steady |

Steady 9, boutique 1 (PT-M7: steady 9, pyramid 1); its measure is unchanged.

## Follow-ups

- The card's reputation: PT-M16's reputation and rankings should replace the stand-in (familiarity saturates within two years, so `step_bp` carries the pace).
- A pyramid (and any strategy) that lays off associates when utilisation falls; v1's scripts never shed staff, which is why the crash kills pyramids.
- T9's heeded rule asking the CFO before its first guarantee (decision 11), if Reece agrees.
- The CFO's forecast as a chart on Finance (the projected covenant headroom by month), and the forecast seeing known commitments (guarantees, capital returns) as well as trends.
- Hours policy by level or by practice (v1's is firm-wide).
