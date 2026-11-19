# Data dictionary

Column-level reference for a save file (`saves/<slug>.ptk.sqlite`). Kept current with migrations.

## Schema v1 (`0001_initial`, PT-M0)

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `save_meta` | `id` | int | Always 1 |
| | `name` | str | The save's slug |
| | `master_seed` | bigint | Master seed minus 2^63 (SQLite integers are signed; ADR-0002 seeds are 0..2^64-1) |
| | `scenario_id`, `difficulty` | str | `scenarios.yaml` keys |
| | `start_year`, `start_month` | int | Turn 0's calendar month (ADR PT-0002) |
| | `current_turn` | int | The next turn to be played |
| | `game_state` | str | `active`, `campaign_complete` or `dissolved` |
| | `ended_turn` | int, null | The last turn played when the game ended |
| `firm` | `id`, `name`, `is_player`, `stage`, `founded_turn`, `home_city` | | Current state of each firm (updated in place) |
| `ledger_entry` | `id`, `turn`, `firm_id`, `memo` | | Append-only; one per balanced entry |
| `ledger_line` | `entry_id`, `account`, `amount_cents` | | Debit positive, credit negative; lines of an entry sum to 0 |
| | `practice`, `office_id` | null | Reporting dimensions (PT-M3b onward) |
| `turn_snapshot` | `turn`, `firm_id`, `kpis_json` | | Append-only month-end KPIs per firm |
| `turn_log` | `turn`, `firm_id`, `kind`, `message` | | Append-only turn log |
| `decision_log` | `turn`, `seq`, `source`, `payload_json` | | Append-only player, delegate and rival actions (ADR-0014; used from PT-M1b) |

## Schema v2 (`0002_people`, PT-M1a)

Current-state tables, updated in place each turn. Attribute sets are JSON lists of `[key, value]` pairs in data-file order (`skills.yaml`, `personality.yaml`, `practices.yaml`); floats round-trip exactly.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `person` | `id` | int | Person id (ascending; founders first) |
| | `first_name`, `last_name` | str | Name |
| | `birth_turn` | int | Turn of birth (negative before the start); age = `(turn − birth_turn) // 12` |
| | `role`, `level` | str | `roles.yaml` key (a lawyer's home practice) and level (ADR PT-0006 §1) |
| | `skills_json`, `personality_json` | text | True 1–20 values; the API shows only revealed ranges |
| | `hidden_json` | text | **Hidden** traits (consistency, burnout risk, big moments, poachability): never in the API |
| | `potential_ability` | float | **Hidden** PA 10–200; the API shows a phrase from the revealed range |
| | `familiarity_json`, `familiarity_peak_json` | text | Practice familiarity 1–20, and the highest reached (decay floor = peak − 3) |
| | `interests_json`, `work_style` | text, str | Shown once the profile is revealed |
| | `tags_json` | text | True behaviour tags; shown only when revealed |
| | `school_tier` | str, null | `schools.yaml` key (lawyers) |
| | `bar_admissions_json` | text | Jurisdiction keys (`scenarios.yaml` `jurisdictions`) |
| | `city` | str | Home city |
| | `strain` | float | 0–100 (spec §5.6); shown for the player's own firm only |
| | `burnout_since`, `last_burnout_turn` | int, null | Turn the current burnout began (null if none); start of the latest burnout |
| | `book_cents` | bigint | A partner's book of business a year (integer cents, 2005 USD) |
| | `portability_bp` | int, null | **Hidden**: share of the book that would follow a partner (bp) |
| | `is_founder`, `founding_partner`, `background` | bool, bool, str | The player's founding partner; any founding partner; their background |
| | `real` | bool | A real lawyer (ADR PT-0013; from PT-M5) |
| `employment` | `id`, `person_id`, `firm_id` | int | A person's employment with a firm |
| | `start_turn`, `end_turn` | int, null | |
| | `status`, `end_reason` | str | `active`, `notice` or `ended`; why it ended |
| `reveal_state` | `observer_firm_id`, `person_id` | int | Primary key: what one firm knows of one person (ADR-0007) |
| | `attributes_json` | text | `[[key, hw, offset, last_updated_turn], ...]`: skills, personality, `potential_ability`, then `fam:<practice>` |
| | `profile_revealed_turn` | int, null | Interests and work style shown from this turn |
| | `revealed_tags_json` | text | `[[tag, turn], ...]` |

## Schema v3 (`0003_hiring`, PT-M1b)

Searches, candidates, offers and person state are current-state tables, updated in place; no record is ever deleted, so ids are `max(id) + 1` and never reused. Money is integer cents (ADR-0003).

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `firm` | `pay_policy_mode` | str | `match`, `lag` or `lead` against the market associate scale (spec 5.4) |
| | `pay_policy_bp` | int | Basis points of the market scale the firm pays (10000 = match) |
| `employment` | `salary_cents` | bigint | Salary a year; 0 for equity partners (profit, not salary). Associates are raised to the firm's scale each month (never cut) |
| `search` | `id`, `firm_id`, `role` | | A search for one `roles.yaml` role |
| | `channel` | str | `campus`, `recruiter`, `job_post` or `referral` |
| | `actor_id` | int | Who opened it (their judgment of talent scouts the batch) |
| | `opened_turn`, `status`, `closed_turn` | | `open` or `closed`; campus, recruiter and referral searches close after one batch |
| | `level` | str, null | A lateral search's target level; null = the channel's level mix |
| | `school_tiers_json` | text | Law school tier filter (JSON list); `[]` = any |
| | `plan_id` | int, null | The PT-M2 hiring plan it serves |
| `candidate` | `person_id` | int | The generated person (in `person`) |
| | `firm_id`, `search_id`, `channel` | | Who may hire them, and how they were found |
| | `ask_cents` | bigint | Their salary expectation a year (shown exactly) |
| | `created_turn`, `expires_turn` | int | Phase 12 of `expires_turn` they leave unless an offer is pending; a campus candidate's is the offer month |
| | `status` | str | `open`, `signed` (a campus hire waiting for September), `hired`, `declined`, `expired` |
| | `resolved_turn`, `interviewed_turn` | int, null | When resolved; the firm's first interview (ADR-0016) |
| `offer` | `id`, `firm_id`, `candidate_id`, `actor_id` | | One pending offer per candidate |
| | `salary_cents` | bigint | Annual salary offered |
| | `made_turn`, `start_turn` | int | The hire joins at `start_turn`: the resolving turn, or the September after (campus) |
| | `status`, `resolved_turn` | | `pending`, `accepted`, `declined`, `withdrawn` |
| | `plan_id`, `unit_id` | int, null | PT-M2's plan and the unit the hire joins |
| `person_state` | `person_id` | int | One row per person tracked |
| | `energy` | int, null | This month's energy: the player's founding partner (and PT-M2's delegates) |
| | `morale` | float, null | 0–100; everyone on the books but founding partners |
| `inbox_item` | `id`, `turn`, `firm_id`, `template` | | Append-only; the player firm's templated log items (`inbox_templates.yaml`) |
| | `title`, `body` | text | Rendered text (money formatted) |
| | `link_kind`, `link_id` | str, int, null | `person`, `candidate`, `search` or `finance` and its id |
| | `read` | bool | UI state only; not in `decision_log` |

`decision_log` is used from PT-M1b: one row per player action, `seq` 1, 2, 3… within a turn, `source` `player`, and `payload_json` the action's fields (replayed in `seq` order before `advance_turn`, ADR-0014).
