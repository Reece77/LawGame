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

## Follow-ups
