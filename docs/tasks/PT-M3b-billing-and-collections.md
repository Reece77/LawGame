# PT-M3b: Billing and collections

**Goal:** hours become money exactly: WIP at standard rates, bills by billing model, write-downs, receivables and collections, with disputes and late payers, so realisation, collection and lockup are ledger facts.

**Spec:** §7.7, §8.2 · **ADRs:** PT-0003 §2–§3, §7 (client book), PT-0005 · **Streams:** `billing` · **Depends on:** PT-M3a's sub-task 4 (matters exist) · **Lane:** B

## Lane

- **Owns:** `ptk/sim/billing/`, accounts 1100–1300, 2200, 4000–4200, 6700; the client book.
- **Must not edit:** matter progress and staffing (PT-M3a); it reads matters through `ptk/sim/interfaces.py`.

## Sub-tasks (commit after each)

1. **WIP posting** from hours × rates (ADR PT-0005 rounding), per (person, matter, month).
2. **Billing models:** hourly, blended, capped, fixed (by progress), success, contingency (WIP held, no bill until recovery), retainer (deferred income).
3. **Bills** on cycles; partner write-downs (an action and a default rule); guideline rejections by client.
4. **Collections:** days-to-pay by client, stress from macro (a constant until PT-M7), bankruptcies' write-offs, the bad-debt provision.
5. **Disputes** as pending items (TST ADR-0014) with outcomes; rule-bender padding discovered.
6. **Client money:** retainers into the client book, transfers on bills, the shortfall invariant (property test).
7. **KPIs:** utilisation, realisation, collection, lockup (derived) in the snapshot; Finance screen's statements (accrual and cash views), WIP and receivables ageing.

## Acceptance criteria

- [ ] For every matter, WIP at standard = Σ tenths × rate / 10 (property test); every entry balances; client book `bank = Σ owed` every month.
- [ ] Revenue in the cash view equals collections; accrual revenue equals billed value + change in WIP net of provisions (reconciliation test).
- [ ] Steady-state firm in the scenario: realisation 84–92%, collection 93–98%, lockup 90–150 days (printed, 10 seeds).
- [ ] `make check` green; `Milestone-Tag: pt-m3b-done`.

## Decisions made

Recorded by the PT-M3b session (2026-11-20). Numbers are `balance.yaml` `billing` defaults.

1. **Where billing reads matters.** Only through `ptk/sim/interfaces.py` (`billing_matters`, `billing_matter`, `billing_client`, `month_hours`, `blended_rate_cents`, `fee_earner_capacity_tenths`, `relationship_score`, `bump_relationship`). Billing runs in phase 5 after PT-M3a's work phase and changes nothing of matter progress or staffing; it moves relationships (write-downs, disputes, padding) through the seam.
2. **Stream `billing` (23), one call site,** keyed `(purpose, id)`: `(0, matter_id)` terms in a matter's first month, `(1, bill_id)` a bill (guideline rejection, dispute, days to pay, short payment), `(2, client_id)` bankruptcy, `(3, bill_id)` the default answer to a dispute. ADR PT-0012's row updated.
3. **Terms.** Billing model by matter kind: deals hourly 55%, capped 15%, fixed 15%, success 15%; cases hourly 60%, blended, capped, success and contingency 10% each (contingency only with stakes, else hourly); investigations hourly 85%, blended 15%; restructurings hourly (court-approved fees); advisory hourly 45%, retainer 25%, blended 15%, fixed 15%; filings fixed 60%, hourly 40% [A]. 20% of named matters bill quarterly, the rest and all flow monthly. Client discount 600 bp at price sensitivity 10, ±80 bp a point, at most 1,500. Caps and fixed prices are expected fees × U(0.95–1.15) and × U(0.90–1.10); a retainer is expected fees ÷ planned months × U(0.85–1.05) a month **for the planned months, then the matter bills hourly** (a retainer that ran on while matters overrun realised up to 140%); a blended rate is the kind's natural-level rate × 0.97; success-fee matters bill 80% of standard monthly plus 35% of expected fees on a win or a closed deal; contingency takes 25–40% of the recovery (60% of the stakes on a win; the last offer seen, else 40%, on a settlement).
4. **Bill timing.** Bills issue in phase 5 for the WIP posted in earlier months (the profession's month-after billing), so a month's WIP is always unbilled at month end; retainers are billed a month in advance (debit receivables, credit 2200) and earned the next month; fixed fees bill as phases complete (Σ completed phase shares × price), the rest at the end (or the completed share if a deal collapses or a case is lost).
5. **Write-downs.** The default rule writes down 60% of the work above expected fees × 1.10 on each hourly, blended, capped or success bill. The partner's write-down (`write_down_matter`, 0–5,000 bp, 2 energy) applies to the next bill and earns +0.04 relationship points per 100 bp. Guideline rejections: 15% of bills at price sensitivity 10 (+1.5 points of chance a point), 1–6% of the bill.
6. **Collections.** Days to pay: 68 (large) or 55 (mid) at price sensitivity 10, +3 a point, × LogNormal(0, 0.30), × the macro stress (1.0 until PT-M7); a bill is paid in the month its days run out (never the month it is issued). Short payments: 30% of bills at price sensitivity 10 (+1.5 points a point) pay 4–16% short, credited (4000). Bankruptcies: 5 bp a month (large) or 25 bp (mid) for a **generated** client with open bills; **real companies never go bankrupt in PT-M3b** (they are real 2005 companies; a scripted history is PT-M7's choice). Bills open 18 months are written off. The bad-debt provision is 1%, 5%, 25% and 75% of bills 0, 3, 6 and 12+ months old (6700/1210).
7. **The WIP provision** (1110) is unbilled WIP less what it is expected to bill (the model's fee before write-downs; fixed fees by progress; contingency at 50%), never negative: prudence books no write-up before a bill.
8. **Disputes** (TST ADR-0014 pending items): 4% of bills at GC temperament 10 (×(1 + 0.08 × (10 − temperament))), 15–35% of the bill disputed, two months to answer (4 energy). Concede: credit it, +1 relationship. Negotiate (the default rule when unanswered): credit half. Hold firm: paid in full with σ(2 × (relationship − 50) ÷ 50), else credited in full and −4 relationship.
9. **Padding** (the `rule_bender` tag): a padding lead's bills carry 8% more standard time that was never worked (posted to WIP at billing, not to hours, which stay PT-M3a's), six times likelier to be disputed; a dispute on a padded bill brings it to light: the padded time is credited, −8 relationship, the firm learns the tag, and that lead pads no more.
10. **Client money** (ADR PT-0003 §7): 25% of mid-size clients' new named matters put two months of planned fees on account (client book); that money pays the matter's undisputed bills at once (a transfer in both books) and the rest is returned at the end; a contingency recovery arrives in the client account, the fee is transferred and the rest paid out. A transfer never exceeds the client's own balance or the bill; bank = Σ owed at every month end (property test).
11. **KPIs** (ADR PT-0005 §4), derived each month into the snapshot: utilisation = billable tenths ÷ fee earners' capacity (the month); **realisation = fees billed for time ÷ standard value of the work billed, success and contingency premiums (4100) excluded** (they are not realisation of time; with them one won contingency case moved a 30-lawyer firm's year by 10 points); **collection = cash ÷ invoices over the bills resolved (paid or written off) in the trailing 12 months** (collected ÷ invoiced in the same window swung from 86% to 115% with payment timing); lockup = (unbilled WIP + receivables) ÷ trailing 12-month accrual fees a day. The accrual revenue reconciliation includes the change in deferred retainer income: fees = billed − credit notes + ΔWIP − Δprovision − Δdeferred.
12. **Statements.** The accrual view is the income and cost accounts; the cash view's revenue is cash debited against receivables (client-money transfers included) and its costs are cash credited against cost accounts. Profit is not yet closed to partners' accounts (PT-M4's December true-up), so the balance sheet shows assets = claims + the year's profit.
13. **Storage.** Billing entries are aggregated into one ledger entry per kind of movement a month (lines by account and practice), so a 360-turn game writes about 3,000 billing entries, not 40,000. Engagements and bills keep every row for history; client funds, provisions and deferred income are derived on load.
14. **Acceptance** (`tests/unit/test_billing_kpis.py`): PT-M3a's acceptance firm (group lift grown to 30 lawyers, leavers replaced) for 36 months, measured over months 13–36, seeds 1–10. Tuned keys (before → after): `discount_base_bp` 400 → 600, `short_pay_bp` 1,500 → 3,000, `short_pay_share` [0.02, 0.10] → [0.04, 0.16], `bankruptcy_bp` {3, 12} → {5, 25}, `dispute_bp` 250 → 400, `dispute_share` [0.10, 0.30] → [0.15, 0.35], `days_to_pay` {75, 60} → {68, 55}. Result, median of seeds: realisation 86.9%, collection 96.2%, lockup 129 days (bands hold for the median; by seed realisation runs 83.6–93.2%, collection 95.8–97.0%, lockup 118–142 days). The spread in realisation comes from fixed fees (an efficient fixed-fee deal realises up to 150%) and named matters' overruns at one 30-lawyer firm.

| Seed | Realisation | Collection | Lockup (days) | Utilisation |
| --- | --- | --- | --- | --- |
| 1 | 88.6% | 96.2% | 127 | 70.0% |
| 2 | 87.5% | 95.8% | 142 | 69.5% |
| 3 | 92.8% | 97.0% | 122 | 58.1% |
| 4 | 86.3% | 96.0% | 118 | 50.2% |
| 5 | 88.4% | 95.9% | 138 | 55.2% |
| 6 | 83.9% | 96.3% | 126 | 50.5% |
| 7 | 84.9% | 96.4% | 132 | 64.5% |
| 8 | 84.6% | 96.5% | 118 | 72.3% |
| 9 | 93.2% | 97.0% | 134 | 68.0% |
| 10 | 83.6% | 96.0% | 132 | 58.4% |
| **Median** | **86.9%** | **96.2%** | **129** | |

## Follow-ups

- **PT-M7 (balance):** utilisation in the acceptance firm is 50–72%, below T7's 75–90%: PT-M3a's default staffing leaves capacity idle (its own follow-up); a 30-year golden game ends with $57m of cash for a two-partner firm with no hiring (fees now arrive, draws and distributions do not yet: PT-M4).
- **PT-M4:** draws, the December true-up and the close of profit to partners' accounts (3100/2700); the cash view's distributions; client-money shortfall as a critical regulatory event needs the event director (PT-M6) to raise it (the engine refuses any transfer that could cause one, so it cannot happen yet).
- **Disbursements** (1300, 4200: court fees, experts, travel recharged to clients) are in the chart of accounts and in this lane, but not in the brief's sub-tasks; not built.
- **Fee arbitration** (spec §7.7, "where the bar provides it") as a fourth answer to a dispute; **e-billing audits** as events (PT-M6).
- **Matter-level write-downs from the Matters screen** (PT-M3c): `POST /finance/write-down` and `GET /finance/matters` are ready for its money columns; the Finance screen shows disputes and bills but not per-matter write-downs.
- **Real companies' bankruptcies** (e.g. 2008's) are a scripted-history question for PT-M7.
- **Rates and discounts** are set at engagement and never move; the yearly rate rise and the pricing director (spec §9.1) belong to PT-M7 and stage 3.
