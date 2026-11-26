# v3 outline: the world

**Status: OUTLINE for Reece's decisions (product manager, 2026-11-26).** This sets out scope, sequencing and rough milestones. Full briefs, research dossiers and formulas come milestone by milestone, starting the day v2 closes (`pt-m18-done`).

## What v3 is for

By the end of v2, Partner Track plays thirty years of a US firm with offices in American cities and London, twenty practices, mergers and the verein, technology eras, risk, reputation and the founder's life. What it lacks is **the rest of the legal world**: the firm can't follow its clients to Paris, Hong Kong or Dubai, can't take outside money, and never competes with the Big Four or alternative legal service providers (ALSPs). It also has one start and one lifetime. v3 adds the world, capital, new competitors, more ways to start and a second thirty years.

## Scope (spec §18, with §19's ideas)

1. **The world:** Europe, Asia-Pacific and the Gulf, each under local rules: who may practise local law, foreign-firm licences and associations, ownership, local salary scales and markets, local rivals, currencies and exchange rates.
2. **Outside capital:** alternative business structures (ABS) where allowed (England and Wales from 2012, Arizona from 2021, the Utah sandbox from 2020), listing where allowed (Australia from 2007, London's AIM and main market from 2015), private equity through management-services structures in the US, and shareholders beside partners.
3. **New rivals:** the Big Four's legal arms (strong in Europe and Asia, barred from most US practice) and ALSPs taking the work technology has exposed (managed review, contracts, compliance), with clients bringing work in-house.
4. **Litigation finance as a business:** beyond PT-M12's funders of single cases, portfolio funding, monetising WIP and receivables, and a firm-owned funding arm where the rules allow.
5. **Conversations** (from TST v6): pitches, lateral interviews, partner pay talks, merger talks and client crises as conversations in which the engine sets the possible outcomes and the LLM only moves the odds within them. Every conversation also works without the LLM.
6. **Scenarios:** a 2010 New York post-crisis start and a 2010 London start, set challenges, and the scenario framework TST's `modes/` provides.
7. **The people pack (spec §19 ideas 1-3 and 6):** the alumni engine, the revolving door (government and the bench), trial weeks for key jury trials, and secondments.
8. **Dynasty mode:** a second thirty years, 2035-2064, in a fully seeded world; the player continues as the successor managing partner, and the founder as senior counsel.

**Out of v3:** Latin America and Africa (v4 candidates); a shared world with Tech Startup Tycoon (spec §19 idea 12; `sim-core` should not preclude it).

## Lessons from v2 applied

- **Foundations run alone.** Anything that changes the ledger or the turn (the world framework, dynasty's run length) runs with no other simulation lane open.
- **At most three parallel lanes**, each owning its own systems under CLAUDE.md §12 rule 6. A region lane owns its own region's data and nothing shared.
- **A balance pass after every phase**, not only at the end, so misses never pile up the way v2's did by PT-M18.
- **Targets judged on seeds 1-40** from the start (CLAUDE.md §12 rule 1).
- **Turn time budgeted per phase.** Each phase states its December 2034 timing allowance before it starts, because v3 adds regions, currencies and rivals, which all cost time.

## Rough milestones

| # | Milestone | Phase / lane | Ports from TST | Notes |
| --- | --- | --- | --- | --- |
| PT-M19 | The world framework: jurisdictions, currencies and FX, local rules, local markets | 0, alone | `geo/`, `geopolitics/rules` (by analogy) | Multi-currency ledger (integer minor units per currency, office functional currencies, USD consolidation, a translation reserve) with a new ADR; FX history 2005-2025 then seeded; PT-M11's London rebuilt as the first instance |
| PT-M20 | Europe: Paris, Frankfurt, Brussels | 1, lane A | — | EU competition work in Brussels; local champions; Brexit 2016-2020 (the Irish roll, passporting); French and German ownership rules |
| PT-M21 | Asia-Pacific: Hong Kong, Singapore, Tokyo, Beijing and Shanghai, Sydney | 1, lane B | — | PRC law closed to foreign firms (representative offices, associations, the 2014 free-trade-zone joint ventures); Singapore's qualifying foreign firm licences; Japan's gaiben rules; Australia's listing and ABS rules |
| PT-M22 | The Gulf: Dubai (DIFC), Abu Dhabi (ADGM), Riyadh, Doha (QFC) | 1, lane C | — | Common-law free-zone courts; Saudi licensing and the 2020s opening; local partner rules |
| PT-M23 | World balance | 1b, alone | — | Global targets (below) on seeds 1-40; carried misses; the turn-time allowance |
| PT-M24 | Outside capital: ABS, private equity and listing | 2, lane A | `markets_public/` (IPO, valuation, the public market) | Shareholders and partners; dividends against distributions; a listed firm's share price; partner lock-ins; real listed firms as firm-level history only (ADR PT-0013) |
| PT-M25 | The Big Four and ALSPs | 2, lane B | rivals' utility AI | Competition for exposed tasks (PT-M14), managed services, clients' in-house teams; Arizona's ABS opening for a Big Four firm in the US |
| PT-M26 | Litigation finance as a business | 2, lane C | — | Portfolio funding, WIP and receivables monetisation, a firm-owned funding arm where allowed |
| PT-M27 | Phase 2 balance | 2b, alone | — | Capital and competitor targets |
| PT-M28 | Conversations | 3, lane A | `talks/`, `meetings` (TST v6 direction A) | Pitches, lateral interviews, pay talks, merger talks, client crises; template mode without the LLM |
| PT-M29 | Scenarios and challenges | 3, lane B | `modes/` | 2010 New York, 2010 London; challenges; scenario rankings |
| PT-M30 | The people pack | 3, lane C | — | Alumni engine, revolving door (the founder may end as a judge), trial weeks, secondments |
| PT-M31 | Dynasty mode, 2035-2064 | 4, alone | `dynasty/` | The successor managing partner; a seeded world after 2034; long-save performance and history compaction |
| PT-M32 | v3 balance and performance; closes v3 | 4b, alone | — | 60-year runs; every carried miss; the turn time at December 2064 |

## Proposed v3 targets (for approval in PT-M23, PT-M27 and PT-M32)

Each needs a dossier source before its band is set.
- **Global reach costs PEP:** a firm with most of its revenue outside the US earns less PEP than a US-focused elite firm of the same revenue, in the band real firms show.
- **Currency risk is real:** sterling's falls in 2008 and 2016 move a London-heavy firm's US-dollar PEP in the direction and size history did.
- **Local rules bind:** no foreign firm practises PRC law, and Gulf, Singapore and Japan offices follow their licences (tests, not bands).
- **Outside capital is a trade, not a cheat:** a listed or private-equity-backed firm grows faster but pays for it in partner retention and distributions; no capital strategy dominates.
- **The Big Four's and ALSPs' share** of the work they compete for stays inside the band history shows to 2025.
- **Dynasty is believable:** over 2035-2064 the market's size, the number of firms and the profit levels stay within plausible ranges of their 2005-2034 path.

## The `sim-core` checkpoint is now due

ADR PT-0001 §5 set two conditions for planning the extraction of a shared `sim-core`: TST v5 closes and Partner Track's PT-M7 has merged. Both are met: TST closed v5 on 2026-11-21. v3 would port four more TST modules (`markets_public/`, `talks/`, `modes/`, `dynasty/`), which makes vendored copies larger and drift more likely. **The product manager will write the extraction plan as a short decision document during PT-M19.** Extraction also needs changes in TST's repository, so it needs a TST session that Reece authorises; no Partner Track session writes there.

## Decisions for Reece (proposed defaults)

1. **Regions:** the ten cities above, plus Sydney as Australia's way into listing. *Default: yes.*
2. **Conversations in v3:** port TST v6's conversations as PT-M28. *Default: yes.*
3. **Dynasty:** the player continues as the successor managing partner, with the founder as senior counsel, to 2064. *Default: yes, as TST v5 chose.*
4. **Scenario starts:** 2010 New York and 2010 London. *Default: those two.*
5. **`sim-core`:** plan the extraction during PT-M19, and extract before phase 2 if the plan costs at most two milestones; otherwise keep transplanting. *Default: yes.*
