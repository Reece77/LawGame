# ADR PT-0012: Partner Track's stream table, with kernel ids reserved

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Inherits: TST ADR-0002 and ADR-0013 in full

## Decision

`STREAM_IDS` is a new append-only table in `ptk/kernel/rng.py`. Ids **1–19** keep TST's names and meanings for kernel and people systems that are ported (people_gen 1, hiring 2, morale 3, events 6, founder 7, growth 8, reveal 9, tags 10, resign 11, retire 12, actions 13, delegate 14, board → `partnership` 17, poach 19), so that a future shared `sim-core` can adopt either game's numbering without renumbering. Ids **20–99** are Partner Track's (v1 below); 99 stays `misc` for tests.

| Name | Id | Key | Used for | Milestone |
| --- | --- | --- | --- | --- |
| `people_gen` | 1 | `(search_id, n)` | Generated people; search 0 is a scenario's starting staff; for a lateral search n = 0 draws the batch size and n ≥ 1 the n-th candidate (PT-M1b) | PT-M1a |
| `hiring` | 2 | `(offer_id,)` | An offer's acceptance draw | PT-M1b |
| `morale` | 3 | `(person_id,)` | Monthly morale noise | PT-M1b |
| `events` | 6 | `()` | The event director's month: the count, the matter draws (per open case matter by id), one draw per pick, one tone draw per queued event | PT-M6 |
| `founder` | 7 | `(founder_index,)` | A founding partner's build; index 0 is the player's | PT-M1a |
| `growth` | 8 | `(person_id,)` | Monthly growth noise | PT-M1a |
| `reveal` | 9 | `(observer_firm_id, person_id)` | Reveal record offsets | PT-M1a |
| `tags` | 10 | `(person_id,)` | Monthly tag reveals of employees | PT-M1b |
| `resign` | 11 | `(person_id,)` | The monthly resignation roll | PT-M1b |
| `actions` | 13 | `(seq,)` | Randomness inside a player action (tag rolls at an interview or reference check; ADR-0014) | PT-M1b |
| `delegate` | 14 | `(person_id, n)` | A delegate's nth hiring request in a turn, through PT-M1b's hook (TST ADR-0015) | PT-M2 |
| `partnership` | 17 | `(purpose, id)`: `(1, person_id)` a de-equitised partner's leaving (the clients' draws), `(2, person_id)` up or out (when they leave, whether for a client's in-house team) | The partnership's own draws (TST's `board` id; one call site, `ptk.sim.partnership.effects.partnership_stream`) | PT-M4 |
| `poach` | 19 | `(person_id,)` | A partner's month of flight: the approach roll, the suitor, offer and guarantee, the decision on an approach due that month, then which clients follow if they leave (one call site, `ptk.sim.partnership.flight.poach_stream`); PT-M5's rivals call the same hook | PT-M4 |
| `demand` | 20 | `(region, practice_index)` | Monthly legal demand noise | PT-M3 |
| `intake` | 21 | `(client_id,)` | New instructions from a client | PT-M3 |
| `matter` | 22 | `(matter_id,)` | Progress noise, events and the outcome | PT-M3 |
| `billing` | 23 | `(purpose, id)`: `(0, matter_id)` terms, `(1, bill_id)` a bill, `(2, client_id)` a client's month, `(3, bill_id)` a dispute's default answer | A matter's billing terms and money on account; a bill's guideline rejection, dispute, days to pay and short payment; bankruptcy; the default answer to a dispute (one call site, `ptk.sim.billing.formulas.billing_draws`) | PT-M3b |
| `conflict` | 24 | `(matter_id,)` | A hidden conflict surfacing | PT-M3 |
| `rfp` | 25 | `(rfp_id,)` | Panel and RFP awards | PT-M5 |
| `rival_firm` | 26 | `(*rival_key,)` | A rival firm's monthly decision noise | PT-M5 |
| `lateral` | 27 | `(person_id,)` | A lateral partner's answer to an offer, then their realised portability, the arrival window and each book client's month (one call site, `ptk.sim.partnership.laterals.lateral_stream`) | PT-M4 |
| `vote` | 28 | `(vote_id, person_id)` | Each partner's vote noise, in partnership votes and the MP election (one call site, `ptk.sim.partnership.governance.vote_noise`) | PT-M4 |
| `strain` | 29 | `(person_id,)` | A generated person's starting strain (PT-M1a); burnout events (PT-M6) | PT-M1a |
| `campus` | 30 | `(year, school_index, search_id)` | Campus candidate pools: one generator per school tier visited by each campus search (PT-M1b added `search_id`, so two practices' searches do not draw the same people) | PT-M1b |
| `client_gen` | 31 | `(client_index,)` | Generated clients and their GCs | PT-M3 |
| `macro_law` | 32 | `(indicator_index,)` | Seeded legal indices after 2025 | PT-M10 |
| `judge_gen` | 33 | `(court_index, n)` | The n-th generated judge of a court (courts.yaml order) at game creation; real judges arrive with PT-M5 | PT-M3a |
| `book` | 34 | `(founder_index,)` | The clients a founding partner's book of business came from, at game creation | PT-M3a |

## Consequences

- A test enumerates every `stream(` call site, as in TST.
