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

## Follow-ups
