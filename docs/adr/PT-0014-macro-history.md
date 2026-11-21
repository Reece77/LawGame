# ADR PT-0014: The macro history to 2015 and history's client failures

- Status: **Accepted** (PT-M7 session, 2026-11-21; engineering decisions under CLAUDE.md §11)
- Context: spec §6 (demand), §14 (history and eras); the PT-M7 brief's sub-task 1 and the product manager's additions (2026-11-20)

## Decision

1. **Indices as dated points.** `backend/data/macro_history.yaml` holds the macro and legal indices (1.0 = the 2005 average) as points at dated months, interpolated linearly between points and held after the last. Mid-year points carry annual figures; extra points carry the 2008 crash's timing. Sources and derivations are in `docs/research/v1-macro.md`. The seeded AR(1) cycles to 2034 are PT-M10's; until then 2015's values hold.
2. **Demand** follows spec §6: `D0 x G x max(floor, 1 + beta_scale x beta_p (I_p - 1)) x eps`. Each practice names its driver series (`practices.yaml` `index`). Where the spec gives a counter-cyclical beta (< 0), the practice reads a pro-cyclical index so the spec's sign holds: restructuring reads `credit` (the square root of 2005's default rate over the year's), litigation and employment read `cycle`.
3. **Collections stress** multiplies clients' days to pay; **lateral heat** multiplies associates' resignations and partners' market value (V_mkt); the **market's rate rise** each January is the year's `rate_rise`. Weights are in `balance.yaml` `macro:`.
4. **Real clients' failures are dated data,** not draws: `clients.yaml` `fails: {ym, kind, src}` on real clients only. A **bankruptcy** (a Chapter 11 filing or a seizure) stops the firm's open work for the client outside restructuring (closed as collapsed), writes its open bills off as bad debts in every month from the filing (so final bills are lost too), and for `estate_months` turns its wallet into restructuring work only (`estate_mult` x its weight); a firm with the client on its books and a restructuring lawyer is instructed in restructuring. A **rescue** (a distressed sale) pays its bills and ends its wallet `rescue_months` later. Wallets are renormalised, so failures move work between clients and never out of the market. No new random stream.
5. **Real companies that kept operating** (Fannie Mae, Freddie Mac, AIG) do not fail; companies whose story begins before 2005 (UAL) are left as they are.

## Consequences

- Every save's demand, collections and lateral market now follow 2005–2015 history; golden snapshots were regenerated (CHANGELOG).
- `clients.yaml` gains Chrysler (appended, so generated clients' ids move by one).
