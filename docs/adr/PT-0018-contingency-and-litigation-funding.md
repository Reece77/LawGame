# ADR PT-0018: Contingency cases off the books until recovery; litigation funding as a non-recourse liability

**Status:** Accepted (PT-M12, 2026-11-25). Extends ADR PT-0003 (partnership accounting, the client book) and PT-0005 (WIP at standard value). Numbers PT-0016 and PT-0017 are reserved for PT-M13 and PT-M15.

## Context

Spec §7.7: a contingency case's fee is a share (25-40%) of the recovery; the firm funds the case, carrying years of WIP with no bill; from about 2010 litigation funders can share the case. PT-M3b posted every matter's WIP to fees (debit 1100, credit 4000) as it was worked, provided 50% of contingency WIP and reversed it on a loss. With plaintiff mass torts (PT-M12) contingency is a practice's main model, and the brief asks that a contingency case's WIP post no fee until its recovery, that a funded case's loss cost the firm only its unfunded WIP, and that recoveries pass through the client book before the firm's fee.

## Decision

1. **Contingency WIP is off the books.** A contingency engagement's hours are valued at standard (the engagement's `wip_cents`, the KPIs' worked value) but post nothing to the ledger: no 1100, no 4000, no WIP provision. `kpis.wip_cents` (lockup, the partnership's WIP) excludes it; `kpis.contingency_wip_cents` reports it.
2. **Recovery.** At the close, a recovery (a win: `billing.recovery_bp` of the stakes; a settlement: the offer) is received into the client book (C1000 / C2000). The fee (`share_bp` of the recovery) is billed at standard 0 to 4100 and transferred from the client book to the firm at once; the rest is paid out to the client. A loss or a disqualification posts nothing.
3. **Funding.** From `billing.funding.from_ym` (January 2010) a funder offers terms on each open, unfunded contingency case (stream `funding`, 120, keyed by the matter at its opening month): it advances `funded_bp` (50-75%) of the case's WIP at standard, at once for the WIP to date when the firm accepts (`AcceptFunding`) and each month after. Advances are a **non-recourse liability**, account **2800 Litigation funders' advances** (debit cash, credit 2800).
4. **The waterfall at the close** (`ptk.sim.billing.funding.close_funding`): the funder is paid first, out of the firm's fee, `return_bp` (2-3x) of its advances, never more than the fee. Of what it is paid, the advances' part clears 2800 and the rest is a funding cost (**6750 Litigation funding costs**). What the funder does not recover of its advances it bears: the advances are released to income (**4400 Funded fees**), so a funded loss leaves the firm with the advances against the unfunded WIP's cost. The month's totals record `funder_paid_cents` and `funded_released_cents`; accrual revenue (`fees_cents`) includes 4400.
5. The firm never runs a funding arm of its own (spec §18, v3) and funders do not appear as entities: the offer is terms, not a party.

## Consequences

- PT-M3b's contingency provision key (`billing.contingency_ev_bp`) no longer applies to contingency engagements (kept for its readers); v1's case mix keeps 10% contingency, whose revenue now arrives at the recovery rather than with the hours, so a firm's revenue timing on those cases changes (golden snapshots regenerated, CHANGELOG).
- A save made before PT-M12 with an open contingency case has its WIP on 1100; PT-M12's saves are incompatible with earlier ones in any case (twenty practices' familiarities), so no migration is written.
- Engagements carry `funded_bp`, `funder_return_bp`, `advances_cents` and `funded_turn` in their JSON row (no schema change).
