# Balance targets (v1)

**Status: DRAFT for Reece's approval.** As in TST: the balance runner plays every strategy on the same seeds, prints every target, and fails the nightly run on pass/fail targets; bands are tuned with `balance.yaml` keys only, or brought back to Reece.

## Setup

| | |
| --- | --- |
| Seeds | 1–10 (nightly); 11–40 for seed-luck checks (CLAUDE.md §9 rule 4) |
| Turns | 132 (January 2005 to December 2015) |
| Scenario | `biglaw_spinout`: an M&A partner and a litigator found a firm in New York with two associates, $600,000 of partners' capital and a $1M revolver, books of $2.5M and $1.5M |
| Difficulty | standard; T5 also easy and hard |
| Events | on, `MockLLMAdapter`; first choice |

## Strategies

| Strategy | People | Work | Money | Partnership |
| --- | --- | --- | --- | --- |
| **do-nothing** | founders only | flow work only, no BD | no revolver use | no votes |
| **boutique** | grow to 25 lawyers, leverage ≤ 2 | two practices, high rates, premium clients | conservative | pure lockstep; admit one partner every two years |
| **steady** | grow while utilisation ≥ 80%; campus class each year | add a practice at each 30 lawyers; cross-sell | revolver ≤ 1 × monthly fees | modified lockstep; admit by business case |
| **lateral rocket** | lateral partners whenever a book of $2M+ is available, with guarantees | follow laterals' books | revolver to its covenant limit | eat what you kill |
| **pyramid** | leverage 5+, utilisation targets 2,100 hours | volume work, fixed fees | moderate | two-tier; few equity admissions |

All strategies staff named matters by the default rule, bill monthly, accept the first settlement offer above the expected value and never de-equitise (except pyramid).

## Targets

| # | Target | Kind |
| --- | --- | --- |
| T1 | **Do-nothing fails:** revenue below $3M and falling at year 5 on ≥ 9 of 10 seeds, or dissolved | pass/fail |
| T2 | **No dominant strategy:** no strategy has the best firm score at year 11 on more than 6 of 10 seeds | pass/fail |
| T3 | **Growth is possible:** steady reaches 100–250 lawyers and $60M–$150M revenue (nominal) by December 2015, median | band |
| T4 | **PEP is believable:** at year 11, median PEP $500k–$1.2M for steady, $1.0M–$2.5M for boutique, $0.7M–$1.6M for pyramid | band |
| T5 | **Difficulty matters:** steady's dissolution rate easy 0–10%, standard 5–20%, hard 20–45% | band |
| T6 | **Associate attrition** 15–25% a year (median across years and strategies); 8–15% of a September class make equity partner within 10 years in steady | band |
| T7 | **Real ratios:** median realisation 84–92%, collection 93–98%, utilisation 75–90%, lockup 90–150 days | band |
| T8 | **The crash bites:** 2009 revenue against 2008, a corporate-heavy firm −10% to −30%; a firm with a restructuring practice above 20% of revenue −5% to +20% | band |
| T9 | **The spiral is real but survivable:** lateral rocket dissolves on 3–6 of 10 seeds by 2015; the same strategy with the CFO's warnings heeded (a script rule: stop guarantees and repay the revolver when the warning comes) dissolves on at most 1 | band |
| T10 | **Strain matters:** pyramid's associates burn out at least twice as often as steady's; steady's at most 5% a year | band |
| T11 | **Rivals hold history:** each pinned rival's revenue within ±15% of its path in December 2009 and December 2015; the top 10 by revenue in 2015 contains at least 8 of history's | pass/fail |
| T12 | **Turn time:** median turn ≤ 250 ms at December 2015 on the steady save | pass/fail |
