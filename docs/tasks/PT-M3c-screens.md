# PT-M3c: Matters, clients and practices screens

**Goal:** the player can see and run the game's heart: named matters with a staffing board, clients and their relationships, practices and their demand.

**Spec:** §16 (Matters, Matter, Clients, Client, Practices, Business development in part) · **Depends on:** PT-M3a; PT-M3b for the money columns · **Lane:** C

## Sub-tasks (commit after each)

1. **Matters list** (TanStack, saved views): client, practice, lead, phase, budget against actual, hours this month, WIP, billed, realisation, risk.
2. **Matter page:** the staffing board (people with free capacity and familiarity in the practice; drag to assign; hours per month; strain warnings), phase timeline, bills, events, settlement offers.
3. **Clients list and client page:** wallet estimate (a range), our share, relationship, relationship partner, practices used, panel status, GC (revealed), cross-sell map with an Introduce action.
4. **Practices screen:** demand trend, our revenue and share, capacity, utilisation, leverage, rates against the rate card.
5. **Explain** on utilisation, realisation, matter margin and win probability (as a band, never the number).
6. **Playwright:** staff a new named matter, bill it, see realisation; introduce a colleague to a client.

## Acceptance criteria

- [ ] No business logic in the front end; every number formatted from the API.
- [ ] The staffing board refuses an over-capacity assignment with the engine's error, and shows conflicts as the engine reports them.
- [ ] `pnpm lint && typecheck && test` and e2e green; `Milestone-Tag: pt-m3c-done`.

## Decisions made

## Follow-ups
