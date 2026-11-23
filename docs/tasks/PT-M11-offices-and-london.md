# PT-M11: Offices, cities and London

**Goal:** the firm can grow beyond its home city. Offices in US cities and in London have leases, local hiring pools, local rates and salaries, local demand and an office managing partner. Lawyers must be admitted where they lead work. London runs under England and Wales's rules: trainees and newly qualified lawyers, the SRA, compulsory insurance and lockstep culture. Real UK rivals (the Magic Circle and others) compete there from 2005.

**Spec:** §3 (stages), §5.2 (trainees), §5.7 (the UK path), §8.8 (offices), §9.1 (office managing partner), §11.1 (bar rules) · **ADRs:** PT-0008 (rivals at real scale, pinned), PT-0010 (ownership rules; ABS itself is v3), PT-0012 · **TST to port:** formulas.md §19 (offices), `tst/sim/geo/` · **Depends on:** PT-M10 (`pt-m10-done`) · **Lane:** B (beside PT-M7c in lane A and PT-M14 in lane C)

## Lane

- **Owns:** `ptk/sim/geo/` (new: cities, offices, regions, bar admissions), `cities.yaml`, `bar_rules.yaml`, the UK hiring path in `ptk/sim/hiring/` (trainees, qualification), the London market in `practices.yaml` and `macro_history.yaml` (a `uk` region's series), UK rivals in `firms.yaml` and `notables.yaml`, the Offices screen, RNG ids **100-109**.
- **Must not edit:** partnership admission, comp, pay scale rules and `ptk/balance/` (PT-M7c: register a strategy in a new module with one line and ask lane A for re-reads); task mixes, eras and AI (PT-M14).
- **Shared files:** keep both sides; re-chain migrations if another merged first.

## Out of scope

Asia, Europe beyond London and the Gulf (v3); ABS entities and outside capital (v3); mergers and the verein (PT-M13); the other ten practices (PT-M12).

## Sub-tasks (commit after each)

1. **Research dossier** `docs/research/london-and-us-cities.md` (sources, S/D/A): the London large-firm legal market by practice in 2005 and its path to 2025 (2008, Brexit 2016, 2020); London rates and the trainee and NQ salary history; UK rivals at FY2005/06 (Clifford Chance, Linklaters, Allen & Overy, Freshfields, Slaughter and May, Herbert Smith, Lovells, Ashurst, Norton Rose, Simmons & Simmons, CMS, Eversheds, DLA, Addleshaw Goddard and others) with their paths and dated events to 2025, and their notable lawyers under ADR PT-0013's rules; demand, rates and salaries for six US cities (Washington, Chicago, Boston, Los Angeles, the Bay Area, Houston) relative to New York.
2. **Cities and offices:** offices as leases (term, rent per lawyer by city, fit-out to 1500, lease liability to 2500), local hiring pools, local rates (the firm's card × the city's ratio), local demand reach (clients' work in a region favours firms with an office there), office P&L by `office_id` (the ledger dimension exists). Opening by an organic start, a lateral group or a team lift; closing is a one-off.
3. **Bar admissions:** a lawyer may lead matters only where admitted; admission by exam (a non-billable cost) or reciprocity; pro hac vice for litigation elsewhere. England and Wales: qualified as a solicitor (or a registered foreign lawyer for US partners in London).
4. **The UK path** (spec §5.2, §5.7): training contracts two years ahead, two-year trainee seats rotating through practices (familiarity), qualification each September (NQ), the London salary scale; UK lockstep as the default comp culture of UK rivals.
5. **UK rules** in `bar_rules.yaml`: compulsory professional indemnity insurance (minimum cover; a cost to `6300`), the SRA as regulator (the disciplinary machinery is PT-M15), client money rules for the client book, LLP status.
6. **UK rivals** from `firms.yaml` with the history pin to 2025 (ADR PT-0008), personalities, notables and panels for UK clients (FTSE 100 names in `clients.yaml`).
7. **Office managing partner seats** (PT-M8's seat exists): one per office from a second office.
8. **Screens:** Offices (cities, leases, headcount, local market, office P&L), admissions on the Person screen, a city selector where hiring and matters need one; e2e: open a London office with a team lift and qualify a trainee.

## Acceptance criteria

- [ ] Office P&Ls sum to the firm's P&L each month (reconciliation test); lease liabilities and fit-out post and amortise correctly.
- [ ] No lawyer leads a matter where they are not admitted (property test); pro hac vice costs post.
- [ ] UK rivals hold their paths to 2025 within ±15% at 2009, 2015 and 2025 (T11 extended to London), on seeds 1-10.
- [ ] A firm that opens London in 2007 with a 10-lawyer team reaches positive office profit within 3 years on at least 6 of 10 seeds (printed); one that opens with an organic start of one partner takes longer (printed).
- [ ] T12 (≤ 250 ms) holds at December 2025 with two offices.
- [ ] `make check`, `make e2e` and the nightly run green; `Milestone-Tag: pt-m11-done`.

## Manual check (Reece)

From `pt-2008`, open Washington and then London, and play to 2012.

## Decisions made

1. **The home office is implicit** (office id 0, no lease): it keeps v1's rent per head, and a ledger line with no `office_id` is its. A firm that never opens an office plays as before: no city demand is drawn, no city clients exist, every factor is 1.0 and payroll, billing and intake take v1's paths.
2. **A city's market is its clients.** Each office city has its own demand by practice (`cities.yaml` `demand` x New York's D0 x the city's mix, the macro's drivers, the `uk` region's multipliers for London) split over that city's clients by wallet (`wallets` now normalises per city). The city's clients (London: the 63 `uk_clients`, then generated ones) are made when a firm first opens there, so nobody serves that market before; panels are the rivals of the city's region. Local reach (spec 8.8): a client's work in a city where the firm has no office costs `geo.reach_penalty` (1.5) logit points of appeal; the office managing partner adds `geo.omp_appeal` (0.4) x e.
3. **Who works where is a person's city**: someone works in the firm's office in their city, else in the home office. Flow work for a city's clients is served first by that office's people, then by the practice's lawyers in other offices (people work across offices); named matters may be staffed from any office; the lead must be admitted (decision 6).
4. **Leases** (spec 8.8's "lease liability to 2500"): undiscounted, the term's rent recognised at signing as a lease liability (2500) against a right-of-use asset (1510, new); each month's rent pays the liability and expenses the asset (6000); fit-out ($25,000 a seat) is capitalised (1500) and amortised straight-line over the 120-month term (6050, new); a lease renews itself at its term's end; breaking one costs six months' rent. Lease sizes: 5, 10, 15, 25, 50 or 100 seats.
5. **Opening**: *organic* (one of the firm's active partners moves; in London they register as a foreign lawyer, elsewhere they apply on motion or sit the exam; they build the office's book from scratch through RFPs and pitches: `geo.organic_clients` 0, tuned from 2, at which an equity partner's office, whose only costs are a small lease and insurance, paid back in its first month on 5 of 10 seeds, faster than a team lift); *lateral group* (generated local partners and associates through a recruiter: PT-M4's arrival, books over 12-24 months, a one-year guarantee); *team lift* (from a rival of the city's region: no recruiter, each partner's book clients follow within six months with the partner's hidden portability (0.55-0.9), the first always; the rival loses that book and grows hostile). No stage gates the action in PT-M11 (spec 3's unlocks are progressive screens; the brief's test opens London in 2007 from a stage-1 firm).
6. **Bar admissions** (spec 11.1): a lead must be admitted in the jurisdiction of the office whose client it is (the home office: the scenario's); in England and Wales a solicitor may lead anything and a registered foreign lawyer only non-contentious work. A case in a court of another jurisdiction also needs its lead admitted there or pro hac vice (a one-off fee to 6600, once a case and lead; none in England and Wales); arbitration needs none. This applies to v1's cases in Delaware, California and Texas courts too: a New York lead now pays pro hac vice there (a few hundred to $2,500 a case).
7. **The UK path**: training contracts are offered by an England and Wales office once a year ($15,000 each, at offer), join in September two years on with four six-month seats in four practices drawn at their making; a trainee's home practice is their seat's; they qualify each September (class 1, admitted in England and Wales) into their last seat's practice. London associates are paid a share of the New York scale's class year (bar_rules.yaml `london_scale`), trainees their year's salary.
8. **UK rules** (bar_rules.yaml): compulsory indemnity insurance for England and Wales offices, a twelfth a month of max(GBP 20,000, $11,000 a lawyer) (6300), minimum cover GBP 2m a claim, GBP 3m for an LLP (data; claims are PT-M15's); the SRA from January 2007; the Accounts Rules (the client book's existing rules enforce them); LLP status; dated ownership rules (lawyers only; legal disciplinary practices from March 2009; ABS licences from October 2011, data only: ABS entities are v3).
9. **UK rivals**: 18 firms (the dossier's 19 less DLA's UK LLP, which the US-basis `dla_piper` already covers) with fiscal-year points at the year their fiscal year ends (April), in dollars at that fiscal year's GBP/USD; Lovells and A&O are absorbed into Hogan Lovells (`hogan_hartson`) and A&O Shearman (`shearman`) at their merger dates, because those firms' outside mergers already carry the combined paths; the other UK mergers are outside mergers (steps) or renames; KWM Europe collapses in January 2017. UK rivals have no New York office in the game: they do not bid on New York RFPs, poach the firm's US lawyers, represent the other side in New York cases or appear in PT-M16's US tables, reputation and press (London tables are a follow-up). A rival approaches only people working in its region; a London partner's suitor in flight is a UK firm. Rivals' price appeal is against their own region's mean.
10. **The office managing partner** seat (spec 9.1) has a slot per office, the home office's included, from a firm's second office; its stage gate is removed (0), since its slots exist only then.
11. **London courts**: a London client's case goes to the Commercial Court (`ew_commercial`) or, for arbitration, the LCIA (`lcia`), both new in courts.yaml with generated judges.
12. **London's market lives in cities.yaml** (its size against New York's and its practice mix), not in practices.yaml, which keeps New York's D0 by practice; the `uk` region's series are multipliers on the macro indices in macro_history.yaml `regions:` (the 2008-09 bank freeze, the eurozone, the 2016 referendum, the 2022-25 IPO drought).
13. **Strategies** for the readings are `london-lift` and `london-organic` in `ptk/balance/offices.py`, registered with one line in `ptk/balance/strategies.py`: they act before steady's moves in the month they open (the open needs 20 of the month's energy).

14. **Matters need no city selector**: a matter's office is its client's city's (an office there, else the home office), and the Matters screen is unchanged; the selector is on Recruitment's search form.

## Readings

- **T11 extended to London** (`test_pt_m11.py`, seeds 1-10): see the final report; seed 1: 41 UK points (2009, 2015, 2025), worst gap 9.5%, no misses. T11 itself (all rivals, `test_pt_m5.py`) seed 1: worst gap 9.5%, top 10 kept 9.
- **London 2007** (`london-lift` / `london-organic`, seeds 1-10, months from opening until the office's cumulative profit since opening is positive): team lift 9, 4, 4, 4, 4, 5, 4, 6, 5, 6 (10 of 10 within 36 months); organic start >60, >60, >60, 40, >60, 43, >60, 36, >60, 42 (median >60).

## Follow-ups

- London's own rankings, reputation (region 1) and press: PT-M16's lists and reputation stay US-only (UK rivals are filtered from `rival_standing`).
- Overheads by office city for lane A's per-lawyer overhead lines (they now take the office's city band, but the office's support staff and technology are not otherwise local).
- UK rivals' New York offices (Clifford Chance, Linklaters, Freshfields, A&O and Lovells had them): bidding on New York RFPs and poaching there would change v1's market; left out here.
- The office managing partner's other effects (office morale, the local hiring pool) and authority (office hiring, lease proposals).
- Local mergers as a way to open a city (spec 8.8) belong with PT-M13's mergers.
- US cities' own courts (Chicago, Los Angeles, Houston cases still draw the New York forums, so their leads need pro hac vice there).
