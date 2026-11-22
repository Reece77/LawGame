# PT-M9: Automation everywhere

**Goal:** every area of the firm can run without the player. The player gives an area to its seat holder with money limits and guardrails. The owner acts each month at a decision quality set by their score. One-offs always come to the player as proposals. A monthly digest says what was done. The player can step in on any area at any time.

**Spec:** §1 pillar 7, §9.4 (the area table and the one-off list) · **ADRs:** TST 0014, 0015; PT-0007; PT-0012 · **TST to port:** formulas.md §40 (areas, owners, money limits, commitments, one-offs as proposals, decision quality, workload in energy, the digest, routine events, the Automation screen); `tst/sim/automation/` except `chain.py`; the front end's `AutomationScreen`, `RunBy`, `OwnerRecord` · **Depends on:** PT-M8 (`pt-m8-done`) · **Lane:** B (beside PT-M10 in lane A and PT-M16 in lane C)

## Lane

- **Owns:** `ptk/sim/automation/` (new), the Automation screen and the digest view, `automation.*` keys, RNG ids **60–64**.
- **Must not edit:** the modules each area drives. An area's rule calls the existing actions and default rules (staffing, billing write-downs, pricing policy, campus targets, conflicts waivers, lateral screening, pro bono policy, lease proposals, AI budget later) through `ptk/sim/interfaces.py` or the existing action functions. If an area needs a hook that does not exist, add a thin wrapper in `interfaces.py` and record it. Never change PT-M10's macro and rivals code, or PT-M16's reputation, press and rankings code.
- **Shared files:** keep both sides; re-chain migrations if another merged first.

## Out of scope

Knowledge and AI (PT-M14: the area exists but stays unavailable until then); offices beyond the home city (PT-M11: the offices area covers the one office); risk and claims (PT-M15: the area exists for conflicts only).

## Sub-tasks (commit after each)

1. **Areas and owners** (spec §9.4's table): staffing per practice group, intake and conflicts, billing and collections, pricing and rates, business development and pitches, associate hiring and campus, associate development, lateral partners, offices and support, pro bono, and routine events. Each area has an owner seat (PT-M8); an area whose seat is vacant cannot be automated.
2. **Money limits and commitments** (TST §40.2): per-area monthly and per-decision limits; commitments made by owners count against them.
3. **One-offs** (spec §9.4's list) always arrive as proposals in the Inbox with the owner's recommendation, never as actions; an area's owner can never take one (test enumerating the list).
4. **Decision quality** (TST §40): `q = clamp(0.55 + 0.03 s, 0.6, 0.98)` from the owner's seat score; the owner chooses the default rule's answer with probability `q`, otherwise a noisy alternative within the guardrails (stream `auto_quality` (60), keyed `(area_index, firm_id)`). Owners spend their own energy; overload lowers `q`.
5. **The digest** (TST §40.4): a monthly Inbox summary of what each area did, with links, flags for decisions near a limit, and the owner's own note; routine events go to the area's owner (TST §40.5).
6. **Run by** (TST's `RunBy`): on every screen an area drives, who is running it, with "Take over" and "Hand back".
7. **The Automation screen** (TST §40.8): areas, owners, limits, guardrails, last month's actions, the owner's record.
8. **Balance:** a strategy variant `steady_automated` (every area automated with sensible limits) in `ptk/balance/` (coordinate with lane A, which owns the runner: add your strategy in a new module and register it in one line). It should reach within 20% of steady's December 2015 revenue and PEP on seeds 1-10 (printed).

## Acceptance criteria

- [ ] No one-off from spec §9.4 can be taken by an area owner (test); every owner action is within its limits (property test).
- [ ] Owners' actions replay identically (recomputation test, ADR-0015).
- [ ] A 100-lawyer firm with every area automated plays a year with no player action beyond one-offs, with a digest each month and no area exceeding its limits.
- [ ] `steady_automated` within 20% of steady's 2015 revenue and PEP (printed).
- [ ] No hidden value reaches the API or a prompt (test over the new schemas).
- [ ] `make check`, `make e2e` and the nightly balance run green; `Milestone-Tag: pt-m9-done`.

## Manual check (Reece)

In `pt-2008`, automate billing, campus hiring and staffing for one practice group, set limits, and Holiday to December 2008. Read the digests.

## Decisions made

## Follow-ups
