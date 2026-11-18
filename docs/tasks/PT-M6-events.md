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

## Follow-ups
