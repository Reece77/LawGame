"""The monthly client-account reconciliation (ADR PT-0003 7; spec 11.4; ADR PT-0017 5).

Each month a firm holding client money reconciles its client bank against what it owes its
clients. A shortfall comes from a posting error (`error_bp` x (1 - weight x the GC's effect))
or a partner's misuse (`misuse_bp` a partner at integrity 10 x exp(slope x (10 - integrity) /
10), x lax supervision; never a person flagged real) (stream `trust`). The shortfall is a share
of the money held for the client with the most on account.

A shortfall is always critical: the event `trust_shortfall` is queued, the firm replaces the
money from its own cash the same month (6320; the client book records the loss and its making
good, so the bank equals what is owed at every month end), a misuse is a disciplinary matter
for the partner (`discipline.open_case`, cause "trust") and the regulator may open an inquiry
(`inquiries`). The client book never mixes with the firm's: only the make-good's firm cash
moves in the firm's ledger.
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.billing.models import ClientBookEntry, ClientBookLine
from ptk.sim.data_models import Balance, GameData
from ptk.sim.ledger import CLIENT_BANK
from ptk.sim.risk import draws as dr
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import (
    TRUST_SHORTFALLS,
    Books,
    gc_effect,
    is_partner,
    lawyers,
    lax,
    with_risk,
)
from ptk.sim.risk.models import Reconciliation
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

SHORTFALL = "C1900_shortfall"  # the client book's claim on whoever took or lost the money
KEPT = 12  # tunable-exempt: reconciliations kept a firm (the screen's year)


def held_cents(state: GameState, firm_id: int) -> tuple[int, int | None]:
    """(money held for clients, the client with the most on account)."""
    funds = [f for f in state.billing.funds if f.firm_id == firm_id and f.owed_cents > 0]
    if not funds:
        return 0, None
    top = max(funds, key=lambda f: (f.owed_cents, -f.client_id))
    return sum(f.owed_cents for f in funds), top.client_id


def reconcile(
    state: GameState, rng: RngFactory, books: Books, balance: Balance, data: GameData
) -> tuple[GameState, tuple[ClientBookEntry, ...], Reconciliation | None]:
    cfg = balance.risk.trust
    owed, client = held_cents(state, books.firm_id)
    if owed <= 0 or client is None:
        return state, (), None
    gen = dr.trust_draws(rng, books.turn, books.firm_id)
    u_error, u_share = float(gen.random()), float(gen.random())
    cause, person_id = "", None
    if u_error < cfg.error_bp / fx.BP * fx.gc_mult(
        gc_effect(state, books.firm_id, balance, data), cfg.gc_bp
    ):
        cause = "error"
    else:
        mult = cfg.lax_mult if lax(state, books.firm_id) else 1.0
        for p in lawyers(state, books.firm_id, data):
            u = float(gen.random())
            if p.real or not is_partner(p):
                continue
            chance = (
                cfg.misuse_bp
                / fx.BP
                * fx.integrity_mult(p.personality["integrity"], cfg.integrity_slope)
                * mult
            )
            if u < chance:
                cause, person_id = "misuse", p.id
                break
    if not cause:
        rec = Reconciliation(
            turn=books.turn, firm_id=books.firm_id, bank_cents=owed, owed_cents=owed
        )
        return _keep(state, rec), (), rec
    funds = state.billing.funds_of(client, books.firm_id)
    amount = min(funds, max(cfg.min_cents, round(owed * fx.uniform(u_share, cfg.share))))
    book = (
        ClientBookEntry(
            turn=books.turn,
            firm_id=books.firm_id,
            memo=f"Client-account shortfall ({cause})",
            lines=(
                ClientBookLine(SHORTFALL, client, amount),
                ClientBookLine(CLIENT_BANK, client, -amount),
            ),
        ),
        ClientBookEntry(
            turn=books.turn,
            firm_id=books.firm_id,
            memo="Shortfall made good from firm money",
            lines=(
                ClientBookLine(CLIENT_BANK, client, amount),
                ClientBookLine(SHORTFALL, client, -amount),
            ),
        ),
    )
    books.pay(TRUST_SHORTFALLS, amount, "Client-account shortfall made good")
    rec = Reconciliation(
        turn=books.turn,
        firm_id=books.firm_id,
        bank_cents=owed - amount,
        owed_cents=owed,
        shortfall_cents=amount,
        cause=cause,  # type: ignore[arg-type]
        person_id=person_id,
        made_good_cents=amount,
    )
    books.inbox("trust_shortfall_found", None, amount_cents=amount, cause=cause)
    if books.firm_id == state.player.id:
        from ptk.sim.events.director import queue_engine_event

        state = queue_engine_event(state, "trust_shortfall", books.turn + 1, client_id=client)
    return _keep(state, rec), book, rec


def _keep(state: GameState, rec: Reconciliation) -> GameState:
    risk = state.risk
    mine = [r for r in risk.reconciliations if r.firm_id == rec.firm_id][-(KEPT - 1) :]
    rest = [r for r in risk.reconciliations if r.firm_id != rec.firm_id]
    rows = sorted([*rest, *mine, rec], key=lambda r: (r.firm_id, r.turn))
    return with_risk(state, replace(risk, reconciliations=tuple(rows)))
