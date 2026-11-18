# ADR PT-0010: Firm ownership rules by jurisdiction and date

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Reuses: TST ADR-0018 (shares) and §25 (IPO chain) only inside an eligible structure

## Decision

1. `bar_rules.yaml` holds, per jurisdiction and dated: who may own or share fees (lawyers only; lawyers plus non-lawyer managers; any owner), whether outside investment and listing are allowed, foreign-firm rules, lateral screening, advertising and referral-fee rules, mandatory insurance minimums, and trust-account rules.
2. History (to verify in the research dossier): **District of Columbia** has allowed non-lawyer partners in limited form since 1991; **England and Wales** licensed alternative business structures under the Legal Services Act 2007 from 2011–12, with UK-listed firms from 2015; **Australia** allowed incorporated and listed practices (first listing 2007); **Utah** opened a regulatory sandbox in August 2020; **Arizona** abolished its Rule 5.4 and licensed ABSs from 1 January 2021. The **Big Four** legal arms enter where rules allow (KPMG's Arizona licence was approved in 2025). Elsewhere, lawyers only.
3. A firm may form an **ABS entity** only in a jurisdiction that allows it, and work done through it is limited to that jurisdiction's rules. An ABS can take outside equity (TST ADR-0018's cap table on that entity only) and, where allowed, list (TST §25's chain). Partners of a US firm cannot share fees with a non-lawyer-owned affiliate in a state that forbids it: the engine enforces this as with conflicts.

## Consequences

- External capital is a real but bounded option, mostly a UK, Australia and Arizona strategy, which gives regions strategic texture.
