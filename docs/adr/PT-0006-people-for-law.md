# ADR PT-0006: People for law: class years, practice familiarity, strain for everyone

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Inherits: TST ADR-0007 (hidden values and revealed ranges), formulas §1–§10
- Generalises: TST §32.1 (founder stress) to every person

## Decision

1. **Levels** replace TST's junior–exec ladder: `paralegal`, `trainee` (UK), `associate_1` … `associate_8`, `senior_associate` (UK label), `counsel`, `income_partner`, `equity_partner`; business services keep `staff`, `manager`, `director`, `chief`. An associate's class year advances each September. Level CA targets and age ranges live in `balance.yaml`.
2. **Practice familiarity.** Each lawyer holds a familiarity 1–20 for every practice area (like Football Manager's positional ratings). A lawyer's effective skill on a matter = their skill × `familiarity_factor(f)` (default 0.70 at f=1, 1.0 at f≥15). Familiarity grows with hours worked in that area (`fam.per_100h`) and decays slowly without them. Familiarity is revealed with a narrow range (it is visible from a CV) and is not hidden.
3. **Strain** 0–100 on every lawyer (founder included; it *is* TST's stress for the founder). Monthly: `+ strain.load × max(0, hours / capacity − strain.comfort)` with `strain.load` 60 and `comfort` = 1.0 + 0.01 × (stamina − 10); recovery when under; holidays and sabbaticals reset. **Burnout** at 80: capacity × 0.7, error chance doubled, resignation chance × 2 for 6 months. The `burnout_risk` hidden trait scales the load. Strain is public for one's own firm; for others it is not shown.
4. **Learning by doing.** TST §3's growth term is multiplied by `learn(h)`, the share of a person's hours that were substantive work at or slightly above their level (not document review). AI that removes junior review work (ADR PT-0011) therefore slows juniors' growth unless the firm builds training: the generational pipeline problem the 2020s pose.
5. **Hidden values** (never in the API or a prompt): potential, `consistency`, `burnout_risk`, `big_moments` (trial and closing performance), `poachability`, `integrity`'s true value (billing padding and misconduct risk), and each partner's **portability** (share of their clients who would follow them).

## Consequences

- People screens show a familiarity grid, hours, utilisation and strain; the squad-management feel of Football Manager comes from balancing hours against strain and learning.
