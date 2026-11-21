# PT-M17: The founding partner's life, family and succession

**Goal:** the founding partner has a life outside the firm: a persona that the firm's choices shape, a personal account with draws, a capital loan, investments and tax, influence in the profession, a family, and an end. At retirement, an election loss or by choice, the player hands the firm to an elected successor and plays them, while the founder becomes senior partner and then a retired partner with an annuity.

**Spec:** §2.2–§2.5, §8.4 (retired-partner annuities), §8.6 (mandatory retirement in the agreement) · **ADRs:** PT-0003 (the personal book is separate; account 2600), PT-0007 §3–§4, PT-0013 (no private-life events for real people) · **TST to port:** formulas.md §32 (stress is PT's strain; persona §32.4; personal book §32.2; foundation §32.3; influence §32.5; legacy §32.6), §45 (family, children, education, estate, adviser, heirs, succession); `tst/sim/founder/` and `tst/sim/family/` · **Depends on:** PT-M7 (`pt-m7-done`) · **Lane:** C (beside PT-M7b in lane A and PT-M8 in lane B)

## Lane

- **Owns:** `ptk/sim/founder/` and `ptk/sim/family/` (new packages), personal accounts (codes beginning 9, the founder's book, kept apart by the ledger's existing rule), account 2600, the Founder and Family screens, `founder_life.*`, `family.*`, `succession.*` keys, RNG ids **50–59**.
- **Must not edit:** `ptk/sim/partnership/` (PT-M7b may tune it), `ptk/sim/org/` (PT-M8), `ptk/sim/billing/`, `ptk/sim/macro.py`.
- **How you reach the partnership:** read the founder's draws, true-up and allocation from the partnership's state (they exist from PT-M4) and post the mirrored personal entries in your own phase-7 step; run the succession election and the retirement-age vote through PT-M4's vote and election functions, exposed in `ptk/sim/interfaces.py` (add thin wrappers there, not changes inside `partnership/`). If a needed function is private, add a public wrapper in `interfaces.py` and record it in "Decisions made".
- **Shared files:** keep both sides; re-chain migrations if another merged first.

## Out of scope

Dynasty mode (v3), the founder's judicial appointment and government service (spec §19 ideas), pro bono's Beloved trait effect beyond the persona rule below, press (PT-M16).

## Sub-tasks (commit after each)

1. **The personal book** (TST §32.2): personal cash, investments, the capital loan (the founder's capital funded by a bank loan in their own book, ADR PT-0003 §5) and tax at `personal.tax_rate` on the founder's profit share; draws and the true-up arrive as mirrored personal entries. Property test: no 9-account ever appears in a firm entry; the personal book balances.
2. **Persona** (TST §32.4): Visionary, Ruthless, Beloved, Reckless, raised by firm choices (spec §2.3's list: de-equitisations, hostile laterals and layoffs; pro bono, raises and comp fairness; new practices; guarantees, revolver leverage, broken public claims). Effects as TST's, on partner confidence and recruiting.
3. **Foundation, influence and legacy** (TST §32.3, §32.5, §32.6): the foundation with an access-to-justice cause; influence as bar politics (the bar association, committees); legacy score from the firm, the name on the door, the foundation and the family.
4. **Family** (TST §45.1–§45.3, §45.6): partner, children, education, estate tax, the family office and the adviser. Life events apply only to the player's own generated family, never to a person flagged real (ADR PT-0013 test).
5. **Mandatory retirement and annuities** (spec §2.5, §8.6): the agreement's `retirement_age` (default 65, changeable by vote through the interface); from 60 the partnership expects a succession plan (a confidence term through `interfaces.confidence_change`); retired partners' annuities as the agreement grants (default none; if granted, a share of the retiree's last allocation for 10 years), booked to 2600 and paid monthly.
6. **Succession** (spec §2.5; TST §45.5): the player names a successor among equity partners (a child who made partner is eligible); the partnership elects them (PT-M4's election through the interface; a weak candidate can lose to a rival nominee); the player then plays the successor as MP: the save's player person changes, energy and persona reset to the successor's, the old founder becomes senior partner (an adviser with opinions, TST §45.5) until retirement. Triggers: by choice, at mandatory retirement, after a lost MP election (ADR PT-0007 §3), on health grounds (TST §45.5). Ironman: a lost election ends the game.
7. **Screens:** Founder (persona, personal account, influence, legacy, foundation) and Family; the succession flow (choose a successor, see the predicted vote range, confirm); e2e: retire the founder at 65 with a successor elected, and play on as the successor.

## Acceptance criteria

- [ ] The personal book balances every month and never mixes with the firm's (property tests); the founder's after-tax income equals their draws and true-up less tax (reconciliation test).
- [ ] Persona traits move with the listed choices and their effects match TST §32.4's worked examples in PT units.
- [ ] A succession hands play to the successor with no change to the firm's state other than the MP seat, the player flag and the founder's status (state-diff test); replay is identical.
- [ ] No family or life event ever selects a person flagged real (test); no hidden value reaches the API or a prompt (test).
- [ ] Annuities post to 2600 and are paid from cash; the balance sheet balances with them.
- [ ] `make check`, `make e2e` and the nightly balance run green, or any changed target recorded with its before and after values; `Milestone-Tag: pt-m17-done`.

## Manual check (Reece)

Start a campaign with a founder aged 50, set Holiday to 2020, and hand over to a successor at 65.

## Decisions made

## Follow-ups
