"""Rival firms at game creation (spec 10.1; ADR PT-0008 1, 3; ADR PT-0013).

Real firms (firms.yaml, those that exist in 2005) start at their fiscal 2005 figures: revenue
is the demand run-rate, so in-game revenue equals the published figure at turn 0; lawyers
split into equity partners, other partners and associates by the published or personality
shares, and over practices by the personality's mix with the firm's strengths doubled.
Revenue per lawyer at capacity is sized so the firm bills at its personality's utilisation;
cost per lawyer so its profit is its PEP times its equity partners.

Generated firms (balance `rivals.generated`): stream `rival_gen`, key `(GENERATED_KEY, n)`,
draws in order: revenue, revenue per lawyer, personality, New York office, the two name
parts. Key people: stream `rival_people` (people.py), notables first, then generated.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.models import Judge, JudgeTraits
from ptk.sim.people.generator import NAME_POOL
from ptk.sim.rivals import streams
from ptk.sim.rivals.data import FirmDef, NotableDef, PersonalityDef
from ptk.sim.rivals.models import (
    GENERATED_KEY,
    REAL_KEY,
    Pool,
    RivalFirm,
    RivalsState,
)
from ptk.sim.rivals.people import ASSOCIATE_LEVELS, STANDING_ORDER, add_members, books, new_member
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

SETUP_TURN = 0
MONTHS = 12  # tunable-exempt: months in a year
GENERATED_ID_OFFSET = 1000  # tunable-exempt: generated firms' ids follow the real ones
BOUTIQUE_ID_OFFSET = 2000  # tunable-exempt: boutiques' ids follow the generated ones
DEFAULT_MARGIN = 0.35  # tunable-exempt: used only when firms.yaml has neither PEP nor EP [A]
NAME_FORMS = ("{a} & {b}", "{a} {b}", "{a}, {b} & Associates", "{a} LLP")  # tunable-exempt


def mix_weights(
    pdef: PersonalityDef, strong: tuple[str, ...], practices: tuple[str, ...]
) -> list[float]:
    raw = [pdef.mix.get(p, 0.0) * (2.0 if p in strong else 1.0) for p in practices]
    if sum(raw) <= 0:
        raw = [1.0 for _ in practices]
    total = sum(raw)
    return [w / total for w in raw]


def build_firm(
    *,
    firm_id: int,
    rival_key: tuple[int, ...],
    key: str,
    name: str,
    short: str,
    personality: str,
    kind: str,
    hq: str,
    ny_office: bool,
    offices: int,
    strong: tuple[str, ...],
    revenue_cents: float,
    lawyers: float,
    equity_partners: float | None,
    pep_cents: float | None,
    turn: int,
    data: GameData,
    balance: Balance,
) -> RivalFirm:
    rb = balance.rivals
    pdef = rb.personalities[personality]
    eq = equity_partners if equity_partners is not None else lawyers * pdef.equity_share
    eq = min(eq, lawyers * pdef.partner_share)
    other = max(0.0, lawyers * pdef.partner_share - eq)
    assoc = max(0.0, lawyers - eq - other)
    weights = mix_weights(pdef, strong, data.practice_keys)
    pools = tuple(
        Pool(practice=p, equity=eq * w, partners=other * w, associates=assoc * w)
        for p, w in zip(data.practice_keys, weights, strict=True)
    )
    profit = (pep_cents * eq) if pep_cents is not None else revenue_cents * DEFAULT_MARGIN
    profit = min(profit, revenue_cents * 0.7)  # tunable-exempt: guards a bad data row
    monthly = round(revenue_cents / MONTHS)
    return RivalFirm(
        id=firm_id,
        rival_key=rival_key,
        key=key,
        name=name,
        short=short,
        personality=personality,
        kind=kind,  # type: ignore[arg-type]
        hq=hq,
        ny_office=ny_office,
        offices=offices,
        base_offices=offices,
        founded_turn=turn,
        pools=pools,
        rpl_cap_cents=revenue_cents / (lawyers * pdef.utilisation),
        cost_per_lawyer_cents=(revenue_cents - profit) / lawyers,
        demand_cents=revenue_cents,
        utilisation=pdef.utilisation,
        revenue=(monthly,) * MONTHS,
        profit=(round(profit / MONTHS),) * MONTHS,
    )


def real_firm(index: int, f: FirmDef, data: GameData, balance: Balance) -> RivalFirm:
    assert f.fy2005 is not None and f.fy2005.revenue_cents and f.fy2005.lawyers
    return build_firm(
        firm_id=balance.rivals.first_firm_id + index,
        rival_key=(REAL_KEY, index),
        key=f.key,
        name=f.name,
        short=f.short,
        personality=f.personality,
        kind="real",
        hq=f.hq,
        ny_office=f.ny_office,
        offices=f.offices,
        strong=f.strong,
        revenue_cents=float(f.fy2005.revenue_cents),
        lawyers=float(f.fy2005.lawyers),
        equity_partners=None
        if f.fy2005.equity_partners is None
        else float(f.fy2005.equity_partners),
        pep_cents=None if f.fy2005.pep_cents is None else float(f.fy2005.pep_cents),
        turn=SETUP_TURN,
        data=data,
        balance=balance,
    )


def generated_firm(n: int, rng: RngFactory, data: GameData, balance: Balance) -> RivalFirm:
    gb = balance.rivals.generated
    gen = streams.rival_gen(rng, SETUP_TURN, GENERATED_KEY, n)
    z = float(gen.standard_normal())
    from ptk.sim import dmath

    revenue = min(
        gb.revenue_cents.hi,
        max(gb.revenue_cents.lo, gb.revenue_median_cents * dmath.exp(gb.revenue_sigma * z)),
    )
    rpl = float(gen.uniform(gb.rpl_cents.lo, gb.rpl_cents.hi))
    keys = sorted(gb.personalities)
    weights = [gb.personalities[k] for k in keys]
    total = sum(weights)
    u = float(gen.random()) * total
    personality = keys[-1]
    for k, w in zip(keys, weights, strict=True):
        if u < w:
            personality = k
            break
        u -= w
    ny = float(gen.random()) < gb.ny_share
    pool = data.names[NAME_POOL].last
    a = pool[int(gen.integers(0, len(pool)))]
    b = pool[int(gen.integers(0, len(pool)))]
    form = NAME_FORMS[int(gen.integers(0, len(NAME_FORMS)))]
    name = form.format(a=a, b=b)
    return build_firm(
        firm_id=balance.rivals.first_firm_id + GENERATED_ID_OFFSET + n,
        rival_key=(GENERATED_KEY, n),
        key=f"gen_{n}",
        name=name,
        short=a,
        personality=personality,
        kind="generated",
        hq="new_york" if ny else "elsewhere",
        ny_office=ny,
        offices=1 + int(revenue // 10_000_000_000),  # tunable-exempt: an office per $100M [A]
        strong=(),
        revenue_cents=revenue,
        lawyers=max(10.0, revenue / rpl),
        equity_partners=None,
        pep_cents=None,
        turn=SETUP_TURN,
        data=data,
        balance=balance,
    )


def staff_key_people(
    rivals: RivalsState,
    firm: RivalFirm,
    partners: int,
    associates: int,
    notables: list[NotableDef],
    rng: RngFactory,
    turn: int,
    data: GameData,
    balance: Balance,
    start: tuple[int, int],
    first_n: int = 0,
) -> RivalsState:
    """Key partners (notables first, by standing, chair first) and rising associates."""
    rb = balance.rivals
    notables = sorted(notables, key=lambda x: (not x.chair, STANDING_ORDER[x.standing], x.key))
    n_partners = min(partners, int(firm.equity_partners + sum(p.partners for p in firm.pools)))
    n_partners = max(n_partners, len(notables))
    weights = [p.lawyers for p in firm.pools]
    practices = _spread(weights, n_partners - len(notables), [p.practice for p in firm.pools])
    book_list = books(firm.demand_cents * rb.key_book_share, n_partners, rb.book_pareto)
    members = []
    pid = rivals.next_person_id
    n = first_n
    for i in range(n_partners):
        notable = notables[i] if i < len(notables) else None
        practice = notable.practice if notable else practices[i - len(notables)]
        level: str = (
            notable.level if notable else ("equity_partner" if i % 4 != 3 else "income_partner")
        )
        members.append(
            new_member(firm, pid, n, turn, practice, level, book_list[i],
                       notable.key if notable else None)
        )  # fmt: skip
        pid += 1
        n += 1
    assoc_practices = _spread(weights, associates, [p.practice for p in firm.pools])
    for i in range(associates):
        level = ASSOCIATE_LEVELS[i % len(ASSOCIATE_LEVELS)]
        members.append(new_member(firm, pid, n, turn, assoc_practices[i], level, 0))
        pid += 1
        n += 1
    rivals = add_members(rivals, members)
    firm = replace(firm, people_made=n, key_target=n_partners)
    return replace(rivals, firms=tuple(firm if f.id == firm.id else f for f in rivals.firms))


def _spread(weights: list[float], n: int, keys: list[str]) -> list[str]:
    """n slots over keys by weight (largest remainder, ties by order), biggest first."""
    if n <= 0:
        return []
    total = sum(weights) or 1.0
    exact = [w / total * n for w in weights]
    counts = [int(x) for x in exact]
    rest = sorted(range(len(keys)), key=lambda i: (-(exact[i] - counts[i]), i))
    for i in rest[: n - sum(counts)]:
        counts[i] += 1
    order = sorted(range(len(keys)), key=lambda i: (-counts[i], i))
    out: list[str] = []
    while len(out) < n:
        for i in order:
            if counts[i] > 0:
                out.append(keys[i])
                counts[i] -= 1
    return out


def new_rivals(
    state: GameState, rng: RngFactory, data: GameData, balance: Balance, real_people: bool
) -> GameState:
    """The rivals at turn 0, and the real judges on the modelled courts' benches."""
    rb = balance.rivals
    start = state.save_meta.start_ym
    rivals = RivalsState(real_people=real_people, next_person_id=rb.first_person_id)
    firms: list[RivalFirm] = []
    for index, fdef in enumerate(data.rivals.firms.firms):
        if fdef.start_ym is not None:
            continue  # a successor: created by its merger
        firms.append(real_firm(index, fdef, data, balance))
    for n in range(rb.generated.count):
        firms.append(generated_firm(n, rng, data, balance))
    rivals = replace(rivals, firms=tuple(sorted(firms, key=lambda f: f.id)))
    by_firm: dict[str, list[NotableDef]] = {}
    for nd in data.rivals.people.notables:
        by_firm.setdefault(nd.firm, []).append(nd)
    for firm in rivals.firms:
        if firm.kind == "real":
            partners, associates = rb.key_partners, rb.key_associates
        else:
            partners, associates = rb.generated.key_partners, rb.generated.key_associates
        rivals = staff_key_people(
            rivals,
            firm,
            partners,
            associates,
            by_firm.get(firm.key, []),
            rng,
            SETUP_TURN,
            data,
            balance,
            start,
        )
    state = replace(state, rivals=rivals)
    return replace(state, market=replace(state.market, judges=bench(state, rng, data, balance)))


# --- Real judges (ADR PT-0013; spec 7.6a) --------------------------------------------------


def court_traits(court: str, data: GameData) -> dict[str, float]:
    """A court's procedural traits from its published statistics (judges.yaml court_stats):
    docket speed from the median months to disposition against the all-district median,
    appetite for trial from trials per judgeship against the modelled courts' mean; the rest
    neutral. Never a side (ADR PT-0013)."""
    keys = [t.key for t in data.courts.judge_traits]
    out = {k: 10.5 for k in keys}  # tunable-exempt: the neutral trait (1-20 midpoint)
    stats = {s.court: s for s in data.rivals.people.court_stats}
    s = stats.get(court)
    national = stats.get("all_districts")
    trials = [x.trials_per_judgeship for x in stats.values() if x.trials_per_judgeship]
    if s is not None and s.disposition_months and national and national.disposition_months:
        ratio = national.disposition_months / s.disposition_months
        out["docket_speed"] = min(20.0, max(1.0, 10.5 * ratio))
    if s is not None and s.trials_per_judgeship and trials:
        mean = sum(trials) / len(trials)
        out["trial_appetite"] = min(20.0, max(1.0, 10.5 * s.trials_per_judgeship / mean))
    return out


def bench(state: GameState, rng: RngFactory, data: GameData, balance: Balance) -> tuple[Judge, ...]:
    """Generated judges stay on courts without real judges (arbitration); courts with real
    judges get them, with traits around their court's published figures (per-judge figures
    where judges.yaml sources one; ADR PT-0013: procedural only), active from the year they
    joined to the year they left (or, with no
    year, a seeded year in 2026-2034), each followed by a generated successor."""
    from ptk.sim.calendar import ym_to_turn
    from ptk.sim.matters.setup import TRAIT_MEAN, TRAIT_SD

    start = state.save_meta.start_ym
    real_courts = {j.court for j in data.rivals.people.judges}
    keep = [j for j in state.market.judges if j.court not in real_courts]
    out: list[Judge] = [replace(j, id=i + 1) for i, j in enumerate(keep)]
    keys = tuple(t.key for t in data.courts.judge_traits)
    pool = data.names[NAME_POOL]
    end_year = start[0] + balance.campaign.standard_turns // MONTHS
    for index, jd in enumerate(data.rivals.people.judges):
        gen = streams.real_swap(rng, SETUP_TURN, 1, index)  # names if real people are off
        first_g = pool.first[int(gen.integers(0, len(pool.first)))]
        last_g = pool.last[int(gen.integers(0, len(pool.last)))]
        left = (
            jd.left if jd.left is not None else int(gen.integers(2026, end_year + 1))
        )  # tunable-exempt: after history
        parts = jd.name.split()
        first, last = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else ("", jd.name)
        sd = balance.rivals.judge_trait_sd  # seeded spread around the court's published mean
        court = court_traits(jd.court, data)
        traits = {
            k: min(20.0, max(1.0, v + sd * float(gen.standard_normal()))) for k, v in court.items()
        }
        traits.update(jd.traits)  # a judge's own sourced traits win
        from_turn = max(0, ym_to_turn(jd.joined, 1, start))
        until = ym_to_turn(left, 1, start)
        if until <= 0:
            continue
        out.append(
            Judge(
                id=len(out) + 1,
                court=jd.court,
                first_name=first if state.rivals.real_people else first_g,
                last_name=last if state.rivals.real_people else last_g,
                traits=JudgeTraits.build(keys, traits),
                real=True,
                from_turn=from_turn,
                until_turn=until,
            )
        )
        if until < balance.campaign.standard_turns:
            g2 = streams.real_swap(rng, SETUP_TURN, 2, index)
            out.append(
                Judge(
                    id=len(out) + 1,
                    court=jd.court,
                    first_name=pool.first[int(g2.integers(0, len(pool.first)))],
                    last_name=pool.last[int(g2.integers(0, len(pool.last)))],
                    traits=JudgeTraits.build(
                        keys,
                        {
                            k: min(
                                20.0, max(1.0, TRAIT_MEAN + TRAIT_SD * float(g2.standard_normal()))
                            )
                            for k in keys
                        },
                    ),
                    from_turn=until,
                )
            )
    return tuple(out)
