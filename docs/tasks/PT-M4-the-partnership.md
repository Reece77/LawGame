# PT-M4: The partnership

**Goal:** the firm is a partnership. Partners contribute capital, draw and are trued up; profit is shared by the chosen comp system; PEP is real; partners' confidence in the managing partner rises and falls; December brings the partnership vote and up-or-out; lateral partners arrive with books and guarantees; partners leave, and a firm can spiral into dissolution.

**Spec:** §2.5 (MP election only), §5.5, §8 (except offices and mergers) · **ADRs:** PT-0003, PT-0007, TST 0018 §4 (game-over states, adapted) · **Streams:** `vote`, `lateral`, `partnership` (17), `poach` (19) · **Depends on:** PT-M3b · **Lane:** A

## Out of scope

Seats, the executive committee and automation (v2); mergers (v2); succession beyond the election's hand-over choice (v2's PT-M17 ports TST §45).

## Sub-tasks (commit after each)

1. **Capital and draws** (spec §8.4): capital accounts, admission funding, capital calls (vote), returns after departure; monthly draws; December allocation and the true-up; retained reserve.
2. **Revolver and covenants** (TST §20.3's pattern): sizing by WIP and receivables, covenants including partner-departure share, breach events; insolvency and dissolution (TST §14.7 adapted).
3. **Comp systems** (spec §8.5): lockstep, modified lockstep, eat what you kill, committee discretion, two-tier; the December comp round (an action screen); satisfaction against contribution and market value.
4. **PEP and KPIs** (spec §8.1–8.2): PEP, leverage, margin, RPL; Explain decomposition of PEP.
5. **Confidence and votes** (ADR PT-0007): monthly confidence, the whip count with ranges, the vote engine (utility, noise, lobbying), the partnership agreement as data with a vote to change terms.
6. **Up or out and the December vote** (spec §5.5): eligibility, sponsors, business cases, equity and income admissions, counsel, departures to in-house roles (alumni flag for v2).
7. **Lateral partners** (spec §5.7): books as ranges, diligence, conflicts import (ADR PT-0009 §4), guarantees (account 2700), portability realised over 12–24 months.
8. **Partner flight** (spec §8.7): the monthly chance, approaches from the static panel firms (rivals proper arrive in PT-M5 and reuse this), counter-offers, clients following, contagion.
9. **The MP election** (ADR PT-0007 §3): term, no-confidence petitions, the election, losing (stay as partner, or hand over to a chosen partner and play them), ironman.
10. **Screens:** Partnership (partners, points, comp, contribution, market band, confidence; the agreement; votes; comp season), Finance additions (capital accounts, draws, revolver); e2e: hold a December vote and admit a partner; survive a lateral departure.

## Acceptance criteria

- [ ] Capital accounts, draws and true-up balance (property tests); spec §8.1's worked example reproduced exactly.
- [ ] Under eat what you kill, a top originator's comp is at least 2× the median partner's; under pure lockstep, at most the plateau ratio (printed).
- [ ] A scripted exodus (three partners from one group in 6 months, with guarantees outstanding and the revolver drawn) dissolves the firm on at least 3 of 10 seeds without intervention, and on at most 1 of 10 with the scripted response (balance target T9's mechanism).
- [ ] Losing an MP election never ends a standard game; dissolution does.
- [ ] No partner's portability, true vote utility or confidence number reaches the API (ranges and labels only).
- [ ] `make check` and e2e green; `Milestone-Tag: pt-m4-done`.

## Manual check (Reece, the first full playtest)

Play 2005–2009 from the `biglaw_spinout` scenario. Make your first partner in December 2008 while the crash bites.

## Decisions made

## Follow-ups
