"""PT-M19a (ADR PT-0019): Partner Track on sim-core 0.1.

- no shadow copies: PT's replaced kernel, llm and db modules are gone, and no module of
  ptk/sim takes the name of a sim-core kernel module except the three PT keeps on purpose;
- the stream table is sim-core's `StreamTable` with PT's rows and the `partnership` alias, and
  every PT stream draws exactly sim-core's derivation;
- the twelve phases are registered in sim-core's slots in today's order;
- GameState's sub-states are registered and survive sim-core's save codec on a played game;
- the three books and the paid-bill bridge are declared with sim-core's types;
- hidden true values are marked, and a record carrying one cannot enter a prompt.
"""

from __future__ import annotations

import dataclasses
import pkgutil
import typing
from pathlib import Path

import pytest
import simcore.kernel
from hypothesis import given
from hypothesis import strategies as st
from simcore.kernel import errors as core_errors
from simcore.kernel.errors import BookError, HiddenValueError
from simcore.kernel.hidden import check_public, hidden_names
from simcore.kernel.rng import CORE_STREAMS, derive
from simcore.state.codec import decode, encode
from simcore.turn import SLOTS
from simcore_llm.prompts import PublicFacts

from ptk.sim import errors, ledger, streams
from ptk.sim.billing.models import ClientBookEntry, ClientBookLine
from ptk.sim.data_models import Balance, GameData
from ptk.sim.founder.models import PERSONAL_ACCOUNTS
from ptk.sim.state import SUB_STATES, GameState
from ptk.sim.turn import PHASES, REGISTRY

BACKEND = Path(__file__).resolve().parents[2]
PTK = BACKEND / "ptk"

# Modules of ptk/sim named like a sim-core kernel module, kept on purpose (ADR PT-0019):
# errors holds PT's domain errors over sim-core's base classes; ledger and log hold PT's entry
# and log types, whose move to sim-core's (entity_id, dims) is cut to 0.2.
KEPT: typing.Final = frozenset({"errors", "ledger", "log"})
REPLACED: typing.Final = ("rng", "money", "dmath", "scale", "calendar")


def test_no_ptk_sim_module_shadows_a_simcore_kernel_module() -> None:
    kernel = {m.name for m in pkgutil.iter_modules(simcore.kernel.__path__)}
    sim = {p.stem for p in (PTK / "sim").rglob("*.py")}
    assert sim & kernel <= KEPT, sorted(sim & kernel - KEPT)
    for name in REPLACED:
        assert not list(PTK.rglob(f"{name}.py")), name


def test_the_llm_and_db_copies_are_gone() -> None:
    assert not (PTK / "llm").exists()
    for name in ("session", "backup", "migrate"):
        assert not (PTK / "db" / f"{name}.py").exists(), name


def test_kernel_errors_are_simcores() -> None:
    for name in ("SimError", "UnbalancedEntryError", "InvalidSeedError", "NotFoundError"):
        assert getattr(errors, name) is getattr(core_errors, name)
    assert issubclass(errors.GameOverError, core_errors.SimError)


# --- Streams ------------------------------------------------------------------------------


def test_the_table_is_pts_rows_on_the_core_table() -> None:
    assert streams.TABLE.ids["partnership"] == CORE_STREAMS["governance"] == 17
    assert not set(streams.OWN_ROWS) & set(CORE_STREAMS)
    for name, sid in CORE_STREAMS.items():
        assert streams.STREAM_IDS[name] == sid
    for name, sid in streams.OWN_ROWS.items():
        assert streams.STREAM_IDS[name] == sid


@given(
    st.integers(0, 2**64 - 1), st.integers(0, 2**31), st.lists(st.integers(0, 2**31), max_size=3)
)
def test_every_stream_draws_simcores_derivation(seed: int, turn: int, key: list[int]) -> None:
    factory = streams.RngFactory(seed)
    for name, sid in sorted(streams.STREAM_IDS.items()):
        ours = factory.stream(turn, name, *key).integers(0, 2**62, 2).tolist()
        assert ours == derive(seed, turn, sid, *key).integers(0, 2**62, 2).tolist(), name


def test_pt_still_refuses_negative_turns_and_keys() -> None:
    with pytest.raises(errors.InvalidSeedError):
        streams.RngFactory(1).stream(-1, "misc")
    with pytest.raises(errors.InvalidSeedError):
        streams.RngFactory(1).stream(0, "misc", -3)


# --- Turn and state -----------------------------------------------------------------------


def test_the_phases_fill_the_twelve_slots_in_todays_order() -> None:
    assert [spec.slot for spec in REGISTRY.order] == list(SLOTS)
    assert [name for name, _ in PHASES] == [spec.name for spec in REGISTRY.order]


def test_every_sub_state_field_is_registered() -> None:
    subs = {
        f.name
        for f in dataclasses.fields(GameState)
        if dataclasses.is_dataclass(f.default) and f.default is not dataclasses.MISSING
    }
    assert {s.key for s in SUB_STATES.specs} == subs
    for spec in SUB_STATES.specs:
        field = next(f for f in dataclasses.fields(GameState) if f.name == spec.key)
        assert spec.empty is field.default


def test_a_played_states_sub_states_round_trip_through_simcores_codec(
    data: GameData, balance: Balance
) -> None:
    from ptk.balance.game import start_game
    from ptk.balance.report import SCENARIO
    from ptk.balance.strategies import PLAYABLE

    game = start_game(data, balance, 2, SCENARIO)
    for _ in range(4):
        PLAYABLE["steady"](game)
        game.turn()
    for spec in SUB_STATES.specs:
        value = getattr(game.state, spec.key)
        assert decode(spec.type, encode(value)) == value, spec.key


# --- Books --------------------------------------------------------------------------------


def test_the_chart_holds_pts_three_books() -> None:
    chart = ledger.CHART
    assert [(b.code, b.prefix) for b in chart.books] == [
        ("firm", ""),
        ("personal", "9"),
        ("client_money", "C"),
    ]
    assert all(chart.book_of(a) is ledger.FIRM_BOOK for a in ledger.ENGINE_ACCOUNTS)
    assert all(chart.book_of(a) is ledger.PERSONAL_BOOK for a in PERSONAL_ACCOUNTS)
    for account in (ledger.CLIENT_BANK, ledger.OWED_TO_CLIENTS):
        assert chart.book_of(account) is ledger.CLIENT_BOOK
    bridge = chart.bridge(ledger.BILL_PAID)
    assert (bridge.from_account, bridge.from_contra) == (ledger.CLIENT_BANK, ledger.OWED_TO_CLIENTS)
    assert (bridge.to_account, bridge.to_contra) == (ledger.CASH, ledger.RECEIVABLES)
    assert bridge.leakage_bp == 0


def test_a_client_book_entry_with_a_firm_account_is_refused() -> None:
    with pytest.raises(errors.UnbalancedEntryError):
        ClientBookEntry(
            turn=0,
            firm_id=1,
            memo="x",
            lines=(
                ClientBookLine(ledger.CLIENT_BANK, 7, 100),
                ClientBookLine(ledger.CASH, 7, -100),
            ),
        )


@given(st.sampled_from(["1000_cash", "C1000_client_bank", "9100_personal_cash", "4000_fees"]))
def test_a_firm_entry_is_accepted_only_inside_the_firm_book(account: str) -> None:
    in_firm = ledger.CHART.book_of(account) is ledger.FIRM_BOOK
    try:
        ledger.LedgerEntry.transfer(
            turn=0, firm_id=1, memo="x", debit="1000_cash", credit=account, amount=100
        )
    except errors.UnbalancedEntryError:
        assert not in_firm
    else:
        assert in_firm


def test_the_chart_refuses_a_bridge_across_the_wrong_books() -> None:
    from simcore.kernel.ledger import BookBridge, Chart

    with pytest.raises(BookError):
        Chart(
            books=ledger.CHART.books,
            bridges=(
                BookBridge(
                    "bad", "client_money", "firm", ledger.CASH, ledger.OWED_TO_CLIENTS,
                    ledger.CASH, ledger.RECEIVABLES,
                ),
            ),
        )  # fmt: skip


# --- Hidden values ------------------------------------------------------------------------

HIDDEN: typing.Final = {
    ("ptk.sim.people.models", "Person"): {"hidden", "potential_ability", "tags", "portability_bp"},
    ("ptk.sim.matters.models", "Matter"): {"hidden_conflict", "merits", "opposing_quality"},
    ("ptk.sim.matters.models", "Judge"): {"traits"},
    ("ptk.sim.matters.models", "GeneralCounsel"): {"personality"},
    ("ptk.sim.risk.models", "Claim"): {"merit", "size_cents"},
    ("ptk.sim.risk.models", "DisciplinaryCase"): {"culpability"},
    ("ptk.sim.billing.models", "Bill"): {"padding_cents"},
    ("ptk.sim.partnership.models", "Partner"): {"satisfaction", "confidence"},
    ("ptk.sim.mergers.models", "BookClient"): {"adverse_client_id"},
}


@pytest.mark.parametrize(("where", "names"), sorted(HIDDEN.items()))
def test_hidden_true_values_are_marked(where: tuple[str, str], names: set[str]) -> None:
    import importlib

    cls = getattr(importlib.import_module(where[0]), where[1])
    assert hidden_names(cls) == names


def test_a_person_cannot_enter_a_prompt(data: GameData, balance: Balance) -> None:
    from ptk.balance.game import start_game
    from ptk.balance.report import SCENARIO

    person = start_game(data, balance, 1, SCENARIO).state.people[0]
    with pytest.raises(HiddenValueError):
        check_public({"people": [person]}, where="event prompt")
    with pytest.raises(HiddenValueError):
        PublicFacts().add("person", person)


def test_pts_calendar_keeps_its_2005_default() -> None:
    from simcore.kernel import calendar

    from ptk.sim import dates

    assert dates.turn_to_ym(0) == (2005, 1) and calendar.turn_to_ym(0) == (2010, 1)
    assert dates.format_turn(359) == calendar.format_turn(359, (2005, 1)) == "Dec 2034"
