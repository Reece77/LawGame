"""PT-M14's balance variants (brief acceptance): steady with a technology strategy.

- `ai-hourly`: steady, and from 2016 the firm subscribes in full to every era's tools as each
  becomes available (generative AI from January 2023, agentic tools from 2025), keeps a
  training programme of `TRAINING_HOURS`, and puts each era's firm-wide rollout to the
  partners until it passes. It bills as it always has (hourly by the matter's terms).
- `ai-fixed`: the same, and from stage 3 it moves exposed work to fixed fees: a product for
  each matter kind of the practices it holds whose task mix is at least `EXPOSED_SHARE`
  exposed, priced at `PRICE_BP` of what the market expects the work to cost; each January it
  retires a product whose closed matters billed less than their hours at standard rates.
  Below stage 3
  (products open at 101 lawyers) it hires toward it (`GROW_TO`, while it has the work and
  the bank is quiet) as a firm planning products would; so does `ai-hourly`, so the two
  differ only in pricing.
- `never`: steady with the same growth push and no technology (the brief's "never adopts").
- `ai-untrained`: `ai-hourly` without the training programme (the learning reading).

Registered in `ptk.balance.strategies.VARIANTS` in one line (lane A owns the runner). The
scripts read only what the player can see and act through `Game.act`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from ptk.balance import moves as mv
from ptk.balance.game import Game
from ptk.sim.tech.actions import (
    InvestInEra,
    LaunchProduct,
    RetireProduct,
    RolloutEra,
    SetTrainingProgramme,
)

FROM_YEAR: Final = 2016  # the scripts adopt from this year (contract analysis, TAR's courts)
TRAINING_HOURS: Final = 40  # the programme, hours a lawyer a year (tech.training.full_hours)
EXPOSED_SHARE: Final = 0.5  # a kind whose exposed tasks are at least this share gets a product
PRICE_BP: Final = 10_000  # products at the market's expected cost
REVIEW_MATTERS: Final = 3  # closed matters before a product's P&L is judged
GROW_TO: Final = 110  # lawyers the scripts hire toward from FROM_YEAR (stage 3 opens at 101)
GROW_MONTHLY: Final = 2  # lateral associates a month while below GROW_TO
PUSH_UTILISATION: Final = 0.60  # ... while the firm has the work and the bank is quiet


def _steady(g: Game) -> None:
    from ptk.balance.strategies import steady  # strategies imports this module

    steady(g)


def _push(g: Game) -> None:
    from ptk.balance.strategies import _grow

    if (
        g.ym[0] >= FROM_YEAR
        and len(g.lawyers()) < GROW_TO
        and mv.utilisation(g) >= PUSH_UTILISATION
        and mv.bank_quiet(g)
    ):
        _grow(g, mv.practices_held(g), GROW_MONTHLY)


def _adopt(g: Game, training: int = TRAINING_HOURS) -> None:
    if g.ym[0] < FROM_YEAR:
        return
    firm = g.state.tech.firm(g.state.player.id)
    me = g.founder_id
    if (0 if firm is None else firm.training_hours) != training:
        g.act(SetTrainingProgramme(me, training))
    for era in g.data.legal_eras.eras:
        if g.ym < era.start:
            continue
        firm = g.state.tech.firm(g.state.player.id)
        mine = None if firm is None else firm.era(era.key)
        if mine is None or mine.subscription_bp < 10_000:
            g.act(InvestInEra(me, era.key, 10_000))
            mine = (g.state.tech.firm(g.state.player.id) or firm).era(era.key)  # type: ignore[union-attr]
        if mine is not None and not mine.rolled_out:
            g.act(RolloutEra(me, era.key))  # refused while the partners' last vote is recent


def _exposed_share(g: Game, kind: str) -> float:
    from ptk.sim.matters.formulas import kind_tasks

    mix = kind_tasks(g.data.market.kinds[kind])
    exposed = {t.key for t in g.data.market.tasks if t.ai_exposure >= g.balance.tech.exposed_min}
    return sum(w for t, w in mix.items() if t in exposed) / sum(mix.values())


def _review(g: Game) -> None:
    """Each January a product whose closed matters (at least `REVIEW_MATTERS`) billed less
    than their hours at standard rates is retired (the Technology screen's product P&L)."""
    firm = g.state.tech.firm(g.state.player.id)
    if firm is None or g.ym[1] != 1:
        return
    for p in firm.products:
        if not p.active:
            continue
        done = [
            e
            for e in g.state.billing.engagements
            if e.closed
            and e.model == "fixed"
            and e.opened_turn >= p.launched_turn
            and (m := g.state.market.matter(e.matter_id)) is not None
            and m.kind_key == p.kind_key
        ]
        if len(done) >= REVIEW_MATTERS and sum(e.billed_cents for e in done) < sum(
            e.standard_cents for e in done
        ):
            g.act(RetireProduct(g.founder_id, p.id))


def _products(g: Game) -> None:
    firm = g.state.tech.firm(g.state.player.id)
    if g.state.player.stage < g.balance.tech.products.stage or firm is None:
        return
    _review(g)
    firm = g.state.tech.firm(g.state.player.id)
    assert firm is not None
    have = {p.kind_key for p in firm.products}  # a retired kind is not relaunched
    for practice in mv.practices_held(g):
        for mk in g.data.practice(practice).matter_kinds:
            if mk.key in have or _exposed_share(g, mk.kind) < EXPOSED_SHARE:
                continue
            if g.act(LaunchProduct(g.founder_id, practice, mk.key, PRICE_BP)):
                have.add(mk.key)


def ai_hourly(g: Game) -> None:
    _steady(g)
    _push(g)
    _adopt(g)


def ai_untrained(g: Game) -> None:
    """`ai-hourly` with no training programme (the learning reading's control)."""
    _steady(g)
    _push(g)
    _adopt(g, training=0)


def ai_fixed(g: Game) -> None:
    _steady(g)
    _push(g)
    _adopt(g)
    _products(g)


def never(g: Game) -> None:
    _steady(g)
    _push(g)


TECH_VARIANTS: Final[dict[str, Callable[[Game], None]]] = {
    "ai-hourly": ai_hourly,
    "ai-fixed": ai_fixed,
    "never": never,
    "ai-untrained": ai_untrained,
}
