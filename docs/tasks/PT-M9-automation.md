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

Recorded by the PT-M9 session (2026-11-22). Engineering choices and the gaps the spec, ADRs and brief left open.

1. **Owners are seat holders only** (the brief: "an area whose seat is vacant cannot be automated"), not TST 40.1's area leads or a CEO: a seat's area belongs to its holder (lateral partners: any executive committee member; associate development: the CHRO; risk and intake: the general counsel; routine events: the COO; knowledge: the CKO). Two areas have no seat of their own: a practice group's **staffing** belongs to the group's leader once they are eligible for the practice group leader's seat (an equity partner), from stage 2, so the manual check can automate it in `pt-2008` (a stage-2 firm, where the PGL seat's stage-3 effect does not yet count); **pro bono** belongs to any partner but the MP ("a pro bono partner", spec 9.4). An owner who leaves or loses their seat hands the area back (`area_returned`); a firm that drops below a seat's stage loses that seat's areas the same way.
2. **One setting** (TST 40.12): giving an area whose seat has a PT-M8 authority rule also enables the seat's authority (so its quarterly pitches go on); taking the area back withdraws it. The seat's monthly rule then runs once, as the area, with the area's limits: `seat_phase.phase_two` takes the automated (seat, slot) pairs and sets their authority aside for the seats' own step only. Areas run PT-M8's rules as they are through a thin wrapper, `interfaces.run_seat_rule`; no module an area drives was edited.
3. **Stream keys.** `auto_quality` (60) is keyed `(area_index, firm_id, slot)`: the brief's `(area_index, firm_id)` plus the slot, because practice groups share the staffing area (as PT-M8 did for `seat_act`). One uniform an area a month decides right or mistake (as PT-M8's seats); the mistake's noise and the actions' own draws follow on the same generator. Routine events draw from `auto_events` (61) keyed `(event_id,)`. Ids 62-64 are unused.
4. **Workload and energy.** Each owner has `owner_energy` (100) workload points a month; an area costs its `energy` (5-25). The brief's "overload lowers q": q falls by `overload_per_energy` (0.004) a point beyond 100, never below `overload_floor` (0.3), and the digest says the owner is stretched. An area's actions spend `action_energy` (40) set for its run, and the owner's own energy is left as it was (as PT-M8's authority); the MP's partnership actions (lateral searches, diligence, offers, sponsors, introductions, partner proposals, revolver repayments, pay policy) are carried out in the MP's name with the MP's energy kept (TST 40.13's founder actions).
5. **Limits.** Per decision: `default_limit_bp` (2%) of cash when given, at least $25,000, rounded to $10,000; monthly: `monthly_limit_mult` (3) x that; both editable. Commitments (`limits.py`'s header): a plan's hires x the level's firm salary for 12 months, a write-down's share of the WIP, a lateral offer's year of comp plus every guaranteed year, a pro bono credit rise's credited hours at the firm's average rate; rates, waivers, RFP pitches, introductions, sponsors and searches commit nothing; a revolver repayment commits its amount.
6. **One-offs** (`config.SPEC_ONE_OFFS`): admissions (a partner proposal on the equity or income track; a "not this year" second look is within the area), de-equitisations, guarantees (a lateral offer or counter with guaranteed years), combinations with a rival's people (mergers are PT-M13), a capital call, agreement changes (terms, the exco term), pay above the market (`set_pay_policy` lead) and a waiver adverse to a key client; appointing seat holders too (TST 40.2). Offices, AI platforms, litigation funding, malpractice settlements and ABS formation have no action in the game yet; leases are the COO's PT-M8 fit-out pitches, which the player answers. Proposals expire after 3 months as declined and are not re-proposed for 6.
7. **Area rules** are in `rules.py`'s header. Staffing is PT-M8's PGL hiring rule: the engine's PT-M7a staffing rule already allocates flow and named matters each month, so the owner adds plans when the group runs hot (strain relief and learning shares are a follow-up). Hiring adds lateral associate plans when the firm runs at or above `busy_bp` (8000), one plan of `lateral_step` (2) per group without one (before groups, the CHRO's own plan per practice), as steady's delegates do. Development proposes partnership candidates in November (`proposal_month`), so the player approves them in December when the rules accept proposals, and gives first-look candidates a second look in December. The pro bono area reviews the credit policy once a year (`pro_bono_month`, January) after the firm's first year: its moving average starts at zero, and a monthly rule read it as a shortfall and raised the credit every month (on seeds 2 and 3 that cost the firm its billable time and it dissolved).
8. **The digest** is one inbox item at month end (phase 12), its body a template (an LLM-written opening paragraph is a follow-up); the Automation screen shows each month's digest with its links (`?month=`). Items produced by automated areas are stored with `inbox_item.in_digest` and left out of the inbox's default list (`listInbox?everything=true` shows them).
9. **Balance** (sub-task 8). `steady_automated` gives every area that can be automated to its best displayed fit with a limit of 10% of last year's fees (at least $500,000, a lateral associate plan) and steady's settings (2 RFPs a month, a campus class of a tenth of the lawyers), approves every proposal, and plays steady's move for any area not automated yet: before stage 3 (101 lawyers) the pricing director and the executive committee do not exist, so steady's firm (about 50 lawyers by 2015) keeps lateral partners and rates in the player's hands throughout. The MP's own partnership moves that no area of spec 9.4 covers (the election's answer, the comp system, December's comp round) and the practice groups stay the script's. Readings (seeds 1-10, 132 turns, medians): steady 2015 revenue $58.74M, December PEP $3.92M, 48 lawyers; steady_automated $53.17M (-9.5%), $3.89M (-0.8%), 41 lawyers. Per seed the two diverge from month one, because the script's extra actions move the player's `actions` stream keys (seed noise, not a systematic effect).
10. **The 100-lawyer year** (acceptance 3) is PT-M8's stage-3 led firm at 100 lawyers with every area but knowledge automated, the player approving each proposal and nothing else: a digest each month, 59 owner decisions and 17 approvals in the year, no decision at or above its limit and no month past an area's monthly limit (`tests/balance/test_pt_m9.py`).
11. **"No hidden value"**: the schema test forbids fields naming a score, quality, chance, probability, overload, draw, best, right, mistake or a hidden value; a mistake is shown as the decision it was; fit bands come from displayed ranges.

## Follow-ups

- Automate everything (TST 40.8's one-click plan with a confirmation), and per-unit headcount targets for the hiring area (TST M27b).
- Staffing beyond PT-M8's hiring rule: strain relief, learning shares and rotation for familiarity within a utilisation band (spec 9.4's staffing targets).
- The digest's opening paragraph written by the LLM in the COO's voice within PT-M6's budget.
- Area KPIs against last month and a target in the digest (TST 40.4); the owners' record on the Person screen.
- Offices (PT-M11), knowledge and AI (PT-M14), risk and claims (PT-M15), mergers (PT-M13) and ABS (PT-M18) bring their areas' rules and one-offs.
- The comp round as an area (it needs a displayed market value for partners, which the game keeps engine-only).
