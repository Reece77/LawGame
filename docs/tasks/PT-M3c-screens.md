# PT-M3c: Matters, clients and practices screens

**Goal:** the player can see and run the game's heart: named matters with a staffing board, clients and their relationships, practices and their demand.

**Spec:** §16 (Matters, Matter, Clients, Client, Practices, Business development in part) · **Depends on:** PT-M3a; PT-M3b for the money columns · **Lane:** C

## Sub-tasks (commit after each)

1. **Matters list** (TanStack, saved views): client, practice, lead, phase, budget against actual, hours this month, WIP, billed, realisation, risk.
2. **Matter page:** the staffing board (people with free capacity and familiarity in the practice; drag to assign; hours per month; strain warnings), phase timeline, bills, events, settlement offers.
3. **Clients list and client page:** wallet estimate (a range), our share, relationship, relationship partner, practices used, panel status, GC (revealed), cross-sell map with an Introduce action.
4. **Practices screen:** demand trend, our revenue and share, capacity, utilisation, leverage, rates against the rate card.
5. **Explain** on utilisation, realisation, matter margin and win probability (as a band, never the number).
6. **Playwright:** staff a new named matter, bill it, see realisation; introduce a colleague to a client.

## Acceptance criteria

- [ ] No business logic in the front end; every number formatted from the API.
- [ ] The staffing board refuses an over-capacity assignment with the engine's error, and shows conflicts as the engine reports them.
- [ ] `pnpm lint && typecheck && test` and e2e green; `Milestone-Tag: pt-m3c-done`.

## Decisions made

1. **Read views in their own module.** `ptk/api/screens.py` holds the new read endpoints (`getStaffingBoard`, `listPracticesScreen`, `explain`); `ptk/api/matters.py` gains only view fields (a matter's `risk` and `risk_notes`, a client's `share_estimate` and `panel_status`). Nothing in `ptk/sim/` changed; every rule (capacity, conflicts, waivers, introductions) stays the engine's, and its errors are shown as sent.
2. **Staffing board.** Everyone who is a fee earner at the firm, team first, then by free hours. `free_hours` is exactly what the engine's capacity check accepts (`matters.max_load` x capacity, less partners' other hours, less planned named hours; a test assigns `free_hours` and `free_hours + 1`). Warnings: burnt out; strain at or above 60 (the strain bar's warning band, `lib/attr.ts`); planned named hours plus other hours above capacity (overtime). Drag a card onto the team (HTML5 drag and drop) or press Add; the hours come from the board's "Hours a month" input (20 by default).
3. **Outlook as a band (Explain "win probability").** Early case assessment is not built (PT-M3a's follow-up), so the band comes from the team's craft *as the firm sees it*: each member's revealed ranges for the kind's craft skills (`outcomes.craft_skills` or `deal_skills`) times the familiarity factor of their revealed familiarity range, weighted by planned hours; the range's midpoint against a typical opposing counsel (`outcomes.opposing_mean`) with even merits (cases) or `p_close` with the matter's critical flag (deals). Bands: Uphill under 30%, Leaning against under 45%, Even under 55%, Leaning our way under 70%, Strong above. Only the band and the team's craft range are sent, never a number; a test shows changing merits or opposing counsel never moves it. Advice and filings have no outlook.
4. **Matter margin** (Explain): last month's hours on the matter at standard value less their salary cost (salary / the level's yearly capacity hours, per hour). Founding partners draw no salary until partnership economics (PT-M4); overheads are not allocated.
5. **Utilisation** (Explain, spec 8.2 "billed ÷ capacity"): last month's hours worked (named and flow) over monthly capacity, for a person, a practice's home people or the firm. Realisation (after merging PT-M3b) is PT-M3b's own figure from `/finance/matters` (billed over the standard value of the work those bills relieved), with billed, collected, unbilled WIP and the pending write-down as its drivers.
6. **Risk** (matters list): from what the firm sees: past due, missed deadlines, over the hours budget, behind the planned pace, nobody staffed, critical. High if past due, a missed deadline or nobody staffed, or three notes; medium with one or two; closed matters are low.
7. **Client share and panel status.** Our share is the trailing 12 months' fees over the wallet estimate's range (both at standard value), so it is a range too. Panel status: key (a key client), active (instructed in the last 12 months) or dormant.
8. **Practices screen.** The demand trend recomputes the market's demand for the months played (up to 12) from the same seeded draws the turn made (`monthly_demand` is a pure function of the seed and month), so no history table is needed. Revenue is our standard value of work last month; share is that over the market's demand; leverage is non-partner fee earners per partner (home practice) against the practice's norm; "ours" against the rate card is the standard value per hour by band last month.
9. **Saved views** live in the browser's `localStorage` (TST keeps them in `saves/ui_settings.json` through an API that Partner Track does not have yet); shared by every save.
10. **Money columns from PT-M3b.** The Matters list joins `listMatterMoney` by matter id for WIP (unbilled, falling back to PT-M3a's standard value before terms are set), billed and realisation; the matter page shows the billing model, billed, collected, money on account, the pending write-down (with the write-down action) and the matter's open and recent bills. No number is computed in the front end.

## Follow-ups

- Early case assessment (merits as a range) would let the outlook band use merits; until then it assumes even merits.
- Saved views could move to a UI-settings endpoint (as TST's `saves/ui_settings.json`) so they survive a browser change.
- The matter page shows only bills the state holds (open, and closed since last month); a per-matter bill history would need a read of `billing_io`'s stored bills.
- Matter margin could use billed value and partners' notional cost once PT-M4 sets partner comp; overheads are not allocated.
- Glossary terms on table headers (TST's `Term`) once Partner Track has a glossary.
