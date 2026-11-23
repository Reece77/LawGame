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

- [ ] Hours on each task equal base hours × efficiency (property test); money still reconciles with hours (PT-0005).
- [ ] By 2030, a fully adopted firm's exposed tasks take 40-70% fewer hours (Reece's question 15 default; printed on seeds 1-10).
- [ ] A firm that adopts early and moves exposed work to fixed fees earns more PEP in 2026-2030 than one that adopts and stays hourly, on at least 7 of 10 seeds; one that never adopts loses realisation and RFPs (printed).
- [ ] Juniors' growth falls without training when AI removes their review hours, and training restores at least half of it (printed).
- [ ] T1-T12 to 2015 unchanged (eras before 2016 are weak); T12 holds at December 2025.
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
9. **Products** (from stage 3): new matters of the kind are fixed-fee at price = expected fees (standard hours) × the market's efficiency on the kind's task mix × `price_bp` (60–150%, default 100%). The billing model draw keeps its order (the product only overrides the result), so other matters' terms are unchanged.
10. **RFPs** from 2023: the player's score gains 0.6 × (the firm's AI score − the market's), each the eras' adoption weighted by their strength on the exposed tasks; a new pitch claim `ai_efficiency` is substantiated when the firm is at or above the market.
11. **Learning** (ADR PT-0006 §4): a record's substantive share × (1 − 1.0 × r × (1 − 0.8 × cover)), where r is the share of the person's task-mix hours AI removes and cover = programme hours / 40 (at most 1). Training hours are non-billable (`other` time in staffing) and count as substantive.
12. **The Knowledge and AI area** is available with the CKO's seat (stage 4); its rule keeps the training programme at its guardrail, subscribes newest era first within a budget a lawyer, and puts rollouts to the partners; an era's first investment (which buys its platform) is a one-off proposal (spec 9.4's "any AI platform above the limit").
13. **Practice save `pt-2022`** (`ptk practice-save pt-2022` or `--year 2022`): the biglaw spin-out played to December 2022, then grown by PT-M7's table twice (114 lawyers, stage 3), for the manual check and e2e `m14.spec.ts`.
14. **Balance scripts** (`ptk/balance/tech.py`, one line in `strategies.VARIANTS`): `never`, `ai-hourly`, `ai-fixed` (and `ai-untrained` for the learning reading) are steady plus a growth push toward 110 lawyers from 2016 (products open at 101 lawyers; steady alone peaks below it), so the three differ only in technology and pricing.

READINGS_PLACEHOLDER

## Follow-ups
