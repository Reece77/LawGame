# ADR PT-0009: Conflicts of interest are an engine rule, not an event

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17

## Decision

1. Each matter records parties and their roles (client, adverse party, other). The state keeps an index of **current clients** and **adverse parties** per firm (former clients for 3 years by default).
2. **Direct conflict:** a firm may not open a matter adverse to a current client. The engine refuses (`ConflictError`) unless the client has given an **advance or specific waiver**, which is a client-relationship action with a probability from the relationship score and the GC's personality, and a relationship cost.
3. **Positional and business conflicts** (acting for a client's direct competitor, or against an industry the firm defends) are allowed but cost relationship with the affected key clients.
4. **Laterals and mergers** import their clients: the engine runs a conflicts check over the incoming client list; each conflict must be resolved (decline the hire, drop a client, obtain a waiver, or set an ethical wall where the jurisdiction allows lateral screens).
5. **Opening a matter without a conflicts check** (an option only when automation is weak or the player skips it) has a seeded chance of a hidden conflict surfacing later: a disqualification motion, a malpractice claim, a bar complaint (spec §11).
6. Rivals obey the same rules.

## Consequences

- Growth has a real tax: the bigger and more diverse the client list, the more work the firm must refuse. Mergers become conflicts puzzles, as in life.
