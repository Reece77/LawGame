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

## Follow-ups
