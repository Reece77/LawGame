"""Pro bono (PT-M7a; spec 7.8): work for the pro bono client, with no fees.

- **Flow.** Each month the firm's lawyers take pro bono flow from their free capacity after
  paid work (`staffing.month_hours`): a pool of (uncredited + uptake x credit) / 12 hours a
  lawyer, so a firm that credits more hours does more.
- **Named matters.** A named pro bono matter arrives with chance `named_bp_per_lawyer` x
  lawyers a month (stream `pro_bono`, keyed by firm): a case or advice for the pro bono
  client (`PRO_BONO_CLIENT_ID`), of `named_hours` hours over `named_months`, staffed by the
  default rule like any named matter. Draws, in order: arrival, kind, hours, months, merits,
  opposing counsel, forum.
- **No money.** Pro bono hours carry no value: no WIP, bills, fees, origination or client
  relationship (`interfaces.month_hours` and `billing_matters` leave them out); utilisation
  stays billable hours over capacity.
- **Credit policy.** Pro bono hours up to the policy (default 50 a year) count toward a
  lawyer's billable target in the hours morale term (`WorkMonth.credited_tenths`).
- **Effects.** Associates' morale target rises with their pro bono hours (up to `morale_max`
  at `morale_full_hours` a month); pro bono hours are all substantive (learning); the firm's
  pro bono hours a lawyer (a moving average) add to its recruiting appeal (the offer score's
  prestige), up to `appeal_max`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Final

from ptk.sim.data_models import Balance, GameData
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters import formulas as fx
from ptk.sim.matters.intake import with_matter
from ptk.sim.matters.models import PRO_BONO_CLIENT_ID, Matter
from ptk.sim.matters.staffing import staff_matter
from ptk.sim.state import GameState, with_firm, with_person_states
from ptk.sim.streams import RngFactory

HOURS_PER_YEAR_MONTHS: Final = 12  # tunable-exempt: months in a year


def lawyer_count(state: GameState, firm_id: int, data: GameData) -> int:
    staff = set(state.staff_ids(firm_id))
    return sum(1 for p in state.people if p.id in staff and data.role(p.role).kind == "lawyer")


def named_intake(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance
) -> tuple[GameState, tuple[LogItem, ...]]:
    """A month's named pro bono matter, if one arrives (module docstring)."""
    cfg = balance.pro_bono
    firm_id = state.player.id
    lawyers = lawyer_count(state, firm_id, data)
    gen = rng.stream(state.turn, "pro_bono", firm_id)
    u = [float(gen.random()) for _ in range(4)]
    merits_z = float(gen.standard_normal())
    opposing_z = float(gen.standard_normal())
    u_forum = float(gen.random())
    if u[0] >= min(1.0, cfg.named_bp_per_lawyer * lawyers / 10000):
        return state, ()
    total = sum(k.weight for k in cfg.named_kinds)
    pick, acc = cfg.named_kinds[-1], 0.0
    for k in cfg.named_kinds:
        acc += k.weight / total
        if u[1] < acc:
            pick = k
            break
    practice = data.practice(pick.practice)
    kind = practice.kind(pick.kind)
    hours = round(cfg.named_hours.lo + (cfg.named_hours.hi - cfg.named_hours.lo) * u[2])
    lo, hi = cfg.named_months
    months = lo + min(hi - lo, int(u[3] * (hi - lo + 1)))
    outcome = data.market.kinds[kind.kind].outcome
    court = None
    if kind.forums:
        forums = sorted(kind.forums.items())
        wsum = sum(w for _, w in forums)
        court, acc = forums[-1][0], 0.0
        for key, w in forums:
            acc += w / wsum
            if u_forum < acc:
                court = key
                break
        months = max(1, round(months * data.courts.court(court).pace))
    out = balance.outcomes
    matter = Matter(
        id=state.market.next_matter_id,
        firm_id=firm_id,
        client_id=PRO_BONO_CLIENT_ID,
        practice=practice.key,
        kind_key=kind.key,
        kind=kind.kind,
        name=f"Pro bono: {pick.label}",
        opened_turn=state.turn,
        planned_months=months,
        expected_fees_cents=0,
        hours_needed_tenths=hours * fx.TENTHS,
        adverse_name="the other side" if outcome == "case" else "",
        checked=state.player.conflict_checks,  # no client is ever adverse (no conflict to hide)
        court=court,
        merits=out.merits_sd * merits_z if outcome == "case" else 0.0,
        opposing_quality=(
            min(20.0, max(1.0, out.opposing_mean + out.opposing_sd * opposing_z))
            if outcome == "case"
            else 0.0
        ),
    )
    state = replace(state, market=with_matter(state.market, matter))
    staffed = staff_matter(state, matter, data, balance)
    state = replace(state, market=with_matter(state.market, staffed))
    item = inbox_item(
        state.turn,
        firm_id,
        "pro_bono_opened",
        link_kind="matter",
        link_id=matter.id,
        matter=matter.name,
        hours=hours,
        months=months,
    )
    return state, (item,)


def record_month(
    state: GameState, pro_bono: Mapping[int, int], data: GameData, balance: Balance
) -> GameState:
    """Year-to-date pro bono by person (reset each January) and the firm's moving average of
    pro bono tenths a lawyer a month."""
    from ptk.sim.matters.staffing import ytd_before

    firm_id = state.player.id
    staff = state.staff_ids(firm_id)
    moved = []
    for pid in staff:
        before = ytd_before(state, pid, balance)
        now = before + pro_bono.get(pid, 0)
        ps = state.person_state(pid)
        if now != ps.pro_bono_ytd_tenths:
            moved.append(replace(ps, pro_bono_ytd_tenths=now))
    state = with_person_states(state, moved)
    lawyers = lawyer_count(state, firm_id, data)
    if lawyers:
        this = sum(pro_bono.values()) / lawyers
        firm = state.firm(firm_id)
        avg = firm.pro_bono_avg_tenths + balance.pro_bono.average_rate * (
            this - firm.pro_bono_avg_tenths
        )
        state = with_firm(state, replace(firm, pro_bono_avg_tenths=avg))
    return state


def morale_term(level: str, pro_bono_tenths: int, balance: Balance) -> float:
    """Morale target points from a month's pro bono hours (associates only)."""
    cfg = balance.pro_bono
    if level not in cfg.morale_levels or pro_bono_tenths <= 0:
        return 0.0
    hours = pro_bono_tenths / fx.TENTHS
    return cfg.morale_max * min(1.0, hours / cfg.morale_full_hours)


def recruiting_appeal(avg_tenths_a_month: float, balance: Balance) -> float:
    """Offer-score points from the firm's pro bono hours a lawyer a year (recruiting appeal)."""
    cfg = balance.pro_bono
    hours_a_year = avg_tenths_a_month * HOURS_PER_YEAR_MONTHS / fx.TENTHS
    return min(cfg.appeal_max, cfg.appeal_per_hour * hours_a_year)
