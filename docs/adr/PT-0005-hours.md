# ADR PT-0005: Hours are integer tenths; money from hours by rate cards

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Extends: TST ADR-0003

## Decision

1. **Hours** are stored as `int` tenths of an hour (`Tenths = int`; 1 = 6 minutes, the profession's billing unit). Never floats.
2. **Capacity** per person per month = `capacity.hours_year[level] / 12` in tenths, × the person's availability (holiday, leave, part-time), × strain's effect (spec §5.6). Hours above capacity are possible (overtime), each tenth above adding strain.
3. **Value of work** = tenths × rate cents / 10, rounded half to even once per (person, matter, month). Rate cards are integer cents per hour by (firm, office, level, practice), set each January.
4. **Utilisation** = billable tenths ÷ (capacity tenths); **realisation** = billed cents ÷ standard-value cents; **collection** = collected ÷ billed; **lockup days** = (WIP + receivables) ÷ trailing daily fees. All are derived, never stored.
5. Non-billable time (pro bono, business development, training, management, knowledge work) is recorded in tenths by category and counts toward strain and toward the firm's credited-hours policy.

## Consequences

- Hours reconcile with money by construction; tests check that WIP at standard equals Σ tenths × rate / 10 for every open matter.
