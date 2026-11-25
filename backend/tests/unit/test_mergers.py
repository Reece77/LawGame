"""PT-M13: mergers and the verein (docs/tasks/PT-M13-mergers-and-the-verein.md; ADR PT-0016).

Acceptance 3 (two thirds of each partnership; the rival's answer reads its partners' expected
PEP change), 8 (no hidden value in the API; no real person attached to merger events or press),
the exit, diligence's ranges, integration's flight, rivals' free-play mergers from 2026 only,
the verein's London way in, and seeded determinism.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import GameOverError, InvalidActionError, NotManagingPartnerError
from ptk.sim.mergers import closing, exits, integration
from ptk.sim.mergers.actions import ApproachFirm, PutTerms, apply_merger_action
from ptk.sim.mergers.books import hidden, sheet
from ptk.sim.mergers.diligence import money_range, partner_quality, reveal, shown_range
from ptk.sim.mergers.models import Terms
from ptk.sim.mergers.profile import player_side, rival_side
from ptk.sim.mergers.talks import approach, bias, talk_utility
from ptk.sim.mergers.terms import passes, their_answer
from ptk.sim.partnership.common import put
from ptk.sim.partnership.governance import count_vote, open_vote
from ptk.sim.partnership.models import with_partner
from ptk.sim.rng import RngFactory
from ptk.sim.turn import advance_turn
from tests.mergers_support import forced, played, targets

_GAME: dict[int, tuple] = {}  # type: ignore[type-arg]


def _game(data: GameData, balance: Balance, seed: int = 1):  # type: ignore[no-untyped-def]
    if seed not in _GAME:
        _GAME[seed] = played(data, balance, seed, months=4)
    return _GAME[seed]


# --- Acceptance 3: two thirds of each partnership --------------------------------------------


@pytest.mark.parametrize(
    ("yes", "n", "ok"),
    [(7, 9, True), (6, 9, False), (2, 3, False), (3, 3, True), (67, 100, True), (66, 100, False)],
)
def test_a_side_passes_only_with_two_thirds(yes: int, n: int, ok: bool, balance: Balance) -> None:
    assert passes(yes, n, balance.mergers.vote_bp) is ok


def test_the_players_partnership_votes_a_merger_by_two_thirds(
    data: GameData, balance: Balance, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nine equity partners, noise off and the deal's utility at zero: each votes by their
    confidence alone. Seven of nine (the MP and six) pass it; six of nine do not."""
    import ptk.sim.mergers.terms as terms_mod

    monkeypatch.setattr(terms_mod, "our_utility", lambda *a, **k: 0.0)
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[0]
    state, deal = forced(state, firm, Terms(our_share_bp=5000), data, balance, stage="terms")
    quiet = balance.model_copy(
        update={
            "partnership": balance.partnership.model_copy(
                update={"votes": balance.partnership.votes.model_copy(update={"noise_sd": 0.0})}
            )
        }
    )
    fp = state.partnership.of(1)
    assert fp is not None
    template = next(p for p in fp.equity_partners if p.person_id != fp.mp_id)
    for k in range(9 - len(fp.equity_partners)):  # a nine-partner partnership
        fp = with_partner(fp, replace(template, person_id=90_001 + k))
    others = [p for p in fp.equity_partners if p.person_id != fp.mp_id]
    assert len(others) == 8
    for yes_wanted, outcome in ((6, "passed"), (5, "failed"), (8, "passed"), (0, "failed")):
        f2 = fp
        for i, p in enumerate(others):
            f2 = with_partner(f2, replace(p, confidence=90.0 if i < yes_wanted else 10.0))
        s2 = put(state, f2)
        s2, vote = open_vote(
            s2, 1, "merger", None, {"deal_id": deal.id, "threshold_bp": quiet.mergers.vote_bp}
        )
        assert vote.threshold_bp == quiet.mergers.vote_bp
        counted = count_vote(s2, s2.partnership.of(1), vote, RngFactory(1), quiet, data)  # type: ignore[arg-type]
        assert counted.status == outcome, (yes_wanted, counted.yes_weight, counted.no_weight)


def test_the_other_side_reads_its_partners_expected_pep_change(
    data: GameData, balance: Balance
) -> None:
    """Same draws, more of the pool for them: at least as many of their partners vote yes."""
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[1]
    rng = RngFactory(7)
    counts = []
    for share in (2000, 4000, 6000, 8000):
        s2, deal = forced(
            state, firm, Terms(our_share_bp=share, rates="blend"), data, balance, stage="terms"
        )
        counts.append(their_answer(s2, deal, firm, rng, data, balance).yes_bp)
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[-1]


def test_an_elite_lockstep_firm_never_talks(data: GameData, balance: Balance) -> None:
    state, _ = _game(data, balance)
    elite = next(f for f in state.rivals.active if f.personality == "elite_lockstep")
    assert bias(elite, "merger", balance) is None
    ours, theirs = player_side(state, data, balance), rival_side(elite, data)
    assert talk_utility(ours, theirs, elite, "merger", balance) is None
    state2, deal, _ = approach(state, elite, "merger", RngFactory(1), data, balance)
    assert deal.id and state2.mergers.deal(deal.id).stage == "ended"  # type: ignore[union-attr]


def test_talks_are_seeded(data: GameData, balance: Balance) -> None:
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[2]
    a = approach(state, firm, "merger", RngFactory(3), data, balance)
    b = approach(state, firm, "merger", RngFactory(3), data, balance)
    assert a[0].mergers == b[0].mergers


# --- Diligence: ranges hold the truth, the books are exact ------------------------------------


def test_diligence_ranges_hold_the_truth_and_narrow(data: GameData, balance: Balance) -> None:
    state, _ = _game(data, balance)
    rng = RngFactory(state.save_meta.master_seed)
    for firm in targets(state, data, balance)[:6]:
        s = sheet(firm, rng, data, balance)
        h = hidden(rng, firm, balance)
        q = partner_quality(state, firm, data, balance)
        widths = []
        for level in range(len(balance.mergers.diligence.half_width)):
            r = shown_range(q, level, h.offsets[0], balance)
            assert r.lo <= q <= r.hi
            lo, hi = money_range(s.annuities, level, h.offsets[1], balance)
            assert lo <= s.annuities <= hi
            widths.append(r.hi - r.lo)
        assert widths == sorted(widths, reverse=True)


# --- Acceptance 8: hidden values and real people ---------------------------------------------


HIDDEN_WORDS = (
    "annuity_share",
    "lease_years",
    "adverse",
    "noise",
    "bias",
    "reservation",
    "waiver_p",
    "hidden",
)


def test_the_mergers_view_carries_no_hidden_value(data: GameData, balance: Balance) -> None:
    from ptk.api.mergers import MergersOut, mergers_out

    def fields(model: type) -> set[str]:
        out: set[str] = set()
        for name, f in model.model_fields.items():  # type: ignore[attr-defined]
            out.add(name)
            ann = f.annotation
            for arg in getattr(ann, "__args__", (ann,)):
                if isinstance(arg, type) and hasattr(arg, "model_fields"):
                    out |= fields(arg)
        return out

    names = fields(MergersOut)
    assert not [n for n in names if any(w in n for w in HIDDEN_WORDS)]
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[0]
    state, deal = forced(state, firm, Terms(our_share_bp=5000), data, balance, stage="talks")
    rng = RngFactory(state.save_meta.master_seed)
    s = sheet(firm, rng, data, balance)
    text = json.dumps(mergers_out(state, data, balance).model_dump())
    for value in (s.annuities, s.leases, s.capital):  # shown only as ranges, never exactly
        assert str(value) not in text
    r = reveal(state, deal, firm, rng, data, balance)
    assert r.wip_cents is None  # the books only after a level of diligence


def test_no_prompt_reads_the_mergers_state() -> None:
    from pathlib import Path

    events = Path(__file__).resolve().parents[2] / "ptk" / "events"
    for path in events.rglob("*.py"):
        assert "mergers" not in path.read_text(encoding="utf-8"), path


def test_no_real_person_is_named_in_merger_events_or_press(
    data: GameData, balance: Balance
) -> None:
    """A real firm's notables join at closing; no merger log item or press moment names or links
    a person (ADR PT-0013)."""
    state, balances = _game(data, balance)
    real = sorted(
        (
            f
            for f in state.rivals.active
            if f.kind == "real"
            and data.geo.city_key(f.hq) is not None
            and rival_side(f, data).lawyers <= balance.mergers.max_lawyers
            and any(m.notable for m in state.rivals.members_of(f.id))
        ),
        key=lambda f: f.id,
    )
    assert real, "a real firm small enough to integrate, with notables"
    firm = real[0]
    state, deal = forced(state, firm, Terms(our_share_bp=6000), data, balance)
    after, _, logs = closing.close_merger(state, deal, RngFactory(1), data, balance)
    reals = {p.id for p in after.people if p.real}
    assert reals  # the notables joined
    names = {f"{p.first_name} {p.last_name}" for p in after.people if p.real}
    for item in logs:
        assert item.link_kind != "person"
        assert not any(str(v) in names for _, v in item.params)
    r = advance_turn(
        after, Decisions(), RngFactory(1), balance, data, balances, answer_critical=True
    )
    for m in r.new_state.standing.press.moments:
        if m.trigger == "merger":
            assert m.person_id is None


# --- The exit ---------------------------------------------------------------------------------


def test_being_absorbed_ends_the_campaign_scored(data: GameData, balance: Balance) -> None:
    state, balances = _game(data, balance)
    firm = targets(state, data, balance)[-1]
    state, deal = forced(
        state, firm, Terms(our_share_bp=1500, name="theirs", mp="theirs"), data, balance
    )
    assert deal.absorbed
    after, logs = exits.absorb(state, deal, data, balance)
    assert after.save_meta.game_state == "exit" and after.ended
    score = after.mergers.exit
    assert score is not None and score.firm_name == firm.name and score.rank >= 1
    assert any(i.template == "merger_exit" for i in logs)
    with pytest.raises(GameOverError):
        advance_turn(after, Decisions(), RngFactory(1), balance, data, balances)


def test_their_name_and_mp_or_a_sliver_of_the_pool_is_an_absorption(
    data: GameData, balance: Balance
) -> None:
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[0]
    state, deal = forced(state, firm, Terms(our_share_bp=5000), data, balance, stage="talks")
    mp = state.founder_of(1)
    assert mp is not None
    out = apply_merger_action(
        state,
        PutTerms(actor_id=mp, deal_id=deal.id, our_share_bp=2000, name="theirs", mp="theirs"),
        RngFactory(1),
        balance,
        data,
    )
    assert out.state.mergers.deal(deal.id).absorbed  # type: ignore[union-attr]
    for share, name, absorbed in ((2000, "combined", False), (700, "ours", True)):
        out = apply_merger_action(
            state,
            PutTerms(actor_id=mp, deal_id=deal.id, our_share_bp=share, name=name),  # type: ignore[arg-type]
            RngFactory(1),
            balance,
            data,
        )
        assert out.state.mergers.deal(deal.id).absorbed is absorbed  # type: ignore[union-attr]
    with pytest.raises(InvalidActionError):
        apply_merger_action(
            state,
            PutTerms(actor_id=mp, deal_id=deal.id, our_share_bp=100),
            RngFactory(1),
            balance,
            data,
        )


def test_only_the_managing_partner_approaches(data: GameData, balance: Balance) -> None:
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[0]
    other = next(
        p.person_id
        for p in state.partnership.of(1).equity_partners
        if p.person_id != state.founder_of(1)
    )  # type: ignore[union-attr]
    with pytest.raises(NotManagingPartnerError):
        apply_merger_action(
            state, ApproachFirm(actor_id=other, rival_key=firm.key), RngFactory(1), balance, data
        )


# --- Integration, rivals, the verein -------------------------------------------------------


def test_integration_raises_the_other_sides_flight(data: GameData, balance: Balance) -> None:
    state, _ = _game(data, balance)
    firm = targets(state, data, balance)[0]
    state, deal = forced(state, firm, Terms(our_share_bp=5000, rates="higher"), data, balance)
    after, _, _ = closing.close_merger(state, deal, RngFactory(1), data, balance)
    integ = after.mergers.integration(deal.id)
    assert integ is not None and integ.their_partners
    mult = integration.flight_multiplier(after, integ.their_partners[0], balance, data)
    assert mult >= 1.0 + balance.mergers.integration.flight_mult * integ.clash - 1e-9
    later = replace(after, turn=integ.until_turn + 1)
    assert integration.flight_multiplier(later, integ.their_partners[0], balance, data) == 1.0


def test_rivals_merge_freely_only_after_2025(data: GameData, balance: Balance) -> None:
    from ptk.sim.calendar import ym_to_turn
    from ptk.sim.rivals.mergers import free_play

    state, _ = _game(data, balance)
    eager = balance.model_copy(
        update={
            "mergers": balance.mergers.model_copy(
                update={"rival": balance.mergers.rival.model_copy(update={"free_rate_bp": 10_000})}
            )
        }
    )
    start = state.save_meta.start_ym
    before = replace(state, turn=ym_to_turn(2025, 10, start))
    same, moves = free_play(before, RngFactory(1), eager)
    assert same is before and not moves
    after = replace(state, turn=ym_to_turn(2026, 1, start))
    merged, moves = free_play(after, RngFactory(1), eager)
    assert len(moves) == 1
    gone = [f for f in merged.rivals.firms if f.status == "merged" and f.ended_turn == after.turn]
    assert len(gone) == 1


def test_a_london_member_opens_london(data: GameData, balance: Balance) -> None:
    from ptk.sim.matters.intake import local_terms
    from ptk.sim.mergers.verein import join

    state, _ = _game(data, balance)
    london = next(
        f
        for f in state.rivals.active
        if data.geo.city_key(f.hq) == "london" and bias(f, "verein", balance) is not None
    )
    state, deal = forced(state, london, Terms(our_share_bp=5000), data, balance, form="verein")
    after, _ = join(state, deal, RngFactory(1), data, balance)
    assert after.mergers.member_keys() == {london.key}
    assert any(c.city == "london" for c in after.market.clients)
    reach = local_terms(after, 1, data, balance)("london")[1]
    assert reach <= 0 < balance.geo.reach_penalty
