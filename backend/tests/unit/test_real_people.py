"""ADR PT-0013's real people (PT-M5 sub-task 1a): the `world.real_people` setting swaps names
only, and no restricted event, tag or effect ever selects a person flagged `real`."""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.people.models import WorkMonth
from ptk.sim.people.strain import strain_month
from ptk.sim.rivals.people import person_of
from ptk.sim.state import GameState
from tests.rivals_support import hire_away, play_until, start

TURNS = 40


def _no_names(state: GameState) -> GameState:
    """The state with every name blanked (people, judges, the rivals' news words)."""
    people = tuple(replace(p, first_name="", last_name="") for p in state.people)
    judges = tuple(replace(j, first_name="", last_name="") for j in state.market.judges)
    moves = tuple(replace(m, detail="") for m in state.rivals.moves)
    rivals = replace(state.rivals, real_people=True, moves=moves)
    market = replace(state.market, judges=judges)
    return replace(state, people=people, rivals=rivals, market=market)


def test_real_people_off_plays_identically_apart_from_names(
    data: GameData, balance: Balance
) -> None:
    """The brief's criterion: a state-cache comparison on everything but names."""
    on = start(data, balance, 8, real_people=True)
    off = start(data, balance, 8, real_people=False)
    # the swap changes names, and only names
    real_on = [j for j in on.market.judges if j.real]
    real_off = [j for j in off.market.judges if j.real]
    assert [(j.first_name, j.last_name) for j in real_on] != [
        (j.first_name, j.last_name) for j in real_off
    ]
    flom = next(m for m in on.rivals.members if m.notable == "skadden__joseph_flom")
    named = person_of(on, flom, data, balance)
    swapped = person_of(off, flom, data, balance)
    assert (named.first_name, named.last_name) == ("Joseph H.", "Flom")
    assert swapped.last_name != "Flom" and swapped.real
    assert replace(named, first_name="", last_name="") == replace(
        swapped, first_name="", last_name=""
    )
    # and play: hire a few notables so real people sit on the player's books too
    on = hire_away(on, "cravath", 0.2, data, balance)
    off = hire_away(off, "cravath", 0.2, data, balance)
    on, a = play_until(on, data, balance, TURNS, 8)
    off, b = play_until(off, data, balance, TURNS, 8)
    assert _no_names(on) == _no_names(off)
    for x, y in zip(a, b, strict=True):
        assert x.ledger_entries == y.ledger_entries
        assert [i.kind for i in x.log_items] == [i.kind for i in y.log_items]


def test_no_restricted_tag_event_or_effect_selects_a_real_person(
    data: GameData, balance: Balance
) -> None:
    state = start(data, balance, 9)
    negative = {t.key for t in data.tags if t.negative}
    real = [person_of(state, m, data, balance) for m in state.rivals.members if m.notable]
    assert real and all(p.real and not set(p.tags) & negative for p in real)
    # real people on the player's books: a decade of tags, strain and events
    state = hire_away(state, "wachtell", 0.5, data, balance)
    state = hire_away(state, "williams_connolly", 0.5, data, balance)
    names = {f"{p.first_name} {p.last_name}" for p in state.people if p.real}
    assert len(names) >= 4
    restricted_kinds = {t.trigger for t in data.event_templates if t.restricted} | {
        "deadline_missed",
        "matter_disqualified",
        "waiver_refused",
        "introduction_failed",
    }
    state, results = play_until(state, data, balance, 60, 9)
    for p in state.people:
        if p.real:
            assert not set(p.tags) & negative
            assert p.burnout_since is None and p.last_burnout_turn is None
    for r in results:
        for item in r.log_items:
            if item.kind in restricted_kinds or item.kind.startswith(tuple(restricted_kinds)):
                assert not any(n in item.message for n in names), item
    restricted = {t.id for t in data.event_templates if t.restricted}
    for ev in state.events.events:
        if ev.template_id in restricted:
            assert not any(state.person(pid).real for pid in ev.person_ids), ev.template_id


def test_a_real_person_never_burns_out(data: GameData, balance: Balance) -> None:
    state = start(data, balance, 10)
    m = next(m for m in state.rivals.members if m.notable)
    person = replace(person_of(state, m, data, balance), strain=balance.strain.burnout_at - 2)
    month = WorkMonth(person_id=person.id, practice_tenths=(("corporate_ma", 4000),))
    for turn in range(12):
        person = strain_month(person, turn, month, balance)
        assert person.burnout_since is None
        assert person.strain < balance.strain.burnout_at
    generated = replace(person, real=False)
    assert strain_month(generated, 13, month, balance).burnout_since is not None
