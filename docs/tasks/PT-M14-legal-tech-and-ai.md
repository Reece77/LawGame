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

## Follow-ups
