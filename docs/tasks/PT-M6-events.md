# PT-M6: Events and the LLM

**Goal:** the firm's story is told: client, matter, people, partnership, market and regulatory events, written by the LLM within its budget or by templates, with bounded effects, storylines and critical events that block Continue.

**Spec:** §15 · **ADRs:** TST 0005 · **Reuse map:** `sim/events/` and `events/` (CHANGED) · **Depends on:** PT-M3a · **Lane:** C

## Sub-tasks (commit after each)

1. **Port the director, validator, service, storylines, relationships and modifiers**; replace `data.py`'s tech names; effect types for law (relationship, reputation placeholder, hours, strain, morale, cash, WIP write-down, matter merits shift, confidence).
2. **Context builder** with ADR-0005 §4 hygiene: revealed ranges, revealed tags, public matter facts; never merits, portability or GC hidden traits (test).
3. **Templates:** at least 40 across the categories and severities (spec §15), including the critical set.
4. **Text kinds:** matter briefings, pitch letters, partner memos, the year-end letter, headlines.
5. **Settings:** budget meter (TST's $10 a month default), offline mode.

## Acceptance criteria

- [ ] All tests use `MockLLMAdapter`; the game is fully playable offline.
- [ ] Every template category and severity has at least one template; LLM drafts that fail validation fall back after one retry (test).
- [ ] At most 6 non-critical events a month for a 50-lawyer firm (median).
- [ ] `make check` and e2e green; `Milestone-Tag: pt-m6-done`.

## Decisions made

1. **Upstream commit.** Ported from TST @ `02fba2aa` (VENDORED.md's commit for every row), not TST's later `121d318`; the files' differences since are TST-only (defence and government events).
2. **Categories, triggers and crises.** Spec 15's eight categories, each with minor, major and critical templates (50 in all). Drawn triggers use only state that exists now (people, clients, matters, the scale, demand). Three crises can fire now: a **key exit** (a partner, or the top 10% of other staff by current ability, rounded down, resigns), a **key client walking** (a client with 15% or more of 12-month fees below relationship 25) and a **key matter's trial** (a critical case in its last phase). Spec 15's other criticals (a partner group's letter, a no-confidence petition, a merger vote, a covenant breach, a trust-account shortfall, a malpractice claim, an AI sanction, a press storm) have critical templates now; they are **engine-queued** (`director.queue_engine_event`) by the milestones that build their systems (PT-M4, v2), like TST's covenant breach.
3. **Key-exit share.** TST's 0.20 rounded up made any senior associate of a four-person founding firm a crisis: 11 of 30 seeds had a blocking critical within two years. Now 0.10 rounded down, with partners always key: 1 of 30 seeds has a critical in two years (a key client walking). Balance key `events.crisis.key_exit_top_fraction`.
4. **Continue is blocked by critical events only** (spec 15: "critical events block Continue"); Continue answers minor and major events with their first choice (TST 16.3, before M10b made majors block). Scripts (the golden seeds, the 360-turn campaign, the round trips, the delegate replay, `ptk advance --answer-first`) answer critical events with their first choice too (`answer_critical`); the player's Continue (API) is refused with 409 `critical_event_open`.
5. **Effect types** (the brief's list): `relationship_delta` is the client relationship (0-100, spec 7.2); colleague relationships are TST 16.7's pairs (`pair_delta`), formed by people on the same open matter team, with temperament starts, tag pushes and monthly drift, but **no W_rel morale term yet** (a follow-up: it would move every PT-M1b morale balance). `hours_pct` changes the hours a matter still needs; `strain_delta` and `morale_delta` move people; `cash_delta` posts 6900 general and administrative (costs) or 4000 fees (gains) against cash, capped in bp of max(cash, 3 x last month's standard-value fees); `merits_shift` moves a case's hidden merits and is shown only in words. `reputation_delta` and `confidence_delta` go through no-op hooks in `ptk/sim/interfaces.py` until PT-M5 and PT-M4. Modifiers' stats are a person's morale target (read by PT-M1b's morale) and strain gain (read by PT-M1a's strain).
6. **WIP write-downs and PT-M3b.** Started against a no-op hook (`interfaces.write_down_wip`); PT-M3b merged during the milestone, so the hook now applies the effect through PT-M3b's write-down: the engagement's next-bill `writedown_bp` rises to at least the event's percent x 100, held to `billing.writedown_max_bp`, with no energy spent; fixed, retainer and contingency matters are unchanged, and the ledger moves when the bill goes out.
7. **The associate-error trigger** fires on errors the team *caught* this month, not on escaped ones: escaped errors are hidden until they surface (PT-M3a's API rule), and an event about one would reveal it.
8. **Restricted templates** (ADR PT-0013): the burnout, associate-error and bar-complaint templates are `restricted` and never name a person flagged real; resignations and tag reveals (`REAL_RESTRICTED_EFFECTS`) are never applied to a real person, are left out of a template's draft, and make the validator reject an LLM draft. The context builder adds the "business and procedural matters only" rule to the system prompt when a real person is in it.
9. **Count weights and the brief's target.** `events.count_weights` widened to 0-4 drawn events ([0.10, 0.35, 0.35, 0.15, 0.05]); cooldowns (template 12 months, person 4, matter 3, client 3) and the critical gap (6) are TST's or follow its pattern. A 50-lawyer firm over 36 months shows a median of **1** non-critical event a month (max 3-4) on seeds 1-5: inside the brief's ceiling of 6 (`tests/unit/test_events_scale.py`).
10. **Text kinds.** Headlines every month (on the Overview, not the inbox); a briefing on each new matter of $1m or more (2 a month at most), a pitch letter to each new client (1 a month), a memo to the partners in June and December and the year-end letter in December, as inbox items. `ptk/llm/base.py` is AS IS and its `TextKind` does not list these kinds, so the service passes them with a cast (a follow-up for TST).
11. **Engine data ids.** The events tables keep their own id counters (`event_counters`), because expired modifiers and colleague pairs of people who left are dropped.
12. **Replay.** As in TST, a replay must write each turn's events with the same adapter (or copy the stored words); the in-memory delegate replay and round-trip tests do so with the mock adapter.
13. **Templates.** The first choice of every template is the reasonable default; no first choice resigns anyone.

## Follow-ups

- W_rel: colleague relationships into morale (TST 13.6/16.7), with a balance check against PT-M1b's attrition target.
- TST's `llm/base.py` `TextKind` could list Partner Track's text kinds (a TST change, then re-copy; or mark it ported here).
- Engines for the engine-queued criticals: PT-M4 (partner group letter, no-confidence petition, covenant breach, merger vote later), v2 (trust accounts, malpractice above the limit, AI sanctions, the press storm).
- Rival-firm and macro events (a rival's collapse or merger, a client's bankruptcy, salary-scale news from rivals) when PT-M5 and PT-M7 land; reputation effects once PT-M5's rankings exist.
- Holiday and "continue until" should answer critical events the way scripts do (`answer_critical`) or stop for them, when they arrive (PT-M7).
- An event history view (TST's events screen with filters) and links from matter and client pages to their events (PT-M3c's screens).
