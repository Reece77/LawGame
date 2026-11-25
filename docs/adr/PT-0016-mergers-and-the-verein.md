# ADR PT-0016: Mergers and the verein: books at closing, identity, the pin

- Status: **Accepted** (PT-M13 session, 2026-11-25, under the brief `docs/tasks/PT-M13-mergers-and-the-verein.md`; for Reece's review with the milestone)
- Date: 2026-11-25
- Ports: TST formulas.md §28 (mergers and acquisitions: diligence, offers, integration, the exit) and §31 (the group: member companies with their own books), re-cast for partnerships
- Builds on: PT-0003 (partnership accounting), PT-0007 (votes), PT-0008 (rivals at real scale, the pin), PT-0009 (conflicts), PT-0012 (streams 130-139), PT-0013 (real people)

## Context

A rival firm (PT-0008) is an aggregate: lawyers in pools by practice and level, a handful of key people (`Member`s, generated on demand), annual run-rates of demand, revenue and cost, and a ledger that posts one month's P&L and pays the profit out at once (its cash is always zero). It keeps no balance sheet, no client relationships and no matters. The player's firm is the opposite: every person, client relationship, matter, bill and partner's capital account is a record. A merger has to turn the first kind of firm into the second, exactly, and a verein has to join the two kinds without ever mixing their books.

## Decision

### 1. Who survives (identity)

1. In an **integrated merger** the player's firm (its id, ledger, partnership and save) is the surviving entity. The other firm's `RivalFirm` ends with status `merged` and `successor` = the player's firm; its key leaves every client panel (`history.replace_panel_key`) and its people, clients and books become the player's firm's records at closing (section 2). The **name** and the **managing partner** are terms: the merged firm takes "ours", "theirs" or the combined name; the MP is the player's founding partner or the other firm's senior partner, who then holds the seat while the player stays a partner (PT-0007 §3's `ousted_mp_id` state, without an election lost).
2. **Absorption.** When the terms give the player's partners less than `mergers.absorbed_below_bp` of the merged profit pool, the player's firm is the one absorbed. Both partnerships vote as usual; when both pass, the campaign ends at closing with outcome **`exit`** (a new `GameOutcome`), scored (section 6). This extends PT-0007 §4 (game over only on dissolution or no successor): an exit is not a defeat, and spec 8.8 names it.
3. **Size limit.** Only firms of at most `mergers.max_lawyers` lawyers can be integrated (TST §28.5's 250-staff rule, re-cast): a larger firm can join a verein with the player, or absorb the player's firm, but is never materialised. Integrated targets have their headquarters in a city the game models (`cities.yaml`): generated firms headquartered "elsewhere" are verein candidates only.

### 2. Books at closing

Rivals keep no balance sheet, so the other firm's **closing balance sheet** is built from its run-rates at the month of closing, by one formula (diligence shows it exactly, section 4):

| Line | Rule |
| --- | --- |
| WIP (1100) | revenue (trailing 12 months) × `books.wip_days` / 365 |
| Receivables (1200) | revenue × `books.ar_days` / 365 |
| Cash (1000) | one month of its costs (`books.cash_months`) |
| Right-of-use (1510) and leases (2500) | its headquarters' rent (lawyers × the city's rent per seat × 12) × the lease's years left (a hidden draw) |
| Annuities (2600) | a hidden burden: `annuity_share` × (WIP + receivables), the share drawn once per firm in `books.annuity_share` |
| Revolver (2300) | `books.debt_share` × (WIP + receivables), raised if needed so capital is not negative |
| Partners' capital (3000) | the balancing figure, split equally over its equity partners (remainder to the first) |

So assets = liabilities + capital by construction. At closing one entry on the player's firm's ledger brings every line in, and each sub-ledger is built to match its account exactly: the capital split becomes each incoming equity partner's `Partner.capital_cents` (paid in, so no instalments); WIP becomes flow WIP (`FlowAccount`) on the book's clients by their share of the book; receivables become open fee bills on those clients, due over `books.ar_due_months`; annuities become `Annuity` records paid monthly (PT-M17's machinery); a lease outside the home city becomes an `Office` (opened `how = "merger"`) whose remaining term is the lease's.

**Eliminations** (what the merged balance sheet leaves out of the sum of the two):
1. **The headquarters lease in the player's home city** is surrendered at closing (office consolidation): its right-of-use asset and lease liability leave together, the surrender (`integration.surrender_months` of its rent) is paid from cash as an integration cost (6000), and its people sit in the home office at the home office's rent per head.
2. **Balances between the two firms** (fees one owes the other) are netted: none arise in the game today, the rule is kept for verein referrals.
3. **The other firm's P&L and drawings** do not cross: its ledger keeps its history under its own firm id and stops at closing.

The property test (`tests/property/test_mergers.py`) holds: for every balance-sheet account, merged after closing = player before + the other firm's closing sheet − eliminations, and every entry balances.

**The client book** (who the other firm's clients are) is drawn when talks open (stream `merger_book`): the clients whose panels carry its key, then, until the book's expected work reaches its revenue, clients of its city's market drawn by wallet in its practices; each with a relationship score, practices and, with probability `book.adverse_p`, an engagement adverse to another client (the conflicts that clearance must solve). The book is fixed for the deal; at closing it is combined **exactly**: every kept book client gets one relationship with the merged firm (a client both firms served keeps one relationship with the higher score and both firms' practices).

### 3. Conflicts clearance (PT-0009 §4)

When both votes pass, every client of both firms is checked. A conflict is (a) one of the player's open matters adverse to a book client, or (b) a book engagement adverse to a client of either firm. Each conflict asks the affected client for a waiver (an advance waiver always holds; otherwise the chance is `clearance.waiver_base` + `clearance.waiver_rel` × relationship / 100, stream `merger_clear`); a waived conflict keeps both (the player's matter is marked `waiver`). Otherwise the merged firm **keeps the better relationship**: the other client leaves (a book client is not taken on; a player's client loses its relationship and its open matters adverse to the kept client end `disqualified`, their WIP written off as PT-M3b does). After clearance no open matter of the merged firm is adverse to one of its clients without a waiver (a property test).

### 4. Hidden values

Engine-only: the other firm's annuity share, lease years left, its partners' true quality, the true conflict count before clearance, its partners' reservation and vote noise, the waiver draws. Diligence shows its run-rate P&L and closing sheet exactly (ADR-0007's "the books are the books") and the rest as ranges `[v (1 - h + o), v (1 + h + o)]` that always contain the truth, with `h` from `diligence.half_width` by level and a fixed offset `o` drawn once per firm (stream `merger_target`), so the midpoint is not the truth. No hidden value is in an API schema or an LLM prompt (a test).

### 5. The verein (TST §31, re-cast)

A verein is a brand shared by member firms, each keeping **its own books, partners and profit pool**: no ledger entry ever carries two members' firm ids (one entry, one firm, as everywhere). Each month the verein's shared costs (`verein.cost_base_cents` + `verein.cost_bp` × the members' revenue) are split by each member's share of the members' revenue; the player's share posts to its own ledger (6900, cash), a rival member's to its own (6900 against its drawings, so its cash stays zero). Referrals are introductions, not money: each quarter a member introduces the player's firm to one of its clients (a relationship at `verein.referral_score`), and the player's firm has no reach penalty in a member's city (PT-M11's `geo.reach_penalty`): a London member is a way into London without an office. Conflicts are checked across the verein: a matter of the player's firm adverse to a client on a member's panel needs a waiver as if the client were its own. A rival member's PEP stays its own (its profit over its equity partners); the player's PEP never reads a member's books (a property test).

### 6. The exit

The score (shown on the ending and in History): the founder's capital account, the founder's December allocations to date (PEP history, PT-M7's T2 score), and the merged firm's standing (its rank by revenue among active firms at closing). Nothing is drawn.

### 7. The history pin (PT-0008 §2)

A real rival that merges with the player's firm, absorbs it or joins its verein: merging ends its pinned path (status `merged`; its dated events are then called off by PT-M5's rule for inactive firms, and T11 reads only active firms); a verein member keeps its own path and pin (its books are its own). Before 2026 rivals merge with each other only as history did; from 2026 a quarter's draw (stream `rival_merger`) may combine an active rival with a smaller complementary one with chance `rival.free_rate_bp` (PT-0015's seeded world).

### 8. Streams (PT-0012, ids 130-139)

| Name | Id | Key | Used for |
| --- | --- | --- | --- |
| `merger_target` | 130 | `(*rival_key,)` at turn 0 | A firm's fixed hidden values: annuity share, lease years left, the diligence ranges' offsets |
| `merger_book` | 131 | `(deal_id,)` | A deal's client book, drawn when talks open |
| `merger_answer` | 132 | `(deal_id, round)` | The other side's answer to an approach (round 0) and to terms: each partner's noise |
| `merger_clear` | 133 | `(deal_id,)` | Clearance's waiver draws, in conflict order |
| `merger_people` | 134 | `(deal_id, n)` | The n-th materialised lawyer of the other firm's pools at closing |
| `integration` | 135 | `(deal_id, client_id)` | A book client's monthly balk at the merged rate card |
| `rival_merger` | 136 | `(0,)` a month's approach to the player (whether, then nothing more: the approacher is the best utility); `(1,)` a quarter's free-play merger from 2026 | Rivals' merger decisions |
| `verein` | 137 | `(verein_id, member_firm_id)` | A member's quarterly introduction |

## Consequences

- A firm that never merges plays as before: the only cost is the rivals' rare approaches (an inbox item the player may ignore).
- Integration costs are the engine's own: PT-M4's flight (a raised chance for partners whose PEP fell or whose practice is subordinated), clients balking at the merged card, the surrendered lease.
- Rivals' merger books are synthetic but consistent: diligence reveals the same sheet closing posts.
