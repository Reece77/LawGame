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
## Schema v4 (`0004_org`, PT-M2)

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
| | `last_raise_turn` | int, null | Turn of the last raise that earned the morale bonus (TST §13.8 cooldown) |
| | `accelerated_years`, `last_promoted_turn` | int, int null | Class years promoted ahead of September; the latest promotion |
| `org_morale_nudge` | `id`, `person_id`, `turn`, `points`, `reason` | int, int, int, float, str | One-off morale changes from org actions (TST §13.7, §13.8), applied by morale in phase 8 of their turn and then cleared |

`decision_log` is written from PT-M2: one row per org action (`source` `player`, payload the action as JSON with its `kind`) and per delegate step (`source` `delegate`).

## Schema v5 (`0005_matters`, PT-M3a)

Clients and judges are written once at game creation. `relationship`, `matter`, `appearance`, `origination` and `market_demand` are current state, rewritten each turn and after each action. `hours_log` is append-only. JSON payload columns hold the rest of each frozen sim model (`ptk/sim/matters/models.py`); hidden values in them (merits, opposing counsel's quality, judges' traits, GCs' personality) never reach the API (CLAUDE.md §10).

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `firm` | `conflict_checks` | bool | The firm runs conflicts checks at intake (ADR PT-0009 §5); off, conflicts open unseen and may surface |
| `client` | `id` | int | 1..300 are `clients.yaml`'s real clients in file order, then the generated ones (stream `client_gen`) |
| | `name`, `sector`, `real` | str, str, bool | `sector` is a `clients.yaml` sectors key |
| | `data_json` | text | `country`, `revenue_bn` (2005 USD bn), `size_class` (`large`/`mid`), `price_sensitivity` and `loyalty` (1–20), `panel` (static panel firm keys), `gc` (first and last name, `birth_turn`, hidden personality) |
| `judge` | `id`, `court` | int, str | Generated judges, courts.yaml order (stream `judge_gen`) |
| | `first_name`, `last_name`, `real` | str, str, bool | Real judges arrive with PT-M5 |
| | `traits_json` | text | Hidden procedural traits 1–20 (`courts.yaml` judge_traits): never a side |
| `relationship` | `client_id`, `firm_id` | int | The firm on the client's panel (only the player's firm keeps relationships in PT-M3a) |
| | `score` | float | 0–100 (spec §7.2) |
| | `partner_id` | int, null | The relationship partner, who earns flow origination credit |
| | `data_json` | text | `practices` (instructed in), `since_turn`, `last_instructed_turn` (current client within `conflicts.current_months`), `advance_waiver`, `lost_share` (last month's unserved share of its flow), `fees` (standard-value cents, the last 12 months), `intro_turns` (latest introduction per practice) |
| `matter` | `id`, `firm_id`, `client_id`, `practice` | int, int, int, str | A named matter (ADR PT-0004) |
| | `status` | str | `open`, `conflicted` (waits for a waiver), `closed`, `declined` |
| | `opened_turn`, `closed_turn` | int, int null | |
| | `data_json` | text | `kind_key`, `kind`, `name`; `planned_months`, `expected_fees_cents`, `hours_needed_tenths`; parties (`adverse_client_id`, `adverse_name`); flags `critical`, `flagged`, `checked`, `waiver`, `hidden_conflict`, `auto_staff`; `originator_id`, `lead_id`, `team` ([person, role, planned tenths a month]); progress (`phase_index`, `phase_progress`, `worked_tenths`, `wip_cents` at standard value, `craft_hours`, `craft_weight`, `under_months`); `errors_caught`, `errors_escaped`, `missed_deadlines`; `court`, `judge_id`, `stakes_cents`; hidden `merits` and `opposing_quality`; `settlement` ([fraction bp of stakes, made turn, expires turn] or null); `outcome` (`won`, `lost`, `settled`, `closed`, `collapsed`, `done`, `disqualified`), `quality` |
| `appearance` | `person_id`, `judge_id`, `tenths` | int | Hours a lawyer has appeared before a judge (motions and trial phases), tenths |
| `origination` | `person_id`, `year`, `cents` | int, int, bigint | Origination credit a calendar year: standard value of the work from a partner's matters and clients |
| `hours_log` | `id`, `turn`, `person_id`, `client_id`, `practice` | | Append-only: every month's hours by person and named matter or client flow (ADR PT-0005) |
| | `matter_id` | int, null | Null for flow work |
| | `tenths`, `substantive_tenths` | int | Hours, and those at or just above the person's level (learn(h)) |
| | `value_cents` | bigint | tenths × rate ÷ 10, rounded half to even once per (person, matter, month); PT-M3b posts it to WIP |
| `market_demand` | `practice`, `demand_cents` | str, bigint | The last month's New York demand by practice index (`00`..`09`, practices.yaml order), standard value |

## Schema v6 (`0006_billing`, PT-M3b)

Billing's books beside the ledger (ADR PT-0003 §2–§3, §7; ADR PT-0005). `engagement` and `bill` keep every row (closed ones stay as history; the state loads open engagements and bills plus those closed in the last turn); `flow_account` and `billing_padder` are current state, rewritten each turn and after each action; `billing_month` holds each month's totals (the state loads the last 12); the client book is append-only. Client funds are derived from the client book and the provisions and deferred income from the ledger, as cash is (ADR-0003). JSON payload columns hold the rest of each frozen sim model (`ptk/sim/billing/models.py`). Billing holds no hidden value.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `engagement` | `matter_id` | int | A named matter's billing terms and unbilled work (one per matter, drawn in the matter's first month, stream `billing` `(0, matter_id)`) |
| | `firm_id`, `client_id`, `model` | int, int, str | `model`: `hourly`, `blended`, `capped`, `fixed`, `success`, `contingency`, `retainer` (spec §7.7); a retainer becomes `hourly` after its term |
| | `closed`, `closed_turn` | bool, int null | Closed once the matter's final bill is issued |
| | `data_json` | text | `opened_turn`, `cycle_months` (1 or 3), `term_months` and `months_billed` (retainers), `discount_bp`, `price_cents` (cap, fixed price or monthly retainer), `rate_cents` (blended rate an hour), `share_bp` (success: share of standard billed monthly; contingency: share of the recovery), `bonus_cents` (success), `wip_cents` and `wip_tenths` (unbilled, standard value), `standard_cents` (all work so far), `billed_cents`, `last_bill_turn`, `writedown_bp` (the partner's write-down on the next bill), `advance_turn` (the month a retainer's advance covers), `offer_bp` (last settlement offer seen), `funds_cents` (money on account for the matter) |
| `flow_account` | `firm_id`, `client_id`, `practice` | int, int, str | A client's flow work in one practice (ADR PT-0004 §2), billed hourly every month |
| | `data_json` | text | `wip_cents`, `wip_tenths`, `last_bill_turn` |
| `bill` | `id` | int | A bill (never reused) |
| | `firm_id`, `client_id`, `matter_id`, `practice` | int, int, int null, str | `matter_id` null for flow work |
| | `model`, `kind` | str, str | `kind`: `fees` (a cycle bill), `final`, `retainer_advance` (debits receivables, credits 2200), `success` (bonus, 4100), `contingency` (share of a recovery, paid from the client account) |
| | `issued_turn`, `status`, `closed_turn` | int, str, int null | `status`: `open`, `disputed`, `paid`, `written_off` |
| | `billed_cents` | bigint | The invoice |
| | `data_json` | text | The whole `Bill`: `due_turn` (when the client pays, from its days to pay), `standard_cents` (WIP relieved), `paid_cents`, `credited_cents` (credit notes: disputes, short payments, padding found), `written_off_cents` (bad debts, 6700), `padding_cents` (a padder's time, shown only once found), `short_cents` (what the client will leave unpaid), `dispute` ([amount, raised turn, expires turn, padded] or null) |
| `billing_month` | `firm_id`, `turn` | int | One month's revenue-chain totals |
| | `data_json` | text | `worked_cents` (WIP posted), `standard_cents` and `billed_cents` (work billed and its fees: realisation), `invoiced_cents`, `collected_cents`, `credited_cents`, `written_off_cents`, `fees_cents` (accrual revenue), `premium_cents` (4100 above standard), `resolved_billed_cents` and `resolved_paid_cents` (bills closed that month: collection), `billable_tenths`, `capacity_tenths` (utilisation) |
| `billing_padder` | `person_id` | int | A lead whose padding a dispute has brought to light (no more padding from them) |
| `client_book_entry` | `id`, `turn`, `firm_id`, `memo` | int, int, int, text | An entry in the client-money book (ADR PT-0003 §7): deposits on account, recoveries received, transfers to the firm for bills (also in the firm's ledger), money returned |
| `client_book_line` | `id`, `entry_id`, `account`, `client_id`, `amount_cents` | int, int, str, int, bigint | `account`: `C1000_client_bank` (debit) or `C2000_owed_to_clients` (credit), by client; every entry balances, and the bank equals Σ owed at every month end |

`turn_snapshot.kpis_json` gains (PT-M3b): `collections_cents`, `wip_cents`, `receivables_cents`, `utilisation_bp`, `realisation_bp`, `collection_bp`, `lockup_days`, `open_disputes`; `revenue_cents` is now the month's accrual fees.

## Schema v7 (`0007_events`, PT-M6)

Events, storylines, queued events, modifiers, colleague pairs and the id counters are current state, rewritten each turn, after each answer and after the event service writes a turn's events. `llm_text` and `llm_call_log` are append-only (a text's words are filled in once, after its turn commits). JSON payload columns hold the rest of each frozen sim model (`ptk/sim/events/models.py`). A colleague pair's value is hidden (the player sees a label); an event row never stores a trigger's hidden cause, only who and what it is about.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `game_event` | `id`, `firm_id`, `turn` | int | `turn` is the month the event is shown in (queued in phase 12 of the month before) |
| | `template_id`, `category`, `severity` | str | `data/events/*.yaml` template; spec 15's category; `minor`, `major` or `critical` |
| | `status` | str | `pending` (queued, words not yet written), `open`, `answered` (by the player), `auto` (first choice at Continue) |
| | `title` | text | Written title (empty while pending) |
| | `data_json` | text | `trigger`, `strength` (never shown), `person_ids`, `unit_id`, `client_id`, `matter_id`, `practice`, `months`, `amount_cents`, `cash_base_cents` (max(cash, 3 × monthly fees) when queued), `tone`, `storyline_id`, `body`, `choices` ([key, label, effects [type, target, value, stat, months], do_nothing]), `chosen`, `resolved_turn`, `source` (`claude`, `template`, `mock`) |
| `storyline` | `id`, `firm_id`, `key`, `status` | int, int, str, str | A multi-month thread (TST 16.6); `active` or `ended` |
| | `data_json` | text | `title`, `step`, `started_turn`, `summary`, `person_ids`, `unit_id`, `client_id`, `matter_id`, `practice`, `next_turn`, `next_template`, `ended_turn` |
| `queued_event` | `id`, `firm_id`, `template_id`, `due_turn`, `done` | | A critical event's follow-up, or an event a later milestone's engine queues (`queue_engine_event`) |
| | `data_json` | text | `source_event_id` (null: the engine), `person_ids`, `unit_id`, `client_id`, `matter_id`, `practice` |
| `event_modifier` | `id`, `firm_id`, `event_id` | int | A running effect of a choice (TST 23.2); dropped when it expires |
| | `target`, `stat` | str | `person:<id>`, `unit:<id>` or `firm:<id>`; `morale_target` or `strain_gain` |
| | `value_pct`, `start_turn`, `end_turn` | float, int, int | The stat × (1 + value_pct / 100) from `start_turn` until `end_turn` (exclusive) |
| `colleague_pair` | `a`, `b` | int | Two people on the same open matter team, `a < b` (TST 16.7); dropped when either leaves the firm |
| | `value`, `start`, `since_turn` | float, float, int | Hidden relationship −100..100, its start from temperaments, the month the pair formed |
| `event_counters` | `id` (1), `next_event_id`, `next_storyline_id`, `next_queued_id`, `next_modifier_id` | int | The next ids (expired modifiers and gone pairs are dropped, so max + 1 is not enough) |
| `llm_text` | `id`, `turn`, `firm_id`, `kind`, `ref_id` | | A read-only text for the month played: `headlines`, `matter_brief` (`ref_id` the matter), `pitch_letter` (`ref_id` the client), `partner_memo`, `year_end_letter` |
| | `status`, `text`, `source` | str, text, str | `pending` until the service writes it, then `written`; `claude`, `template` or `mock` |
| `llm_call_log` | `id`, `turn`, `purpose`, `model`, `prompt_hash` | | One adapter call (ADR-0005 §6): `event`, `story` or a text kind; the first 16 hex digits of the prompt's SHA-256 |
| | `input_tokens`, `output_tokens`, `cost_cents`, `latency_ms` | int, int, float, int | `cost_cents` is the meter's (real money, not game money) |
| | `outcome`, `created_at` | str, str | `ok`, `rejected`, `budget`; wall-clock time (the meter only, never the sim) |
| | `prompt`, `response` | text, null | Only with `PTK_LLM_DEBUG=1` |

`inbox_item` gains templates `event` and `critical_event` (link kind `event`, the event's card) and `llm_text` (a written briefing, letter or memo; headlines show on the Overview instead).

## Schema v8 (`0008_partnership`, PT-M4)

The partnership is current state, rewritten each turn and after each action: one row per firm holding the whole `FirmPartnership` (`ptk/sim/partnership/models.py`) as JSON, and a row (`firm_id` 0) with the id counters. Hidden values live only in this JSON and never reach the API: each partner's `confidence` and `satisfaction`, and (in `person`) their `portability_bp`.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `partnership` | `firm_id` | int | The firm; 0 is the counters row (`next_vote_id`, `next_approach_id`) |
| | `data_json` | text | `agreement` (the agreement's terms, spec 8.6: `comp_system`, `two_tier`, `voting`, the vote thresholds in bp, `track_years`, `mp_term_years`, `retirement_age`, `notice_months`, `capital_share_bp`, `draw_share_bp`, `retain_bp`); `mp_id`; `partners` (by person: `klass` equity or income, `admitted_turn`, `points`, `capital_required_cents`, `capital_cents` (the 3000 sub-ledger), `capital_instalment_cents`, `budget_cents` and `budget_base_cents` (draws follow the budget; quarterly re-forecasts only cut it), `drawn_ytd_cents`, `current_cents` (the 2700 sub-ledger: allocated, not yet paid), `guarantee_cents` and `guarantee_until_turn`, `promised_cents` and `promised_points` (counter-offers and promises), `comp_last_cents`, `satisfaction` and `confidence` (hidden), `gate_steps` and `adjust_bp` (the December comp round), `working_ytd_cents` (working credit), `lobbied_turn`, `seat`, `nudge` (one-off confidence points)); `capital_returns` (leavers' capital and current accounts still owed: `monthly_cents`, `remaining_capital_cents`, `remaining_current_cents`, `start_turn`); `votes` (`kind` admission, terms, capital_call, deequity, election; `subject_id`, `params`, `opened_turn`, `threshold_bp`, `status`, `resolved_turn`, `yes_weight`, `no_weight`, `ballots`: who voted which way, never a utility); `candidacies` (this December's proposals: `track`, `sponsor_id`, `year`, `vote_id`); `sponsors` ([associate, partner]); `moving_on` (up or out: `told_turn`, `leave_turn`, `in_house`); `approaches` (`suitor_key`, `suitor_name`, `suitor_firm_id`, `offer_comp_cents`, `guarantee_years`, `made_turn`, `respond_by_turn`, `status`, the counter's comp, points, guarantee years and seat, `stay_hint`: the band shown); `departures` (`turn`, `leave_turn`, `practice`, `reason`, `equity`, the suitor, `book_cents`, `follows`: [client, turn]); `laterals` (lateral partner candidates: `search_id`, `practice`, `ask_cents`, `guarantee_ask_years`, `book_lo_cents` and `book_hi_cents` (the range shown; the true book is the person's `book_cents`), `client_ids`, `conflict_ids`, `created_turn`, `expires_turn`, `diligence`, `status`, the offer); `arrivals` (a lateral's book clients still to come: [person, client, turn, practice]); `pnl` (the last 13 month ends: cumulative accrual revenue and costs, equity partners, lawyers); `pnl_closed_revenue_cents`, `pnl_closed_costs_cents` and `wc_closed_cents` (where the year began: the allocation is the year's cash-basis profit); `last_profit_cents`, `last_pep_cents`, `last_revenue_cents`; `allocated_ytd_cents` (leavers' draws allocated this year); `equity_months` and `months` (PEP's average); `facility_cents`, `breach_months`, `called_turn`, `insolvent_months` (the revolver and the bank); `draws_suspended`; `last_warning_turn` (the CFO's); `term_ends_turn`, `low_confidence_months`, `election_lost_turn`, `ousted_mp_id` (the MP's term and elections) |

`turn_snapshot.kpis_json` gains (PT-M4): `pep_cents`, `rpl_cents`, `margin_bp`, `leverage_bp` (lawyers per equity partner × 10,000), `equity_partners`, `revolver_cents` (drawn); trailing twelve months. `save_meta.game_state` may also be `election_lost` (ironman only). Ledger accounts first posted in PT-M4: 2300 (revolver), 2700 (partner current accounts), 3000 (capital in and out), 3100 (profit allocated), 3200 (draws), 6600 (lateral diligence), 6800 (revolver interest); a lateral partner's recruiter retainer and fee go to 6200.

## Schema v9 (`0009_rivals`, PT-M5)

Rival firms are current state in one JSON document, rewritten each turn and after each market action (`ptk/db/rivals_io.py` encodes the frozen models of `ptk/sim/rivals/models.py` from their type hints; floats round-trip exactly). Rival key people are **not stored**: each is generated on demand from its member record (stream `rival_people`, a pure function of the seed), until the player's firm meets them, when their record moves to `person`. Every rival also has a `firm` row (`is_player` false), because ledger entries and the turn log refer to firm ids; rival firms post one balanced entry a month (fees, salaries and costs, the month's profit to drawings, cash unchanged). Client panels (`client.data_json`'s `panel`) are rewritten when RFP awards, mergers and collapses change them. Hidden values in `rival_state` (a firm's demand, AR(1) shock, the player's effects, rate index, cost and capacity; a key person's book) never reach the API.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `rival_state` | `id` | int | Always 1 |
| | `real_people` | bool | `world.real_people` at game creation (ADR PT-0013): real lawyers' and judges' names, or generated ones with the same draws |
| | `data_json` | text | `firms` (id, `rival_key`, key, name, personality, kind `real`/`generated`/`boutique`, status `active`/`merged`/`collapsed`/`failed`, `pools` by practice: equity, other partners, associates; revenue per lawyer at capacity, cost per lawyer, demand, rate index, shock, offset, utilisation, the last 12 months' fees and profit, `history` by year: revenue, lawyers, equity partners, PEP; departures, cooldowns, a successor's anchor, stance, `people_made`, `key_target`); `members` (key people: person id, firm, kind, practice, book, level, the generation keys, `notable`, `outside`); `moves` (the last 24 months' decisions and history events); `approaches`; `rfps` (open, and awarded in the last 24 months, with the player's pitch and the winners); `free_agents`; `history_done` (each dated event: `happened`, `called_off` or `forward`); `appeals` (each active rival's NY panel appeal by practice); `opposing` (a case's opposing counsel: matter id, rival key or "" for a pool); id counters |
| `judge` | `from_turn`, `until_turn` | int, int | The first turn on the bench and the first turn off it (null: never leaves); real judges from `judges.yaml` by their years, then generated successors |

`decision_log` gains rows with `source` `rival`: each rival move's fields, for history only (ADR-0015 5: replay recomputes them). `inbox_item` gains templates `rfp_open`, `rfp_won`, `rfp_lost` (link kind `rfp`), `rival_approach`, `rival_poached`, `rival_approach_declined` and `rival_joined`.

## Schema v10 (`0010_v1_gaps`, PT-M7a)

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `firm` | `pro_bono_credit_hours` | int, null | Pro bono hours a year credited toward each lawyer's billable target (spec 7.8); null: `pro_bono.credit_hours` (50) |
| | `pro_bono_avg_tenths` | float | The firm's pro bono tenths a lawyer a month, a moving average (`pro_bono.average_rate`); its recruiting appeal |
| | `rate_rise_bp` | int, null | Each January's rate rise in bp; null: the market's (`rivals.rate_inflation`) |
| | `rate_index` | float | The firm's rate card over the practices' 2005 cards (1.0 at the start); every hour's standard value, blended rates and new matters' expected fees use it |
| `person_state` | `pro_bono_ytd_tenths` | int | Pro bono worked this calendar year (reset by January's month); its credit is capped by the firm's policy |
| `client` | row `id` 0 | | The pro bono client (`PRO_BONO_CLIENT`): pro bono matters reference it; it is never loaded into the client universe (no wallet, panel or relationship) |

`matter.data_json` gains `assessment` (PT-M7a, early case assessment: `[turn, lo, hi]`, the revealed range of the case's merits in logit points, always holding the hidden `merits`; null until assessed). A pro bono matter has `client_id` 0 and `expected_fees_cents` 0. `hours_log` rows for pro bono work have `client_id` 0 and `value_cents` 0: they post no WIP and are not billable (utilisation is billable hours over capacity). `inbox_item` gains templates `rates_rose`, `case_assessed` and `pro_bono_opened`.

## Schema v11 (`0011_founder_life`, PT-M17)

The founder's life and family are current state in two JSON documents, rewritten each turn and after each founder or family action (`ptk/db/founder_io.py` encodes the frozen models of `ptk/sim/founder/models.py` and `ptk/sim/family/models.py` from their type hints). The players' personal books are their own double entry, like the client-money book: personal accounts (codes beginning 9) appear only in `personal_line`, never in `ledger_line` (`LedgerEntry` refuses them). Family members are rows in `person` with no employment until a child joins the firm; their potential and hidden traits are hidden as anyone's.

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `founder_life` | `key` | text | `founder_life` or `family` |
| | `data_json` | text | `founder_life`: `lives` (every person the player has played: the four persona traits 0-100, `status` managing_partner, partner, senior_partner, retired, `since_turn`, `until_turn`, `causes` [turn, trait, change, words], the year's revolver-leverage points, bar politics: `influence`, `committee`, `bar_spend_cents`, `standing`, `office_until_turn`, `office_turns`; `successor_plan`); `books` (each player's running balances by account, the family office's `mandate`, and the partnership marks the next month's mirror compares: drawn year to date, current account, capital, a leaver's capital return); `foundations` (`name`, `cause`, `created_turn`, lifetime `grants_cents` and `gifts_cents`, the last grant); `annuities` (retired partners': `monthly_cents`, `remaining_cents` (the 2600 sub-ledger), `start_turn`, `end_turn`); `annuity_terms` (the agreement's annuity term once voted; null: `founder_life.annuity`); `successions` (`turn`, `trigger` choice, retirement, election, health; `founder_id`, `successor_id`, `vote_id`, `rival_id`, `result` open, elected, lost, lapsed, handed_over); `retirement_due_turn` and `due_trigger`; `opinions` (the senior partner's: vote, stance, words, overruled); `best_revenue_cents` (legacy). `family`: `family` (`setting`, `head_id`, `family_time`, `relationship`, `partner_since`, `married`, `low_months`, `next_index`, `lifetime_gifts_cents`, `estate_tax_cents`, `trust_turn`, `notes`) and `members` (`relation` partner, child, ex_partner; `member_index`, `head_id`, `joined_turn`, `parent_ids`, `closeness`, `school`, `law_school`, `milestones`, `mentored`, `joined_firm_turn`, `seen_level`, `left_turn`) |
| `personal_entry` | `id` | int | Entry id (written order) |
| | `turn` | int | The turn (or the action's turn) |
| | `person_id` | int | Whose book |
| | `memo` | text | What it was |
| | `source` | text | `opening`, `draws`, `true_up`, `tax`, `capital`, `loan`, `invest`, `annuity`, `gift`, `grant`, `education`, `estate`, `gift_heir`, `trust`, `divorce` |
| `personal_line` | `entry_id` | int | The entry |
| | `account` | text | A personal account: 9100 cash, 9110 investments, 9120 capital in the firm, 9130 family office, 9140 family trust, 9200 foundation endowment; 9300 spending, 9310 income tax, 9320 loan interest, 9330 education, 9340 estate and gift tax, 9350 foundation grants, 9360 divorce settlement; 9400 draws, 9410 true-up, 9420 investment gains, 9430 losses, 9440 annuity income; 9500 capital loan, 9510 tax payable; 9900 opening net worth |
| | `amount_cents` | bigint | Debit positive, credit negative; each entry sums to zero |

Ledger accounts first posted in PT-M17: 2600 (retired-partner annuities: booked against 3100 at retirement, paid monthly from 1000) and 6950 (bar politics). `employment.end_reason` `retired` (mandatory retirement through PT-M4's departure). `save_meta.game_state` may be `election_lost` when a forced succession's vote is lost on ironman. `inbox_item` gains templates `foundation_created`, `foundation_grants`, `bar_office_won`, `bar_office_lost`, `annuity_granted`, `annuity_vote`, `succession_due_retirement`, `succession_due_health`, `succession_elected`, `succession_lost`, `succession_handover`, `adviser_opinion`, `family_divorce`, `family_milestone`, `family_partner_met`, `family_married`, `family_child_born` and `family_joined_firm`.

## Schema v12 (`0012_pressure`, PT-M7b)

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `firm` | `rate_card` | text (JSON) | The firm's card by practice: `{practice: bp}`, its share of each practice's top 2005 card (`practices.yaml`). A new firm starts every practice at `rates.card.start_bp` times the difficulty's `card_mult_bp`; each January a practice moves at most `rates.card.step_bp` toward the share its reputation earns. A practice's hours, blended rates and new matters' fees are valued at the card times `rate_index`. `{}` (a save from before PT-M7b): every practice at the full card |
| | `billable_target_hours` | int, null | The hours policy: a firm-wide billable target, hours a year (`staffing.policy_min_hours`-`policy_max_hours`); the default staffing rule and flow plan toward it, above `staffing.plan_fill` and up to `staffing.policy_fill_max` of capacity. Null: each level's `billable_target_hours` |

`partnership.data_json` gains (PT-M7b): each `pnl` point's `drawn_cents`, `capital_cents` and `cash_cents` (the month end's revolver balance, partners' capital and cash: the CFO's forecast reads their trailing trend), and `last_forecast_turn` (the CFO's last forecast warning). `billing_month.data_json` gains `crisis_writedown_cents` (the month's write-downs from clients' crisis requests). Difficulty's new fields (`books_mult_bp`, `revolver_mult_bp`, `loyalty_points`, `card_mult_bp`) are read from `scenarios.yaml` by the save's `difficulty`; they are not stored. `inbox_item` gains template `cfo_forecast` (link kind `finance`).

## Schema v13 (`0013_leadership`, PT-M8)

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `leadership` | `id` | int, pk | Always 1 |
| | `data_json` | text | `ptk.sim.org.seat_models.LeadershipState` as JSON: `holders` (firm, seat key, slot, person, appointed turn: 0 for a single seat, 1..9 for an executive committee member), `authorities` (firm, seat, slot, enabled, guardrails as `[key, value]` pairs; slot is a practice group's unit id for its leader), `decisions` (the last `authority.keep_decision_turns` months of what holders did under authority, with an engine-only mistake flag the API never shows), `pitches` (id, firm, seat, slot, holder, kind, title, why, made turn, cost, low/central/high cases in the kind's unit, params, status, resolved turn, follow-through baseline, outcome, measured), `firms` (the executive committee's `exco_elected` term, a proposed term awaiting the December vote, the last partners' meeting) and `next_pitch_id` |

A practice group leader's seat is the unit's leader (`org_unit.leader_id`, PT-M2): it is not copied into `leadership`, so PT-M2's existing leaders are the holders. The managing partner's seat is the partnership's MP. `decision_log` gains `source` `seat` rows (a `SeatDecision` as JSON), recomputed on replay. `llm_text.kind` gains `seat_report` (`ref_id`: the holder). `inbox_item` gains templates `seat_appointed`, `seat_vacated`, `pitch`, `pitch_answered`, `pitch_lapsed`, `pitch_scored`, `partners_meeting`, `exco_term` and `exco_elected`, and link kinds `org` and `pitch`.

## Schema v15 (`0015_standing`, PT-M16)

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `standing` | `id` | int, pk | Always 1 |
| | `data_json` | text | `ptk.sim.reputation.models.StandingState` as JSON. `reputation`: `entries` (firm, practice, region (0 New York), `value` 0-100, `mean` the long-run mean it drifts toward), `causes` (the player's last `reputation.causes_kept` changes: turn, practice or null for every practice, delta, cause), `outcomes` (the player's public outcomes in the record window: turn, practice, matter, outcome, points), `practice_value` (the player's standard value of work by practice, the last 12 months), `stars` (the player's star partners last month: person, practice), `prestige` (firm, 0-100). `press`: `moments` (id, trigger, turn, status pending/open/skipped/answered, `due_turn`, practice, rival firm, person (never a real person for a restricted trigger), displayed facts, tone, answered turn, `by_office`, a bold answer's reputation `baseline` and `backfired`, engine-only until it happens), `claims` (id, kind headcount/no_layoffs/match_scale/band, made and deadline turns, moment, practice, target, public baseline, ambition, audience, status open/kept/broken, resolved turn, reminder turn), `credibility` (0-100; null before the first month) and `cred_history`, `feuds` (rival firm, score 0-100, causes, rivalry turn, the rival's key partners lost to the player as last counted), `statements` (id, rival, person or null for its spokesperson, turn, kind statement/jab/answer, text), `next_id`, `scale_seen` (the market's first-year salary last month). `rankings`: the latest `tables` (fiscal year, kind revenue/pep, place, firm, name, value, lawyers), `league` (quarter-end turn, practice, region, place, firm, name, deals, value), `bands` (year, practice, region, firm, name, band 1-6, score), `people` (year, practice, person, firm, name, band), `places` (year, place, firm, name, survey score); `submission` (year, turn, matter ids, referee client ids, strength 0-1); `history` (the player's places: turn, list kind, practice, place or band); `years` (the player's fiscal years recorded each December: year, revenue, lawyers, PEP); `published` (list kind -> the turn it last published) |
| `ranking_entry` | `id` | int, pk | Written order |
| | `turn` | int | The month the list published |
| | `kind` | text | `revenue`, `pep`, `league`, `places`, `bands`, `people` |
| | `practice` | text, null | The practice (league tables, bands, individuals) |
| | `place` | int | The place; the band (1-6) for `bands` and `people` |
| | `firm_id` | int | The firm (the player's or a rival's id) |
| | `person_id` | int, null | A named individual (`people`) |
| | `name` | text | The firm's or person's name as published |
| | `value_cents` | bigint, null | Revenue or PEP (tables), deal value (league); the score x 100 (places, bands) |
| | `count` | int, null | Lawyers (tables), deals (league) |
| | `year` | int, null | The fiscal year (tables) or the ranking's year (places, bands, individuals) |

`ranking_entry` is appended when a list publishes (the turn's write) and never rewritten; the live state keeps only each list's latest edition. A save from before PT-M16 has no `standing` row: its first month seeds reputation. `decision_log` gains actions `answer_press` and `make_submission`. `inbox_item` gains templates `tables_published`, `league_tables`, `places_published`, `directory_bands`, `submission_made`, `press_moment`, `claim_made`, `claim_kept` and `claim_broken`, and link kinds `rankings` and `press`.
## Schema v14 (`0014_automation`, PT-M9)

| Table | Column | Type | Meaning |
| --- | --- | --- | --- |
| `automation` | `id` | int, pk | Always 1 |
| | `data_json` | text | `ptk.sim.automation.models.AutomationState` as JSON: `owners` (firm, area key from `balance.yaml` `automation.areas`, slot: a practice group's unit id for staffing else 0, the owner's person id, per-decision `limit_cents`, `monthly_cents`, priority, since turn, `answer_events`, guardrails as `[key, value]` pairs), `decisions` (the last `automation.keep_decision_turns` months of what owners did: firm, turn, seq, area, slot, person, kind (decision, mistake, proposal, over_budget, stretched, event, note; the API shows a mistake as a decision), action kind, text, commitment in cents, link kind and id, proposal id), `proposals` (id, firm, area, slot, owner, made and expiry turns, the action as JSON, title, why, the owner's recommendation, commitment, status pending/approved/declined/expired/failed, resolved turn) and `next_proposal_id` |
| `inbox_item` | `in_digest` | bool, default false | The item came from an automated area: the inbox's default view leaves it out and the month's digest lists it (TST 40.4) |

`decision_log` gains `source` `area` rows (an `AreaDecision` as JSON), recomputed on replay (ADR-0015). `inbox_item` gains templates `area_given`, `area_returned`, `auto_proposal`, `auto_proposal_expired`, `auto_proposal_answered` and `automation_digest`, and link kind `automation` (a proposal's id, or for a digest the month's turn).
