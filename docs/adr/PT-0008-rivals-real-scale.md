# ADR PT-0008: Rival firms at real scale in one economy, pinned to history to 2025

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Inherits: TST ADR-0010 (rivals as full entities, utility AI, fidelity tiers)
- Learns from: TST M34's `economy_scale` (in-game companies earned about a tenth of their real revenue, so every money threshold had to be scaled)

## Decision

1. **One economy at real scale.** Legal demand by region and practice is sized so that real firms' 2005 revenues are their in-game revenues (within ±10% at turn 0), and the market's total equals a published estimate of large-firm legal spend. Every threshold (ABS rules, insurance minimums, ranking cut-offs) is compared at face value. No `economy_scale`.
2. **History pin.** To December 2025, each real rival's revenue, lawyer count, equity partners and PEP follow its published path within a band (`history.pin_band`, ±15%), by steering its utility AI (rates, hiring, laterals) toward the path, and by dated events (mergers, collapses, splits) that happen as history had them **unless the player has changed the conditions** (for example, the player hired a third of a collapsing firm's top partners beforehand, which brings the collapse forward; or merged with the firm, which removes it). From 2026, rivals play freely.
3. **Fidelity.** Each rival keeps its top 30 partners and 10 rising associates as individuals (scoutable, poachable); the rest are pools by (practice, level, office region).
4. **Personalities:** `elite_lockstep`, `global_verein`, `performance_machine`, `litigation_boutique`, `tech_coast`, `regional_champion`, `volume_mid_market`, `big_four_legal` (from their ABS dates), each with utility weights for the rival action set (spec §10).

## Consequences

- Rankings, league tables and PEP comparisons feel real from the first month.
- The history pin is the riskiest balance work; it gets its own milestone checks (spec §16).
