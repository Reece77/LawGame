# ADR PT-0003: Partnership accounting, matter money and client money

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Inherits: TST ADR-0003 (integer cents, double entry, cash derived from the ledger)
- Replaces for Partner Track: TST ADR-0018 (shares, SAFEs, rounds)

## Context

A law firm is a partnership (in the US usually an LLP; in the UK an LLP; some are professional corporations). It has no share capital to sell. Partners contribute capital, take monthly **draws** against expected profit, and receive a **true-up** when the year's profit is known. Revenue passes through work in progress (WIP), bills, and receivables. Firms also hold **client money** (retainers, settlement funds, escrow) that legally belongs to clients and may never be used as firm cash. The Am Law figures the game's rivals are pinned to are on a cash basis.

## Decision

1. **Chart of accounts** (`accounts.yaml`), integer cents, every movement a balanced `LedgerEntry`:

| Range | Accounts |
| --- | --- |
| 1000s assets | 1000 cash (operating); 1100 unbilled WIP (at standard rates); 1110 WIP provision (expected write-downs); 1200 receivables (billed, uncollected); 1210 bad-debt provision; 1300 disbursements recoverable; 1400 prepaid (insurance, rent); 1500 PP&E and fit-out; 1600 loans to partners (capital loans, where the firm arranges them) |
| 2000s liabilities | 2000 payables; 2100 accrued salaries and bonuses; 2200 deferred fee income (retainers earned over time); 2300 bank revolver; 2400 term debt and private placements; 2500 lease liabilities; 2600 retired-partner annuities (unfunded obligations, Dewey's trap); 2700 partner current accounts (allocated profit not yet drawn) |
| 3000s partners' equity | 3000 partners' capital (by partner, sub-ledger); 3100 undistributed profit (the year to date); 3200 drawings (contra) |
| 4000s income | 4000 fees by practice (sub-accounts per practice area); 4100 success and contingency fees; 4200 disbursement recoveries; 4300 interest |
| 5000–6000s costs | 5000 associate and counsel salaries; 5010 bonuses; 5020 income-partner salaries; 5100 staff salaries; 5200 benefits; 6000 rent; 6100 technology and AI; 6200 recruiting and lateral fees; 6300 malpractice insurance; 6400 marketing and business development; 6500 knowledge and research subscriptions; 6600 professional fees; 6700 write-offs; 6800 interest; 6900 general admin; 6950 lobbying and bar politics; 6970 fines and sanctions |

2. **Revenue chain.** Hours worked post to **1100 WIP** at the timekeeper's standard rate (debit WIP, credit 4000 fees). Billing moves WIP to 1200 receivables at the billed value; the difference is a **billing write-down** (debit 4000, credit 1100). Collection moves receivables to cash; uncollected amounts become **collection write-offs** (debit 6700 or 4000 by cause). Fixed fees recognise revenue by matter progress, not hours. So *realisation* and *collection* are ledger facts, not estimates.
3. **Profit and PEP.** Distributable profit for a year = income − costs (cash basis for comparison with rivals; accrual for the books; both are queries over the ledger, the cash-basis view excludes the change in WIP and receivables). **PEP** = distributable profit allocated to equity partners ÷ the year's average equity partners. Income (non-equity) partners are salaried costs plus a bonus (5020).
4. **No corporate income tax** for a US LLP or UK LLP: tax is paid by partners personally, through the founder's personal book (TST §32.2 `personal.tax_rate`) for the player's own share. An ABS company (ADR PT-0010) pays corporation tax.
5. **Capital.** Each equity partner has a capital account (3000 sub-ledger) with a required level (`capital.share_of_comp_bp`, default 3,000 bp of target comp), paid in at admission or over 3 years, often funded by a partner bank loan that sits in the partner's personal book, not the firm's. Capital is returned over 3 years after departure (a cash call on the firm: the exodus mechanism, spec §8.7).
6. **Draws and true-up.** Equity partners draw `draw.share_bp` (default 7,000 bp) of their budgeted share monthly (debit 3200, credit cash); in December the year's profit is allocated (3100 → 2700 by partner) and the true-up paid in January–April as cash allows.
7. **Client money is a separate book.** Each office holds a **client account** ledger (`client_book`, its own double entry; accounts `C1000 client bank`, `C2000 owed to clients` by client). Money moves to the firm's book only by a bill paid from client funds (a transfer entry recorded in both books). The engine refuses any action that would make the firm's cash depend on client money; a shortfall in a client account is always a critical regulatory event (spec §11). This is an invariant with a property test: for every client account, `bank = Σ owed to clients` at every month end.

## Consequences

- Statements reconcile by construction, as in TST; realisation, collection and lockup are queries.
- TST's cap table, options, SAFEs and rounds are not used. The ABS route (ADR PT-0010) can later add a share capital for an ABS entity using TST ADR-0018 unchanged.
- The exodus spiral (capital returned, annuities owed, revolver covenants) is visible in the books, not a scripted event.
