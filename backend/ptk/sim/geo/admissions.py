"""Bar admissions (PT-M11; spec 11.1; bar_rules.yaml).

A lawyer may lead a matter only where they are admitted: the jurisdiction of the office whose
client it is (the home office: the scenario's home jurisdiction). In England and Wales a
solicitor (`ew`) may lead anything; a registered foreign lawyer (`ew_rfl`, a US lawyer in
London) only non-contentious work. A case in a court of another jurisdiction also needs its
lead admitted there, or admitted for that case alone (pro hac vice: a one-off fee to 6600,
where the jurisdiction offers it; none in England and Wales). Arbitration needs no admission.

Admission elsewhere comes by a bar exam (sat in the jurisdiction's exam months, the result
after `results_months`; stream `bar_exam`, 101, keyed (exam id,); its cost to 6200 and study
hours each month until the sitting), on motion after `motion_years` in practice where admitted
in a jurisdiction that counts, or by registering as a foreign lawyer in England and Wales.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Final

from ptk.sim.calendar import MONTHS_PER_YEAR, turn_to_ym
from ptk.sim.data_models import Balance, GameData
from ptk.sim.geo.cities import matter_office_id, office_jurisdiction, person_office_id
from ptk.sim.geo.models import AdmissionRecord, Exam, ProHacVice, with_admission
from ptk.sim.ledger import CASH, PROFESSIONAL_FEES, LedgerEntry, LedgerLine
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.matters.models import Matter
from ptk.sim.people.models import Person
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person

CONTENTIOUS: Final = frozenset({"case", "investigation"})
SOLICITOR: Final = "ew"
FOREIGN: Final = "ew_rfl"


def required_jurisdiction(state: GameState, matter: Matter, data: GameData) -> str:
    return office_jurisdiction(state, matter.firm_id, matter_office_id(state, matter), data)


def court_ok(person: Person, matter: Matter, data: GameData, base: str) -> bool:
    """The matter's court admits the person: admitted there, arbitration, or pro hac vice
    offered (granted at a fee when they lead)."""
    cj = data.geo.court_jurisdiction(matter.court)
    if cj is None or cj == base or cj in person.bar_admissions:
        return True
    rules = data.geo.rules(cj)
    return rules is not None and rules.pro_hac_vice_cents is not None


def admitted_for(person: Person, matter: Matter, jurisdiction: str, data: GameData) -> bool:
    """Admitted where the matter's office is (the RFL rule for non-contentious London work)."""
    if jurisdiction in person.bar_admissions:
        return True
    if jurisdiction == SOLICITOR and FOREIGN in person.bar_admissions:
        rules = data.geo.rules(SOLICITOR)
        return rules is not None and rules.foreign_lead and matter.kind not in CONTENTIOUS
    return False


def may_lead(state: GameState, person: Person, matter: Matter, data: GameData) -> bool:
    if not data.geo.jurisdictions:
        return True  # test data without bar rules
    base = required_jurisdiction(state, matter, data)
    if not admitted_for(person, matter, base, data):
        return False
    return court_ok(person, matter, data, base)


def lead_check(state: GameState, matter: Matter, data: GameData) -> Callable[[Person], bool]:
    """The staffing rule's filter for a matter's lead."""
    if not data.geo.jurisdictions:
        return lambda _p: True
    base = required_jurisdiction(state, matter, data)
    return lambda p: admitted_for(p, matter, base, data) and court_ok(p, matter, data, base)


def needs_pro_hac_vice(person: Person, matter: Matter, data: GameData, base: str) -> str | None:
    cj = data.geo.court_jurisdiction(matter.court)
    if cj is None or cj == base or cj in person.bar_admissions:
        return None
    return cj


def pro_hac_vice_month(
    state: GameState, data: GameData
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Phase 4, after staffing: each case led by someone not admitted in its court is admitted
    for it (once a lead and case), at the jurisdiction's fee to 6600."""
    if not data.geo.jurisdictions:
        return state, (), ()
    firm_id = state.player.id
    granted = {(g.matter_id, g.person_id) for g in state.geo.pro_hac_vice}
    new: list[ProHacVice] = []
    entries: list[LedgerEntry] = []
    for m in state.market.open_matters(firm_id):
        if m.lead_id is None or m.court is None or (m.id, m.lead_id) in granted:
            continue
        lead = state.person(m.lead_id)
        base = required_jurisdiction(state, m, data)
        cj = needs_pro_hac_vice(lead, m, data, base)
        if cj is None:
            continue
        rules = data.geo.rules(cj)
        if rules is None or rules.pro_hac_vice_cents is None:
            continue
        new.append(ProHacVice(m.id, lead.id, cj, state.turn))
        office = matter_office_id(state, m) or None
        if rules.pro_hac_vice_cents:
            entries.append(
                LedgerEntry(
                    turn=state.turn,
                    firm_id=firm_id,
                    memo=f"Pro hac vice: {m.name}",
                    lines=(
                        LedgerLine(PROFESSIONAL_FEES, rules.pro_hac_vice_cents, office_id=office),
                        LedgerLine(CASH, -rules.pro_hac_vice_cents, office_id=office),
                    ),
                )
            )
    if not new:
        return state, (), ()
    rows = tuple(sorted((*state.geo.pro_hac_vice, *new), key=lambda g: (g.matter_id, g.person_id)))
    return replace(state, geo=replace(state.geo, pro_hac_vice=rows)), tuple(entries), ()


# --- Admission elsewhere ------------------------------------------------------------------------


def years_admitted(state: GameState, person: Person, data: GameData) -> float:
    """Years in practice: from the person's qualification (their class year or birth estimate)."""
    rec = [r for r in state.geo.admissions if r.person_id == person.id]
    if rec:
        return (state.turn - min(r.turn for r in rec)) / MONTHS_PER_YEAR + _years_before(person)
    return _years_before(person)


def _years_before(person: Person) -> float:
    """A lawyer's years of practice at game start or hire, from their level (ADR PT-0006 1)."""
    level = person.level
    if level.startswith("associate_"):
        return float(int(level.rsplit("_", 1)[1]) - 1)
    return {
        "senior_associate": 8.0,
        "counsel": 9.0,
        "income_partner": 9.0,
        "equity_partner": 12.0,
    }.get(level, 0.0)  # tunable-exempt: the ladder's years (spec 5.2)


def next_sitting(turn: int, start: tuple[int, int], months: tuple[int, ...]) -> int:
    """The first turn after `turn` whose month is an exam month."""
    for k in range(1, MONTHS_PER_YEAR + 1):
        if turn_to_ym(turn + k, start)[1] in months:
            return turn + k
    return turn + MONTHS_PER_YEAR


def start_admission(
    state: GameState,
    person_id: int,
    jurisdiction: str,
    kind: str,
    data: GameData,
    balance: Balance,
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """Enter a lawyer for a bar exam or apply on motion; or register a foreign lawyer (at once).
    Raises ValueError where the rules do not allow it."""
    person = state.person(person_id)
    rules = data.geo.rules(jurisdiction)
    if rules is None:
        raise ValueError(f"no bar rules for {jurisdiction!r}")
    if jurisdiction in person.bar_admissions:
        raise ValueError(f"already admitted in {rules.label}")
    if any(e.person_id == person_id and e.jurisdiction == jurisdiction for e in state.geo.exams):
        raise ValueError("an admission is already in progress")
    firm_id = state.player.id
    office = person_office_id(state, firm_id, person) or None
    turn = state.turn
    adm = rules.admission
    if jurisdiction == FOREIGN:
        if not any(j.startswith("us_") for j in person.bar_admissions):
            raise ValueError("only a lawyer admitted in the US registers as a foreign lawyer")
        state = admit(state, person_id, jurisdiction, "rfl")
        cost = balance.geo.rfl_cost_cents
        return state, _fee(turn, firm_id, "Registration as a foreign lawyer", cost, office), ()
    if kind == "motion":
        if adm.motion_years is None:
            raise ValueError(f"{rules.label} does not admit on motion")
        if not set(adm.motion_from) & set(person.bar_admissions):
            raise ValueError(f"{rules.label} admits on motion only from {list(adm.motion_from)}")
        if years_admitted(state, person, data) < adm.motion_years:
            raise ValueError(f"motion needs {adm.motion_years} years in practice")
        result, cost = turn + adm.motion_months, adm.motion_cost_cents
    else:
        if not adm.exam:
            raise ValueError(f"{rules.label} has no exam")
        result = next_sitting(turn, state.save_meta.start_ym, adm.exam_months) + adm.results_months
        cost = adm.exam_cost_cents
    geo = state.geo
    exam = Exam(
        geo.next_exam_id,
        person_id,
        jurisdiction,
        "motion" if kind == "motion" else "exam",
        turn,
        result,
    )
    state = replace(state, geo=replace(geo, exams=(*geo.exams, exam), next_exam_id=exam.id + 1))
    memo = f"{'Admission on motion' if kind == 'motion' else 'Bar exam'}: {rules.label}"
    return state, _fee(turn, firm_id, memo, cost, office), ()


def _fee(
    turn: int, firm_id: int, memo: str, cost: int, office: int | None
) -> tuple[LedgerEntry, ...]:
    from ptk.sim.ledger import RECRUITING

    if cost <= 0:
        return ()
    return (
        LedgerEntry(
            turn=turn,
            firm_id=firm_id,
            memo=memo,
            lines=(
                LedgerLine(RECRUITING, cost, office_id=office),
                LedgerLine(CASH, -cost, office_id=office),
            ),
        ),
    )


def admit(state: GameState, person_id: int, jurisdiction: str, how: str) -> GameState:
    person = state.person(person_id)
    if jurisdiction in person.bar_admissions:
        return state
    bars = tuple(sorted({*person.bar_admissions, jurisdiction}))
    state = with_person(state, replace(person, bar_admissions=bars))
    record = AdmissionRecord(person_id, jurisdiction, state.turn, how)  # type: ignore[arg-type]
    return replace(state, geo=with_admission(state.geo, record))


def exams_month(
    state: GameState, rng: RngFactory, data: GameData
) -> tuple[GameState, tuple[LogItem, ...]]:
    """Phase 8: results due this month (a motion is granted; an exam passes by its draw)."""
    due = [e for e in state.geo.exams if e.result_turn <= state.turn]
    if not due:
        return state, ()
    logs: list[LogItem] = []
    staff = set(state.staff_ids(state.player.id))
    for exam in due:
        if exam.person_id not in staff:
            continue
        rules = data.geo.rules(exam.jurisdiction)
        assert rules is not None
        if exam.kind == "motion":
            passed = True
        else:
            u = float(rng.stream(state.turn, "bar_exam", exam.id).random())
            passed = u < rules.admission.pass_bp / 10_000  # tunable-exempt: bp
        if passed:
            state = admit(state, exam.person_id, exam.jurisdiction, exam.kind)
        person = state.person(exam.person_id)
        logs.append(
            inbox_item(
                state.turn,
                state.player.id,
                "bar_admitted" if passed else "bar_failed",
                link_kind="person",
                link_id=person.id,
                name=f"{person.first_name} {person.last_name}",
                jurisdiction=rules.label,
            )
        )
    left = tuple(e for e in state.geo.exams if e.result_turn > state.turn)
    return replace(state, geo=replace(state.geo, exams=left)), tuple(logs)


def studying(state: GameState, data: GameData) -> dict[int, int]:
    """Study hours a month (tenths) of those with an exam still to sit (non-billable)."""
    out: dict[int, int] = {}
    for e in state.geo.exams:
        if e.kind != "exam":
            continue
        rules = data.geo.rules(e.jurisdiction)
        if rules is not None:
            out[e.person_id] = out.get(e.person_id, 0) + rules.admission.study_hours * 10
    return out
