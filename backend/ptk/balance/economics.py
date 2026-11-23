"""PT-M7c: a firm's economics at December of a year, decomposed into the PEP identity's terms
(spec 8.1: PEP = RPL x margin x leverage) and the growth terms (hires, attrition, admissions,
demand won against demand available), for `tools/firm_economics.py`.

Read-only over a balance run: it plays the strategy as `report.play` does and reads the game
between turns (the ledger's cumulative balances, the staff list, the market's demand). It never
changes what the run does.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import median
from typing import Final

from ptk.balance.game import PLAYER, Game, is_associate, start_game
from ptk.balance.report import SCENARIO, _loaded
from ptk.balance.seats import fill_seats
from ptk.balance.strategies import PLAYABLE
from ptk.sim.billing.kpis import trailing
from ptk.sim.calendar import turn_to_ym
from ptk.sim.partnership.kpis import explain

YEAR: Final = 2015
DECEMBER: Final = 12
# Cost groups of the expense accounts (accounts.yaml)
LAWYER_PAY: Final = ("5000_associate_salaries", "5010_bonuses", "5020_income_partner_salaries")
STAFF_PAY: Final = ("5100_staff_salaries",)
BENEFITS: Final = ("5200_benefits",)
RENT: Final = ("6000_rent",)
PARTNERS: Final = ("equity_partner", "income_partner")


@dataclass(slots=True)
class Decomposition:
    strategy: str
    seed: int
    dissolved: bool = False
    lawyers: int = 0
    equity_partners: int = 0
    income_partners: int = 0
    associates: int = 0
    revenue_cents: int = 0  # the year's fees (trailing 12 months at December)
    profit_cents: int = 0
    pep_cents: int | None = None
    rpl_cents: int | None = None
    margin: float | None = None
    leverage: float | None = None  # lawyers per equity partner (averages, spec 8.1)
    hours: float | None = None  # billable hours per lawyer
    rate_cents: int | None = None  # standard value per billable hour
    realisation: float | None = None
    collection: float | None = None
    costs: dict[str, int] = field(default_factory=dict)  # the year's expense by group
    hires: dict[int, int] = field(default_factory=dict)  # year -> lawyers who joined
    leavers: dict[int, int] = field(default_factory=dict)  # year -> lawyers who left
    admissions: dict[int, int] = field(default_factory=dict)  # year -> made equity partner
    won_share: float | None = None  # the year's worked value over the market's demand
    held_share: float | None = None  # ... over the demand in the practices the firm holds
    unserved: float | None = None  # the year's flow the firm could not staff, of its flow


def _group(account: str) -> str:
    if account in LAWYER_PAY:
        return "lawyer_pay"
    if account in STAFF_PAY:
        return "staff_pay"
    if account in BENEFITS:
        return "benefits"
    if account in RENT:
        return "rent"
    return "other"


def decompose(strategy: str, seed: int, year: int = YEAR, data_dir: str = "data") -> Decomposition:
    data, balance = _loaded(data_dir)
    game = start_game(data, balance, seed, SCENARIO, "standard")
    script = PLAYABLE[strategy]
    out = Decomposition(strategy, seed)
    types = {a.code: a.type for a in data.accounts}
    practices = data.practice_keys
    start_balances: dict[str, int] = {}
    staff_before = {p.id: p.level for p in game.lawyers()}
    worked = market = held_market = 0
    turns = (year - game.ym[0] + 1) * 12
    for _ in range(turns):
        if game.state.ended:
            out.dissolved = True
            break
        fill_seats(game)
        script(game)
        game.turn()
        y, m = turn_to_ym(game.state.turn - 1, game.state.save_meta.start_ym)
        if (y, m) == (year - 1, DECEMBER):
            start_balances = _expenses(game, types)
        now = {p.id: p.level for p in game.lawyers()}
        joined = [pid for pid in now if pid not in staff_before]
        left = [pid for pid in staff_before if pid not in now]
        admitted = [
            pid
            for pid, level in now.items()
            if level == "equity_partner" and staff_before.get(pid, "equity_partner") != level
        ]
        out.hires[y] = out.hires.get(y, 0) + len(joined)
        out.leavers[y] = out.leavers.get(y, 0) + len(left)
        out.admissions[y] = out.admissions.get(y, 0) + len(admitted)
        staff_before = now
        if y == year:
            demand = game.state.market.demand_cents
            month = next(
                (
                    t
                    for t in trailing(game.state.billing, PLAYER, game.state.turn)
                    if t.turn == game.state.turn - 1
                ),
                None,
            )
            held = _held(game)
            worked += month.worked_cents if month else 0
            market += sum(demand)
            held_market += sum(d for k, d in zip(practices, demand, strict=True) if k in held)
    if game.state.ended:
        out.dissolved = True
    end = _expenses(game, types)
    out.costs = dict(Counter(end) - Counter(start_balances)) if start_balances else end
    staff = game.lawyers()
    out.lawyers = len(staff)
    out.equity_partners = sum(1 for p in staff if p.level == "equity_partner")
    out.income_partners = sum(1 for p in staff if p.level == "income_partner")
    out.associates = sum(1 for p in staff if is_associate(p.level))
    fp = game.state.partnership.of(PLAYER)
    if fp is not None:
        e = explain(game.state, fp)
        out.revenue_cents, out.profit_cents = e.revenue_cents, e.profit_cents
        out.pep_cents, out.rpl_cents = e.pep_cents, e.rpl_cents
        out.margin = None if e.margin_bp is None else e.margin_bp / 10_000
        out.leverage = e.leverage
        out.hours = e.hours_per_lawyer
        out.rate_cents = e.average_rate_cents
        out.realisation = None if e.realisation_bp is None else e.realisation_bp / 10_000
        out.collection = None if e.collection_bp is None else e.collection_bp / 10_000
    out.won_share = worked / market if market else None
    out.held_share = worked / held_market if held_market else None
    return out


def _held(game: Game) -> set[str]:
    from ptk.balance.moves import practices_held

    return set(practices_held(game))


def _expenses(game: Game, types: dict[str, str]) -> dict[str, int]:
    out: Counter[str] = Counter()
    for (firm, account), amount in game.balances.items():
        if firm == PLAYER and types.get(account) == "expense":
            out[_group(account)] += amount
    return dict(out)


def _per(cents: float, n: float) -> float:
    return cents / n if n else 0.0


def row(d: Decomposition) -> dict[str, float | None]:
    """One run's terms, in $k and ratios (per lawyer at December)."""
    n = d.lawyers or 1
    years = [y for y in d.hires if y >= YEAR - 4]
    return {
        "lawyers": d.lawyers,
        "EP": d.equity_partners,
        "IP": d.income_partners,
        "assoc": d.associates,
        "rev $M": d.revenue_cents / 1e8,
        "PEP $k": None if d.pep_cents is None else d.pep_cents / 1e5,
        "RPL $k": None if d.rpl_cents is None else d.rpl_cents / 1e5,
        "margin": d.margin,
        "lawyers/EP": d.leverage,
        "EP/lawyers": None if not d.leverage else 1 / d.leverage,
        "hours": d.hours,
        "rate $": None if d.rate_cents is None else d.rate_cents / 100,
        "realis.": d.realisation,
        "collect.": d.collection,
        "lawyer pay/L $k": _per(d.costs.get("lawyer_pay", 0), n) / 1e5,
        "overhead/L $k": _per(sum(v for k, v in d.costs.items() if k != "lawyer_pay"), n) / 1e5,
        "hires/yr": _per(sum(d.hires.get(y, 0) for y in years), len(years)),
        "leavers/yr": _per(sum(d.leavers.get(y, 0) for y in years), len(years)),
        "admits/yr": _per(sum(d.admissions.get(y, 0) for y in years), len(years)),
        "share": d.won_share,
        "share held": d.held_share,
    }


def medians(rows: list[dict[str, float | None]]) -> dict[str, float | None]:
    keys = rows[0].keys() if rows else ()
    out: dict[str, float | None] = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r[k] is not None]  # type: ignore[arg-type]
        out[k] = median(vals) if vals else None
    return out
