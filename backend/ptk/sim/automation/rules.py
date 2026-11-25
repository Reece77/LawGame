"""Each area's monthly rule (spec 9.4's "what the owner does each month"; PT-M9).

Ported from backend/tst/sim/automation/rules.py @ 80a38079 (Tech Startup Tycoon) as a pattern;
changed: Partner Track's areas. An area whose seat has a PT-M8 authority rule runs that rule
as it is (`interfaces.run_seat_rule`), with the area's guardrails and its quality draw; the
rest act through the player's own action functions. Rules read only what the firm can see
(last month's hours, open matters, WIP, RFPs, displayed ranges, the inbox's figures).

- Staffing (a practice group's leader): PT-M8's rule: a hiring plan for the group when its
  last month ran at or above `busy_bp` and it is under its headcount cap. The engine's own
  staffing rule (PT-M7a) allocates flow work and staffs named matters every month.
- Intake and conflicts (general counsel): PT-M8's waiver requests on held instructions; a
  waiver adverse to a key client is a one-off, so it arrives as a proposal.
- Billing and collections (CFO): PT-M8's write-downs of long-unbilled time within the band
  (bills go out and receivables are chased on cycle by the engine); the revolver repaid down
  to `revolver_months` of last month's standard value from cash above a month of it.
- Pricing and rates (pricing director): PT-M8's January rise within the band.
- Business development (CMO): PT-M8's RFP pitches; then `intros_per_month` introductions of
  a colleague to a client with a good relationship in a practice it does not use yet.
- Associate hiring and campus (CHRO): PT-M8's campus targets in the register months; when the
  firm's last month ran at or above `busy_bp`, a lateral plan of `lateral_step` for each
  practice group without one (before there are groups, the CHRO's own plan per practice);
  the pay policy kept at `pay_pct_bp` of the market (above it is a one-off).
- Associate development (CHRO): sponsors for associates in the prospects levels who have none;
  in `automation.proposal_month` (November), the partnership candidates the business case
  supports (one equity partner per `lawyers_per_equity` lawyers), proposed to the player for
  December's vote (admissions are one-offs).
- Lateral partners (an executive committee member): a lateral partner with a book of at least
  `min_book_k` for each practice the firm should hold (2 + lawyers / `lawyers_per_practice`),
  then for leverage above `leverage_x10`/10 associates a partner while busy; one step a month
  (search, diligence, offer at the ask; a guarantee makes it a one-off).
- Offices and support (COO): business-services support kept at `support_per_100` people per
  100 lawyers (0, the default: off until a support-coverage system exists).
- Knowledge and AI (CKO, PT-M14): the training programme, subscriptions within the budget a
  lawyer (newest era first) and rollout votes; a new platform is a one-off (a proposal).
- Risk and claims (general counsel, PT-M15): keeps the conflict checks on; answers claims'
  offers by the default rule (a settlement above the deductible left is a one-off); settles
  inquiries within `settle_fine_k`, else contests; keeps the renewal's deductible within
  `max_deductible_k`.
- Pro bono (a partner): once a year (`automation.pro_bono_month`), after the firm's first year
  (its moving average starts at zero), the credit policy stepped toward `target_hours` pro bono
  hours a lawyer a year when the firm is more than `tolerance_pct` away.
- Routine events: answered in phase 1 (`ptk.sim.automation.events`); nothing here.

A mistake is the seat rule's own (one fewer, the second best, a month late) or a noisy step
within the guardrails (`AutoRun.noisy`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from ptk.sim import interfaces
from ptk.sim.automation import owners
from ptk.sim.automation.run import AutoRun
from ptk.sim.calendar import turn_to_ym
from ptk.sim.data_models import PARTNER_LEVELS
from ptk.sim.ledger import CASH, REVOLVER
from ptk.sim.org.seats import managing_partner
from ptk.sim.partnership.models import FirmPartnership
from ptk.sim.state import GameState

BP: Final = 10_000  # tunable-exempt: basis points
K_CENTS: Final = 100_000  # tunable-exempt: cents in $1,000 (guardrails in $k)
TENTHS: Final = 10  # tunable-exempt: hours are tenths
MONTHS: Final = 12  # tunable-exempt: calendar
ASSOCIATE: Final = "associate_"
DECEMBER: Final = 12  # tunable-exempt: calendar


def _seat_rule(run: AutoRun) -> None:
    a = owners.area_def(run.balance, run.owner.area)
    assert a.seat is not None

    def act(state: GameState, action: object, text: str, mistake: bool) -> tuple[bool, GameState]:
        run.state = state
        taken = run.attempt(action, text, mistake=mistake)
        return taken, run.state

    rails = tuple(
        (k, run.rail(k)) for k, *_ in owners.guardrails(run.owner.area, run.balance, run.data)
    )
    run.state = interfaces.run_seat_rule(
        run.state, run.firm_id, a.seat, run.owner.slot, run.owner.person_id, rails, run.right,
        run.gen, run.balance, run.data, act,
    )  # fmt: skip


# --- What the firm can see ----------------------------------------------------------------------


def _lawyers(state: GameState, firm_id: int, run: AutoRun) -> list[int]:
    return [
        e.person_id
        for e in state.staff(firm_id)
        if run.data.role(state.person(e.person_id).role).kind == "lawyer"
    ]


def _practice(run: AutoRun, person_id: int) -> str:
    return run.data.role(run.state.person(person_id).role).practice or ""


def _held(run: AutoRun) -> list[str]:
    held = {
        _practice(run, p)
        for p in _lawyers(run.state, run.firm_id, run)
        if run.state.person(p).level in PARTNER_LEVELS
    }
    return [k for k in run.data.practice_keys if k in held]


def firm_utilisation_bp(run: AutoRun) -> int:
    from ptk.sim.org.authority import utilisation_bp

    people = tuple(e.person_id for e in run.state.staff(run.firm_id))
    return utilisation_bp(run.state, people, run.data, run.balance) or 0


def _month_value(run: AutoRun) -> int:
    staff = set(run.state.staff_ids(run.firm_id))
    return sum(r.value_cents for r in run.state.market.hours if r.person_id in staff)


def _groups(run: AutoRun) -> list[tuple[int, str, int]]:
    """(unit id, practice, leader id) of the practice groups with an eligible leader."""
    out = []
    for unit in run.state.org.firm_units(run.firm_id):
        if unit.kind != "practice_group" or unit.practice is None or unit.leader_id is None:
            continue
        if run.state.employer_of(unit.leader_id) != run.firm_id:
            continue
        out.append((unit.id, unit.practice, unit.leader_id))
    return out


def _shown(run: AutoRun, person_id: int) -> float:
    from ptk.sim.people.reveal import shown_rating

    rec = run.state.reveal(run.firm_id, person_id)
    if rec is None:
        return 0.0
    p = run.state.person(person_id)
    return shown_rating(p, rec, run.data.role(p.role).primary)


# --- Rules ------------------------------------------------------------------------------------


def staffing(run: AutoRun) -> None:
    _seat_rule(run)


def intake(run: AutoRun) -> None:
    _seat_rule(run)


def pricing(run: AutoRun) -> None:
    _seat_rule(run)


def billing(run: AutoRun) -> None:
    from ptk.sim.partnership.actions import RepayRevolver

    _seat_rule(run)
    fees = _month_value(run)
    cap = run.noisy(run.rail("revolver_months") * fees)
    drawn = -run.balances.get((run.firm_id, REVOLVER), 0)
    spare = run.balances.get((run.firm_id, CASH), 0) - fees
    mp = managing_partner(run.state, run.firm_id)
    if mp is not None and drawn > cap and spare > 0:
        amount = min(drawn - cap, spare)
        run.attempt(
            RepayRevolver(mp, amount),
            f"repaid ${amount / 100:,.0f} of the revolver",
            mistake=not run.right,
            link=("finance", 0),
        )


def bd(run: AutoRun) -> None:
    from ptk.sim.matters.actions import Introduce

    _seat_rule(run)
    held = set(_held(run))
    mp = managing_partner(run.state, run.firm_id)
    if mp is None:
        return
    options = []
    for rel in run.state.market.relationships:
        if (
            rel.firm_id != run.firm_id
            or rel.score < run.rail("min_relationship")
            or not rel.practices
        ):
            continue
        for practice in sorted(held - set(rel.practices)):
            affinity = max(
                run.data.practice(p).cross_sell.get(practice, 0.0) for p in rel.practices
            )
            if affinity > 0:
                options.append((-(affinity * rel.score), rel.client_id, practice))
    options.sort()
    if not run.right and len(options) >= 2:
        options[0], options[1] = options[1], options[0]
    made = 0
    lawyers = _lawyers(run.state, run.firm_id, run)
    for _, client_id, practice in options:
        if made >= run.rail("intros_per_month"):
            break
        colleague = max(
            (p for p in lawyers if _practice(run, p) == practice and p != mp),
            key=lambda p: (_shown(run, p), -p),
            default=None,
        )
        if colleague is None:
            continue
        client = run.state.market.client(client_id).name
        if run.attempt(
            Introduce(mp, client_id, colleague, practice),
            f"introduced a {run.data.practice(practice).label} colleague to {client}",
            mistake=not run.right,
            link=("client", client_id),
        ):
            made += 1


def hiring(run: AutoRun) -> None:
    from ptk.sim.hiring.actions import SetPayPolicy
    from ptk.sim.org.actions import CreatePlan

    _seat_rule(run)  # the CHRO's campus targets (PT-M8)
    b, state = run.balance, run.state
    util = firm_utilisation_bp(run)
    busy = run.noisy(run.rail("busy_bp"), "busy_bp")
    if util >= busy:
        step = run.rail("lateral_step")
        groups = _groups(run)
        targets: list[tuple[int | None, str, int]]
        if groups:
            targets = [(unit, practice, leader) for unit, practice, leader in groups]
        else:  # before practice groups: the CHRO's own plans, one per practice held
            targets = [(None, p, run.owner.person_id) for p in _held(run)]
        for unit, practice, leader in targets:
            plans = run.state.org.firm_plans(run.firm_id)
            if any(
                p.status == "active"
                and not p.campus
                and p.unit_id == unit
                and (unit is not None or p.role == run.data.practice_role(practice).key)
                for p in plans
            ):
                continue
            n = max(1, run.noisy(step))
            where = "the firm" if unit is None else run.state.org.unit(unit).name  # type: ignore[union-attr]
            run.attempt(
                CreatePlan(
                    actor_id=run.owner.person_id,
                    owner_id=leader,
                    role=run.data.practice_role(practice).key,
                    target=n,
                    channel="job_post",
                    ratio_bp=b.authority.plan_ratio_bp,
                    unit_id=unit,
                ),
                f"opened a plan for {n} lateral associate(s) in {where}"
                f" at {util / 100:.0f}% utilisation",
                mistake=not run.right,
                link=("org", unit or 0),
            )
    want = run.rail("pay_pct_bp")
    policy = state.player.pay_policy
    mode = "match" if want == BP else ("lag" if want < BP else "lead")
    if (policy.mode, policy.pct_bp) != (mode, want) and run.right:
        mp = managing_partner(run.state, run.firm_id)
        if mp is not None:
            run.attempt(
                SetPayPolicy(mp, mode, want),  # type: ignore[arg-type]
                f"set associate pay to {mode} the market ({want / 100:.0f}%)",
                link=("finance", 0),
            )


def development(run: AutoRun) -> None:
    from ptk.sim.partnership.actions import ProposePartner, SetSponsor
    from ptk.sim.partnership.careers import eligible

    state, b = run.state, run.balance
    fp = state.partnership.of(run.firm_id)
    mp = managing_partner(state, run.firm_id)
    if fp is None or mp is None:
        return
    lawyers = _lawyers(state, run.firm_id, run)
    partners = [p for p in lawyers if state.person(p).level in PARTNER_LEVELS]
    prospects = set(b.morale.prospects_levels)
    load: dict[int, int] = {p: 0 for p in partners}
    for _a, s in fp.sponsors:
        if s in load:
            load[s] += 1
    done = 0
    for pid in sorted(lawyers):
        if done >= run.rail("sponsors_per_month"):
            break
        level = state.person(pid).level
        if level not in prospects or fp.sponsor_of(pid) is not None:
            continue
        same = [p for p in partners if _practice(run, p) == _practice(run, pid) and p != mp]
        if not same:
            continue
        ranked = sorted(same, key=lambda p: (load[p], -_shown(run, p), p))
        sponsor = ranked[0] if run.right or len(ranked) == 1 else ranked[1]
        if run.attempt(
            SetSponsor(mp, pid, sponsor),
            f"made {_full(state, sponsor)} sponsor of {_full(state, pid)}",
            mistake=sponsor != ranked[0],
            link=("person", pid),
        ):
            load[sponsor] += 1
            done += 1
    month = turn_to_ym(state.turn, state.save_meta.start_ym)[1]
    if month == DECEMBER and run.right:
        _second_looks(run, fp, mp, lawyers)
    if month != b.automation.proposal_month:
        return
    per = run.rail("lawyers_per_equity")
    equity = sum(1 for p in lawyers if state.person(p).level == "equity_partner")
    admit = max(0, round(len(lawyers) / max(1, per)) - equity)
    if not run.right:
        admit = max(0, admit + (1 if run.gen.random() < 0.5 else -1))  # tunable-exempt: a coin
    cands = [p for p in lawyers if eligible(state, fp, p, b) and fp.candidacy(p) is None]
    cands.sort(key=lambda p: (-_shown(run, p), p))
    for pid in cands[:admit]:
        name = _full(state, pid)
        run.attempt(
            ProposePartner(mp, pid, "equity"),
            f"put {name} up for equity partnership in December",
            link=("person", pid),
            recommendation=(
                f"{name} is among our strongest candidates and the business case supports "
                f"{admit} admission(s) this year. I recommend we put them to the vote."
            ),
        )


def _second_looks(run: AutoRun, fp: FirmPartnership, mp: int, lawyers: list[int]) -> None:
    """December: candidates in their first eligible year who are not proposed get a second
    look next year rather than up or out (not an admission, so within the area)."""
    from ptk.sim.partnership.actions import ProposePartner
    from ptk.sim.partnership.careers import class_year, eligible, tracks_for

    state, b = run.state, run.balance
    for pid in sorted(lawyers):
        fp_now = state.partnership.of(run.firm_id) or fp
        if not eligible(state, fp_now, pid, b) or fp_now.candidacy(pid) is not None:
            continue
        year = class_year(state.person(pid).level)
        if year is None or year > fp_now.agreement.track_years:
            continue
        if "not_this_year" not in tracks_for(state, fp_now, pid):
            continue
        run.attempt(
            ProposePartner(mp, pid, "not_this_year"),
            f"gave {_full(state, pid)} a second look next year",
            link=("person", pid),
        )
        state = run.state


def _full(state: GameState, pid: int) -> str:
    p = state.person(pid)
    return f"{p.first_name} {p.last_name}"


def laterals(run: AutoRun) -> None:
    from ptk.sim.partnership.actions import Diligence, LateralOffer, LateralSearch

    state = run.state
    fp = state.partnership.of(run.firm_id)
    mp = managing_partner(state, run.firm_id)
    if fp is None or mp is None:
        return
    fees = _month_value(run)
    if run.balances.get((run.firm_id, CASH), 0) <= run.rail("cash_months") * fees:
        return  # the bank is not quiet enough
    lawyers = _lawyers(state, run.firm_id, run)
    held = _held(run)
    wanted = 2 + len(lawyers) // max(1, run.rail("lawyers_per_practice"))
    practice = None
    if len(held) < wanted:
        missing = [p for p in run.data.practice_keys if p not in held]

        def pull(p: str) -> float:
            return sum(run.data.practice(h).cross_sell.get(p, 0.0) for h in held)

        missing.sort(key=lambda p: (-pull(p), run.data.practice_keys.index(p)))
        if missing:
            practice = missing[0] if run.right or len(missing) == 1 else missing[1]
    else:
        partners = sum(1 for p in lawyers if state.person(p).level in PARTNER_LEVELS)
        assoc = sum(1 for p in lawyers if state.person(p).level.startswith(ASSOCIATE))
        if (
            partners
            and assoc * 10 > run.rail("leverage_x10") * partners
            and firm_utilisation_bp(run) >= run.rail("busy_bp")
            and held
        ):

            def ratio(p: str) -> tuple[float, str]:
                staff = [x for x in lawyers if _practice(run, x) == p]
                pp = sum(1 for x in staff if state.person(x).level in PARTNER_LEVELS)
                aa = sum(1 for x in staff if state.person(x).level.startswith(ASSOCIATE))
                return (aa / max(1, pp), p)

            practice = max(held, key=ratio)
    if practice is None:
        return
    label = run.data.practice(practice).label
    open_ = [c for c in fp.laterals if c.status == "open" and c.practice == practice]
    if not open_:
        run.attempt(LateralSearch(mp, practice), f"opened a lateral partner search in {label}")
        return
    best = max(open_, key=lambda c: (c.book_lo_cents, -c.person_id))
    if not best.diligence:
        run.attempt(
            Diligence(mp, best.person_id), f"ran diligence on {_full(state, best.person_id)}"
        )
        return
    if best.book_lo_cents < run.rail("min_book_k") * K_CENTS:
        return
    years = run.rail("guarantee_years")
    name = _full(state, best.person_id)
    run.attempt(
        LateralOffer(mp, best.person_id, best.ask_cents, years),
        f"offered {name} ({label}) {best.ask_cents / 100:,.0f} a year"
        + (f" with {years} guaranteed year(s)" if years else ""),
        mistake=not run.right,
        link=("partnership", 0),
        recommendation=(
            f"{name} brings a book we can see at ${best.book_lo_cents / 100:,.0f} to "
            f"${best.book_hi_cents / 100:,.0f} in {label}. I recommend we make the offer."
        ),
    )


def offices(run: AutoRun) -> None:
    from ptk.sim.org.actions import CreatePlan

    per_100 = run.rail("support_per_100")
    if per_100 <= 0:
        return
    state = run.state
    lawyers = len(_lawyers(state, run.firm_id, run))
    support = sum(
        1
        for e in state.staff(run.firm_id)
        if run.data.role(state.person(e.person_id).role).kind == "business_services"
    )
    want = run.noisy(lawyers * per_100 // 100)
    if support >= want or any(
        p.status == "active" and p.role == "operations" for p in state.org.firm_plans(run.firm_id)
    ):
        return
    owner = run.owner.person_id
    from ptk.sim.org.actions import may_own_plan

    if not may_own_plan(state, owner, run.balance):
        return
    n = want - support
    run.attempt(
        CreatePlan(owner, owner, "operations", n, "job_post", run.balance.authority.plan_ratio_bp),
        f"opened a plan for {n} support staff",
        mistake=not run.right,
    )


def knowledge(run: AutoRun) -> None:
    """PT-M14 (spec 9.4): the CKO keeps the training programme at its guardrail, subscribes
    to each era begun within the monthly budget a lawyer (newest era first, full coverage
    while the budget lasts), and puts a rollout to the partners where one is due. An era's
    first investment buys its platform: a one-off, so it comes to the player as a proposal."""
    from ptk.sim.tech.actions import InvestInEra, RolloutEra, SetTrainingProgramme
    from ptk.sim.tech.efficiency import ym_of

    state, b, data = run.state, run.balance, run.data
    owner = run.owner.person_id
    firm = state.tech.firm(run.firm_id)
    hours = run.noisy(run.rail("training_hours"), "training_hours")
    if (0 if firm is None else firm.training_hours) != hours:
        run.attempt(
            SetTrainingProgramme(owner, hours),
            f"set the training programme at {hours} hours a lawyer a year",
            mistake=not run.right,
            link=("tech", 0),
        )
    budget = run.rail("budget_per_lawyer") * 100  # tunable-exempt: dollars to cents
    ym = ym_of(state)
    for era in reversed(data.legal_eras.eras):
        if ym < era.start or era.subscription_cents <= 0:
            continue
        firm = run.state.tech.firm(run.firm_id)
        mine = None if firm is None else firm.era(era.key)
        bp = min(10000, budget * 10000 // era.subscription_cents)  # tunable-exempt: bp
        budget -= era.subscription_cents * bp // 10000  # tunable-exempt: bp
        if (0 if mine is None else mine.subscription_bp) != bp:
            run.attempt(
                InvestInEra(owner, era.key, bp),
                f"set {era.label} at {bp / 100:.0f}% coverage",
                mistake=not run.right,
                link=("tech", 0),
            )
        held = run.state.tech.firm(run.firm_id) or firm
        cur = None if held is None else held.era(era.key)
        wait = b.tech.adoption.retry_months
        if (
            run.rail("rollout")
            and cur is not None
            and cur.subscription_bp > 0
            and not cur.rolled_out
            and (cur.vote_turn is None or state.turn - cur.vote_turn >= wait)
        ):
            run.attempt(
                RolloutEra(owner, era.key),
                f"put the {era.label} rollout to the partners",
                link=("tech", 0),
            )


def risk(run: AutoRun) -> None:
    """PT-M15: conflict checks on; claims' offers answered by the default rule (a settlement
    above what is left of the deductible is a one-off, so it comes to you); regulators'
    inquiries settled when the fine's middle is within `settle_fine_k`, else contested; the
    next renewal's deductible kept at most `max_deductible_k`."""
    from ptk.sim.matters.actions import SetConflictChecks
    from ptk.sim.risk.actions import RespondClaim, RespondInquiry, SetPolicyTerms
    from ptk.sim.risk.claims import default_answer

    me = run.owner.person_id
    if not run.state.player.conflict_checks and run.right:
        run.attempt(SetConflictChecks(me, True), "turned the conflict checks back on")
    if not run.balance.risk.enabled:
        return
    risk = run.state.risk
    for claim in [c for c in risk.claims if c.firm_id == run.firm_id and c.stage == "offer"]:
        choice = default_answer(claim)
        if not run.right:
            choice = "contest" if choice == "settle" else "settle"
        run.attempt(
            RespondClaim(me, claim.id, choice),
            f"chose to {choice} claim {claim.id}",
            mistake=not run.right,
            link=("risk", claim.id),
            recommendation=choice,
        )
    for inq in [
        i for i in risk.inquiries if i.firm_id == run.firm_id and i.is_open and i.choice is None
    ]:
        mid = (inq.fine_lo_cents + inq.fine_hi_cents) // 2
        choice = "settle" if mid <= run.rail("settle_fine_k") * K_CENTS else "contest"
        run.attempt(
            RespondInquiry(me, inq.id, choice),
            f"chose to {choice} the regulator's inquiry",
            link=("risk", inq.id),
        )
    cap = run.rail("max_deductible_k") * K_CENTS
    options = [d.cents for d in run.data.insurance.deductibles if d.cents <= cap]
    terms = risk.firm(run.firm_id).terms
    if options and terms.deductible_cents is not None and terms.deductible_cents <= cap:
        return
    if options and terms.deductible_cents != options[-1]:
        run.attempt(
            SetPolicyTerms(me, terms.insurer, terms.limit_cents, options[-1]),
            f"asked for a deductible of ${options[-1] // 100:,} at the next renewal",
            link=("risk", 0),
        )


def pro_bono(run: AutoRun) -> None:
    from ptk.sim.matters.actions import SetProBonoCredit

    firm = run.state.player
    b = run.balance
    ym = turn_to_ym(run.state.turn, run.state.save_meta.start_ym)
    if ym[1] != b.automation.pro_bono_month or run.state.turn - firm.founded_turn < MONTHS:
        return  # once a year, and only on a year of the moving average
    hours = firm.pro_bono_avg_tenths * MONTHS / TENTHS  # a lawyer's pro bono hours a year
    target = run.rail("target_hours")
    tol = target * run.rail("tolerance_pct") / 100
    credit = (
        b.pro_bono.credit_hours
        if firm.pro_bono_credit_hours is None
        else firm.pro_bono_credit_hours
    )
    step = run.noisy(run.rail("step_hours"))
    if hours < target - tol:
        new = min(b.pro_bono.credit_max_hours, credit + step)
    elif hours > target + tol:
        new = max(0, credit - step)
    else:
        return
    if new == credit:
        return
    run.attempt(
        SetProBonoCredit(run.owner.person_id, new),
        f"set the pro bono credit at {new} hours a year ({hours:.0f} done a lawyer)",
        mistake=not run.right,
        link=("finance", 0),
    )


def events(run: AutoRun) -> None:
    """Routine events are answered in phase 1 (`ptk.sim.automation.events`)."""


RULES: Final[dict[str, Callable[[AutoRun], None]]] = {
    "staffing": staffing,
    "intake": intake,
    "billing": billing,
    "pricing": pricing,
    "bd": bd,
    "hiring": hiring,
    "development": development,
    "laterals": laterals,
    "offices": offices,
    "knowledge": knowledge,
    "risk": risk,
    "pro_bono": pro_bono,
    "events": events,
}


def run_area(run: AutoRun) -> None:
    RULES[owners.area_def(run.balance, run.owner.area).rule](run)
