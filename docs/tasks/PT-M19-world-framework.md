# PT-M19: The world framework

**Goal:** the frame v3's regions hang on. A jurisdiction is data plus an optional rules provider: its currency, who may practise its law, how a foreign firm may be present (a representative office, an association with a local firm, a joint venture, a licensed foreign firm, full practice), ownership rules, a local salary scale and rate card, demand by practice, tax treatment and local rivals. Money gains a currency: each office keeps its books in its own currency, and the firm consolidates to US dollars each month, with a translation reserve, so a fall in sterling shows in a London-heavy firm's US-dollar PEP. London is rebuilt as the first jurisdiction on the frame. PT-M20 to PT-M22 then add Europe, Asia-Pacific and the Gulf as data and rules, without touching the frame.

**Outline:** `docs/v3-outline.md` (phase 0) · **Spec:** §10.4 (offices), §18 (v3) · **ADRs:** PT-0003 (partnership accounting), PT-0010 (ownership by jurisdiction), PT-0014, PT-0015, PT-0019; new **PT-0020** (currencies, translation and the consolidated books) and **PT-0021** (jurisdictions and local rules) · **sim-core:** the currency dimension (SC-0004 and `translate`); the ledger change ships as `sim-core` **v0.3.0**, made in this lane (plan step 3) · **Depends on:** `pt-m19b-done` · **Lane:** runs alone (it changes the books and every state hash).

## Lane

- **Owns:** `ptk/sim/geo/` (jurisdictions and their rules providers), the ledger's currency work in `sim-core` (release `v0.3.0`) and its adoption here, the new data files `jurisdictions.yaml`, `currencies.yaml` and `fx_history.yaml` (monthly to December 2025), the seeded FX paths after 2025 (`macro_seed`, PT-0015), `cities.yaml` and `bar_rules.yaml` reshaped by jurisdiction, the balance keys for FX and translation, the Offices and Finance screens' currency display, RNG ids **160-169**.
- **Must not:** add any region beyond the US and England and Wales (PT-M20 to PT-M22); add hedging, outside capital or the Big Four (later milestones).

## Sub-tasks (commit after each)

1. **Research dossier** `docs/research/world-framework.md` (sources, S/D/A): monthly exchange rates 2005-2025 for GBP, EUR, CHF, HKD, SGD, JPY, CNY, AUD, AED, SAR and QAR (Federal Reserve H.10, the Bank of England), with the dollar pegs (HKD, AED, SAR, QAR) and their bands; how international firms report (US firms in dollars; UK LLPs in sterling; translation at closing and average rates); the kinds of foreign-firm presence and their rules at framework level for the v3 cities (types only: each region's details are PT-M20 to PT-M22's); tax on a partnership's foreign profits at framework level.
2. **Currencies in the books** (`sim-core` 0.3, ADR PT-0020): integer minor units per currency; balances keyed by entity, account and currency; each office's functional currency; monthly translation into US dollars, the P&L at the month's average rate and the balance sheet at its closing rate, with the difference in a translation reserve in partners' equity; client money in the client's currency, never translated into a firm entry. PT-M19a's cuts 1-2 (the entry type, balances keyed by currency) land here. Golden snapshots and the state cache are re-recorded **once**, with the reason in `CHANGELOG.md`.
3. **FX paths:** history to 2025 from the dossier; seeded paths after (PT-0015) with each currency's volatility, and pegs that hold within their bands; the macro shocks' links (2008, the 2016 referendum, 2022).
4. **Jurisdictions** (ADR PT-0021): a `Jurisdiction` with its currency, bar and admission rules, presence types and their conditions (licence, local partner share, cap on foreign lawyers, which practices are open), ownership rules (PT-0010 generalised), local salary scale and rate card, demand by practice, tax and local rivals. A `RulesProvider` interface for rules that data cannot express. The US and England and Wales are the two instances; London's present behaviour is rebuilt on the frame.
5. **Pay and partners abroad:** salaries paid in the local currency from the local scale; partners' profit shares set in US dollars and paid in the local currency at the month's rate; capital accounts in US dollars.
6. **Screens:** amounts shown in their own currency, with US-dollar totals; an FX line on Finance; Offices show each jurisdiction's presence type and rules. e2e: open London, watch the 2016 fall in sterling move PEP in US dollars.

## Acceptance criteria

- [ ] Every entry balances per book **and per currency**; client money is never translated into a firm entry; translation reconciles (the consolidated balance sheet equals the translated office books plus the translation reserve) (property tests).
- [ ] A US-only firm's results are unchanged: cash, revenue, PEP and every balance match the pre-PT-M19 build month by month (test on seeds 1-3, comparing values rather than hashes).
- [ ] Sterling's falls in 2008 and 2016 move a London-heavy firm's US-dollar PEP in the direction and rough size the dossier gives (printed on seeds 1-40; the band proposed as T19 for the product manager's approval).
- [ ] Pegged currencies stay within their bands through 2034 (test).
- [ ] A fixture jurisdiction added only as data, with a stub rules provider, opens an office with no code change in the frame (test).
- [ ] T1-T18 hold on seeds 1-40 (no new miss beyond CLAUDE.md §12's rules); T12: median of five at most 200 ms in December 2025 and at most 250 ms in December 2034.
- [ ] `sim-core` `v0.3.0` tagged and pinned; `make check`, `make e2e` and the nightly green; `Milestone-Tag: pt-m19-done`.

## Manual check (Reece)

From `pt-2008`, open London in 2009 and play to 2017; read the Finance screen's FX line through the referendum.

## Decisions made

(The session records its decisions here.)

## Follow-ups

(The session records follow-ups here.)
