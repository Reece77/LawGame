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
| `rfp` | 25 | `(0, client_id)` a client's monthly RFP roll; `(1, rfp_id)` an award | A panel review's or big-matter RFP's opening (bidders, practice, size) and award (PT-M5: the opening needed a key before the RFP has an id) | PT-M5 |
| `rival_firm` | 26 | `(*rival_key,)` | A rival firm's month: its demand shock, then one N(0, 0.1) per action, then the drawn actions' draws | PT-M5 |
| `lateral` | 27 | `(person_id,)` | A lateral partner's answer to an offer, then their realised portability, the arrival window and each book client's month (one call site, `ptk.sim.partnership.laterals.lateral_stream`) | PT-M4 |
| `vote` | 28 | `(vote_id, person_id)` | Each partner's vote noise, in partnership votes and the MP election (one call site, `ptk.sim.partnership.governance.vote_noise`) | PT-M4 |
| `strain` | 29 | `(person_id,)` | A generated person's starting strain (PT-M1a); burnout events (PT-M6) | PT-M1a |
| `campus` | 30 | `(year, school_index, search_id)` | Campus candidate pools: one generator per school tier visited by each campus search (PT-M1b added `search_id`, so two practices' searches do not draw the same people) | PT-M1b |
| `client_gen` | 31 | `(client_index,)` | Generated clients and their GCs | PT-M3 |
| `macro_law` | 32 | `(indicator_index,)` | Seeded legal indices after 2025 (unused: PT-M10 took ids 65-66 by its brief's lane, ADR PT-0015) | PT-M10 |
| `judge_gen` | 33 | `(court_index, n)` | The n-th generated judge of a court (courts.yaml order) at game creation; real judges arrive with PT-M5 | PT-M3a |
| `book` | 34 | `(founder_index,)` | The clients a founding partner's book of business came from, at game creation | PT-M3a |
| `rival_gen` | 35 | `(1, n)` a generated firm; `(2, n)` a boutique | A generated firm's making at turn 0; a month's boutique roll and founding (n: boutiques founded so far) | PT-M5 |
| `rival_people` | 36 | `(*rival_key, n)` | A rival's n-th key person, generated on demand from their member record (a pure function of the seed) | PT-M5 |
| `real_swap` | 37 | `(1, judge_index)`; `(2, judge_index)` | A real judge's generated name (used when `world.real_people` is off) and traits' spread; the generated judge who succeeds them | PT-M5 |
| `opposing` | 38 | `(matter_id,)` | A new case's opposing counsel (a named rival or a pool) | PT-M5 |
| `rival_fate` | 39 | `(*rival_key,)` | A rival's collapse hazard roll (drawn only when the hazard is above zero), then its people's scatter | PT-M5 |
| `rival_poach` | 40 | `(*rival_key, 0, made_turn)` | The answer to a rival's approach to one of the player's people (TST 15.6's key; PT-M4's flight keeps `poach`) | PT-M5 |
| `pro_bono` | 41 | `(firm_id,)` | A month's named pro bono matter: arrival, kind, hours, months, merits, opposing counsel, forum (spec 7.8) | PT-M7a |
| `seat_act` | 45 | `(seat_index, firm_id, slot)` | A seat holder's month under authority: the first uniform decides whether they take the right rule (TST 24.2); the actions' own draws follow on the same generator. seat_index: the seat's position in seats.yaml; slot: 0, or a practice group's unit id | PT-M8 |
| `pitch` | 46 | `(firm_id, person_id)` | A holder's quarterly pitch: whether (by true ambition), then which candidate (by true seat score and the committee's effect) (TST 27.1) | PT-M8 |
| `crisis` | 42 | `(kind, id)` | A bill's crisis write-down request: whether the client asks, then its size; kind 0 a matter's bill (id: the matter), kind 1 + the practice's index a client's flow bill (id: the client) (spec 14) | PT-M7b |
| `deal_collapse` | 43 | `(matter_id,)` | A deal's monthly chance to collapse in progress while its practice's driver index is below 1 (spec 14) | PT-M7b |
| `founder_life` | 50 | `(purpose, *key)`: `(1, person_id)` a retiring partner's departure (PT-M4's `depart` draws with it); `(2, person_id)` a bar election | The founder's life (one call site, `ptk.sim.founder.streams.life_stream`; lane C's range 50-59) | PT-M17 |
| `family` | 51 | `(head_id, index)` a member's making (index from 1); `(head_id, 0, k)` a month's life event of kind k (0 a partner met, 1 a child born); `(person_id, 1)` a child's month of development; `(head_id, 2, 0)` the January health step-back | The player's family and the health trigger of succession (one call site, `ptk.sim.family.people.family_stream`) | PT-M17 |
| `macro_seed` | 65 | `(index_number,)` an index's path (its position in `macro_data.SERIES`); `(len(SERIES),)` the recession regime | The seeded indices from January 2026 to December 2034, drawn once at turn 0 (ADR PT-0015) | PT-M10 |
| `scale_seed` | 66 | `(0,)` the rate rises; `(1,)` the salary scale's steps | The seeded January rate rises and the associate salary scale's steps from 2026 (ADR PT-0015) | PT-M10 |
| `investments` | 52 | `(person_id,)` | A player's month of investment and family-office returns (one call site, `ptk.sim.founder.personal.investment_stream`) | PT-M17 |
| `press` | 70 | `(firm_id,)` | The month's claim checks: a broken public claim's reminder wait (one generator a month, drawn per broken claim in id order; lane C's range 70-79) | PT-M16 |
| `press_rival` | 71 | `(*rival_key, n)` | A real rival's managing partner at their firm's move (a lateral hire, a team lift, a new office, a merger): whether they speak, then whether it is a jab at the player; n counts the firm's spoken moves that month | PT-M16 |
| `auto_quality` | 60 | `(area_index, firm_id, slot)` | An automated area's month (spec 9.4): the first uniform decides whether the owner takes the default rule's answer (q from the true seat score, less overload); a mistake's noise and the actions' own draws follow on the same generator. area_index: the area's position in `automation.areas`; slot: 0, or a practice group's unit id (lane B's range 60-64) | PT-M9 |
| `auto_events` | 61 | `(event_id,)` | An area owner's answer to a routine event (TST 40.5): the best displayed choice with probability q, else the second best | PT-M9 |

## Consequences

- A test enumerates every `stream(` call site, as in TST.
