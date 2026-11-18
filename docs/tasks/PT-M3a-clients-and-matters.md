# PT-M3a: Clients and matters (rules and API)

**Goal:** the heart of the game. Legal demand by practice flows to clients; clients instruct the firms on their panels; the firm checks conflicts, staffs named matters and flow work, and its people's hours drive progress, outcomes, relationships, utilisation, strain and learning.

**Spec:** §6, §7.1–7.6, §7.8 · **ADRs:** PT-0004, PT-0005, PT-0009, PT-0011 §1 (task mixes only; no eras) · **Streams:** `demand`, `intake`, `matter`, `conflict`, `client_gen` · **Depends on:** PT-M1b, PT-M2 · **Lane:** A

## Out of scope

Billing and money (PT-M3b: until it merges, hours post to WIP only); rivals beyond static 2005 panel firms with fixed appeal (PT-M5); screens beyond API and CLI (PT-M3c); AI eras (v2).

## Sub-tasks (commit after each)

1. **Practices data** for v1's ten practices (spec §6): demand base by region (one region in v1: the home market, sized from the dossier), drivers and sensitivities, rate cards by level, leverage and margin norms, matter kinds, task mixes, conflict density, cross-sell affinities. A short dossier `docs/research/v1-market.md` with sources.
2. **Clients:** 300 real clients (2005) and generated ones (`client_gen`), wallets by practice, panels (the player's firm on panels where the founders' books came from), GCs as people, relationships (spec §7.2) with relationship partners and origination credit.
3. **Demand and intake** (spec §6 formula, §7.4): monthly demand, allocation to clients, wallet shares by the appeal model, flow streams and named matters (ADR PT-0004 thresholds).
4. **Conflicts** (ADR PT-0009): parties, the index, refusals, waivers (an action), skipped checks' hidden conflicts. Property test: no matter is ever open adverse to a current client without a waiver.
5. **Staffing and work:** staffing actions (assign, set hours, remove), the default staffing rule (used by delegates and scripts), capacity and overtime, flow absorption; each person's monthly hours by matter and task; feeds growth, familiarity and strain (PT-M1a) and the hours morale term (PT-M1b).
6. **Progress and outcomes** (spec §7.5–7.6): phases, team output, supervision span on matters, deadlines and slips, litigation `p_win` with hidden merits, deal closing, errors (recorded; claims arrive in v2), settlement offers as pending items.
6a. **Courts and judges** (spec §7.6a): courts data, generated judges with procedural traits, random assignment, the judge's effect on duration, cost, settlement and sanctions (never on the side), forum choice, appearance familiarity. **Test:** swapping a case's judge never changes `p_win`'s sign of advantage; only path, timing and cost move.
7. **Relationships move** with outcomes, service and cross-practice breadth; cross-sell introductions (an action).
8. **API and CLI:** matters, clients, practices endpoints (revealed ranges only: merits and GC hidden traits never shown); `ptk matters`, `ptk staff`.

## Acceptance criteria

- [ ] Same seed, same intake and outcomes (golden).
- [ ] Hours reconcile: Σ person-hours = Σ matter-hours + flow hours, every month (property test).
- [ ] A stronger team (mean effective skill +3) wins at least 15 points more litigation on the same cases (printed over 1,000 seeded cases).
- [ ] An over-strained team (strain ≥ 80) makes at least twice the errors of a rested one.
- [ ] Named matters ≤ 40 open for a 50-lawyer firm (median), so the player's list stays manageable.
- [ ] `make check` green; `Milestone-Tag: pt-m3a-done`.

## Decisions made

## Follow-ups
