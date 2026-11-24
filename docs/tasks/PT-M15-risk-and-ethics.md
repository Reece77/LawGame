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

(The session records its decisions here.)

## Follow-ups

(The session records follow-ups here.)
