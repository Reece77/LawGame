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
