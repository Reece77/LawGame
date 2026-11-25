"""Automated areas in phase 2 (spec 9.4; TST formulas.md 40.2-40.3; ADR-0015).

Ported from backend/tst/sim/automation/run.py @ 80a38079 (Tech Startup Tycoon); changed:
Partner Track's actions and areas; one quality draw an area a month from stream
`auto_quality` (id 60) keyed (area index, firm id, slot): the brief's (area_index, firm_id) and
the slot, because practice groups share the staffing area (as PT-M8's `seat_act`). The owner
takes the default rule's answer with probability q = clamp(0.55 + 0.03 s, 0.6, 0.98) from the
TRUE score s, less `overload_per_energy` for each energy point their areas cost beyond
`owner_energy` (at least `overload_floor`); otherwise a noisy alternative within the
guardrails. The actions' own draws follow on the same generator.

Each decision goes through `AutoRun.attempt`: a spec 9.4 one-off, or a commitment at or above
the owner's per-decision limit, becomes a proposal; a commitment that would take the month past
the owner's monthly limit waits ("over this month's limit"); anything else is applied at once
through the same action functions the player uses, as the owner (the managing partner's own
partnership actions in the MP's name, the MP's energy left as it was). A firm with no owners
and no pending proposals is returned untouched (the brief's "nothing else moves").
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Final

import numpy as np

from ptk.sim.automation import limits, owners
from ptk.sim.automation.config import MP_ACTIONS
from ptk.sim.automation.models import (
    AreaDecision,
    AreaOwner,
    AutomationState,
    AutoProposal,
    DecisionKind,
)
from ptk.sim.data_models import Balance, GameData
from ptk.sim.errors import SimError
from ptk.sim.ledger import CASH, AccountCode, LedgerEntry, apply_entries
from ptk.sim.log import LogItem, inbox_item
from ptk.sim.money import Cents
from ptk.sim.org.seats import managing_partner
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState, with_person_states

STREAM: Final = "auto_quality"
BP: Final = 10_000  # tunable-exempt: basis points


def with_automation(state: GameState, auto: AutomationState) -> GameState:
    return replace(state, automation=auto)


def quality(score: float, b: Balance) -> float:
    """clamp(base + per_score x s, min, max) (TST 40.3, spec 9.4)."""
    q = b.automation.quality
    return max(q.min, min(q.max, q.base + q.per_score * score))


def overload(state: GameState, person_id: int, b: Balance) -> int:
    """Energy points the person's areas cost beyond their month's `owner_energy`."""
    cost = sum(
        owners.area_def(b, o.area).energy
        for o in state.automation.owners
        if o.person_id == person_id
    )
    return max(0, cost - b.automation.owner_energy)


def owner_quality(state: GameState, o: AreaOwner, b: Balance, data: GameData) -> float:
    q = quality(owners.true_area_score(state, o.area, o.person_id, b, data), b)
    extra = overload(state, o.person_id, b)
    if extra:
        q = max(b.automation.overload_floor, q - b.automation.overload_per_energy * extra)
    return q


def _apply(
    state: GameState,
    action: object,
    draws: Callable[[], np.random.Generator],
    rng: RngFactory,
    b: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> tuple[GameState, tuple[LedgerEntry, ...], tuple[LogItem, ...]]:
    """One action through its own system's apply function (as `ptk.sim.actions.apply_action`,
    with the area's draws instead of the player's `actions` stream)."""
    from ptk.sim.billing.actions import BILLING_ACTION_TYPES, apply_billing_action
    from ptk.sim.events.actions import EVENT_ACTION_TYPES, apply_event_action
    from ptk.sim.hiring.actions import apply_hiring
    from ptk.sim.matters.actions import MATTER_ACTION_TYPES, apply_matter_action
    from ptk.sim.org.actions import OrgAction, apply_org_action
    from ptk.sim.partnership.actions import PARTNERSHIP_ACTION_TYPES, apply_partnership_action
    from ptk.sim.rivals.actions import RIVAL_ACTION_TYPES, apply_rival_action

    t = type(action)
    a: object = action
    if type(a).__module__.endswith("org.actions"):
        out = apply_org_action(state, a, b, data)  # type: ignore[arg-type]
        _ = OrgAction
        return out.state, (), out.log_items
    if t in MATTER_ACTION_TYPES.values():
        m = apply_matter_action(state, a, draws, b, data)  # type: ignore[arg-type]
        return m.state, m.entries, m.log
    if t in BILLING_ACTION_TYPES.values():
        o = apply_billing_action(state, a, draws, b, rng=rng)  # type: ignore[arg-type]
        return o.state, o.entries, o.log
    if t in RIVAL_ACTION_TYPES.values():
        r = apply_rival_action(state, a, draws, b, data)  # type: ignore[arg-type]
        return r.state, r.entries, r.log
    if t in PARTNERSHIP_ACTION_TYPES.values():
        p = apply_partnership_action(state, a, rng, draws, b, data, balances)  # type: ignore[arg-type]
        return p.state, p.entries, p.log
    if t in EVENT_ACTION_TYPES.values():
        e = apply_event_action(state, a, b, data)  # type: ignore[arg-type]
        return e.state, e.entries, e.log
    from ptk.sim.risk.actions import RISK_ACTION_TYPES, apply_risk_action  # PT-M15

    if t in RISK_ACTION_TYPES.values():
        cash = balances.get((state.player.id, CASH), 0)
        k = apply_risk_action(state, a, b, data, cash)  # type: ignore[arg-type]
        return k.state, k.entries, k.log
    h = apply_hiring(state, a, draws, b, data, balances)  # type: ignore[arg-type]
    return h.state, h.entries, h.log


def payload_json(action: object) -> str:
    from ptk.sim.actions import action_payload

    return json.dumps(action_payload(action), sort_keys=True)  # type: ignore[arg-type]


@dataclass(slots=True)
class AutoRun:
    """One area's month for its owner: every action passes the one-off and limit tests."""

    state: GameState
    rng: RngFactory
    balance: Balance
    data: GameData
    balances: dict[tuple[int, AccountCode], Cents]
    owner: AreaOwner
    gen: np.random.Generator
    right: bool
    entries: list[LedgerEntry] = field(default_factory=list)
    logs: list[LogItem] = field(default_factory=list)
    lines: list[tuple[DecisionKind, str, str, int, str | None, int | None, int | None]] = field(
        default_factory=list
    )
    committed: int = 0
    over_budget: bool = False

    @property
    def firm_id(self) -> int:
        return self.owner.firm_id

    def rail(self, key: str) -> int:
        return owners.rail(self.owner.guardrails, self.owner.area, key, self.balance, self.data)

    def bounds(self, key: str) -> tuple[int, int]:
        for k, _l, _d, lo, hi in owners.guardrails(self.owner.area, self.balance, self.data):
            if k == key:
                return lo, hi
        raise KeyError(key)

    def noisy(self, value: int, key: str | None = None) -> int:
        """A mistake's noisy alternative: value x (1 +- mistake_noise), within the guardrail's
        bounds when it is one (the right rule returns value unchanged)."""
        if self.right:
            return value
        n = self.balance.automation.mistake_noise
        out = round(value * (1 + float(self.gen.uniform(-n, n))))
        if key is not None:
            lo, hi = self.bounds(key)
            out = max(lo, min(hi, out))
        return out

    def note(self, kind: DecisionKind, text: str) -> None:
        self.lines.append((kind, "", text, 0, None, None, None))

    def attempt(
        self,
        action: object,
        text: str,
        *,
        mistake: bool = False,
        link: tuple[str, int] | None = None,
        recommendation: str = "",
    ) -> bool:
        """Apply the action, or file it as a proposal, or let it wait: True when applied."""
        b, data = self.balance, self.data
        kind = str(getattr(action, "kind", ""))
        if limits.is_one_off(self.state, action, b):
            self.propose(action, 0, "it is a one-off", text, recommendation, link)
            return False
        cost = limits.commitment(self.state, action, b, data)
        if cost > 0 and cost >= self.owner.limit_cents:
            self.propose(action, cost, "it is at or above the limit", text, recommendation, link)
            return False
        if self.committed + cost > self.owner.monthly_cents:
            if not self.over_budget:
                self.note("over_budget", "over this month's limit: the rest waits")
                self.over_budget = True
            return False
        mp = managing_partner(self.state, self.firm_id)
        kept = None
        if kind in MP_ACTIONS and mp is not None:  # in the MP's name, the MP's energy kept
            kept = self.state.person_state(mp)
            self.state = with_person_states(
                self.state, [replace(kept, energy=b.automation.action_energy)]
            )
        gen = self.gen
        try:
            state, entries, logs = _apply(
                self.state, action, lambda: gen, self.rng, b, data, self.balances
            )
        except SimError:
            if kept is not None:
                self.state = with_person_states(self.state, [kept])
            return False
        if kept is not None:
            state = with_person_states(
                state, [replace(state.person_state(mp or 0), energy=kept.energy)]
            )
        self.state = state
        self.entries += entries
        self.balances = dict(apply_entries(self.balances, entries))
        self.logs += [replace(i, in_digest=True) for i in logs]
        self.committed += cost
        lk, lid = link if link is not None else (None, None)
        self.lines.append(("mistake" if mistake else "decision", kind, text, cost, lk, lid, None))
        return True

    def propose(
        self,
        action: object,
        cost: int,
        why: str,
        text: str,
        recommendation: str = "",
        link: tuple[str, int] | None = None,
    ) -> None:
        """TST 40.2: a proposal for the player, unless the same move is pending, or was
        declined or expired within `automation.repropose_months`."""
        b, state, o = self.balance, self.state, self.owner
        payload = payload_json(action)
        quiet = b.automation.repropose_months
        auto = state.automation
        for p in auto.proposals:
            if p.firm_id != o.firm_id or p.action_json != payload:
                continue
            if p.status == "pending" or (
                p.status in ("declined", "expired")
                and (p.resolved_turn if p.resolved_turn is not None else p.made_turn)
                > state.turn - quiet
            ):
                return
        pid = auto.next_proposal_id
        name = _name(state, o.person_id)
        plan = as_proposal(text)
        words = recommendation or f"I recommend we {plan}."
        proposal = AutoProposal(
            id=pid,
            firm_id=o.firm_id,
            area=o.area,
            slot=o.slot,
            person_id=o.person_id,
            made_turn=state.turn,
            expires_turn=state.turn + b.automation.proposal_months,
            action_json=payload,
            title=plan[:1].upper() + plan[1:],
            why=why,
            recommendation=words,
            commitment_cents=cost,
        )
        auto = replace(auto, proposals=(*auto.proposals, proposal), next_proposal_id=pid + 1)
        self.state = with_automation(state, auto)
        self.logs.append(
            inbox_item(
                state.turn,
                o.firm_id,
                "auto_proposal",
                link_kind="automation",
                link_id=pid,
                name=name,
                area=owners.area_def(b, o.area).label,
                what=plan,
                why=why,
                recommendation=words,
                commitment_cents=cost,
            )
        )
        lk, lid = link if link is not None else (None, None)
        self.lines.append(
            (
                "proposal",
                str(getattr(action, "kind", "")),
                f"proposed to {plan} ({why})",
                cost,
                lk,
                lid,
                pid,
            )
        )


# A rule's past-tense text ("opened a plan ...") as a proposal ("open a plan ...").
PRESENT: Final[dict[str, str]] = {
    "opened": "open",
    "wrote": "write",
    "repaid": "repay",
    "introduced": "introduce",
    "offered": "offer",
    "made": "make",
    "asked": "ask",
    "pitched": "pitch",
    "ran": "run",
    "turned": "turn",
    "registered": "register",
}


def as_proposal(text: str) -> str:
    first, _, rest = text.partition(" ")
    return f"{PRESENT.get(first, first)} {rest}".strip()


def _name(state: GameState, person_id: int) -> str:
    p = state.person(person_id)
    return f"{p.first_name} {p.last_name}"


# --- Phase 2 -----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AutoMonth:
    state: GameState
    entries: tuple[LedgerEntry, ...] = ()
    log: tuple[LogItem, ...] = ()
    decisions: tuple[AreaDecision, ...] = ()


def _gone(state: GameState, b: Balance, data: GameData) -> tuple[GameState, list[LogItem]]:
    """Owners who left or lost their seat: the area returns to the player (TST 40.1)."""
    logs: list[LogItem] = []
    auto = state.automation
    kept = []
    for o in auto.owners:
        if owners.may_own(state, o.firm_id, o.area, o.slot, o.person_id, b, data):
            kept.append(o)
            continue
        logs.append(
            inbox_item(
                state.turn,
                o.firm_id,
                "area_returned",
                link_kind="automation",
                link_id=0,
                name=_name(state, o.person_id),
                area=owners.area_def(b, o.area).label,
            )
        )
    if len(kept) == len(auto.owners):
        return state, logs
    return with_automation(state, replace(auto, owners=tuple(kept))), logs


def expire_proposals(state: GameState) -> tuple[GameState, list[LogItem]]:
    """Unanswered proposals lapse as declined ("expired") after proposal_months (TST 40.2)."""
    auto = state.automation
    logs: list[LogItem] = []
    out = []
    changed = False
    for p in auto.proposals:
        if p.status == "pending" and state.turn >= p.expires_turn:
            p = replace(p, status="expired", resolved_turn=state.turn)
            changed = True
            logs.append(
                inbox_item(
                    state.turn,
                    p.firm_id,
                    "auto_proposal_expired",
                    link_kind="automation",
                    link_id=p.id,
                    name=_name(state, p.person_id),
                    what=p.title,
                )
            )
        out.append(p)
    if not changed:
        return state, logs
    return with_automation(state, replace(auto, proposals=tuple(out))), logs


def area_gen(
    rng: RngFactory, turn: int, area_index: int, firm_id: int, slot: int
) -> np.random.Generator:
    """Stream `auto_quality` (60) keyed (area index, firm id, slot): the one call site."""
    return rng.stream(turn, "auto_quality", area_index, firm_id, slot)


def automation_month(
    state: GameState,
    rng: RngFactory,
    b: Balance,
    data: GameData,
    balances: Mapping[tuple[int, AccountCode], Cents],
) -> AutoMonth:
    """Phase 2: every owner runs their areas in priority order (the player's firm only)."""
    auto = state.automation
    if state.ended or (not auto.owners and not auto.pending(state.player.id)):
        return AutoMonth(state)
    from ptk.sim.automation.rules import run_area

    state, logs = _gone(state, b, data)
    state, expired = expire_proposals(state)
    logs += expired
    entries: list[LedgerEntry] = []
    current = dict(balances)
    lines: list[AreaDecision] = []
    seq = sum(1 for d in state.automation.decisions if d.turn == state.turn)
    by_person: dict[int, list[AreaOwner]] = {}
    for o in state.automation.owners:
        by_person.setdefault(o.person_id, []).append(o)
    for person_id in sorted(by_person):
        areas = sorted(
            by_person[person_id], key=lambda o: (o.priority, owners.area_index(b, o.area), o.slot)
        )
        saved = state.person_state(person_id)
        stretched = overload(state, person_id, b)
        for o in areas:
            index = owners.area_index(b, o.area)
            gen = area_gen(rng, state.turn, index, o.firm_id, o.slot)
            right = float(gen.random()) < owner_quality(state, o, b, data)
            state = with_person_states(
                state, [replace(state.person_state(person_id), energy=b.automation.action_energy)]
            )
            run = AutoRun(state, rng, b, data, current, o, gen, right)
            if stretched:
                run.note("stretched", "more areas than time: decisions suffer")
            run_area(run)
            state, current = run.state, run.balances
            entries += run.entries
            logs += run.logs
            for kind, action, text, cost, lk, lid, pid in run.lines:
                lines.append(
                    AreaDecision(
                        o.firm_id, state.turn, seq, o.area, o.slot, person_id, kind, action,
                        text, cost, lk, lid, pid,
                    )
                )  # fmt: skip
                seq += 1
        state = with_person_states(
            state, [replace(state.person_state(person_id), energy=saved.energy)]
        )
    state = remember(state, lines, b)
    return AutoMonth(state, tuple(entries), tuple(logs), tuple(lines))


def remember(state: GameState, new: list[AreaDecision], b: Balance) -> GameState:
    auto = state.automation
    keep_from = state.turn - b.automation.keep_decision_turns + 1
    kept = tuple(d for d in auto.decisions if d.turn >= keep_from)
    if not new and kept == auto.decisions:
        return state
    return with_automation(state, replace(auto, decisions=kept + tuple(new)))


def seat_masks(state: GameState, b: Balance) -> frozenset[tuple[str, int]]:
    """(seat, slot) of every seat whose PT-M8 monthly rule an automated area runs this month:
    the seats' own authority step skips them so the rule runs once (TST 40.12's one setting)."""
    out = set()
    for o in state.automation.owners:
        a = owners.area_def(b, o.area)
        if a.seat_rule and a.seat is not None:
            out.add((a.seat, o.slot))
    return frozenset(out)
