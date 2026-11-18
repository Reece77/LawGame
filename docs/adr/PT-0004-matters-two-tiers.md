# ADR PT-0004: Matters in two fidelity tiers

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Extends: TST ADR-0010's fidelity tiers (individuals and pools), applied to work

## Context

A 50-lawyer firm runs about 400 open matters; a 3,000-lawyer firm runs tens of thousands. Simulating every matter individually, with staffing and outcomes, would swamp the player and the turn budget (TST's 2039 turns run in about 400 ms). Yet the game's drama lives in individual matters: the bet-the-company trial, the merger that collapses at signing.

## Decision

1. **Named matters** are individual entities with a client, practice area, kind, lead partner, a staffing plan of named people, a budget, hours by task and level, progress, an outcome and bills. A matter is named when any holds: expected fees ≥ `matters.named_min_cents` (default $250,000 in 2005 dollars, rising with the rate index); the client is a **key client** (top 20 by fees, or flagged); it carries a critical risk (bet-the-company litigation, a public deal, a regulatory investigation); or the player flags it.
2. **Flow work** is everything else: per (client, practice area, office) a monthly demand in hours by level, absorbed by the practice group's available people in proportion to their free capacity, billed at the group's blended realisation, with outcomes as a distribution that moves client satisfaction. Each person's month is the sum of their named-matter hours and their share of flow hours.
3. **Promotion and demotion.** A flow stream that produces a named-matter trigger opens a named matter (its hours move out of the flow). A named matter that finishes ends; no matter becomes flow mid-life.
4. **Rivals** have named matters only where they face the player (opposing counsel, co-counsel, a competing RFP); all else is flow at practice-pool level.
5. **Targets:** at the player's stage 5 (2,000+ lawyers), named matters ≤ 600 open at once (median), and a turn ≤ 600 ms on the reference save.

## Consequences

- The player manages perhaps 10–40 named matters at a time, which is the Football Manager squad scale; flow is managed through practice groups and automation (spec §9.4).
- Every person's hours, utilisation and strain are exact, because both tiers report hours per person.
