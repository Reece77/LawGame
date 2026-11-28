# PT-M19b: sim-core 0.2, the lift (SC-2b)

**Goal:** the second half of `docs/sim-core-plan.md` step 2. Partner Track's general modules move into `sim-core` behind its 0.1 interfaces and are released as `v0.2.0`. Partner Track then depends on 0.2 and deletes its copies, **with golden snapshots and `tests/fixtures/state_hashes.json` unchanged** (plan decision 8). After this, the world framework (PT-M19) and Plaza start on a shared core, and v3's ports from Tech Startup Tycoon go into `sim-core`, not into a Partner Track copy.

**Plan:** `docs/sim-core-plan.md` §2 (marks), §2.4 (the five asks), §4 (streams), §5 step 2, §6 (guard tests), §9 (Reece's decisions) · **sim-core:** `docs/adoption.md`, ADRs SC-0001 to SC-0011 · **ADR:** PT-0019 (amend it, or add PT-0020 for 0.2) · **Depends on:** `pt-m19a-done` · **Lane:** runs alone, in two repositories: `Reece77/sim-core` (this session is the one Reece names to write it) and `Reece77/LawGame`. Tech Startup Tycoon stays read-only.

## Scope

1. **The lift into `sim-core`,** using Partner Track's versions as the base (plan decision 4): `people/` (generation, attributes and the reveal, morale, familiarity, retirement), `hiring/`, `org/` (seats, authority and pitches), the `actions/` framework, the `events/` framework (director, templates, the LLM's text kinds) and the UI additions `adoption.md` lists (`formatHours`, `formatBpShort`, the strain band, one range shape). Law-specific parts stay in Partner Track behind providers (practices, matters, partnership pay, bar rules). Each lifted module meets the plan's guard tests (§6), and the three fixture consumers (`pt_like`, `tst_like`, `plaza_like`) exercise it.
2. **Case machinery and the governing body from PT:** `CaseKind`'s per-kind draw policy (`adoption.md`), so that PT's claims, discipline cases and inquiries reproduce their draws; the governing body's weights resolved (show PT's points are always whole, or widen `Member.weight` to exact rationals). If PT's draws can't be reproduced, that part waits for 0.3 (the plan's cut line).
3. **The cut line:** `automation/`, `founder/` and `family/` lift only if they reproduce exactly; otherwise they go to 0.3, as the plan allows. The entry type and balances keyed by currency (PT-M19a's cuts 1-2) are **not** in this milestone: they change the state's hashes, so PT-M19 takes them as a feature change with a recorded re-record. PT-M19a's cuts 3-5 (`GameState` as a `CoreState`, `LogItem`, inbox rendering) are in scope only if hashes stay unchanged.
4. **Release `v0.2.0`** in `sim-core` with its changelog and `adoption.md` updated, after its own `make check` and the consumers' snapshot runs pass.
5. **Partner Track on 0.2:** pin the tag (the pin test), delete every lifted copy (`test_core_adoption.py` extended to the new modules), and keep `VENDORED.md` to what is still ported.

## Out of scope

Any change to a result. TST's adoption (SC-3, a TST session after its v6 closes). Plaza. New features of either game.

## Acceptance criteria

- [ ] `sim-core` `v0.2.0` is tagged; its `make check`, guard tests and three consumers pass.
- [ ] Partner Track pins `v0.2.0`. Golden snapshots and `state_hashes.json` are **unchanged and never re-recorded**; every existing test passes unweakened.
- [ ] No lifted module has a copy left in `ptk/` (test); `VENDORED.md` lists only files still ported.
- [ ] Every move that couldn't meet the exit test is listed as a cut for 0.3 in the brief and in `adoption.md`.
- [ ] T12: the median of five at most 200 ms on CI (PT-M18's level: 162 ms).
- [ ] `make check`, `make e2e` and the nightly green; merge with `Milestone-Tag: pt-m19b-done`.

## Decisions made

(The session records its decisions here.)

## Follow-ups

(The session records follow-ups here.)
