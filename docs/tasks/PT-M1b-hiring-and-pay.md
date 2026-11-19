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

- [x] An offer at 1.10× expectation is accepted at least 30 points more often than at 0.95× (TST M1b's criterion, re-measured).
- [x] A September class starts on the scale's salary for its year; bonuses post in December (ledger test).
- [x] Every money movement balances (property test).
- [x] `make check` and e2e green; `Milestone-Tag: pt-m1b-done`.

## Decisions made

- **Offers resolve when their month is played.** An action belongs to the next turn to be played (ADR-0014), so an August campus offer resolves in phase 1 of the August turn; the player sees the answer in September. A lateral hire joins in the same phase.
- **Campus calendar in data** (`balance.campus`): registration January-April (one open campus search per practice), the pool is drawn in phase 12 of April, the summer programme is May-July (each month a `scouting_month` on the summer associates, and summer pay at 80% of a first-year's monthly scale salary to 6200), offers only in August, start the September after. Summer associates are generated at `associate_1`; a class that joins in September does not also step up a class year that day.
- **Stream `campus` keyed `(year, school_index, search_id)`** (ADR PT-0012's table amended) so two practices' campus searches do not draw the same people.
- **Asks live on the candidate** (TST kept them on the person): the market's pay for the level in the firm's city, times the school tier's share (`hiring.ask.tier_bp`), times 1 + Normal(0, 4%), in whole $1,000s.
- **The offer score** drops TST's equity and stage terms (a partnership grants no options) for the prestige term; fit counts interests the candidate's home role favours (interest weight ≥ 2). `w_salary` is 4.5, not TST's 4.0: with 4.0 the measured gap over generated laterals was 29.4 points. Neutral candidate: 0.95× 27.4%, 1.00× 42.6%, 1.10× 74.1% (gap 46.7); measured over 40 seeds' job-post batches the gap clears 30 points (test).
- **Associates' pay** is `max(current salary, the firm's scale for the class year)`, applied in phase 9 every month: a new year's scale or a September step raises it; nothing ever cuts it (a lag set after matching takes effect only for new hires). Senior associates are paid as class 8. Off-scale levels are paid from `salary_scale.yaml` bands times the city multiplier; equity partners take no salary.
- **The 2005-2015 scale history** follows the spec's first-year figures ($125,000 in 2005, $160,000 from 2007); the 2006 row, the class steps and the bonus amounts are approximate design defaults (no salary dossier exists yet).
- **Bonuses**: December, by class year from the market table times the firm's policy (associates) or a discretionary share of salary (others), prorated by months employed in the year; notice employments get none. Bonus fairness is a one-off December morale shock (`morale.bonus_*`), not a standing term.
- **Morale's hours term needs recorded hours**: until PT-M3a staffs matters, a person with no `WorkMonth` gets no hours term (rather than the idle −5). Prospects (years 6-8) are −3 without a sponsor until PT-M4 brings sponsors. The manager term is `ptk.sim.interfaces.manager_morale_term` (0 until PT-M2).
- **Resignation base 170 bp a month** (TST's 80 gave 6.7% a year here); measured over 60 seeds × 36 months, associate attrition is 17.5% a year (balance target T6: 15-25%). Bonus timing: associates ×2.0 in January, ×1.3 February, ×0.7-0.5 October-December; income partners ×2.0 in April. Equity partners do not resign here (their flight is PT-M4); founding partners have no morale.
- **Founder energy** is 60 a month with TST M4c's costs (interview 8, references 4, job post 5, recruiter 5, referral 10, campus 5, scout 20); only the player's founding partner acts; PT-M2's delegates get energy through the hook.
- **The People screen lists people on a firm's books only**; candidates are on the Recruitment screen (their profiles still open by id).
- **Records are never dropped** from the state (searches, candidates, offers), so ids are `max + 1`; TST's NextIds counters are not ported.

## Follow-ups

- The salary dossier: check the 2006 row, the class steps and the bonus table; add 2016-2025 (spec 5.4: $180,000 2016, $190,000 2018, $202,500 and $215,000 2021-22, $225,000 2024) and the 2021 special bonuses (v1's brief stops at 2015).
- The UK path (trainees two years ahead, NQ in September; v2).
- Firing and severance (TST's `fire`), retirement (stream `retire` 12), free agents and the free-agent tag's moves.
- Keep resolved candidates' people out of the per-turn load once saves grow (TST's live-records sweep).
- An offer-dialog hint that uses the founder's prestige and the campus scale against the market once PT-M5 supplies prestige.
- PT-M3a: named-matter exposure in interesting work; real hours in the hours term (and the idle −5 then applies).
