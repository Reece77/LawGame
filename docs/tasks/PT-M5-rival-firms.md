# PT-M5: Rival firms

**Goal:** about 40 real firms at their 2005 sizes and a field of generated firms compete for clients, bid on RFPs, poach partners and associates in both directions, open boutiques when partners leave, and follow their real paths to 2015 unless the player changes their fate.

**Spec:** §7.2 (panels and RFPs), §10 · **ADRs:** TST 0010, 0015; PT-0008 · **Streams:** `rfp`, `rival_firm`, `poach` · **Depends on:** PT-M3a; merges after PT-M4 (uses its flight machinery) · **Lane:** B

## Sub-tasks (commit after each)

1. **Dossier and data:** `docs/research/rivals-2005.md` (revenue, lawyers, equity partners, PEP, practices, offices, comp system, 2005–2015 path, dated events: mergers, collapses), `firms.yaml` with sources; stable `rival_key`s (TST ADR-0013 amendment).
1a. **Real people dossier** (ADR PT-0013): `docs/research/notables-2005.md` and `notables.yaml` (5–10 notable lawyers per major rival, with sources and S/D/A tags, skills as ranges from public standing, real moves and retirements to 2015), `judges.yaml` (real trial judges in the modelled courts with procedural traits from published statistics and orders, appointments and retirements to 2015); the `world.real_people` setting and its generated swap. **Test:** no restricted event, tag or effect ever selects a person flagged `real`.
2. **Rivals as firms:** key partners (top 30) and rising associates as individuals, pools by practice and level; ledgers; the same engine rules.
3. **Utility AI** (spec §10.2): needs, personality weights, cooldowns; decisions logged and replayed by recomputation.
4. **Panels and RFPs** (spec §7.2): panel reviews, RFP events, pitches (team, price, claims), awards; the player's pitch action.
5. **Poaching both ways:** rivals' approaches to the player's people (PT-M4's machinery), the player's approaches to rivals' key people; team lifts.
6. **Spin-off boutiques** (TST §15.4 pattern): founded by departing partner groups; their growth and failure.
7. **History pin** (ADR PT-0008 §2) to 2015: steering toward paths, dated events conditional on the player's effects.
8. **Screens:** Market (rival list with personality label, money label, stance), Rival firm page, Market news; opposing counsel names on matters.

## Acceptance criteria

- [ ] Balance target T11 (rivals hold history at 2009 and 2015) passes on seeds 1–10.
- [ ] A player who hires a third of a historically collapsing firm's top partners a year before its date brings the collapse forward on at least 7 of 10 seeds (conditional history works).
- [ ] With `world.real_people` off, the same seed plays identically apart from names (state-cache comparison on everything but names).
- [ ] Turn time ≤ 250 ms at December 2015 (T12).
- [ ] `make check` and e2e green; `Milestone-Tag: pt-m5-done`.

## Decisions made

## Follow-ups
