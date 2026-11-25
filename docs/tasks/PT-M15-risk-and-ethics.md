# PT-M15: Risk and ethics

**Goal:** mistakes and misconduct cost something. Escaped errors and aggrieved litigation clients become malpractice claims with visible stages, a hidden merit and size, defence costs and an insurer. Insurance renews each year by claims history, revenue and practice mix, and the excess over the limit falls on the partnership. Lawyers face disciplinary cases driven by their hidden integrity and reduced by supervision and the general counsel's checks; regulators can sanction the firm where its systems failed. The client book is reconciled monthly, and a trust-account shortfall is always critical. Clients audit bills against their guidelines, and disputes go to fee arbitration. A firm that cuts corners earns more for a while and pays for it.

**Spec:** §11.3 (malpractice and insurance), §11.4 (discipline), §11.6 (billing disputes and audits), §7.6 (errors), §7.7 (bills and disputes), §9.1 (the general counsel's seat), §12.1 (a public claim lowers reputation) · **ADRs:** PT-0003 §7 (client money), PT-0005 (hours), PT-0010 (bar rules by jurisdiction), PT-0012, PT-0013 (real people) · **TST to port:** formulas.md §48's case machinery (investigations with visible stages, settle or contest, fines to `6970_fines`; `tst/sim/regulation/`) and §11.6's dispute events · **Depends on:** PT-M7c (`pt-m7c-done`); replaces PT-M11's flat England and Wales insurance cost · **Lane:** C (beside PT-M12 in lane A and PT-M13 in lane B)

## Lane

- **Owns:** `ptk/sim/risk/` (new: claims, insurance, discipline, regulators' inquiries, trust-account reconciliation, billing audits and fee arbitration), `risk.*` keys in `balance.yaml`, `insurance.yaml` (insurers and their terms), the disciplinary process fields in `bar_rules.yaml`, billing disputes and audits in `ptk/sim/billing/` (funding is lane A's), the general counsel's seat effect on checks, `data/events/risk.yaml` (templates), the Risk screen, ADR **PT-0017** (claims, insurance and discipline; the real-people rule's enforcement), RNG ids **140-149**.
- **Must not edit:** practices data and `ptk/balance/` (PT-M12, lane A: register a strategy in a new module with one line and ask for re-reads); `ptk/sim/mergers/` (PT-M13: a merged firm inherits the other side's open claims through the hook it leaves).
- **Shared files:** keep both sides; re-chain migrations if another lane merged first. `ptk/sim/matters/progress.py` already records escaped errors: read them through `interfaces.py`, do not change error chances (balance is lane A's).

## Out of scope

Workplace-conduct cases beyond their professional consequences (spec §11.4 keeps them to HR and the GC; no private-life detail); criminal prosecution of anyone; ABS and outside ownership (v3).

## Sub-tasks (commit after each)

1. **Research dossier** `docs/research/risk-and-ethics.md` (sources, S/D/A): malpractice claim frequency and severity for large firms (the ABA's Profile of Legal Malpractice Claims, ALAS and broker reports), claims by practice and cause, defence costs and time to resolution, premium levels per lawyer and how they moved after 2008, typical limits and deductibles, England and Wales's minimum terms (PT-M11 has them) and the SRA's sanctions on firms, US disciplinary rates and outcomes, trust-account rules (US IOLTA, the SRA Accounts Rules), e-billing guideline reductions and fee-arbitration rates. **ADR PT-0013:** aggregate statistics only; no real person named in any case.
2. **Claims** (spec §11.3): from escaped errors (each with a delay before it surfaces) and from a share of lost high-stakes cases; each claim a case with visible stages (notice, investigation, defence, settlement or trial), a hidden merit and size, defence costs and the insurer's part; a public claim lowers reputation in that practice (PT-M16's reputation). **Test:** with no escaped errors and no lost cases there are no claims (property test).
3. **Insurance:** a policy (insurer, limit, deductible, premium) renewing each year by claims history, revenue and practice mix, with mutual and commercial insurers; the deductible and any excess over the limit fall on the firm, and an excess the firm cannot pay is a capital call on the partners (PT-0003). England and Wales offices' compulsory cover takes PT-M11's minimum terms. **Property test:** each claim's payments equal the insurer's share plus the deductible plus the excess, and every entry balances.
4. **Discipline** (spec §11.4): cases against lawyers for billing padding by a rule-bender, conflicts violations, trust-account misuse, misleading the court and failures of supervision; the chance from hidden integrity, reduced by supervision and the GC's checks; outcomes from dismissal to disbarment (capacity lost, or the person leaves); regulators' inquiries into the firm where its systems failed, with fines to `6970_fines` (the SRA for London offices). **ADR PT-0013:** a person flagged `real` is never the subject of a case, a claim's blame or a negative event; they are excluded where subjects are drawn (test over 30-year runs).
5. **Trust accounts** (PT-0003 §7): a monthly reconciliation of the client book; a shortfall (from misuse or an error) is a critical event and a disciplinary matter; the client book never mixes with the firm's (the ledger already enforces it; add the reconciliation and its events).
6. **Billing audits and disputes** (spec §11.6): clients' e-billing audits against their outside counsel guidelines reduce bills by rule; disputes arise from overruns, guideline breaches and padding found; fee arbitration where the bar provides it; public disputes harm reputation.
7. **The general counsel's seat and the risk area:** the GC's skill sets the checks' strength (conflicts, intake, billing review); PT-M9's automation gains a risk area whose rule sets cover and handles routine claims within limits.
8. **Strategies and readings:** register a `cowboy` strategy (steady with lax supervision, no GC and rule-bending laterals) against steady; lane A re-reads T1-T12 with claims and insurance on.
9. **Screens:** Risk (claims with stages, the policy and its renewal, disciplinary cases, the trust-account reconciliation, audits and disputes), risk items in Needs you; e2e: a claim from an escaped error goes through its stages to settlement under the policy, and a trust-account shortfall raises a critical event.

## Acceptance criteria

- [ ] Claims arise only from escaped errors and lost high-stakes cases (property test); claim frequency per 100 lawyers a year for steady is within the dossier's band (printed on seeds 1-10; the band in `balance-targets.md` as T14, proposed by the session for the product manager's approval).
- [ ] Premiums per lawyer within the dossier's band for a firm of steady's size (printed); a firm with worse claims history pays more at renewal (test).
- [ ] Claim payments reconcile with insurer, deductible and excess, and an unpaid excess becomes a capital call (property test).
- [ ] The `cowboy` strategy has at least twice steady's claims and disciplinary cases over 2005-2015 on at least 8 of 10 seeds, and lower PEP by 2015 on at least 6 of 10 (printed and gated).
- [ ] No person flagged `real` is ever the subject of a claim's blame, a disciplinary case or a negative risk event (test); no hidden value (merit, size, integrity) reaches the API or a prompt (test).
- [ ] T1-T12 re-read by lane A with before and after values; no new miss without a row authorised by Reece or the product manager.
- [ ] T12 (≤ 250 ms) holds at December 2025.
- [ ] `make check`, `make e2e` and the nightly run green; `Milestone-Tag: pt-m15-done`.

## Manual check (Reece)

From `pt-2008`, hire a rule-bending lateral without a GC in the seat, play to 2012, and watch the Risk screen.

## Decisions made

1. **Player firm only.** Risk runs for the player's firm, in phase 6 after payroll (`ptk.sim.risk.phase`); rivals' risk stays inside their pinned economics (PT-0008). `risk.enabled: false` turns it all off. Recorded in ADR PT-0017 (proposed).
2. **Sub-tasks 3-6 in one commit:** they share the action module and the phase; no split imports on its own.
3. **Claims.** Only two sources: the month's rise in a matter's `errors_escaped` (read from state; `progress.py` and its error chances are untouched) and a lost case with stakes of at least $5M. **One open claim a client** (a client with a claim open or on its way makes no second: it sues once; later escapes join it): without it a strained matter, or a big client's many matters, made a dozen claims in a few months and steady's counts swung 0-32 by seed. Conversion `from_error_bp` tuned 600 -> 900 -> 500 -> 700 -> 600 -> **800** (steady escapes 30-70 errors a 100 lawyers a year); the GC's weight on claims and discipline `gc_bp` 4000 -> **7000** (a vacant seat x1.35, a strong GC x0.3).
4. **Claims-made policy, defence within limits, per-claim limit and deductible.** The firm's part goes to a new account `6310_claims`; a part its cash cannot cover is paid in as capital by the equity partners by points (no vote: the claim is owed), mirrored in the founder's book by PT-M17's capital tracking.
5. **The premium replaces two older costs:** PT-M7's per-lawyer insurance overhead ($800 a lawyer a month, `pay.overhead_per_lawyer_cents.insurance`, kept in the YAML but skipped while risk is on) and PT-M11's flat England and Wales premium (`geo.offices.insurance_entry`, skipped while risk is on). A London office now raises the policy's limit to the minimum terms (an LLP's £3M) instead. Premium = fees x the market's dated rate (130 bp in 2005 to 140 bp in 2025, `insurance.yaml`) x practice mix x experience modifier x terms. Modifier bounds 0.75-2.5 -> 0.8-2.0, loss weight 0.30 -> 0.15 (at the first bounds steady's premium reached $17k-$30k a lawyer after a bad run).
6. **Discipline.** Formal cases (not every complaint): neglect 3 bp and court 4 bp a lawyer-month at integrity 10, by exp(1.6 x (10 - integrity)/10), x3 rule-bender, x2 cowboy; outcomes by culpability band (admonition, reprimand, suspension, disbarment). US bars do not fine lawyers here; England and Wales' `individual_fines` is recorded in bar_rules.yaml for later. A suspended lawyer stays on the books with no billable capacity (`interfaces.suspended`, read in `staffing.fee_earners`).
7. **Regulators:** New York's grievance committees can discipline firms but not fine them (fine cap 0: a censure and its reputation cost); the SRA's fines are capped at a game $500k (the Tribunal's are unlimited; the dossier's corrected cap dates are in bar_rules.yaml's note).
8. **Trust shortfalls are made good the same month** from firm cash (`6320_trust_shortfalls`), with a `C1900_shortfall` line in the client book on both sides, so PT-0003 §7's invariant (bank = owed at every month end) still holds; the critical event follows next month. The engine-queued `trust_shortfall` and `malpractice_claim` templates moved from `regulatory.yaml` to `data/events/risk.yaml` with wording and effects that do not charge the shortfall twice.
9. **Lax supervision** is a firm policy (`SetSupervision`): it frees `risk.policy.lax_hours` of each partner's non-billable hours a month and multiplies claims, discipline and misuse (x2). Tuned for the brief's cowboy criterion (rule 1, my keys): `lax_hours` 15 -> 5 (at 15 the freed capacity kept steady's hiring rule from hiring and cowboy dissolved on 4 of 10 seeds), claims' `lax_mult` 1.6 -> **3.0**, discipline's 2.0 -> **6.0**. Readings (seeds 1-10, final keys): cowboy has at least twice steady's claims and cases on **8 of 10** and lower PEP in December 2015 on **6 of 10** (both gated nightly at the brief's thresholds, and passing at them: seeds 4 and 9 are steady's busiest claim years). The catch rate in `progress.py` is not touched (the brief: error chances are lane A's).
10. **`cowboy`** (`ptk/balance/risk.py`, one line in `strategies.VARIANTS`): steady with lax supervision, the GC seat vacated each month after PT-M8's fill-seats step, conflict checks off, and steady's lateral partner step replaced by one without diligence that judges the book by the top of its range ("rule-bending laterals": scripts see only what the player sees, so the hidden rule-bender tag cannot be chosen).
11. **Fee arbitration** comes only from a dispute the firm held and won (the client goes further); the filing is the hold action's own draw, the award stream `arbitration`'s.
12. **T14 proposed** (for the product manager's approval): claim notices per 100 lawyer-years 2006-2015, median of steady's seeds 1-10, band **1.5-5.0** (the dossier's 2-4 notices for a 50-250 lawyer firm, widened because a 30-90 lawyer firm's 10 years give 3-60 notices). Premium per lawyer in December 2015 within the dossier's $5k-$10k (gated nightly beside it). Readings (final keys): T14 median **1.72** notices a 100 lawyer-years (per seed 0.0-6.5), premium median **$9,434** a lawyer ($8.5k-$18.9k); cowboy 2x on **8 of 10**, lower PEP on **7 of 10**.
13. **Premium rates x1.35** (`insurance.yaml`, 130-145 bp -> 175-195 bp), rule 2: with the first rates a steady firm's premium (~$7k a lawyer) was below the $9.6k-a-lawyer overhead it replaced, and the nightly read T9.rocket 7/10 (main 5/10, band 3-6). At the new rates T9.rocket reads 5/10 on seeds 1-10.
14. **T2 and T5.standard on seeds 1-10 are seed variance (rule 4):**

    | Target | seeds 1-10, branch | seeds 1-10, main | seeds 11-40, branch | seeds 11-40, main | band |
    | --- | --- | --- | --- | --- | --- |
    | T2 (most wins) | steady 9 | steady 5 | steady 16/30 (53%) | steady 19/30 (63%) | at most 60% |
    | T5.standard | 0/10 | 2/10 | 2/30 (6.7%) | 2/30 (6.7%) | 5-20% |
    | T9.rocket | 5/10 | 5/10 | 16/30 (53%) | 14/30 (47%) | 30-60% |

    On seeds 1-10 steady survives seeds 4 and 9, which it lost on main, and pyramid's claims and premiums cost it the seeds it won. Rule 3 forbids adding known-miss rows myself: the rows are Reece's or the product manager's to authorise.
15. **Practice save `pt-risk`** (the e2e): `pt-2008` with a claim walked to the claimant's offer, a second surfacing next month and a shortfall, staged through the engine with the chances forced (`ptk.practice.risk_demo`).

## Follow-ups

- Lane A (PT-M12): re-read T1-T12 with claims and insurance on (premiums replace the per-lawyer insurance overhead; claims, audits and fines move cash), before and after values to this brief.
- PT-M13: a merged firm should take over the other side's open claims (`RiskState.claims` by firm id) and their policy history.
- PT-M16: a public claim, sanction or fee suit could make a press moment (now a reputation pulse only).
- An excess layer (a tower of policies) and the annual aggregate limit; tail cover when a partner leaves; the mutual's assessments in a bad year.
- England and Wales: the SRA's individual fines and the Legal Ombudsman's fee complaints; the Assigned Risks Pool (closed 2013) for a firm no insurer will take.
- Workplace-conduct cases (spec 11.4), kept out of scope by the brief.
