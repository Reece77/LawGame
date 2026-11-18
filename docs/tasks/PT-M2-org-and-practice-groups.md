# PT-M2: Org and practice groups

**Goal:** the firm has practice groups and teams with leaders; supervising partners' span, quality and mentoring shape morale and growth; and delegates can run hiring.

**Spec:** §3 (stage unlocks), §9.1 (seats arrive in v2; here only unit leaders) · **ADRs:** TST 0014, 0015 · **Reuse map:** `org/` (CHANGED: units, span, manager quality, mentoring, reorganising, raises and promotions, delegated hiring; seats, authority, CEO and pitches are v2) · **Depends on:** PT-M1a · **Lane:** B, beside PT-M1b

## Lane

- **Owns:** `ptk/sim/org/`, the Org screen, `org.*` keys.
- **Must not edit:** `ptk/sim/hiring/` (PT-M1b) except through the delegate hook PT-M1b exposes; shared files (balance.yaml, CHANGELOG, data dictionary): keep both sides.

## Sub-tasks (commit after each)

1. **Units:** firm root, practice group (one per practice, unlocks at 10 lawyers), team; reporting lines; port TST §13.1–13.4.
2. **Mentoring and growth:** TST §13.5 with the supervising partner as manager; the `mentor` tag bonus.
3. **Reorganising, raises, promotions** (TST §13.7–13.8), with levels from ADR PT-0006 (promotion beyond class year is "accelerated"; partnership is PT-M4).
4. **Delegated hiring** (TST §13.10): hiring plans owned by a recruiting manager or a group leader; campus targets per group.
5. **Org screen** and the profile's org panel; e2e: create a practice group, set a leader, open a plan.

## Acceptance criteria

- [ ] TST §13.12's worked examples pass in PT units.
- [ ] Delegates act in phase 2 with their own energy and stream; replay recomputes their actions (ADR-0015 test).
- [ ] `make check` and e2e green; `Milestone-Tag: pt-m2-done`.

## Decisions made

## Follow-ups
