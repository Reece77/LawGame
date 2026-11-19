# PT-M1a: Lawyers

**Goal:** the founding partners and generated lawyers exist with Partner Track's skills, levels, practice familiarity, personality and hidden potential; they grow by doing work, are seen through revealed ranges, and carry strain.

**Spec:** §2.1, §5.1–5.3, §5.6 · **ADRs:** TST 0007, 0013; PT-0006, PT-0012 (streams `strain`) · **Reuse map:** `people/` (CHANGED, light) · **Depends on:** PT-M0 · **Lane:** A

## Out of scope

Hiring, pay and morale (PT-M1b), matters (PT-M3a). Until PT-M3a, a person's hours are a test input (a `WorkMonth` record per person) so growth, familiarity and strain can be tested.

## Sub-tasks (commit after each)

1. **Data:** `skills.yaml` (spec §5.1, in group order; append-only), `roles.yaml` (a lawyer role per v1 practice, paralegal, six business-services roles), `practices.yaml` (v1's ten practice keys only; the rest of the practice data arrives in PT-M3a), levels and CA targets (spec §5.2), law school tiers, `personality.yaml` and `interests.yaml` AS IS, `tags.yaml` with the new tags, `backgrounds.yaml`. Loader validation tests.
2. **Port `people/`** with provenance headers: models, CA (TST §1) by role, generation (TST §2) with school tier and familiarity (home practice 10–16 by level, others 1–6), reveal (TST §4, ADR-0007) including familiarity as a narrow-range attribute. Seeded tests.
3. **The founding partner build** (spec §2.1): background, age, skills within limits, book of business as a number on the person (its use arrives with clients), bar admissions.
4. **Growth with learning** (spec §5.3, ADR PT-0006 §4): TST §3 × `learn(h)`; familiarity growth and decay. Property tests: attributes stay in 1–20; familiarity in 1–20.
5. **Strain** (spec §5.6): the meter, burnout state, recovery; the founder's case. Worked example as a test (2,600 hours a year burns out in about 8 months; 2,200 never).
6. **API and screens:** People list and Person profile with ranges, familiarity grid, strain (own firm only); hidden-value test (no PA, hidden trait or portability in any response).

## Acceptance criteria

- [ ] Same seed, same people (golden).
- [ ] No hidden value reaches the API (test enumerates every people schema).
- [ ] Spec §5.6's worked example passes; growth's worked examples (TST §3 adapted) pass.
- [ ] `make check` green; `Milestone-Tag: pt-m1a-done`.

## Decisions made

- **Upstream commit.** `people/` and the data files are ported from TST `02fba2aae1be2e43b179d3b6c1794d48e5dcdf56`, the commit every other vendored file records. TST's later `reveal.py` change (M45, one vectorised draw giving the same numbers) is not taken.
- **v1's ten practices** (Reece, 2026-11-19): corporate and M&A, private equity, capital markets, banking and finance, restructuring, commercial litigation, white collar, IP, employment, real estate. Tax and the regulatory practices wait for PT-M12.
- **Six business-services roles** (Reece, 2026-11-19): finance, human_resources, it, marketing_bd, operations and records_and_conflicts. Knowledge management arrives with PT-M14; pricing, facilities, risk_and_compliance and legal_technologist with the systems that use them. Role keys are append-only.
- **Tags.** TST's nine tags are kept in order (including maverick and job-hopper, which spec §5.3 names) and PT's seven are appended. Credit taker, toxic high performer, cowboy and rule-bender carry `negative: true`; `draw_tags` never gives one to a person flagged `real` (ADR PT-0013). Only grinder's strain load (×0.7) acts in PT-M1a.
- **Levels.** All eighteen of ADR PT-0006 §1 are in `balance.yaml` `people.levels`, with CA targets from spec §5.2 (associate years 1–3 at 80, 90, 100; 4–6 at 105, 112.5, 120; 7–8 at 125), age ranges, capacity and billable targets, the home-practice familiarity range (10–16 rising by level) and the next class year. Business services use staff 70, manager 100, director 125, chief 145. Associates advance a class year each September in phase 8.
- **Law school tier** is the first draw for a lawyer (T14-equivalent 25, national 45, regional 30); it shifts the target CA mean (+6, 0, −6) and the potential gap (+8, 0, −5). The UK tiers are data for v2 and never drawn. The salary effect waits for PT-M1b.
- **Generation order** keeps TST's draws in TST's order, with the school tier first and familiarity and a partner's portability last. Salary expectations, regions and city talent bonuses are left out (PT-M1b, v2). Generated lawyers past trainee are admitted in the scenario's home jurisdiction.
- **Familiarity.** Home practice uniform in the level's range, others 1–6; business services staff are 1 everywhere (no draws). Reveal records for familiarity start at half-width 1.5 (on a CV), are drawn after PA's, and narrow with every action that narrows skills. The taper above 15 scales the gain by (20 − f) / 5 at the point it crosses 15 (diminishing returns, zero at 20); decay stops at max(1, peak − 3), so the peak is stored per practice.
- **The founding partner** is built with TST §5's point system (base 5, 110 points, cap 18, age 34–52, default 42). Each background names a home practice (the founder's role, at equity partner, instead of TST's best fit), the practices known at 15–17, a book of business range drawn in $50,000 steps, and extra bar admissions (USPTO for the patent litigator, DC for the government lawyer). Every founding partner, the scenario's co-founders included, is built this way from stream `founder` keyed by index (0 = the player's). Co-founders and starting staff come from `scenarios.yaml` (BigLaw spin-out: a trial-lawyer co-founder aged 46, a third-year corporate associate and a second-year litigator; solo founder: a paralegal).
- **What the firm knows at the start.** Its founding partners exactly (TST §5); its starting staff as an interviewed hire (stranger ranges narrowed by one interview with the player's founding partner as scout). Each month every employee gets one `employed_month` of narrowing, with the firm's best true judgment of talent as scout.
- **learn(h)**: a month with no hours learns at the lower bound (0.5). `WorkMonth` carries hours by practice, substantive hours, other hours (BD and management) and rest (none, holiday, sabbatical); it is an optional `advance_turn` argument until PT-M3a staffs matters, so the 360-turn golden games run with no hours.
- **Strain.** Capacity is a twelfth of the level's yearly hours (×0.7 in burnout). A holiday (−25) or sabbatical (−40) month replaces the −8 recovery, while hours above comfort that month still add load. Burnout's error and resignation doubling is exposed as `burnout_effects_active` (6 months from its start) for PT-M1b and PT-M3a to use. Stream `strain` draws a generated person's starting strain (10–30); founders start at 20. The `strain` row in ADR PT-0012 is updated to say so.
- **Hidden values.** The API never carries PA, hidden traits, portability, half-widths, offsets or familiarity peaks; potential is a phrase. Strain, burnout and a partner's book show for the player's own firm only. "Ability" on the People screen is CA computed from the low and high ends of the revealed role-skill ranges.
- **Persistence.** Schema v2 adds `person`, `employment` and `reveal_state` (current-state tables, upserted each turn); attribute sets are JSON in data-file order.

## Follow-ups

- Languages as a count plus a list (spec §5.1); `languages` is one 1–20 skill for now.
- A paralegal's home practice is stored only through their familiarity; store it on the person when practice groups (PT-M2) need it.
- Sortable and saved column views on the People table (TST's DataTable and `ui_settings.py`).
- Hours YTD, utilisation, morale and partnership prospects on the People screen (PT-M1b, PT-M3a, PT-M4).
- Founder build in the New game screen beyond the background (skill allocation, personality preset, name and age): the API's `FounderSpec` already accepts them.
- Restrict `real` people's tags and events by test once real lawyers exist (PT-M5).
