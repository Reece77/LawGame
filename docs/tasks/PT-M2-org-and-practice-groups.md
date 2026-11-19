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

- **Upstream commit.** `org/models`, `formulas`, `rules`, `delegates` and `actions/org.py` are ported from TST `02fba2aae1be2e43b179d3b6c1794d48e5dcdf56`, the commit every other vendored file records (VENDORED.md). Not ported: teammate-tag morale (§13.6, which TST moved to relationships in M6), work-location policy (§13.9), divisions, seats, authority, the CEO, pitches and reports (v2).
- **The interface.** PT-M1b published its delegate hook in `ptk/sim/interfaces.py` on `pt-m1b-hiring-and-pay` (commit `f84ce66`) before sub-task 4, so that one commit is merged into this branch and the org uses it unchanged: every delegate step is a hook request (`OpenSearchRequest`, `InterviewRequest`, `ScoutRequest`, `OfferRequest`, `CloseSearchRequest`) applied as the delegate. PT-M2 fills the body of `manager_morale_term` (W_mgr, §13.4) and appends `org_morale_changes` (this turn's one-off morale), `salary_cents` and `set_salary` (the pay seam a raise uses; PT-M1b replaces their bodies). Until PT-M1b's hiring is built the hook is its placeholder; `available_hook` turns that into "no hiring yet" and delegates find nothing to do.
- **Org state is its own.** Units, membership, plans, raise history and one-off morale live in `GameState.org` (`OrgState`) with their own tables (schema v3, `0003_org`), not on `Employment`, so the two lanes touch different tables. The firm root is implicit, as in TST.
- **One-off morale** (reorganising, raises, cuts, promotions) is recorded as `MoraleNudge`s for PT-M1b's morale to add in phase 8 of their turn (`interfaces.org_morale_changes`); the org clears them at the end of phase 8, so each counts once. The founding partner has none (TST).
- **Units.** A practice group is one per practice, directly under the firm, from 10 lawyers on the books (founding partners included; paralegals and business services do not count; spec §3). Its name defaults to the practice's label. Teams sit under the firm or a practice group and need no unlock. Groups stay if the firm later drops below 10 lawyers. A dissolved unit is kept for history; its practice can have a new group.
- **Who leads.** The player's own founding partner leads the root and cannot be moved, lead a unit, be promoted or raised (TST's founder rule); co-founding partners can. The supervising partner is TST's manager: the unit's leader, looking one level up for leaders and leaderless units.
- **Mentoring.** `M_growth` is computed at the start of phase 8 from true skills and passed to `people_month`, which multiplies growth by it (1 for anyone not on a firm's books). The golden people fingerprint changed (CHANGELOG).
- **Promotions** follow `org.promote_to`: trainee → associate 1, associate n → n+1, associate 8 or senior associate → counsel, staff → manager → director. A step to the class year September would bring anyway is **accelerated** and counted on the person (`accelerated_years`). No promotion makes a partner (the partnership vote, PT-M4) or a chief (TST: no exec). +5 morale once.
- **Raises** need a salary, so they are refused ("salaries arrive with payroll") until PT-M1b fills the pay seam; the morale rules (+3 for ≥5% once per 12 turns, −10 for any cut) are tested through a stand-in payroll.
- **Founder energy.** TST charges founder energy for reorganising; Partner Track has no founder energy yet (PT-M1b), so org actions cost none for now.
- **Plan owners** are a unit leader or a recruiting manager (`org.delegates.plan_owner_roles`: `human_resources`). A plan pauses when its owner leaves or stops qualifying. **Campus targets per group** are plans on channel `campus`: one per practice group, for the group's own practice, at `associate_1`; the hook only lets campus offers through in the offer month.
- **Delegate energy** is the hook's: each delegate gets `org.delegates.energy_per_month` (100) in phase 2 through `set_energy`, and each request costs what hiring says (`energy_cost`); while interviewing they keep `org.delegates.reserve` (20, TST's scout cost) back for a scouting pass. Scouting is per search (the hook's `ScoutRequest`). Randomness is stream `delegate` (14), key `(person_id, n)`, `n` counting that delegate's accepted requests this turn (STREAM_IDS and ADR PT-0012 updated).
- **Decision log and replay.** Each player org action is a `decision_log` row (`source` `player`, the action as JSON); each delegate step is a row with `source` `delegate`. The ADR-0015 test replays a save from turn 0 with only the player rows and recomputes the delegate rows exactly. Because PT-M1b's hiring is not built yet, the delegate tests use a deterministic stand-in behind the same hook (`tests/org_fake_hiring.py`).
- **What the screen shows.** A supervising partner appears with their number of direct reports, an "over span" flag and TST's label (strong, fine, stretched); no quality score, span limit or skill value is a field (a test enumerates the org schemas).
- **Group-lift scenario.** A third scenario (three founding partners, seven associates and a paralegal: 10 lawyers) makes practice groups reachable before hiring exists; the e2e test uses it.
- **Plan activity** is a turn-log item (`plan_activity`) until an inbox exists.

## Follow-ups

- When PT-M1b lands: fill `interfaces.salary_cents`/`set_salary` from payroll; have morale call `manager_morale_term` and `org_morale_changes`; add an integration test of delegates against real hiring; charge founder energy for reorganising as TST does.
- `manager_morale_term` builds the firm's reporting lines per call; cache the view per turn if morale's phase gets slow at scale.
- Org screen: rename and re-parent teams, raises and editing plans (the API has them); an inbox summary per plan.
- Teammate-tag morale (§13.6) through relationships, and practice group leaders as seats with authority (spec §9.1, v2).
- CLI `ptk org`.
