# PT-M7a: v1 gaps

**Goal:** close the gaps Reece's product manager found reviewing PT-M3a to PT-M6 (2026-11-20) before PT-M7 balances v1: a reachable first partnership vote in the default scenario, default staffing that fits typical teams and fills idle capacity, pro bono, early case assessment, yearly rate rises with the appeal's price term, and Holiday or "continue until" that stops for what needs the player.

**Spec:** §4.2 (Holiday), §5.5, §7.1 (price term), §7.5, §7.6 (early case assessment), §7.8 (pro bono), §15 (critical events) · **ADRs:** TST 0005 (hidden values), PT-0004, PT-0005, PT-0006 §4 (learning), PT-0012 (streams), PT-0013 · **Targets:** `docs/balance-targets.md` T7 (utilisation), T10 (burnout) · **Follow-ups closed:** PT-M3a (staffing at skill 10, early case assessment, pro bono, rates), PT-M3c (win-probability band), PT-M6 (Holiday and critical events) · **Depends on:** PT-M3a–PT-M6 (all merged) · **Lane:** A (before PT-M7)

## Out of scope

The macro and legal indices, strategy scripts, the balance runner and tuning to T1–T12 (PT-M7); History and onboarding (PT-M7); reputation and pro bono rankings (v2, PT-M16); the founder's Beloved trait (v2, PT-M17); Tech Startup Tycoon is read-only (CLAUDE.md §3).

## Sub-tasks (commit after each)

1. **Scenario fix.** In `biglaw_spinout` the starting corporate associate is a fourth-year (`associate_4`, class 4 in January 2005), so at the default track of 8 years they are eligible at the December 2008 vote. A test plays the scenario to December 2008 and finds them eligible. Golden snapshots regenerated, the reason in `CHANGELOG.md`.
2. **Default staffing for expected output.** The default rule plans each member's hours from their expected output (effective skill on the kind's tasks ÷ 10 × the strain factor, floored), not from skill 10, so a typical team (effective skill 8–9) finishes near the planned months; a matter near its end takes the hours its remaining output needs at the team's expected output. Flow fills idle capacity before anyone is left unassigned: after the home and familiar pools, remaining idle fee earners take what is left of any practice's flow. Pro bono flow (sub-task 3) comes after paid work. Tunables in `balance.yaml`.
3. **Pro bono (spec §7.8).** Pro bono flow (a monthly pool of hours per lawyer) and named pro bono matters (occasional cases and advisory work for a pro bono client) with no fees: no WIP, no bills, no origination, no client relationship. The firm's **credit policy** (default 50 hours a year counting toward each lawyer's billable target; an action). Effects: associates' morale (a morale term for pro bono hours) and learning (pro bono hours count as substantive), and recruiting appeal (the firm's pro bono hours per lawyer in the offer score's prestige). Utilisation stays billable hours over capacity. A **Pro bono** column (year-to-date hours) on the People screen and a credit-policy setting on the Org screen.
4. **Early case assessment (spec §7.6).** An action on an open case (litigation, arbitration, investigation): energy from the actor and non-billable hours from the lead this month; it reveals the case's merits as a range whose width shrinks with the lead's legal reasoning and judgment (stream `actions`), always containing the true merits. PT-M3c's outlook band uses the range's midpoint when it exists, and the Explain item shows the range in words. Merits stay hidden in every API schema and every prompt (tests).
5. **Yearly rate rises.** Each January the firm's rate card (its rate index over the practices' 2005 cards) rises by a player-set percentage (default: the market's, `rivals.rate_inflation`); an action sets it. Every hour's standard value, blended engagements and new matters' expected fees use the indexed card. The appeal's **price term** (spec §7.1) is `1 − firm index ÷ market index`, so the default firm stays neutral and a firm that raises faster than the market loses share. Rivals already set their own rates (PT-M5). The rate rise setting and the current index on the Org screen.
6. **Holiday and "continue until"** (spec §4.2; PT-M6 follow-up): play up to N months, or until a date, each month its own transaction (ADR-0004), stopping before a month when: a critical event waits (never answered for the player), the next month is December and the partnership has candidates to propose or a vote open, a settlement offer is open, or a rival's approach to a partner is open; also at the game's end. The API returns the months played and the stop reason; a Holiday control in the header; `ptk holiday` in the CLI.

## Acceptance criteria

- [ ] `biglaw_spinout`'s corporate associate is eligible for the December 2008 vote at track 8 (test); golden regeneration recorded.
- [ ] The acceptance firm (PT-M3a's 50-lawyer grown firm, `tests/matters_support.grown_firm`, leavers replaced, months 12–48, seeds 1–5): median utilisation in **75–90%** (T7) and associates' burnout starts **≤ 5% a year**; closed named matters' median duration within 1.5 × planned months. Printed with before and after values.
- [ ] Hours still reconcile with pro bono (Σ person-hours = Σ matter-hours + flow hours + pro bono flow) and pro bono never posts WIP, bills or ledger lines (property test).
- [ ] Credited pro bono hours never exceed the policy per person per year; pro bono raises associates' morale target and recruiting acceptance (unit tests).
- [ ] Early case assessment: the revealed range contains the true merits on 1,000 seeded cases, narrows with a better lead, costs energy and the lead's hours; no API schema or prompt carries `merits` (tests).
- [ ] Rate rises: January raises the index by the policy (default market), the price term is 0 for the default firm and negative above the market (unit tests).
- [ ] Holiday stops for each reason (critical event, December vote, settlement offer, approach, months, date) and every month played is its own committed turn (integration tests); e2e covers a Holiday from the header and the two new settings.
- [ ] Schema v10 migration; `docs/data-dictionary.md`, `VENDORED.md` (if touched), ADR PT-0012 streams, `CHANGELOG.md` updated.
- [ ] `make check` and `make e2e` green; merged with `Milestone-Tag: pt-m7a-done`.

## Decisions made

## Follow-ups
