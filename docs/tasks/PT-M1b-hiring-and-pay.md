# PT-M1b: Hiring and pay

**Goal:** the firm can hire through the campus cycle, lateral searches and referrals; pays associates on a market salary scale with December bonuses; and its people's morale and resignations respond to pay, hours, prospects and management.

**Spec:** §5.3–5.5 (morale and resignation terms; pay), §5.7 · **ADRs:** TST 0014, 0016; PT-0002 (firm-year cycles), PT-0003 (payroll accounts) · **Reuse map:** `hiring/` (CHANGED) · **Depends on:** PT-M1a · **Lane:** A

## Out of scope

Lateral **partners** with books and guarantees (PT-M4); the partnership vote (PT-M4); delegated hiring (PT-M2).

## Sub-tasks (commit after each)

1. **Searches and offers:** port TST §7 (channels, candidate pools, interviews required, references, acceptance logistic, pitch), with recruiter fees at 20–25%, the firm's prestige term (0 until PT-M5/M16 provide it), and law school tier filters.
2. **The campus cycle** (spec §5.7): summer programme months, August offers, September starts a year later; stream `campus`; the UK path is a follow-up (v2).
3. **The salary scale and bonuses** (spec §5.4): `salary_scale.yaml` by year and class year (history to 2015 for v1, *dossier*), the firm's choice per year (match, lag by %, lead), December bonuses by class year; counsel and business-services bands by city.
4. **Payroll** (TST §8 pattern): salaries, benefits, bonuses, recruiting fees, rent per head; accounts 5000–5200, 6000, 6200.
5. **Morale and resignations** (spec §5.3): TST §9 and §10 with the hours, scale, bonus-fairness, prospects and interesting-work terms; bonus-timing seasonality of resignations; lateral market heat (a constant until PT-M7's macro).
6. **Screens:** Recruitment (campus season panel, searches, candidates, offers), payroll on the Overview; inbox items for accepted and declined offers, resignations.
7. **CLI, e2e and close-out:** `ptk hire`, a Playwright run hiring a first-year class through the campus cycle; CHANGELOG, data dictionary.

## Acceptance criteria

- [ ] An offer at 1.10× expectation is accepted at least 30 points more often than at 0.95× (TST M1b's criterion, re-measured).
- [ ] A September class starts on the scale's salary for its year; bonuses post in December (ledger test).
- [ ] Every money movement balances (property test).
- [ ] `make check` and e2e green; `Milestone-Tag: pt-m1b-done`.

## Decisions made

## Follow-ups
