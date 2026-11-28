"""PT-M13's invariants (docs/tasks/PT-M13-mergers-and-the-verein.md, acceptance 1, 2 and 4).

- At closing the merged firm's balance sheet equals the two firms' sheets combined less ADR
  PT-0016's eliminations (the surrendered home-city lease), every sub-ledger matches its
  account, and the client book is combined exactly; every entry balances.
- After clearance no open matter of the merged firm is adverse to one of its clients without a
  waiver, even when the book and the firm's matters are built to collide.
- In a verein no entry carries two member firms, and each member's profit, its PEP's numerator,
  moves only by its own share of the shared costs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ptk.sim.billing.kpis import receivables_cents, wip_cents
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import (
    ANNUITIES,
    CASH,
    LEASES,
    PARTNERS_CAPITAL,
    RECEIVABLES,
    REVOLVER,
    RIGHT_OF_USE,
    WIP,
    apply_entries,
)
from ptk.sim.matters.conflicts import conflict_index
from ptk.sim.mergers import closing
from ptk.sim.mergers.books import sheet
from ptk.sim.mergers.clearance import clear, kept_book
from ptk.sim.mergers.models import Terms, Verein, with_deal, with_verein
from ptk.sim.mergers.profile import annualised
from ptk.sim.mergers.talks import put_mergers
from ptk.sim.mergers.verein import costs
from ptk.sim.streams import RngFactory
from tests.mergers_support import forced, played, targets

PROPERTY = settings(
    max_examples=6, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
SHEET_ACCOUNTS = (
    CASH,
    WIP,
    RECEIVABLES,
    RIGHT_OF_USE,
    LEASES,
    ANNUITIES,
    REVOLVER,
    PARTNERS_CAPITAL,
)
_GAMES: dict[int, tuple] = {}  # type: ignore[type-arg]


def _game(data: GameData, balance: Balance, seed: int):  # type: ignore[no-untyped-def]
    if seed not in _GAMES:
        _GAMES[seed] = played(data, balance, seed, months=4)
    return _GAMES[seed]


@PROPERTY
@given(
    seed=st.integers(1, 3),
    pick=st.integers(0, 5),
    share=st.integers(3000, 7000),
    rates=st.sampled_from(["ours", "theirs", "higher", "blend"]),
)
def test_closing_combines_the_books_exactly(
    data: GameData, balance: Balance, seed: int, pick: int, share: int, rates: str
) -> None:
    state, balances = _game(data, balance, seed)
    firm = targets(state, data, balance)[pick]
    state, deal = forced(state, firm, Terms(our_share_bp=share, rates=rates), data, balance)  # type: ignore[arg-type]
    rng = RngFactory(seed)
    before = {a: balances.get((1, a), 0) for a in SHEET_ACCOUNTS}
    s = sheet(firm, rng, data, balance)
    assert s.assets == s.claims  # the other firm's sheet balances by construction
    ours_before = {r.client_id for r in state.market.relationships if r.firm_id == 1}
    after_state, entries, _ = closing.close_merger(state, deal, rng, data, balance)
    for e in entries:
        assert len(e.lines) >= 2 and sum(ln.amount for ln in e.lines) == 0
        assert e.firm_id == 1 and all(type(ln.amount) is int for ln in e.lines)
    after = dict(apply_entries(balances, entries))
    # merged = ours + theirs - eliminations (the home-city lease leaves with its asset; its
    # surrender is paid from cash as an integration cost)
    closed = after_state.mergers.deal(deal.id)
    assert closed is not None and closed.stage == "closed"
    surrender = after_state.mergers.integration(deal.id).surrender_cents  # type: ignore[union-attr]
    carried_lease = surrender == 0
    expected = {
        CASH: before[CASH] + s.cash - surrender,
        WIP: before[WIP] + s.wip,
        RECEIVABLES: before[RECEIVABLES] + s.receivables,
        RIGHT_OF_USE: before[RIGHT_OF_USE] + (s.right_of_use if carried_lease else 0),
        LEASES: before[LEASES] - (s.leases if carried_lease else 0),
        ANNUITIES: before[ANNUITIES] - s.annuities,
        REVOLVER: before[REVOLVER] - s.revolver,
        PARTNERS_CAPITAL: before[PARTNERS_CAPITAL] - s.capital,
    }
    for account, value in expected.items():
        assert after.get((1, account), 0) == value, account
    # every sub-ledger is its account
    assert after.get((1, WIP), 0) == wip_cents(after_state.billing, 1)
    assert after.get((1, RECEIVABLES), 0) == receivables_cents(after_state.billing, 1)
    fp = after_state.partnership.of(1)
    assert fp is not None
    capital = sum(p.capital_cents for p in fp.partners) + sum(
        r.remaining_capital_cents for r in fp.capital_returns
    )
    assert -after[(1, PARTNERS_CAPITAL)] == capital
    owed = sum(a.remaining_cents for a in after_state.founder_life.annuities)
    assert -after.get((1, ANNUITIES), 0) == owed
    # the client book is combined exactly: one relationship per client, ours and the kept book
    rels = [r.client_id for r in after_state.market.relationships if r.firm_id == 1]
    assert len(rels) == len(set(rels))
    dropped_ours = {c.our_client_id for c in closed.conflicts if c.outcome == "kept_theirs"}
    assert set(rels) == (ours_before - dropped_ours) | {b.client_id for b in kept_book(closed)}
    # the other firm is gone and no panel carries its key
    gone = after_state.rivals.firm(firm.id)
    assert gone is not None and gone.status == "merged"
    assert all(firm.key not in c.panel for c in after_state.market.clients)


@PROPERTY
@given(
    seed=st.integers(1, 3),
    pick=st.integers(0, 5),
    collide=st.integers(1, 6),
    u=st.integers(0, 10_000),
)
def test_after_clearance_no_matter_is_adverse_to_a_client(
    data: GameData, balance: Balance, seed: int, pick: int, collide: int, u: int
) -> None:
    state, _ = _game(data, balance, seed)
    firm = targets(state, data, balance)[pick]
    state, deal = forced(state, firm, Terms(our_share_bp=5000), data, balance)
    ours = sorted(r.client_id for r in state.market.relationships if r.firm_id == 1)
    book = list(deal.book)
    # build collisions: book engagements against our clients, our matters against book clients
    for i in range(min(collide, len(book), len(ours))):
        book[i] = replace(book[i], adverse_client_id=ours[(i + u) % len(ours)])
    market = state.market
    open_ = [m for m in market.open_matters(1)]
    for i, m in enumerate(open_[:collide]):
        target = book[(i + u) % len(book)].client_id
        if target != m.client_id:
            market = replace(
                market,
                matters=tuple(
                    replace(x, adverse_client_id=target) if x.id == m.id else x
                    for x in market.matters
                ),
            )
    deal = replace(deal, book=tuple(book))
    state = put_mergers(replace(state, market=market), with_deal(state.mergers, deal))
    rng = RngFactory(seed + u)
    after, _, _ = closing.close_merger(state, deal, rng, data, balance)
    index = conflict_index(after.market, 1, after.turn, balance)
    for m in after.market.open_matters(1):
        if m.adverse_client_id is not None and m.adverse_client_id in index.current:
            assert m.waiver or m.adverse_client_id in index.advance_waivers, m.id
    # and the clearance step alone resolves every conflict it finds
    _, cleared, _ = clear(state, deal, rng, balance)
    assert len(cleared.conflicts) >= 1 or not open_


@PROPERTY
@given(
    seed=st.integers(1, 3),
    members=st.integers(1, 3),
    player_revenue=st.integers(0, 50_000_000_000),
)
def test_a_verein_keeps_every_book_apart(
    data: GameData, balance: Balance, seed: int, members: int, player_revenue: int
) -> None:
    state, _ = _game(data, balance, seed)
    london = [f for f in state.rivals.active if data.geo.city_key(f.hq) == "london"][:members]
    v = Verein(
        id=1,
        name="Founders Verein",
        formed_turn=state.turn,
        members=tuple(sorted((f.key, 0) for f in london)),
    )
    state = put_mergers(state, with_verein(state.mergers, v))
    profit_before = {f.id: f.profit for f in london}
    after, entries = costs(state, player_revenue, balance)
    ids = {1, *(f.id for f in london)}
    paid: Counter[int] = Counter()
    for e in entries:
        assert e.firm_id in ids  # one entry, one member firm
        assert sum(ln.amount for ln in e.lines) == 0
        paid[e.firm_id] += next(ln.amount for ln in e.lines if ln.amount > 0)
    for f in london:  # each member's profit pool moves by its own share only
        now = after.rivals.firm(f.id)
        assert now is not None
        assert sum(profit_before[f.id]) - sum(now.profit) == paid[f.id]
    # the shares sum to the verein's cost, split by revenue
    revenues = [player_revenue // 12] + [annualised(f.revenue) // 12 for f in london]
    total = sum(revenues)
    if total > 0:
        cfg = balance.mergers.verein
        assert sum(paid.values()) == cfg.cost_base_cents + total * cfg.cost_bp // 10_000
