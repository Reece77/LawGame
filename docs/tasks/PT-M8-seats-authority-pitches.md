# PT-M8: Seats, authority and pitches

**Goal:** the firm has a leadership. The player appoints people to the seats of spec §9.1 (executive committee, practice group leaders, office managing partners, the firm's general counsel, CFO, COO, CMO, CHRO, and later the pricing director and the chief knowledge officer); each seat's score moves the firm; seat holders get authority within guardrails and act each month; and they pitch big moves each quarter and report in their own voice.

**Spec:** §3 (stage unlocks), §9.1, §9.2, §9.3 · **ADRs:** TST 0014, 0015; PT-0007 (the partnership governs), PT-0012 (streams) · **TST to port:** formulas.md §18.3–18.4 (seats, support coverage), §24 (authority), §27.1–27.2 (pitches, reports); `tst/sim/org/` executives, authority, ceo (seat scoring only), pitches, reports · **Depends on:** PT-M7 (`pt-m7-done`) · **Lane:** B (beside PT-M7b in lane A and PT-M17 in lane C)

## Lane

- **Owns:** `ptk/sim/org/seats.py`, `authority.py`, `pitches.py`, `reports.py` (new), the Org screen's Leadership panel, the Inbox's pitch and report items, `seats.*`, `authority.*`, `pitches.*` keys in `balance.yaml`, RNG ids **45–49**.
- **Must not edit:** `ptk/sim/billing/`, `ptk/sim/partnership/`, `ptk/sim/matters/staffing.py`, `ptk/sim/macro.py` (PT-M7b is tuning them), `ptk/sim/people/founder.py` and any `founder`/`family` package (PT-M17).
- **Seat effects on others' systems** go through one function in `ptk/sim/interfaces.py`, `seat_effect(state, firm_id, seat_key) -> float` (the spec's `e`, −0.5..1). Wire the consumers in files you own now; wire those in PT-M7b's files (CFO collection, pricing realisation, COO support coverage) only after `pt-m7b-done`, by merging `main` before your final pull request. If PT-M7b has not merged when you are otherwise done, wait for its tag (sleep 600 between checks, up to 72 checks) before wiring.
- **Shared files:** keep both sides of `balance.yaml`, `CHANGELOG.md`, `docs/data-dictionary.md` and `rng.py` (your ids are 45–49 only). If another branch merged a migration first, re-chain your `down_revision` onto it; never edit another's migration.

## Out of scope

Automation areas, money limits, one-offs and the digest (PT-M9); the managing-partner election (PT-M4 built it) and succession (PT-M17); offices beyond the home city (PT-M11: office managing partner seats exist but stay vacant without a second office); merger pitches (PT-M13).

## Sub-tasks (commit after each)

1. **Seat data** (`seats.yaml`): every seat of spec §9.1 with its stage, eligible levels (partner seats need an equity or income partner; business-services seats a business-services person at manager level or above, or a partner), the score weights and the effect. Practice group leader per active practice group (PT-M2's unit leader becomes the seat holder; migrate existing leaders).
2. **Seat score and effect** (TST §18.3): `s` = Σ weight × the holder's skill (true values, engine-only), `e = clamp((s − 10)/8, −0.5, 1)`, vacant from the seat's stage = −0.5. The API shows the holder's revealed ranges and a fit band, never `s`. Appoint, replace and vacate actions (energy; a partner seat holder's confidence moves by their ambition when appointed or removed).
3. **The executive committee** (spec §9.2): 3 members at stage 3, up to 9 at stage 5; appointed by the MP until the partnership agreement's `exco_elected` term is voted on (default appointed below 100 lawyers, elected at the December vote from stage 3). Its average confidence is reported quarterly as the partners' meeting summary (TST §14.6's warnings, through PT-M6's events).
4. **Effects in your own files and through the interface:** MP (confidence +0.5 e a month, through `interfaces.confidence_change`), executive committee (decision quality of firm-wide proposals), practice group leader (staffing quality and associate morale in the group), general counsel (conflicts-check quality: PT-M3a's hidden-conflict chance × (1 − 0.4 e)), CMO (RFP pitch quality +), CHRO (associate morale and campus quality); CFO, pricing and COO after `pt-m7b-done` (lane note).
5. **Authority** (TST §24): per seat, what the holder may do without asking, inside guardrails set by the player (hire within a plan, staff within a group, write down within a band, pitch for RFPs within a price band). Holders act in phase 2 with their own energy and the stream `seat_act` (45), keyed by `(seat_index, firm_id)`; their decisions are logged and recomputed on replay (ADR-0015 test). The spec §9.4 one-offs are never within authority.
6. **Pitches** (TST §27.1): each quarter, seat holders with authority pitch at most one big move (chance by ambition, quality by seat score; stream `pitch` (46)): a lateral partner with a book (PGL), a new practice group (PGL), a campus class size change (CHRO), a rate move for a practice (pricing), a panel push on named clients (CMO), a fit-out or lease (COO), a cost programme (CFO). Each has a low and a high case, Approve, Modify or Decline, and a follow-through record (TST §27.1) that moves the holder's morale and confidence.
7. **Reports with a voice** (TST §27.2): quarterly, each chief seat holder's short report (MockLLMAdapter in tests; templates offline; the holder's persona and tags flavour it; no hidden values in the prompt).
8. **Screens:** the Org screen's Leadership panel (seats, holders, fit band, vacancies with a candidates list, authority guardrails), pitches and reports in the Inbox; e2e: appoint a CFO, receive and approve a pitch.

## Acceptance criteria

- [ ] TST §18.3's seat worked examples pass in PT units; a vacant CFO seat at stage 2 gives `e` = −0.5.
- [ ] No seat score, true skill or pitch outcome reaches the API or a prompt (test enumerating every new schema).
- [ ] Seat holders' actions replay identically (recomputation test); no one-off from spec §9.4 can be taken under authority (test).
- [ ] A strong practice group leader (score 16) against a weak one (score 6) gives the group at least 5 points better associate morale and 3 points better utilisation over 24 months, on seeds 1–10 (printed).
- [ ] At most one pitch a quarter per seat; a 100-lawyer firm sees 2–6 pitches a quarter (median).
- [ ] `make check`, `make e2e` and the nightly balance run green, or any changed target recorded with its before and after values; `Milestone-Tag: pt-m8-done`.

## Manual check (Reece)

In `pt-2008`, appoint a CFO and a CHRO, set their guardrails, and play to December 2008. Read the first quarterly reports.

## Decisions made

## Follow-ups
