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

Engineering and design details the spec, ADRs and brief left open (session of 2026-11-20).

**Data (sub-tasks 1, 1a)**
1. **Dossier gaps closed** by three research passes (`docs/research/notables-2005.md`, "Gaps closed"): 204 notables kept (10 rows dropped for no [S] 2005 role, 2 added), each with a career-start year (167 [S], 18 [D], 19 [A], 15 of those "no source", given 1980) and a "left practice (YYYY)" year with no cause where they stopped by 2025; a person leaving for government, the bench or in-house who never returned has that year as their end. LeBoeuf has no notable (none could be sourced for January 2005).
2. **Rivals' path** (`firms.yaml`, from the dossier's path pass): FY2005, 2007, 2009, 2012 and 2015 revenue (FY2009 [S] for 40 keys, FY2015 [S] for 37 of 38 survivors) and lawyers (mostly [D]/[A], ±15%). FY2005 equity partners are all [A] (M4: FY2012 margin carried back); PEP [S] for 8 firms. **DLA Piper is pinned on its US basis to FY2009 only** (the verein basis from FY2012 is a different scope); Hogan Lovells, K&L Gates, Reed Smith and Cooley grow by **outside mergers** (steps in the path); Morgan Lewis's FY2015 includes Bingham. Williams & Connolly's and Boies Schiller's FY2005 figures are [A] ($210M/230, $180M/200). T11 checks only points whose revenue is [S].
3. **Real judges**: 162 from `judges.yaml` replace the generated judges on the eight courts that have real ones (arbitration stays generated). No per-judge statistics were found, so each judge's traits are their court's published figures (docket speed from median months to disposition against all districts; trial appetite from trials per judgeship) with a seeded spread (`rivals.judge_trait_sd` 2.0, [A]); a judge's own sourced trait wins (one: Gammerman's docket speed). A judge whose `left` is unknown leaves in a seeded year 2026-2034; each departure brings a generated successor.
4. **`world.real_people` off keeps the `real` flag** (so the restrictions still apply and play is identical); only names differ: notables keep the generated names their draws give, judges get names from stream `real_swap`.

**Economy and the pin (sub-tasks 2, 7)**
5. **Rival people are generated on demand** from their member record (stream `rival_people` keyed `(*rival_key, n)`, memoised): a game stores no rival people until the player's firm meets one (then their record moves to `GameState.people`). Their skills do not grow while at a rival; they age, step class years, are made partner, retire (real ones the January after their `left_practice` year; everyone at `rivals.retire_age` 68) and move (notables' dated moves). This keeps game creation at about 0.25 s and saves small.
6. **Rival person ids start at 10,000,000** (`RIVAL_PERSON_BASE`); `GameState.next_id("person")` counts only ids below it, so the player's ids never meet a rival's.
7. **Demand while pinned** = the path's revenue run-rate × e^shock + the player's effects (`offset_cents`, decaying at `pin.recovery_per_year` 20%); the shock is AR(1) (σ 1.2%, φ 0.85: a stationary 2.3%). Headcount steers to the path's lawyers scaled by demand; rates steer to the path's revenue per lawyer at the personality's utilisation. After 2015 demand grows with `rivals.market_growth` (the Am Law aggregate by year, [A]), the personality's bias and its pricing. On seed 1 every pinned rival ends within ±6% at 2009 and 2015.
8. **Costs** are cost per lawyer, calibrated at turn 0 so profit is PEP × equity partners, growing `rivals.cost_growth` 3.5% a year; each rival posts one balanced entry a month and distributes its profit to drawings (rival cash stays 0).
9. **Equity partners and PEP are not pinned** (only revenue and lawyers, as the instructions say); they follow the pools.
10. **Laterals between rivals, team lifts and new offices move demand only in free play**; while pinned the path already holds history's moves (a notable's dated lateral moves the person, not demand).

**Decisions, RFPs, poaching (sub-tasks 3-6)**
11. **Utility AI**: nine actions (`rivals.data.RIVAL_ACTIONS`), one noise draw per action every month in a fixed order, top action plus a second if U ≥ 0.5; cooldowns per action. `bid_rfp` is not an action: RFP bidders are drawn by size (`rfp.bidders`); `merge`, `adopt_ai`, `raise_salary_scale` and `launch_fixed_fee` are follow-ups (mergers are v2 in PT-M4's brief; AI from its era).
12. **RFPs**: large clients review panels every 3 years (staggered by client id) and run big-matter RFPs (30 bp a month). An unpitched incumbent competes for its seat but keeps only what it had; a big matter needs a pitch. *Found by PT-M3a's guard*: a first version added the review's three practices to an unpitched incumbent's relationship and pushed the 50-lawyer firm's open named matters from main's 23.5-36 to 33-56 on seeds 11-40 (rule 2); the fix brings them to 22-25 on seeds 11-14 (main 23.5-31.5).
13. **Pitch price is not modelled** (team and claims only): a discount would need billing to honour it; follow-up. Claims are `references`, `track_record`, `continuity`; an unsubstantiated claim counts against the pitch.
14. **Rivals' approaches** go to the player's partners and senior associates (never a founding partner: PT-M4's flight decides those), at most 4 a year, answered next month on stream `rival_poach` (PT-M4's flight keeps `poach`, keyed `(person_id,)`). The player counters by matching the offer. **At PT-M4's merge, partners' approaches go through its `PartnerFlightHook` with the rival as the suitor** (see the merge notes below).
15. **The player's approaches** (`ApproachRival`, `ApproachFreeAgents`) create a *closed* referral search whose candidates are 2-4 key people (no generic batch follows) asking 30% over market; interview and offer as any lateral. A hire takes the person's book × portability off the rival, lowers its panel appeal (key partners against its target) and counts toward its collapse hazard.
16. **Collapses**: hazard = 120 bp a month per point of 12-month departed share above 15%, ×1 within 36 months of a dated collapse, ×0.05 × fragility otherwise; a merger is called off if either side lost a third. Hiring a third of Howrey's partners in March 2010 brings its collapse forward on 10 of 10 seeds (it falls within a few months).
17. **Boutiques**: 15 bp a month across the market, 2-6 partners of one practice from a real rival, books at 60%; litigation groups found `litigation_boutique`s, others `elite_lockstep`. They (and generated firms) fail at 150 bp a month while losing money for a year.
18. **Panel appeal** of a rival not in clients.yaml's 16 static panel firms comes from its size (1.0 + 0.5 log10(revenue / $100M), clamped 0.6-1.8), close to the static firms' 1.2-1.7.
19. **Real people never burn out**: a real person's strain is held 1 point below `strain.burnout_at` (PT-M1a's `strain_month`), as ADR PT-0013 forbids burnout collapses for them.

**Tests and tooling**
20. **T11 and T12** run without strategy scripts (PT-M7 builds them): T11 with the biglaw spin-out unmanaged on seeds 1-10; T12 on a 150-lawyer grown firm (steady's 2015 size) to December 2015, median of 12 turns, **221 ms** alone (`make check-timing`, a new `timing` marker excluded from the parallel run).
21. **Persisted turns**: the rivals' state is one JSON document per save with a content-checked in-process cache; more than 20 entries in a turn go in one bulk insert. A persisted turn is about 150 ms at 2005.
22. **Golden balances** now include the rivals' books (the golden test fingerprints every balance).

## Follow-ups

1. PT-M4's merge: partners' approaches through `partner_flight()` with `Suitor(rival.key, rival.name, rival.id)`, PT-M4's `_suitor_for` choosing among live rivals instead of the static panel firms, departures with a rival suitor joining that rival, and the player's hire of a rival partner through `arrive` (book clients, guarantee). Recorded here as done or deferred at merge.
2. Pitch price (a discount honoured by billing); `bid_rfp`, `merge` (free play), `adopt_ai` and `launch_fixed_fee` as rival actions.
3. Extend the pin to 2025 (ADR PT-0008) with FY2016-2025 paths; a second research pass for FY2009 and FY2012 lawyer counts (most are [A] ±15%) and FY2005 PEP and equity partners (Am Law 2006 table).
4. Notables who returned to practice after government or the bench (Varney, Holder, Breuer, Mitchell) leave the roster for good: model the return. LeBoeuf needs notables; Cooley has 2, Dewey Ballantine, White & Case and Reed Smith 3.
5. `courts.yaml` paces are [A]; the judges dossier's 2005 statistics put E.D.N.Y. slower (about 1.38 × S.D.N.Y.) and W.D. Tex. as fast as E.D. Tex.: PT-M3a's data to revisit.
6. Rival people's skills do not grow at a rival; a yearly growth step for key people if Reece wants rivals' stars to develop.
7. The Commercial Division roster in `judges.yaml` is approximate for 11 of 17 justices (nycourts.gov unreachable).
