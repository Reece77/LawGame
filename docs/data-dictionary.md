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

## Schema v3 (`0003_org`, PT-M2)

Current-state tables for the org (TST formulas.md §13), written after every turn and every org action. The firm root is implicit: a person with no `org_member` row, and a unit or plan with a null `unit_id` or `parent_id`, belong to it; its leader is the player's founding partner.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `org_unit` | `id`, `firm_id` | int | Unit id (never reused) and its firm |
| | `kind` | str | `practice_group` (one per practice, from 10 lawyers) or `team` |
| | `name` | str | Unique among the firm's active units (case-insensitive), at most 64 characters |
| | `parent_id` | int, null | A team's practice group; null = the firm root (practice groups always) |
| | `leader_id` | int, null | A member of the unit who leads it; leads at most one unit |
| | `practice` | str, null | A practice group's practice (`practices.yaml` key) |
| | `created_turn`, `status`, `dissolved_turn` | int, str, int | `active` or `dissolved` (kept for history) |
| `org_member` | `person_id`, `unit_id` | int | A person's unit (rewritten each write) |
| `hiring_plan` | `id`, `firm_id`, `owner_id` | int | A delegated hiring plan (TST §13.10) and its delegate (a unit leader or a recruiting manager) |
| | `unit_id` | int, null | Where hires join; null = the firm root |
| | `role`, `level` | str, str null | What it hires; `level` filters searches (a campus plan's is `associate_1`) |
| | `target`, `hired`, `hires_json` | int, int, text | Hires wanted; accepted so far; their person ids |
| | `channel`, `focus`, `ratio_bp` | str, str, int | `job_post`, `recruiter`, `referral`, `campus` (a practice group's campus target) or `any`; `current` or `potential`; offered salary in bp of the ask (at most `org.delegates.max_ratio_bp`) |
| | `created_turn`, `status`, `closed_turn` | int, str, int | `active`, `paused` (owner left or no longer qualifies), `filled` or `closed` |
| | `activity_json` | text, null | What the delegate did in its last active turn (searches, interviews, scouted, offers) |
| `org_person` | `person_id` | int | Org facts about one person |
| | `energy` | int, null | A delegate's **own** energy (null: not a delegate); reset to `org.delegates.energy_per_month` after phase 12 (ADR-0015) |
| | `last_raise_turn` | int, null | Turn of the last raise that earned the morale bonus (TST §13.8 cooldown) |
| | `accelerated_years`, `last_promoted_turn` | int, int null | Class years promoted ahead of September; the latest promotion |
| `org_morale_nudge` | `id`, `person_id`, `turn`, `points`, `reason` | int, int, int, float, str | One-off morale changes from org actions (TST §13.7, §13.8), applied by morale in phase 8 of their turn and then cleared |

`decision_log` is written from PT-M2: one row per org action (`source` `player`, payload the action as JSON with its `kind`) and per delegate step (`source` `delegate`).
