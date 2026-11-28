"""Practice saves (PT-M7): ready-made positions to learn on. `pt-2008` is a 60-lawyer firm in
June 2008, three months before Lehman, with a corporate associate who is a partnership
candidate in December 2008 (the brief's manual check: get the firm through the crash).
`pt-2022` (PT-M14) is a 120-lawyer firm (stage 3) in December 2022, a month after ChatGPT:
decide the firm's AI strategy. `pt-risk` (PT-M15) is `pt-2008` with a malpractice claim whose
claimant has just offered to settle, a second claim about to surface, and a client-account
shortfall found at the month's reconciliation (its critical event arrives next month).

Built, not hand-written: the biglaw spin-out plays from January 2005 to June 2008 over the pure
sim (critical events take their first choice, events written with the mock adapter), so the
macro history, the rivals and the market are 2008's; then the firm grows at once to about 60
lawyers: lateral equity partners through PT-M4's arrival hook with their clients, income
partners and associates at their levels, panels worth the firm's capacity and the partners'
capital. Deterministic: the same data give the same save. Outside the sim (it writes a file).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final

import numpy as np
from simcore.kernel.calendar import ym_to_turn
from simcore_llm.offline import MockLLMAdapter
from simcore_llm.settings import LLMSettings

from ptk.db import core
from ptk.db.billing_io import write_client_book
from ptk.db.core import make_sessionmaker, shared_engine
from ptk.db.saves import save_path
from ptk.db.state_io import insert_new, write_billing
from ptk.events.service import Writer, write_pending_events
from ptk.sim.billing.models import ClientBookEntry
from ptk.sim.data_models import Balance, GameData
from ptk.sim.decisions import Decisions
from ptk.sim.errors import SaveExistsError
from ptk.sim.hiring.models import PersonState
from ptk.sim.hiring.pay import firm_pay_cents
from ptk.sim.interfaces import LateralArrival, partner_flight
from ptk.sim.ledger import CASH, PARTNERS_CAPITAL, LedgerEntry, apply_entries
from ptk.sim.matters.intake import with_relationship
from ptk.sim.matters.models import Relationship
from ptk.sim.people.generator import generate_person, people_gen_stream
from ptk.sim.people.models import AttrSet, Employment
from ptk.sim.people.reveal import new_reveal_state
from ptk.sim.setup import new_game
from ptk.sim.state import GameState, with_people, with_person_states, with_reveals
from ptk.sim.streams import RngFactory
from ptk.sim.turn import advance_turn

MAX_CLIENT_FEES_CENTS: Final = 400_000_000  # tunable-exempt: no one client above $4M a year
PRACTICE_SEARCH: Final = 950  # people_gen search id for practice saves' staff (no real search)
CANDIDATE_PRACTICE: Final = "corporate_ma"
# The grown firm by practice: (practice, lateral equity partners, income partners, associates)
GROWTH: Final = (
    (
        "corporate_ma",
        3,
        2,
        (
            "associate_1",
            "associate_1",
            "associate_2",
            "associate_2",
            "associate_3",
            "associate_4",
            "associate_5",
            "associate_6",
            "associate_7",
        ),
    ),
    (
        "private_equity",
        2,
        1,
        ("associate_1", "associate_2", "associate_3", "associate_4", "associate_6"),
    ),
    (
        "banking_finance",
        1,
        1,
        ("associate_1", "associate_2", "associate_2", "associate_3", "associate_5"),
    ),
    ("capital_markets", 1, 0, ("associate_1", "associate_4")),
    (
        "commercial_litigation",
        2,
        2,
        (
            "associate_1",
            "associate_1",
            "associate_2",
            "associate_3",
            "associate_4",
            "associate_5",
            "associate_6",
        ),
    ),
    ("restructuring", 1, 0, ("associate_2", "associate_3", "associate_4")),
    ("real_estate", 1, 1, ("associate_1", "associate_1", "associate_3", "associate_5")),
    ("white_collar", 1, 0, ("associate_2", "associate_3")),
)


@dataclass(frozen=True, slots=True)
class PracticeSave:
    key: str
    label: str
    seed: int
    scenario: str
    until_ym: tuple[int, int]
    capital_cents: int  # partners' capital paid in at the jump
    lateral_comp_cents: int
    lateral_book_cents: int
    fees_per_lawyer_cents: int  # the panels the firm is given, a year per lawyer at standard
    copies: int = 1  # PT-M14: the GROWTH table hired this many times (pt-2022: stage 3)
    risk_demo: bool = False  # PT-M15: stage a claim, a second on its way and a shortfall


PRACTICE_SAVES: Final = {
    "pt-2008": PracticeSave(
        key="pt-2008",
        label="June 2008: a 60-lawyer firm before the crash",
        seed=2008,
        scenario="biglaw_spinout",
        until_ym=(2008, 6),
        capital_cents=1_500_000_000,  # tunable-exempt: the practice save's own setting, $15M
        lateral_comp_cents=150_000_000,  # tunable-exempt: $1.5M
        lateral_book_cents=250_000_000,  # tunable-exempt: $2.5M
        fees_per_lawyer_cents=80_000_000,  # tunable-exempt: $800k
    ),
    # PT-M15 (the e2e): a claim to settle under the policy and a client-account shortfall
    "pt-risk": PracticeSave(
        key="pt-risk",
        label="June 2008: a malpractice claim on the desk and a client-account shortfall",
        seed=2008,
        scenario="biglaw_spinout",
        until_ym=(2008, 6),
        capital_cents=1_500_000_000,  # tunable-exempt: as pt-2008
        lateral_comp_cents=150_000_000,  # tunable-exempt: as pt-2008
        lateral_book_cents=250_000_000,  # tunable-exempt: as pt-2008
        fees_per_lawyer_cents=80_000_000,  # tunable-exempt: as pt-2008
        risk_demo=True,
    ),
    # PT-M14 (the brief's manual check): decide the firm's AI strategy a month after ChatGPT
    "pt-2022": PracticeSave(
        key="pt-2022",
        label="December 2022: a 120-lawyer firm as generative AI arrives",
        seed=2022,
        scenario="biglaw_spinout",
        until_ym=(2022, 12),
        capital_cents=3_000_000_000,  # tunable-exempt: the practice save's own setting, $30M
        lateral_comp_cents=250_000_000,  # tunable-exempt: $2.5M
        lateral_book_cents=400_000_000,  # tunable-exempt: $4M
        fees_per_lawyer_cents=110_000_000,  # tunable-exempt: $1.1M
        copies=2,
    ),
}


def build(
    spec: PracticeSave, data: GameData, balance: Balance
) -> tuple[GameState, list[LedgerEntry]]:
    """The practice position in memory: its state and every ledger entry since January 2005."""
    made = new_game(
        name=spec.key,
        firm_name="Practice & Partners LLP",
        master_seed=spec.seed,
        scenario_id=spec.scenario,
        difficulty="standard",
        data=data,
        balance=balance,
    )
    state, entries = made.state, list(made.ledger_entries)
    balances = dict(apply_entries({}, entries))
    rng = RngFactory(spec.seed)
    writer = Writer(MockLLMAdapter(), LLMSettings(), lambda: 1_000_000.0)
    until = ym_to_turn(*spec.until_ym, state.save_meta.start_ym)
    while state.turn < until and not state.ended:
        result = advance_turn(
            state, Decisions(), rng, balance, data, balances, answer_critical=True
        )
        entries += result.ledger_entries
        balances = dict(apply_entries(balances, result.ledger_entries))
        state = write_pending_events(
            result.new_state, balances.get((state.player.id, CASH), 0), writer, balance, data
        )
    state, more = _grow(state, spec, rng, data, balance, balances)
    entries += more
    return _at_stage(state, data, balance), entries


def _at_stage(state: GameState, data: GameData, balance: Balance) -> GameState:
    """PT-M8: the grown firm opens at the stage its lawyers give (spec 3), as phase 10 would
    set it at the month's end, so the seats of its stage can be filled at once."""
    from ptk.sim.org.rules import lawyer_count
    from ptk.sim.partnership.formulas import stage_for
    from ptk.sim.state import with_firm

    firm = state.player
    stage = max(
        firm.stage, stage_for(lawyer_count(state, firm.id, data), balance.partnership.stages)
    )
    return with_firm(state, replace(firm, stage=stage))


def _grow(
    state: GameState,
    spec: PracticeSave,
    rng: RngFactory,
    data: GameData,
    balance: Balance,
    balances: dict[tuple[int, str], int],
) -> tuple[GameState, list[LedgerEntry]]:
    firm = state.player
    entries = [
        LedgerEntry.transfer(
            turn=state.turn,
            firm_id=firm.id,
            memo="Partners' capital (practice save)",
            debit=CASH,
            credit=PARTNERS_CAPITAL,
            amount=spec.capital_cents,
        )
    ]
    balances = dict(apply_entries(balances, entries))
    n = 0

    def person(practice: str, level: str):
        nonlocal n
        n += 1
        pid = max(p.id for p in state.people) + 1
        return generate_person(
            people_gen_stream(rng, state.turn, PRACTICE_SEARCH, n),
            data,
            balance,
            state.turn,
            data.practice_role(practice),
            level,
            person_id=pid,
            city=firm.home_city,
            jurisdiction="us_ny",
        )

    def observe(st: GameState, p) -> GameState:
        reveal = new_reveal_state(
            observer_firm_id=firm.id, person=p, turn=st.turn, rng=rng, data=data, balance=balance
        )
        return with_reveals(st, [reveal])

    partners: list[tuple[int, str]] = []
    for practice, equity, income, associates in GROWTH * spec.copies:
        for _ in range(equity):
            p = replace(person(practice, "equity_partner"), book_cents=spec.lateral_book_cents)
            state = observe(with_people(state, [p]), p)
            res = partner_flight().arrive(
                state,
                LateralArrival(p.id, firm.id, None, spec.lateral_comp_cents, 0),
                draws=_draws(rng, state.turn, p.id),
                balance=balance,
                data=data,
                balances=balances,
            )
            state = res.state
            entries += res.entries
            balances = dict(apply_entries(balances, res.entries))
            partners.append((p.id, practice))
        for level in ("income_partner",) * income + associates:
            p = person(practice, level)
            if practice == CANDIDATE_PRACTICE and level == "associate_7":
                # the December 2008 candidate: a strong seventh-year, eighth from September
                p = replace(p, skills=AttrSet(tuple((k, max(v, 13.0)) for k, v in p.skills.items)))
            state = observe(with_people(state, [p]), p)
            salary = firm_pay_cents(
                data, balance, level, spec.until_ym, firm.home_city, firm.pay_policy
            )
            employment = Employment(
                id=state.next_id("employment"),
                person_id=p.id,
                firm_id=firm.id,
                start_turn=state.turn,
                salary_cents=salary,
            )
            state = replace(state, employments=(*state.employments, employment))
            state = with_person_states(
                state, [PersonState(person_id=p.id, morale=balance.morale.start)]
            )
            if level == "income_partner":
                partners.append((p.id, practice))
    return _panels(state, partners, spec, data, balance), entries


def _draws(rng: RngFactory, turn: int, person_id: int) -> Callable[[], np.random.Generator]:
    return lambda: rng.stream(turn, "misc", person_id)


def _panels(
    state: GameState,
    partners: list[tuple[int, str]],
    spec: PracticeSave,
    data: GameData,
    balance: Balance,
) -> GameState:
    """Clients for the grown firm, largest first, each in a partner's practice, until the
    clients' wallets in those practices reach the firm's capacity (a rough panel size)."""
    from ptk.sim.matters.market import base_monthly_demand, firm_reputation, player_share, wallets

    firm = state.player.id
    lawyers = sum(
        1 for e in state.staff(firm) if data.role(state.person(e.person_id).role).kind == "lawyer"
    )
    target = lawyers * spec.fees_per_lawyer_cents
    shares = wallets(state.market.clients, data, balance, state.turn, state.save_meta.start_ym)
    demand = base_monthly_demand(data)
    keys = data.practice_keys
    have = {r.client_id for r in state.market.relationships if r.firm_id == firm}
    reps = {p: firm_reputation(state, firm, p, balance) for p in keys}
    appeals = dict(state.rivals.appeals) or None

    def expected(rel: Relationship) -> float:
        client = state.market.client(rel.client_id)
        return sum(
            shares.wallet(rel.client_id, keys.index(p), demand)
            * 12
            * player_share(client, rel, p, reps[p], False, data, balance, appeals)
            for p in rel.practices
        )

    total = sum(expected(r) for r in state.market.relationships if r.firm_id == firm)
    market = state.market
    i = 0
    for client in sorted(market.clients, key=lambda c: (-c.revenue_bn, c.id)):
        if total >= target or not partners:
            break
        if client.id in have or (client.real and _failing(client.name, data)):
            continue
        pid, practice = partners[i % len(partners)]
        rel = Relationship(
            client_id=client.id,
            firm_id=firm,
            score=55.0,
            partner_id=pid,
            practices=(practice,),
            since_turn=state.turn,
            last_instructed_turn=state.turn,
        )
        fees = expected(rel)
        if not 0 < fees <= MAX_CLIENT_FEES_CENTS:
            continue
        market = with_relationship(market, rel)
        total += fees
        i += 1
    return replace(state, market=market)


def _failing(name: str, data: GameData) -> bool:
    """History's failing clients are left out of the practice panels (the save is for learning
    the crash, not for losing its first clients to it)."""
    return any(c.name == name and c.fails is not None for c in data.clients.real_clients)


# PT-M12: a practice position is built once per process and data (deterministic, and the
# state is immutable): later saves and copies (`slug`) start from it instead of replaying
# from January 2005 (pt-2022 replays 216 months)
_BUILT: dict[tuple[str, int, int], tuple[GameState, tuple[LedgerEntry, ...]]] = {}


def _built(
    spec: PracticeSave, data: GameData, balance: Balance
) -> tuple[GameState, list[LedgerEntry]]:
    key = (spec.key, id(data), id(balance))
    if key not in _BUILT:
        made, made_entries = build(spec, data, balance)
        _BUILT[key] = (made, tuple(made_entries))
    state, entries = _BUILT[key]
    return state, list(entries)


def create_practice_save(
    save_dir: Path, key: str, data: GameData, balance: Balance, slug: str | None = None
) -> Path:
    """Write the practice save `key` as a new save (refused if the slug exists)."""
    spec = PRACTICE_SAVES[key]
    path = save_path(save_dir, slug or spec.key)
    if path.exists():
        raise SaveExistsError(f"a save named {slug or spec.key!r} already exists")
    state, entries = _built(spec, data, balance)
    book: tuple[ClientBookEntry, ...] = ()
    if spec.risk_demo:
        state, more, book = risk_demo(state, spec, data, balance, entries)
        entries += more
    meta = replace(state.save_meta, name=slug or spec.key)
    state = replace(state, save_meta=meta)
    save_dir.mkdir(parents=True, exist_ok=True)
    core.upgrade_new(path)
    sessions = make_sessionmaker(shared_engine(path))
    with sessions() as session, session.begin():
        insert_new(session, state, tuple(entries))
        write_billing(session, state.billing)
        write_client_book(session, book)  # PT-M15: the demo's money on account and shortfall
    return path


def risk_demo(
    state: GameState,
    spec: PracticeSave,
    data: GameData,
    balance: Balance,
    entries: list[LedgerEntry],
) -> tuple[GameState, list[LedgerEntry], tuple[ClientBookEntry, ...]]:
    """PT-M15's demo, staged through the engine with the chances forced (the rules, not the
    luck, are what the save shows): $500k on account for the firm's largest client; two
    escaped errors on two clients' open matters become claims, the first walked from notice to the
    claimant's offer, the second surfacing next month; the month's reconciliation finds a
    posting error (made good from firm cash; the critical event is queued for next month)."""
    from ptk.sim.billing.books import ClientBook
    from ptk.sim.billing.models import ClientFunds
    from ptk.sim.risk import claims as cl
    from ptk.sim.risk import insurance, trust
    from ptk.sim.risk.common import Books
    from ptk.sim.risk.config import Span
    from ptk.sim.risk.models import with_claim

    rng = RngFactory(spec.seed)
    firm = state.player.id
    balances = dict(apply_entries({}, entries))
    books = Books(firm, state.turn, balances.get((firm, CASH), 0))
    state = insurance.insurance_month(state, firm, books, balance, data)
    picked: dict[int, int] = {}  # client -> matter: two matters of two clients
    for m in state.market.open_matters(firm):
        if m.team and m.lead_id is not None and m.client_id not in picked and len(picked) < 2:
            picked[m.client_id] = m.id
    chosen = set(picked.values())
    after = replace(
        state,
        market=replace(
            state.market,
            matters=tuple(
                replace(m, errors_escaped=m.errors_escaped + 1) if m.id in chosen else m
                for m in state.market.matters
            ),
        ),
    )
    r = balance.risk
    zero = Span(lo=0, hi=0)
    c = r.claims.model_copy(
        update={
            "from_error_bp": 10_000,
            "delay_months": zero,
            "drop_bp": 0,
            "offer_bp": 10_000,
            "stages": r.claims.stages.model_copy(
                update={"notice": zero, "investigation": zero, "defence": Span(lo=6, hi=6)}
            ),
        }
    )
    forced = balance.model_copy(update={"risk": r.model_copy(update={"claims": c})})
    state = cl.make_claims(state, after, rng, forced, data)
    mine = [x for x in state.risk.claims if x.firm_id == firm]
    first, second = mine[-2], mine[-1]
    state = replace(state, risk=with_claim(state.risk, replace(second, surfaces_turn=state.turn)))
    claim = first
    for _ in range(6):  # notice, investigation, defence, the offer: one stage a step
        state, claim = cl.claim_month(state, claim, rng, books, forced, data)
        state = replace(state, risk=with_claim(state.risk, claim))
        if claim.stage == "offer":
            break
    client = max(
        (x for x in state.market.relationships if x.firm_id == firm),
        key=lambda x: (x.score, -x.client_id),
    ).client_id
    deposit = ClientBook(state.turn, firm)
    deposit.receive("Money on account", client, 50_000_000)
    funds = (
        *state.billing.funds,
        ClientFunds(client_id=client, firm_id=firm, owed_cents=50_000_000),
    )
    state = replace(state, billing=replace(state.billing, funds=funds))
    t = r.trust.model_copy(update={"error_bp": 10_000})
    shortfall = balance.model_copy(update={"risk": r.model_copy(update={"trust": t})})
    state, made_good, _ = trust.reconcile(state, rng, books, shortfall, data)
    return state, list(books.entries), (*deposit.entries(), *made_good)
