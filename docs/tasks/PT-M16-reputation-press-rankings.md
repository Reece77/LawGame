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

## Follow-ups
