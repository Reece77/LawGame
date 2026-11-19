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
