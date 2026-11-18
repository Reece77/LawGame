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

## Follow-ups
