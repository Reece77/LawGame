# PT-M13: Mergers and the verein

**Goal:** firms combine. The firm can approach any firm, a real rival or a generated one, and be approached. Due diligence narrows what the firm knows of the other side's books, partners, conflicts, annuities and leases. Terms set the points ratio, the name, the managing partner and governance, and the harmonisation of comp systems and rates. Both partnerships vote, each by two thirds. Every client of both firms clears conflicts, and conflicted work is lost. Integration then tests the combination: culture clash, partners whose PEP falls leave, low-rate clients balk at the merged card. A verein instead joins member firms under one brand while each keeps its own books and profit pool, so a firm can grow abroad without pooling profit. Accepting a merger in which the firm is absorbed ends the campaign as a scored exit.

**Spec:** §8.8 (mergers and the verein), §8.5 (comp systems), §8.7 (flight and the spiral), §10.1-§10.3 (rivals and history's mergers), §11.2 (conflicts), §12.2 (merger press) · **ADRs:** PT-0003 (partnership accounting), PT-0007 (governance and votes), PT-0008 (rivals at real scale, pinned to history), PT-0009 (conflicts), PT-0010 (ownership by jurisdiction), PT-0012, PT-0013 (real people) · **TST to port:** formulas.md §28 (mergers and acquisitions: diligence, offers, integration and the exit, `tst/sim/mna/`) and §31 (the group: member companies with their own books, `tst/sim/group/`), re-cast for partnerships · **Depends on:** PT-M7c (`pt-m7c-done`); uses PT-M11's offices and London · **Lane:** B (beside PT-M12 in lane A and PT-M15 in lane C)

## Lane

- **Owns:** `ptk/sim/mergers/` (new: targets, diligence, terms, votes, clearance, closing, integration, the verein, the exit), `mergers.*` keys in `balance.yaml`, the merger vote kind in `ptk/sim/partnership/governance.py` (add the kind; do not change other kinds' rules), rivals' merger decisions in `ptk/sim/rivals/` (approaching the firm, answering its approach, mergers between rivals after 2025), history's interplay in `ptk/sim/rivals/history.py` (a rival merged with the firm leaves its pinned path), merger press moments through PT-M16's hooks, the Mergers screen, ADR **PT-0016** (mergers and the verein: books at closing, identity, the pin), RNG ids **130-139**.
- **Must not edit:** practices data, demand and `ptk/balance/` (PT-M12, lane A: register strategies in a new module with one line and ask for re-reads); `ptk/sim/risk/` (PT-M15: inherited claims are its, so leave a hook through `interfaces.py`).
- **Shared files:** keep both sides; re-chain migrations if another lane merged first.

## Out of scope

Outside capital, ABS entities and listing (v3); combinations with the Big Four or ALSPs (v3); offices in Asia, Europe beyond London and the Gulf (v3; a verein member firm may sit only in a region the game models: the US and London).

## Sub-tasks (commit after each)

1. **Research dossier** `docs/research/law-firm-mergers.md` (sources, S/D/A): large-firm mergers 2005-2025 (deal counts by year from the Altman Weil and Fairfax trackers, the significant combinations already in `firms.yaml`'s history), how terms were set (points ratios, name, governance, comp harmonisation), partner losses in the two years after a merger, client losses from conflicts, rate harmonisation, failed mergers and votes that failed, and the verein: which firms used one (Baker McKenzie, DLA Piper, Dentons, Norton Rose Fulbright, Hogan Lovells, Squire Patton Boggs, King & Wood Mallesons) and how costs and profits were shared. **ADR PT-0013:** firm-level facts only; no misconduct or blame attached to a real person, including in failed combinations.
2. **Targets and approaches:** a target list with a fit view (practices, offices, rates, PEP, culture from comp system and personalities); an approach costs the MP's energy and a confidentiality window; rivals approach the firm by a utility rule (complementary practices, a weaker PEP, a new region). Before 2026 rivals merge with each other only as history did (PT-0008); after 2025, by the seeded world's rules (PT-0015).
3. **Due diligence** (TST §28.2): costs professional fees and months; reveals the other firm's books exactly and its partners' quality, annuity burden, leases and conflict overlap as ranges that narrow with effort. Hidden true values never reach the API or a prompt (test).
4. **Terms and votes:** the points ratio (each firm's partners' share of the merged profit pool), the name, the MP and executive committee, the comp system and rate harmonisation; the rival's partnership answers by its partners' expected PEP change and personalities; each side's partners vote by PT-0007's rules with a two-thirds threshold. Counter-terms and walking away.
5. **Conflicts clearance and closing:** every client of both firms checked (PT-0009); conflicted matters are resolved at closing (the firm keeps the better relationship, the other client leaves, waivers where possible). Closing combines the books: capital accounts carried, receivables and WIP carried, leases and annuities assumed, the client books combined exactly. Accounts and the merged firm's identity are ADR PT-0016's.
6. **Integration** (TST §28.5): culture clash from differing comp systems and personalities; partners whose PEP falls, or whose practice is subordinated, leave at a raised rate through PT-M4's flight machinery (the spiral can follow); low-rate clients facing the merged card leave at a rate; office consolidation; press moments.
7. **The verein:** member firms keep their own books, partners and profit pools under a shared brand; shared costs (brand, technology, management) by a formula of each member's revenue; reputation and referrals shared; conflicts checked across the verein. A London member firm is a way to open London (PT-M11's follow-up, "local mergers as a way to open a city"). No firm entry spans two members.
8. **Being absorbed and the exit:** a larger firm's approach the player accepts, which both partnerships pass, ends the campaign as an exit scored by the founder's capital, PEP history and the merged firm's standing; a merger of equals keeps the campaign going with the player as MP or not, by the terms.
9. **Strategies and readings:** register a `merger` strategy (steady that merges with a complementary mid-size firm in 2010-2012) and a `verein` strategy (steady that joins a London member firm); read them against steady with lane A.
10. **Screens:** Mergers (targets, diligence, terms, the two votes, clearance, integration's progress), the verein on the Firm screen, the exit ending; e2e: merge with a generated firm through both votes and clearance, and form a verein with a London firm.

## Acceptance criteria

- [ ] At closing, the merged firm's balance sheet equals the two firms' balance sheets combined less the eliminations ADR PT-0016 defines, and the client book is combined exactly (property test); every entry balances.
- [ ] After clearance, no matter of the merged firm is adverse to one of its clients without a waiver (property test).
- [ ] A merger passes only with two thirds of each partnership (deterministic tests); a rival's answer reads its partners' expected PEP change.
- [ ] In a verein, no entry spans two member firms and each member's PEP comes from its own pool (property test).
- [ ] Integration losses are realistic: partners lost within 24 months of closing in the dossier's band (printed on seeds 1-10; the band in `balance-targets.md` as T13, proposed by the session for the product manager's approval).
- [ ] Rivals not merged with the firm hold T11 and T11.2025 (seeds 1-10); a rival merged with the firm leaves its path without failing T11.
- [ ] The `merger` strategy's lawyers and revenue in 2015 against steady printed on seeds 1-10 and 11-40 (T3's growth is expected partly from here); T1-T12 re-read by lane A with no new miss without an authorised row.
- [ ] No hidden value reaches the API or a prompt; no real person is attached to misconduct or blame in merger events or press (tests).
- [ ] T12 (≤ 250 ms) holds at December 2025 with a merged firm and a verein member.
- [ ] `make check`, `make e2e` and the nightly run green; `Milestone-Tag: pt-m13-done`.

## Manual check (Reece)

From `pt-2008`, approach a mid-size rival in 2011, take it through diligence and both votes, and play two years of integration.

## Decisions made

(The session records its decisions here.)

## Follow-ups

(The session records follow-ups here.)
