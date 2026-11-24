# PT-M14: Legal technology and AI

**Goal:** technology changes how many hours work takes, era by era: e-discovery and offshore review in the 2000s, court-accepted technology-assisted review from 2012, contract analysis from 2016, generative AI from December 2022, agentic tools from 2025 (seeded after). A firm invests, trains and wins its partners' buy-in; clients expect the savings; and the firm chooses between hourly billing (losing revenue on exposed tasks), fixed fees (capturing the margin) and a reshaped pyramid, while protecting its juniors' learning.

**Spec:** §13, §7.7 (fixed fees and products), §5.3 (learning), §9.1 (the chief knowledge officer seat), §9.4 (the knowledge and AI area) · **ADRs:** PT-0011 (tech acts on tasks), PT-0006 §4 (learning by doing), PT-0015 (the seeded world), PT-0012 · **Depends on:** PT-M10 (`pt-m10-done`); PT-M9's knowledge area becomes available · **Lane:** C (beside PT-M7c in lane A and PT-M11 in lane B)

## Lane

- **Owns:** `ptk/sim/tech/` (new: eras, adoption, efficiency, client expectations, training, products), `legal_eras.yaml`, the task-level hours factor where matters compute hours (one hook in `ptk/sim/matters/` that multiplies a task's hours by the firm's efficiency, added through `interfaces.py`), AI realisation pressure on exposed tasks (one hook in billing through `interfaces.py`), the Technology screen, the CKO seat's effect, the knowledge area's rule, RNG ids **110-119**.
- **Must not edit:** partnership, pay and `ptk/balance/` (PT-M7c: register strategies in a new module with one line; ask lane A for re-reads), offices, regions and UK rules (PT-M11).
- **Shared files:** keep both sides; re-chain migrations if another merged first.

## Sub-tasks (commit after each)

1. **Research dossier** `docs/research/legal-tech.md` (sources, S/D/A): adoption curves and dated milestones (e-discovery platforms; offshore review and LPOs from 2008; *Da Silva Moore* and TAR in 2012; contract-analysis tools from 2016; ChatGPT on 30 November 2022; firm-wide generative AI tools from 2023; courts' AI standing orders and sanctions from 2023; agentic tools from 2025), measured hour savings by task where published, client surveys on AI discounts, and ALSP growth.
2. **Eras and efficiency** (ADR PT-0011 §2-§3): `legal_eras.yaml` with each era's window and strength by task to 2025, then seeded strength paths to 2034 (`tech_seed` 110); efficiency = 1 − exposure × strength × adoption, per task; hours on each task scale by it.
3. **Adoption:** investment (capex to 1500 and subscriptions to 6100), training hours (non-billable), the CKO's seat score, and partner buy-in (partners' adaptability and technology skill; a firm-wide rollout needs a vote-like threshold). Adoption decays without upkeep.
4. **Client expectations** (ADR PT-0011 §4): clients' willingness to pay for exposed tasks on hourly bills falls with the market's average adoption, with a lag; realisation on those tasks falls through the billing hook. Panel RFPs ask for AI and efficiency claims from 2023 (the pitch claim exists in PT-M5).
5. **Fixed-fee products** (spec §13): from stage 3, a firm can launch a fixed-price product for a matter kind (priced per matter, delivered with the firm's efficiency); margin is the firm's gain or loss.
6. **Learning** (ADR PT-0006 §4): hours that AI removes reduce juniors' substantive share; training programmes (non-billable hours, cost) buy it back. Print the 2030 cohort's growth with and without training.
7. **The knowledge and AI area** (PT-M9) becomes available with the CKO seat; its rule invests within its budget and trains.
8. **Screens:** Technology (eras, adoption by task, investment, training, client expectations, products), AI fields on the matter and pricing screens; e2e: adopt generative AI in 2023 and launch a fixed-fee product.

## Acceptance criteria

- [x] Hours on each task equal base hours × efficiency (property test); money still reconciles with hours (PT-0005).
- [x] By 2030, a fully adopted firm's exposed tasks take 40-70% fewer hours (Reece's question 15 default; printed on seeds 1-10).
- [ ] (known miss `PT-M14.fixed_fees`, PT-M18: 4/10 and 9/30; the never-adopter's losses: met) A firm that adopts early and moves exposed work to fixed fees earns more PEP in 2026-2030 than one that adopts and stays hourly, on at least 7 of 10 seeds; one that never adopts loses realisation and RFPs (printed).
- [x] Juniors' growth falls without training when AI removes their review hours, and training restores at least half of it (printed).
- [x] T1-T12 to 2015 unchanged (eras before 2016 are weak); T12 holds at December 2025.
- [ ] `make check`, `make e2e` and the nightly run green; `Milestone-Tag: pt-m14-done`.

## Manual check (Reece)

Load a 2022 save (`ptk practice-save --year 2022` if the session adds it; otherwise play to 2022) and decide the firm's AI strategy.

## Decisions made

Engineering and tuning decisions the spec, ADR PT-0011 and the brief left open (CLAUDE.md §11; TST's §9 rules by analogy). Numbers are `balance.yaml` `tech.*` and `legal_eras.yaml` unless named.

1. **Eras compound.** A firm's efficiency on task t = 1 − exposure_t × (1 − Π_e (1 − s_e,t × a_e)), where s_e,t is era e's strength on the task this month and a_e the firm's adoption of era e (with one era, ADR PT-0011 §3's `1 − exposure × strength × adoption`). The dossier (s8) left this to the brief.
2. **Era strengths from the dossier.** Each era's `tasks` weight is the dossier s8's "share of hours removed" ÷ (the task's `ai_exposure` × the era's 2025 strength), capped at 1 (generative AI's 2025 strength 0.45, so the spec's 0.5 falls in 2026); seeded targets after December 2025 (stream `tech_seed`, 110): generative AI U(0.65, 0.85) by December 2030, agentic U(0.6, 0.8) by December 2032 (the spec's range), the market's TAR, contract-analysis, generative and agentic adoption likewise. The market's generative-AI adoption is the dossier's "any use" share × a depth factor (~0.5: TR 2025's 26% active against ~85% any use) [D/A].
3. **Exposed tasks** are those with `ai_exposure` ≥ 0.5 (review, diligence, research, drafting). The 40–70% criterion is their unweighted mean saving for a fully adopted firm (every era at adoption 1) at December 2030.
4. **The hours hook** (`interfaces.tech_hours`): output an hour on a task mix is divided by the mix's factor Σ w_t × E_t / Σ w_t (progress and the staffing rule's expected output, so teams plan and work fewer hours), flow work's hours are multiplied by the flow mix's factor, and the pace check multiplies the planned pace by the phase's factor (a faster team is not "under-staffed"). A firm with no technology gets an exact no-op (factor 1.0, no training, no learning loss): T1–T12 to 2015 and the state cache are unchanged.
5. **Adoption** moves monthly toward target = coverage × (0.6 + 0.4 × training) × (0.5 + 0.5 × buy-in), at `speed` 0.08 × (1 + 0.5 × the CKO's e) up and `decay` 0.05 down (no upkeep: coverage 0, target 0). Training = programme hours × (1 + 0.3 e) / 30. Buy-in = the equity partners' mean (adaptability + technology) / 2 from 7 to 15 (engine-only: never in the API). An era with a platform needs it bought. Without a firm-wide rollout adoption is capped at the pilot's 0.35.
6. **The rollout vote** (stream `tech_vote`, 111): each equity partner supports at (adaptability + technology) / 2 + N(0, 2) ≥ 10; more than half must support; a failed vote may be retried after 6 months.
7. **Costs.** A platform is capex to `1500_ppe`, amortised to `6100_technology` over 36 months (no depreciation account exists; lane B's leases may add one); subscriptions (per lawyer a month × coverage) and the training programme ($50 an attendee-hour) post to 6100 monthly. Platform and subscription prices are [A] except generative AI's $1,000 a lawyer a month (dossier s7, third-party Harvey estimates).
8. **Client expectations** (`interfaces.tech_billing`) from January 2016 (`pressure_from`: the pre-2016 eras are weak and T1–T12 to 2015 must not move): on hourly, blended, capped and success-fee bills and flow bills, each task's cut = 0.7 × max(0, 1 − E_market / E_firm) + 0.10 × (1 − E_market), at most 0.6, with E_market the market's efficiency 12 months earlier; a bill's cut weights the kind's task mix by the hours the firm spends on each task. Fixed fees, retainers and contingency are not cut.
9. **Products** (from stage 3): new matters of the kind whose drawn terms are hourly, blended, capped or fixed become fixed-fee (success, contingency and retainer terms stay the client's choice) at price = expected fees (standard hours) × the market's efficiency on the kind's task mix × `price_bp` (60–150%, default 100%). The billing model draw keeps its order (the product only overrides the result), so other matters' terms are unchanged.
10. **RFPs** from 2023: the player's score gains 0.6 × (the firm's AI score − the market's), each the eras' adoption weighted by their strength on the exposed tasks; a new pitch claim `ai_efficiency` is substantiated when the firm is at or above the market.
11. **Learning** (ADR PT-0006 §4): a record's substantive share × (1 − 1.0 × r × (1 − 0.8 × cover)), where r is the share of the person's task-mix hours AI removes and cover = programme hours / 40 (at most 1). Training hours are non-billable (`other` time in staffing) and count as substantive.
12. **The Knowledge and AI area** is available with the CKO's seat (stage 4); its rule keeps the training programme at its guardrail, subscribes newest era first within a budget a lawyer, and puts rollouts to the partners; an era's first investment (which buys its platform) is a one-off proposal (spec 9.4's "any AI platform above the limit").
13. **Practice save `pt-2022`** (`ptk practice-save pt-2022` or `--year 2022`): the biglaw spin-out played to December 2022, then grown by PT-M7's table twice (114 lawyers, stage 3), for the manual check and e2e `m14.spec.ts`.
14. **Balance scripts** (`ptk/balance/tech.py`, one line in `strategies.VARIANTS`): `never`, `ai-hourly`, `ai-fixed` (and `ai-untrained` for the learning reading) are steady plus a growth push toward 110 lawyers from 2016 (products open at 101 lawyers; steady alone peaks below it), so the three differ only in technology and pricing.

15. **Tuning (rule 1, this milestone's keys), with the readings it followed** (`tools/tech_readings.py`, seeds 1-10; each run steady to December 2015, then `never`, `ai-hourly` and `ai-fixed` to December 2030):
    - run 1 (buy-in 7-15, support score 10, discount 0.10): pt-2022's 26 equity partners average (adaptability + technology) / 2 = 7.0 (technology 4.1), so no rollout passed and adoption stayed at the 0.35 pilot cap; fixed beat hourly on 2 of 10. **`buyin_from` 7 -> 4, `buyin_to` 15 -> 12, new `buyin_floor` 0.7, `support_score` 10 -> 6.5**; the scripts' growth push waits for utilisation 0.6 and a quiet bank (rule 2: it hired seeds 3, 9 and 10 into insolvency).
    - run 2: every surviving seed's rollout passed (generative AI adoption 0.82-0.84 by 2030); fixed beat hourly on 5 of 10. **`clients.discount` 0.10 -> 0.25** (dossier s4); the `ai-fixed` script retires a product whose closed matters billed less than their hours at standard rates (rule 2: the screen shows the product's P&L).
    - run 3: 4 of 10. **Products replace hourly-type terms only** (decision 9).
    - run 4 (final): 4 of 10, the table below.

| seed | never PEP 2026-30 ($M) / realisation / RFPs won-lost from 2023 | ai-hourly | ai-fixed | fixed > hourly |
|---|---|---|---|---|
| 1 | 29.78 / 68.6% / 2-157 | 37.70 / 77.5% / 4-156 | 47.26 / 97.9% / 5-156 | yes |
| 2 | 36.36 / 65.4% / 6-153 | 31.88 / 75.8% / 15-98 | 32.94 / 83.6% / 15-146 | yes |
| 3 | dissolved before 2016 (steady, every branch) | — | — | — |
| 4 | 36.84 / 67.0% / 8-143 | 46.44 / 76.4% / 26-140 | 46.44 / 76.4% / 26-140 (stage 2: no products) | tie |
| 5 | 39.62 / 69.9% / 3-156 | 47.63 / 77.6% / 20-153 | 37.12 / 75.2% / 19-153 | no |
| 6 | 29.04 / 67.0% / 6-160 | 52.12 / 82.6% / 18-148 | 47.97 / 79.7% / 18-148 | no |
| 7 | 35.66 / 72.5% / 12-163 | 48.04 / 92.7% / 34-135 | 80.61 / 135.9% / 33-136 | yes |
| 8 | 43.55 / 75.9% / 8-153 | 50.89 / 83.5% / 28-135 | 60.00 / 104.8% / 27-138 | yes |
| 9 | dissolved before 2016 (steady, every branch) | — | — | — |
| 10 | dissolved 2016-2030 | 50.47 / 80.4% / 11-151 | 26.47 / 74.2% / 15-76 | no |

    The never-adopter loses realisation (65-76% against the adopters' 76-93%) and RFPs (2-12 won from 2023 against 4-34) on every surviving seed; clients' AI cuts over the trailing months at December 2030 are $47.6-80.3M for `never` against $6.0-15.9M (hourly) and $1.3-13.7M (fixed). **Criterion 3's "at least 7 of 10" is not met (4 of 10; 4 of the 7 seeds with products)**: see the question for Reece below.
16. **Criterion 2** (fully adopted exposed tasks at December 2030, seeds 1-10): 51.1, 52.4, 55.8, 54.9, 54.5, 55.1, 55.4, 51.9, 52.4, 51.2% fewer hours (band 40-70%; also `tests/unit/test_pt_m14_tech.py`).
17. **Criterion 4** (learning, the 2030 cohort: juniors in years 1-3 present all year, from `ai-hourly`'s January 2030, growth in CA over 2030 with AI off / AI without training / AI with training, share of the loss restored), run 4: seed 1 3.118 / 2.348 / 3.038 (0.90); 4 5.396 / 3.936 / 5.327 (0.95); 5 2.907 / 2.031 / 2.796 (0.87); 6 4.233 / 2.971 / 4.093 (0.89); 7 4.518 / 3.535 / 4.501 (0.98); 8 3.531 / 2.767 / 3.464 (0.91); 10 3.490 / 2.544 / 3.421 (0.93); seed 2's cohort of 3 lost nothing (none on exposed work), seeds 3 and 9 dissolved. Training restores 0.87-0.98 of the loss (at least half: met).
18. **Criterion 5**: with PT-M14's two new fields left out, the state cache's nine runs (January 2005 to December 2015) are identical to the previous fixture month by month: T1-T12 to 2015 cannot have moved. T12 at December 2025: `make check-timing` (see the final report).

22. **T12 (rule 6).** CI's static job read T12 with two offices at 267 and 261 ms on two pushes (the pushes in between passed). Run alone on this machine, alternating with `main` in a separate worktree (ms, median December 2025 turn): main 170 / 158 / 166, PT-M14 163 / 150 / 161 (idle); after the memo below, main 234 / 198 / 192 / 222 / 185 / 195 / 205, PT-M14 199 / 225 / 209 / 211 / 198 / 198 / 202 (a busier machine). PT-M14 costs no measurable time; the test sits near its budget on CI runners on `main` too. Made proportional anyway, with identical results (state cache and golden unchanged): billing's kind task mix, and each hours record's substantive share, task split and card rate, are memoised on the task mix's identity. CI still read 258 ms, so `org.rules.has_mentor_teammate` (each person's morale and growth scanned their whole unit, through the linear `state.person`) now counts each unit's mentors once per view and people tuple (rule 8: PT-M11 has merged; identical results: the state cache's nine runs, golden and the org tests). After it, alternating with `main`: main 201 / 202 / 206 / 202, PT-M14 186 / 178 / 188 / 205 ms.

### Reece's decision on criterion 3 (via the product manager, 2026-11-23) and the final readings

**Decision:** price acceptance. A product above 100% of the market's cost is taken by a share of clients falling linearly from all at 100% to none at 150% (`tech.products.accept_full_bp` 10000, `accept_none_bp` 15000; billing's terms draw u2, which a product's price does not use, decides each client); the rest keep the terms they would have had. The `ai-fixed` script prices at 110% (80% take-up). Read on seeds 1-10 and 11-40; if neither reaches 7 of 10 (or the same share), a known-miss row owned by PT-M18 records both readings (authorised by the product manager).

19. **Run 5** (after merging main with PT-M11, price acceptance), seeds 1-10, `tools/tech_readings.py`:

| seed | never PEP 2026-30 ($M) / realisation / RFPs won-lost from 2023 | ai-hourly | ai-fixed (products) | fixed > hourly |
|---|---|---|---|---|
| 1 | 40.02 / 69.1% / 7-160 | 25.78 / 109.2% / 2-17 (the firm shrank to 9 lawyers, stage 2) | 25.78 (0) | tie |
| 2 | 39.27 / 69.8% / 6-161 | 40.04 / 73.3% / 14-146 | 38.70 / 75.3% (10) | no |
| 3 | dissolved before 2016 (steady) | — | — | — |
| 4 | 19.81 / 116.1% / 2-18 (shrank to 5 lawyers) | 50.25 / 82.5% / 5-168 | 50.25 (0: stage 2) | tie |
| 5 | 45.76 / 71.6% / 5-159 | 43.41 / 81.3% / 21-145 | 44.67 / 98.3% (10) | yes |
| 6 | 40.62 / 71.3% / 2-157 | 41.21 / 76.3% / 18-155 | 48.51 / 101.7% (10) | yes |
| 7 | 41.84 / 70.9% / 4-161 | 35.02 / 79.5% / 21-146 | 43.78 / 100.7% (10) | yes |
| 8 | 39.90 / 71.8% / 14-154 | 43.87 / 81.9% / 17-143 | 66.57 / 114.3% (10) | yes |
| 9 | dissolved before 2016 (steady) | — | — | — |
| 10 | 33.09 / 70.9% / 3-163 | 37.53 / 86.1% / 11-152 | 36.87 / 86.0% (10) | no |

    Fixed beats hourly on **4 of 10** (4 of the 6 seeds with products; the two losses are within 2-3%). The never-adopter's realisation is 69-72% on every seed it survives at size, against 73-86% for adopters, and it wins 2-14 RFPs from 2023 against 5-21. Criterion 2 is unchanged (51.1-55.8%); criterion 4: training restores 0.95-1.04 of the loss (seeds 2, 4-8, 10).
20. **Seeds 11-40** (criterion 3 only: `ai-fixed` forked from `ai-hourly` at the first month the firm could launch a product; the scripts are identical until then): fixed beats hourly on **9 of 30** (9 of the 16 seeds where the firm reaches stage 3 and launches products; 6 dissolve on both branches, 8 never reach stage 3).

| seed | ai-hourly PEP 2026-30 ($M) / realisation / lawyers 2030 | ai-fixed (products) | fixed > hourly |
|---|---|---|---|
| 11 | 0.00 / 0.0% / 43 | 0.00 / 0.0% / 43 (0) | no (dissolved) |
| 12 | 47.45 / 82.2% / 61 | 47.45 / 82.2% / 61 (0) | no |
| 13 | 31.61 / 80.0% / 73 | 31.61 / 80.0% / 73 (0) | no |
| 14 | 39.07 / 79.7% / 128 | 52.69 / 115.3% / 127 (10) | yes |
| 15 | 14.82 / 76.4% / 34 | 14.82 / 76.4% / 34 (0) | no |
| 16 | 0.00 / 0.0% / 16 | 0.00 / 0.0% / 16 (0) | no (dissolved) |
| 17 | 44.35 / 80.8% / 134 | 44.78 / 81.4% / 134 (10) | yes |
| 18 | 32.78 / 79.5% / 121 | 31.86 / 85.9% / 119 (10) | no |
| 19 | 10.78 / 126.1% / 3 | 10.78 / 126.1% / 3 (0) | no |
| 20 | 39.60 / 80.0% / 125 | 39.40 / 75.8% / 137 (10) | no |
| 21 | 34.50 / 77.0% / 123 | 36.41 / 88.4% / 123 (10) | yes |
| 22 | 28.97 / 79.3% / 100 | 38.59 / 104.1% / 100 (10) | yes |
| 23 | 29.46 / 81.4% / 129 | 31.19 / 81.9% / 111 (10) | yes |
| 24 | 70.86 / 78.8% / 102 | 45.44 / 81.5% / 103 (10) | no |
| 25 | 32.73 / 81.2% / 132 | 35.49 / 95.8% / 164 (10) | yes |
| 26 | 15.34 / 138.0% / 2 | 15.34 / 138.0% / 2 (0) | no |
| 27 | 0.00 / 0.0% / 18 | 0.00 / 0.0% / 18 (0) | no (dissolved) |
| 28 | 44.92 / 85.8% / 122 | 50.08 / 89.2% / 122 (10) | yes |
| 29 | 54.79 / 83.2% / 106 | 80.07 / 114.3% / 118 (10) | yes |
| 30 | -1.65 / 83.3% / 35 | -1.65 / 83.3% / 35 (0) | no (dissolved) |
| 31 | 0.00 / 0.0% / 0 | 0.00 / 0.0% / 0 (0) | no (dissolved) |
| 32 | 14.76 / 82.6% / 30 | 14.76 / 82.6% / 30 (0) | no |
| 33 | 41.72 / 78.5% / 124 | 40.34 / 80.9% / 112 (10) | no |
| 34 | 43.27 / 80.9% / 35 | 43.27 / 80.9% / 35 (0) | no |
| 35 | 45.56 / 84.4% / 119 | 55.35 / 105.4% / 120 (10) | yes |
| 36 | 37.58 / 76.9% / 77 | 37.58 / 76.9% / 77 (0) | no |
| 37 | 0.00 / 0.0% / 41 | 0.00 / 0.0% / 41 (0) | no (dissolved) |
| 38 | 35.68 / 80.4% / 130 | 32.74 / 83.0% / 141 (10) | no |
| 39 | 11.78 / 138.3% / 4 | 11.78 / 138.3% / 4 (0) | no |
| 40 | 41.65 / 77.0% / 104 | 39.74 / 76.2% / 104 (10) | no |

21. **Criterion 3 is a known miss** (`ptk/balance/known_misses.py`, `PT-M14.fixed_fees`, owner PT-M18, authorised by the product manager): 4 of 10 on seeds 1-10, 9 of 30 on seeds 11-40. Where the firm offers products, fixed fees win 13 of 22 seeds; most misses are firms that never reach stage 3 (products' gate) or dissolve, which PT-M18's balance owns.

## Follow-ups

- Criterion 3 (known miss `PT-M14.fixed_fees`, PT-M18): firms that never reach stage 3 cannot offer products; PT-M18 may revisit the products' stage gate or the growth that reaches it.
- Products: a price below the market's cost could raise the firm's appeal for the kind (more work); products have no demand effect yet.
- Partners' buy-in: training covers associates and counsel only; a partners' programme (raising their technology skill) would give a player a way to win the rollout vote.
- Rivals' own adoption is the market's path; a rival that leads or lags on AI (ADR PT-0011 §4: "rivals and ALSPs move too") and ALSPs and the Big Four's legal arms (dossier s5) are not modelled.
- The pyramid-to-diamond reshaping is left to the player's hiring; no script tests it.
- Courts' AI standing orders and sanctions (dossier s1) as events (PT-M15's discipline machinery).
- The readings take about two hours on four cores (a 110-lawyer firm's turns run seconds each in 2025-2030); a state cache at December 2015 would halve them.
