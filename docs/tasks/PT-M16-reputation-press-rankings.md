# PT-M16: Reputation, press and rankings

**Goal:** a firm's standing is earned and public. Reputation by practice and region builds over about a decade from outcomes, league-table positions, stars and directory bands, and gates the rates a firm can charge and the work it wins. The legal press reports, the managing partner's public claims are held to account, and the yearly revenue and profit tables, quarterly league tables and October directory rankings put every firm, the player's included, in its place.

**Spec:** §7.1 (the appeal's reputation term), §12.1-§12.3 · **ADRs:** PT-0008 (rivals at real scale), PT-0012, PT-0013 (real people in the press: professional matters only) · **TST to port:** formulas.md §29 (press moments, promises, credibility, feuds) and §30.4 (rankings); `tst/sim/press/` · **Depends on:** PT-M7b (`pt-m7b-done`); inherits the known misses T3 lawyers and T4 steady (Reece, 2026-11-22) · **Lane:** C (beside PT-M10 in lane A and PT-M9 in lane B)

## Lane

- **Owns:** `ptk/sim/reputation/`, `ptk/sim/press/`, `ptk/sim/rankings/` (new), the reputation stand-in it replaces (the familiarity-based `Rep` in `ptk/sim/matters/` appeal and PT-M7b's card), the Rankings and Press screens, `reputation.*`, `press.*`, `rankings.*` keys, RNG ids **70-79**.
- **Must not edit:** `ptk/sim/macro.py`, the rivals' pin and `ptk/balance/` (PT-M10: you may ask lane A to re-read targets; do not change the runner); `ptk/sim/org/` and automation (PT-M9). Read rivals through `ptk/sim/interfaces.py`, adding thin wrappers where needed.
- **Shared files:** keep both sides; re-chain migrations if another merged first.

## Sub-tasks (commit after each)

1. **Reputation** (spec §12.1): per (firm, practice, region) 0-100, public; monthly moves from public outcomes (won trials, closed public deals), league-table positions, stars joining and leaving, directory bands, malpractice and scandals later (PT-M15), and drift toward the firm's long-run mean. Real rivals start from their 2005 standing (from `firms.yaml` and the dossier's practice strengths); a new firm starts low (default 15 in its founders' practices, 5 elsewhere). **Prestige** = revenue-weighted average reputation plus a profit-per-partner rank term; it replaces PT-M7a's recruiting proxy.
2. **Reputation gates rates and work:** the appeal's reputation term uses real reputation; the new-firm card (PT-M7b) rises with reputation in each practice, reaching the top card only near the top of the market's reputation (curve keys in `reputation.*`). Pace: a well-run firm takes 8-12 years to reach the top decile in a practice (printed on seeds 1-10).
3. **The legal press** (TST §29): press moments (ranking day, a big verdict, a lateral splash, a merger, layoffs, a collapse nearby, salary-scale moves) with bold, measured or deflect answers; public claims checked at their deadlines; credibility; rival managing partners as characters with statements. **ADR PT-0013:** real lawyers appear only in professional matters (moves, matters, rankings), never misconduct, private life or controversy (test).
4. **Rankings** (spec §12.3): the revenue and profit-per-partner tables each spring for the prior year (an Am Law 100 and 200 analogue, the player included once large enough); quarterly league tables by practice and region (deal counts and values from matters, rivals' from their flow); the October directory bands 1-6 per practice and region and individual bands, from reputation, key matters and the March submission (an action: choose up to five matters and referees; each referee spends a little of a client relationship).
5. **Best places to work** (associate survey) from morale, hours, pay and training; it feeds campus appeal.
6. **Screens:** Rankings (tables, league tables, directory bands with history), Press (moments, claims and their status, credibility), reputation on Practices and on rival pages; e2e: a March submission and an October band.
7. **Balance (with lane A):** re-read T3 lawyers and T4 steady on seeds 1-10 after sub-task 2; tune only `reputation.*` keys; record before and after values. If they reach their bands, ask lane A (or, after PT-M10 merges, do it yourself under CLAUDE.md §11 rule 8) to remove their known-miss rows.

## Acceptance criteria

- [ ] Reputation stays in 0-100 (property test); a new firm cannot bill at the top card in its first five years on any of seeds 1-10.
- [ ] The 2005 directory bands put history's leaders in band 1 for their known practices (for example Wachtell in M&A, Cravath in corporate, Skadden in M&A and litigation), at least 80% agreement with the dossier's strengths.
- [ ] Public claims are checked at their deadlines and move credibility as TST §29.3's worked examples, in PT units.
- [ ] No real person is the subject of a restricted press moment (test); no hidden value reaches the API or a prompt.
- [ ] T3 lawyers and T4 steady re-read and printed with their seed tables.
- [ ] `make check`, `make e2e` and the nightly balance run green with known misses as recorded; `Milestone-Tag: pt-m16-done`.

## Manual check (Reece)

Play a fresh campaign to 2010 and read each spring's tables and October's bands: does the firm's climb feel earned?

## Decisions made

Recorded by the PT-M16 session (2026-11-22). Readings are seeds 1-10, steady, January 2005 to December 2015 (`tools/reputation_pace.py`, `ptk/standing_pace.py`); "main" is `b5cfdd0` (before PT-M9 merged) on the same machine.

1. **Reputation's model** (`ptk/sim/reputation/`, spec 12.1). Per (firm, practice, region) 0-100 (one region, New York, until PT-M11). Each month `value += speed x (mean - value) + pulses`, the long-run mean `floor 5 + size 15 x s + record 65 x r + pep 15 x q`: s the practice's lawyers (log, full at 300), q the PEP percentile among firms with a PEP, r the record: the player's public outcomes (named matters by outcome and size, over 36 months, full at `record_full`), a rival's franchise (0.6 in its `firms.yaml` strong practices, generated firms none, + 0.4 x its share of the practice's market). Pulses: the player's outcomes, star partners (book >= $3M) joining and leaving, rivals' key partners leaving, league-table places (top 3, top 10), October's bands, the press and events (`interfaces.reputation_change`, previously a no-op). Real rivals start at their mean, a new firm at 15 / 5 (the brief). Prestige = revenue-weighted reputation + 10 x PEP percentile; `reputation.prestige.offer_weight` x prestige / 100 replaces `hiring.prestige_term` (0) in offer scores.
2. **The 2005 bands.** With directory thresholds 72/60/50/40/30/15, 118 of the 123 dossier strengths (firms.yaml `strong`) start in band 1 (agreement 96%; Wachtell M&A 85, Cravath and Skadden band 1 as the brief names; test `test_the_2005_bands_put_historys_leaders_in_band_1`). Generated firms' largest pools are not a franchise (their record is market share only), so they do not crowd band 1.
3. **The appeal's reputation term** (spec 7.1): `Rep = the partners' standing in the practice (the best partner's familiarity, PT-M3a's measure) + reputation.appeal_span x reputation / 100 + the band's appeal_bonus`. A flat floor in place of the partners' standing (0.75, 0.9, 0.95, 1.0 tried) gave a new firm appeal in practices where no partner has standing; it took work it could not serve and the first-year guards broke (PT-M17's annuity test's firm lost money in 2005 at every floor; with the standing restored the branch matched main exactly). **For Reece:** reputation adds to the partners' standing rather than replacing it; the stand-in's measure survives as the partners' personal standing, which is what the earlier milestones' guards pin.
4. **`appeal_span` against PT-M4's exodus guard** (`test_the_exodus_spiral`: heeded at most 1 and ignored at least 3 of 10 dissolved; main 1 and 3+), my key (CLAUDE.md 9 rule 2): span 0.05 1/3, 0.1 1/2, 0.15 2/3, **0.2 1/3**, 0.25 2/4, 0.3 3/3. The guard is knife-edge (non-monotone in the span); 0.2 passes and gives a top-decile firm about +0.16 Rep.
5. **The card** (sub-task 2): PT-M7b's target reads `card_progress` = reputation / (0.95 x the market's top-decile reputation in the practice), curve 2 (`reputation.card`, replacing `rates.card.full_reputation` and `curve`); `start_bp` 9850 and `step_bp` 50 stay PT-M7b's. Acceptance: the highest share any practice reached in the first five years is 99.0-99.6% on seeds 1-10 (none at the full card; nightly test `tests/balance/test_pt_m16.py`).
6. **Pace** (sub-task 2: 8-12 years to the top decile): `record_full` 30 -> 50 and `pulse` 1.5 -> 0.5 (at 30 / 1.5: median 7 years, 5-9, and private equity reputations saturated at 100; at 50 / 1.5: median 7.5, 6-11, still 100 on two seeds). At 50 / 0.5: **8 of 10 seeds reach the top decile, after 7, 8, 8, 8, 8, 9, 10, 10 years** (median 8); seed 8 does not by 2015, seed 9 dissolves (as on main). The practice is private equity on 9 of 10: its market's top decile (35.5) is low, few real firms being strong there.
7. **The press** (TST 29, ported): moments are the press's own (answered on the Press screen by `answer_press`, an unanswered one gets the press office's measured answer at its month's end), not the event director's; effects in reputation points for TST's brand-target points (same numbers), audience 0.5/1.0/1.5 by the firm's stage (below 2, below 4, 4+); claims are Partner Track's (headcount, no layoffs, matching the scale, a directory band); a broken claim raises PT-M17's Reckless source `broken_claim` and costs partners' confidence for trust; only real rivals' managing partners speak (164 firms' moves made a jab every month). **ADR PT-0013:** layoffs, collapse, jab, rivalry and reminder moments never carry a person; a real managing partner's jab is spoken by the firm's spokesperson; the state holds people by id only and the API names them, so `world.real_people` off changes nothing but names (PT-M5's test).
8. **Rankings**: tables in April for the prior fiscal year (revenue 200 places, PEP 100, firms of $60M or more, the player recorded each December); league tables at each quarter's end for practices with deal or restructuring kinds (the player's closed matters at fees x 400; rivals' a quarter of their practice revenue x 0.6 in deals of the practice's typical size); bands in October (the player adds key matters and its submission: +6 x strength, or -4 without one); individuals: rivals' real notables by standing (elite 1, leading 2, strong 3) and the player's partners who led 3+ public matters in three years; Best places to work in July (before August's campus offers). Each list's latest edition is in the state and every edition in the new `ranking_entry` table (the screen's history), so the live state does not grow.
9. **Streams** `press` 70 (the month's reminder waits) and `press_rival` 71 (`(*rival_key, n)`); ADR PT-0012's table.
10. **Schema** v15 (`0015_standing`), re-chained after PT-M9's `0014_automation`, which merged first.
11. **Band 6 and October's pulses** (my keys): band 6 from 20 -> 15 and the bands' reputation points [2, 1.2, 0.6, 0, -0.4, -0.8] -> [2, 1.2, 0.6, 0.2, 0, 0]. At 20 no new firm earned a band in its second October on seeds 1-8 (reputation 10-20 less the missing submission's 4), and band 6 cost reputation that being unranked did not. At 15, seeds 1 and 3 enter band 6 in their founders' practices by October 2006 without a submission.
12. **Fixtures moved to robust seeds** (CLAUDE.md 9 rule 5; no assertion loosened): PT-M6's events property test (the first seed from 8 with an open matter at turn 8), PT-M4's guarantee test (seed 5: the scenario sinks seeds 2-4 and 7 on main too), the Screens API (seed 1: seed 3 opens no named matter by March now), e2e m3c (seed 18), m16 (seed 1, which earns band 6 by October 2006); e2e m7, m8 and m9 answer a blocking critical event in the practice save first (`answerBlocking`), the leadership API (answers a blocking critical event first, as the e2e do), PT-M1b's save round trip (compares without engagements closed in the last turn, which the loader never holds and billing never reads).

**T3 lawyers and T4 steady** (sub-task 7; their bands unchanged; PT-M10 had not merged, so the known-miss rows are lane A's to update):

| Seed | main lawyers | PT-M16 lawyers | main PEP | PT-M16 PEP |
| --- | --- | --- | --- | --- |
| 1 | 18 | 72 | $4.19M | $5.35M |
| 2 | 51 | 79 | $4.15M | $4.98M |
| 3 | 66 | 75 | $3.18M | $5.99M |
| 4 | 49 | 48 | $5.12M | $3.93M |
| 5 | 50 | 77 | $3.32M | $5.65M |
| 6 | 45 | 69 | $3.87M | $6.26M |
| 7 | 19 (dissolved) | 42 | -$3.39M | $5.03M |
| 8 | 49 | 53 | $5.48M | $3.56M |
| 9 | 47 | 13 (dissolved) | $3.97M | -$1.24M |
| 10 | 36 | 59 | $2.77M | $3.67M |
| **Median** | **48** | **64** | **$3.92M** | **$5.01M** |

T3 lawyers moves toward its band (100-250) but stays a miss; T4 steady moves away from its band ($0.5-1.2M): earned reputation lifts the card and demand, so a firm earns more per partner. No `reputation.*` key brings either into its band. **For Reece (proposed default):** keep both known misses with these readings; T4 steady's band was set before reputation could raise a firm's card, and a $5M PEP for a 60-80 lawyer firm in 2015 is in line with the Am Law 50's profit per partner.

## Follow-ups

- Reputation by region once offices beyond New York arrive (PT-M11): the region axis is in the model and the stream keys.
- The top decile measured among firms with a real presence in the practice (generated firms' small pools make private equity's top decile low).
- A press moment's deep link from the inbox (the link id is a moment or a claim; the API could say which).
- `PressOut.claim_months` as two fields (the generated client sees the tuple as `number[]`).
- LLM-written statements for rival managing partners within PT-M6's budget (templates only now).
- Malpractice and scandals' reputation pulses with PT-M15.
