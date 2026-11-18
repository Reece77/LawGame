# PT-M7: Balance and v1 close

**Goal:** v1 is a game: the macro history from 2005 to 2015 drives demand (the crash included); five strategies play ten years on ten seeds against `docs/balance-targets.md`; Holiday, History and onboarding make it playable for a decade.

**Spec:** §14 (to 2015), §17 · **Depends on:** all v1 milestones · **Lane:** A (closes v1)

## Sub-tasks (commit after each)

1. **Macro and legal indices 2005–2015** (`macro_history.yaml` extended): M&A, PE, IPO, default rate, litigation, enforcement, lateral heat, rate inflation; a dossier with sources; connect to demand, collections stress and lateral heat.
2. **Strategy scripts** for the five strategies; the runner (TST's framework), nightly workflow, `known_misses.py`.
3. **Tune** to T1–T12, recording before and after values in "Decisions made".
4. **Holiday** with stop reasons (critical events, votes, offers), **History** (firm timeline, rankings by year), **onboarding** (TST M29's guided first year and What next).
5. **The 10-year run** printed; a practice save `pt-2008` (a 60-lawyer firm in June 2008).

## Acceptance criteria

- [ ] T1, T2, T11 and T12 pass; the bands pass or are carried with a recorded decision for Reece.
- [ ] Golden snapshots and the state cache recorded for v1.
- [ ] `make check`, e2e and nightly green; `Milestone-Tag: pt-m7-done`.

## Manual check (Reece)

Load `pt-2008` and get the firm through the crash. Then start a fresh campaign and play to 2015.

## Decisions made

## Follow-ups
