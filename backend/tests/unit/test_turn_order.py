"""The turn pipeline keeps ADR-0006's 12 slots, with Partner Track's names (spec 4.1)."""

from ptk.sim.turn import PHASES


def test_phase_order_is_fixed() -> None:
    assert [name for name, _ in PHASES] == [
        "apply_player_decisions",
        "delegate_and_rival_decisions",
        "knowledge_progress",
        "intake_and_staffing",
        "work_and_billing",
        "payroll_and_operating_costs",
        "financing",
        "people_updates",
        "market_and_macro_update",
        "stage_checks",
        "snapshot_and_month_end_report",
        "event_director_requests",
    ]


def test_phase_names_match_functions() -> None:
    for name, phase in PHASES:
        assert phase.__name__ == name
