"""Malpractice claims (spec 11.3, 7.6; ADR PT-0017 2).

- **Making.** Each escaped error on the player's matters (`progress.py` records them; read here
  as the month's rise in a matter's `errors_escaped`) becomes a latent claim with chance
  `risk.claims.from_error_bp` x the GC's term (a client with a claim open or on its way makes
  no second one: it sues once) x lax supervision x conflict checks off; a lost
  case with stakes of at least `grievance_min_stakes_cents` brings an aggrieved client's claim
  with chance `grievance_bp` (stream `risk_claim`). A latent claim draws a delay before it
  surfaces, a hidden merit (Beta) and size, and the demand the claimant will make. **Nothing
  else makes a claim** (the property test).
- **Stages** (stream `risk_case`, a generator a claim a month): notice (the policy in force
  answers it, claims-made), investigation (the claimant may drop it, more likely on weak
  merit), defence (filed in court: public above `public_min_cents`, which costs reputation in
  the practice; the claimant may offer to settle), trial (the claimant wins with chance
  merit and is awarded the size). An offer waits `offer_window` months for the firm's answer
  (`RespondClaim`), then the default rule settles when the offer is at most the firm's own
  reading (the merit range's middle x the demand).
- **Money.** Defence costs each month and the indemnity at the end are split by the policy
  (`formulas.split_payment`): the firm pays within the deductible and above the limit (6310);
  the insurer pays the rest. When the firm's cash cannot cover its part, the partners pay in
  capital for the gap (`common.capital_call`).
"""

from __future__ import annotations

from dataclasses import replace

from ptk.sim.data_models import Balance, GameData
from ptk.sim.matters.models import Matter
from ptk.sim.risk import draws as dr
from ptk.sim.risk import formulas as fx
from ptk.sim.risk.common import CLAIMS, Books, blame, capital_call, gc_effect, lax, with_risk
from ptk.sim.risk.models import Claim, ClaimChoice, RiskState, take_id, with_claim
from ptk.sim.rng import RngFactory
from ptk.sim.state import GameState

CASE_KINDS = frozenset({"case", "investigation"})
U_EVENT, U_STAGE, U_OFFER, U_TRIAL, U_RANGE = range(5)
DRAWS = 5


def _size(m: Matter, gen_u: float, cfg: Balance) -> int:
    c = cfg.risk.claims
    if m.kind in CASE_KINDS and m.stakes_cents > 0:
        raw = m.stakes_cents * fx.log_uniform(gen_u, c.size_stakes_share)
    else:
        raw = m.expected_fees_cents * fx.log_uniform(gen_u, c.size_fee_mult)
    return max(c.size_min_cents, min(c.size_max_cents, round(raw)))


def conversion(state: GameState, firm_id: int, balance: Balance, data: GameData) -> float:
    """The chance an escaped error becomes a claim this month (engine-only)."""
    c = balance.risk.claims
    p = c.from_error_bp / fx.BP * fx.gc_mult(gc_effect(state, firm_id, balance, data), c.gc_bp)
    if lax(state, firm_id):
        p *= c.lax_mult
    if not state.firm(firm_id).conflict_checks:
        p *= c.checks_off_mult
    return min(1.0, p)


def _latent(
    risk: RiskState,
    state: GameState,
    m: Matter,
    source: str,
    gen_draws: list[float],
    merit: float,
    balance: Balance,
) -> RiskState:
    c = balance.risk.claims
    risk, cid = take_id(risk)
    size = _size(m, gen_draws[0], balance)
    claim = Claim(
        id=cid,
        firm_id=m.firm_id,
        matter_id=m.id,
        client_id=m.client_id,
        practice=m.practice,
        source="error" if source == "error" else "grievance",
        created_turn=state.turn,
        surfaces_turn=state.turn + fx.span(gen_draws[1], c.delay_months),
        merit=merit,
        size_cents=size,
        demand_cents=round(size * fx.uniform(gen_draws[2], c.demand_mult)),
        blamed_id=blame(state, m.id),
    )
    return with_claim(risk, claim)


def make_claims(
    start: GameState, state: GameState, rng: RngFactory, balance: Balance, data: GameData
) -> GameState:
    """The month's new latent claims from the player's escaped errors and lost cases."""
    c = balance.risk.claims
    firm_id = state.player.id
    before = {m.id: m for m in start.market.matters if m.firm_id == firm_id}
    risk = state.risk
    p_error = None
    a, b = c.merit
    def suing() -> set[int]:  # clients with a claim open or on its way: they sue once
        return {c.client_id for c in risk.claims if c.stage != "closed" and c.firm_id == firm_id}

    claimed = suing()
    for m in state.market.matters:
        if m.firm_id != firm_id or m.client_id in claimed:
            continue
        old = before.get(m.id)
        for k in range(old.errors_escaped if old is not None else 0, m.errors_escaped):
            if p_error is None:
                p_error = conversion(state, firm_id, balance, data)
            gen = dr.claim_draws(rng, state.turn, dr.ERROR, m.id, k)
            if float(gen.random()) >= p_error:
                continue
            u = [float(x) for x in gen.random(3)]
            risk = _latent(risk, state, m, "error", u, float(gen.beta(a, b)), balance)
            break  # later escapes this month join the same claim
        claimed = suing()
        if m.client_id in claimed:
            continue
        lost_now = m.outcome == "lost" and (old is None or old.outcome != "lost")
        if lost_now and m.kind in CASE_KINDS and m.stakes_cents >= c.grievance_min_stakes_cents:
            gen = dr.claim_draws(rng, state.turn, dr.GRIEVANCE, m.id)
            if float(gen.random()) >= c.grievance_bp / fx.BP:
                continue
            u = [float(x) for x in gen.random(3)]
            risk = _latent(risk, state, m, "grievance", u, float(gen.beta(a, b)), balance)
    return with_risk(state, risk)


# --- The monthly stages ------------------------------------------------------------------


def _pay(
    state: GameState, claim: Claim, amount: int, books: Books, what: str
) -> tuple[GameState, Claim]:
    """Pay `amount` on a claim: the policy's split, the firm's part from cash (a capital call
    for what the cash cannot cover)."""
    s = fx.split_payment(
        amount,
        claim.deductible_cents - claim.deductible_paid_cents,
        claim.limit_cents - claim.insurer_paid_cents,
    )
    called = 0
    if s.firm > books.cash:
        state, called = capital_call(
            state, books, s.firm - max(0, books.cash), f"Capital call: claim {claim.id}"
        )
        if called:
            books.inbox("claim_capital_call", claim.id, amount_cents=called)
    books.pay(CLAIMS, s.firm, f"Claim {claim.id}: {what}")
    claim = replace(
        claim,
        deductible_paid_cents=claim.deductible_paid_cents + s.deductible,
        insurer_paid_cents=claim.insurer_paid_cents + s.insurer,
        excess_paid_cents=claim.excess_paid_cents + s.excess,
        called_cents=claim.called_cents + called,
    )
    return state, claim


def defence_month_cents(claim: Claim, balance: Balance) -> int:
    c = balance.risk.claims
    return max(
        c.defence_min_cents, min(c.defence_max_cents, claim.demand_cents * c.defence_bp // fx.BP)
    )


def _defend(
    state: GameState, claim: Claim, books: Books, balance: Balance, mult: float = 1.0
) -> tuple[GameState, Claim]:
    cost = round(defence_month_cents(claim, balance) * mult)
    state, claim = _pay(state, claim, cost, books, "defence costs")
    return state, replace(claim, defence_cents=claim.defence_cents + cost)


def close_claim(
    state: GameState, claim: Claim, outcome: str, indemnity: int, books: Books
) -> tuple[GameState, Claim]:
    state, claim = _pay(state, claim, indemnity, books, outcome)
    claim = replace(
        claim,
        stage="closed",
        stage_until=None,
        outcome=outcome,  # type: ignore[arg-type]
        indemnity_cents=claim.indemnity_cents + indemnity,
        offer_cents=0,
        offer_expires=None,
        closed_turn=books.turn,
    )
    books.inbox(
        "claim_closed",
        claim.id,
        outcome=outcome,
        indemnity_cents=claim.indemnity_cents,
        firm_cents=claim.firm_paid_cents,
        insurer_cents=claim.insurer_paid_cents,
    )
    return state, claim


def _notice(
    state: GameState, claim: Claim, u: list[float], books: Books, balance: Balance, data: GameData
) -> tuple[GameState, Claim]:
    from ptk.sim.interfaces import bump_relationship

    c = balance.risk.claims
    policy = state.risk.policy(claim.firm_id, books.turn)
    width = max(
        0.05,
        c.merit_width - c.merit_width_gc * max(0.0, gc_effect(state, claim.firm_id, balance, data)),
    )
    lo, hi = fx.merit_range(claim.merit, width, u[U_RANGE])
    claim = replace(
        claim,
        stage="notice",
        noticed_turn=books.turn,
        stage_until=books.turn + fx.span(u[U_STAGE], c.stages.notice),
        merit_lo=lo,
        merit_hi=hi,
        policy_id=None if policy is None else policy.id,
        deductible_cents=0 if policy is None else policy.deductible_cents,
        limit_cents=0 if policy is None else policy.limit_cents,
    )
    state = bump_relationship(state, claim.client_id, claim.firm_id, c.relationship_points)
    books.inbox(
        "claim_notice", claim.id, demand_cents=claim.demand_cents, limit_cents=claim.limit_cents
    )
    if claim.demand_cents > claim.limit_cents and claim.firm_id == state.player.id:
        from ptk.sim.events.director import queue_engine_event

        state = queue_engine_event(
            state,
            "malpractice_claim",
            books.turn + 1,
            client_id=claim.client_id,
            matter_id=claim.matter_id,
            practice=claim.practice,
        )
    return state, claim


def default_answer(claim: Claim) -> ClaimChoice:
    """The default rule (and an unanswered offer): settle when the offer is at most the
    firm's own reading of the claim, the merit range's middle x the demand."""
    view = (claim.merit_lo + claim.merit_hi) / 2 * claim.demand_cents
    return "settle" if claim.offer_cents <= view else "contest"


def answer_offer(
    state: GameState, claim: Claim, choice: ClaimChoice, books: Books
) -> tuple[GameState, Claim]:
    if choice == "settle":
        return close_claim(state, claim, "settled", claim.offer_cents, books)
    claim = replace(claim, stage="defence", offer_cents=0, offer_expires=None, contested=True)
    books.inbox("claim_contested", claim.id)
    return state, claim


def claim_month(
    state: GameState, claim: Claim, rng: RngFactory, books: Books, balance: Balance, data: GameData
) -> tuple[GameState, Claim]:
    """One month of one claim."""
    from ptk.sim.reputation.formulas import apply_pulse

    c = balance.risk.claims
    turn = books.turn
    if claim.stage == "latent":
        if turn < claim.surfaces_turn:
            return state, claim
        u = [float(x) for x in dr.claim_month(rng, turn, claim.id).random(DRAWS)]
        return _notice(state, claim, u, books, balance, data)
    u = [float(x) for x in dr.claim_month(rng, turn, claim.id).random(DRAWS)]
    due = claim.stage_until is not None and turn >= claim.stage_until
    if claim.stage == "notice":
        if due:
            claim = replace(
                claim,
                stage="investigation",
                stage_until=turn + fx.span(u[U_STAGE], c.stages.investigation),
            )
        return state, claim
    if claim.stage == "investigation":
        state, claim = _defend(state, claim, books, balance)
        if u[U_EVENT] < c.drop_bp / fx.BP * (1.0 - claim.merit):
            return close_claim(state, claim, "dropped", 0, books)
        if due:
            public = claim.demand_cents >= c.public_min_cents
            claim = replace(
                claim,
                stage="defence",
                stage_until=turn + fx.span(u[U_STAGE], c.stages.defence),
                public=public,
            )
            books.inbox("claim_filed", claim.id, demand_cents=claim.demand_cents)
            if public:
                state = apply_pulse(
                    state,
                    claim.firm_id,
                    c.public_points,
                    "a malpractice claim",
                    balance,
                    claim.practice,
                )
        return state, claim
    if claim.stage == "defence":
        state, claim = _defend(state, claim, books, balance)
        if due:
            return state, replace(
                claim, stage="trial", stage_until=turn + fx.span(u[U_STAGE], c.stages.trial)
            )
        if not claim.contested and u[U_EVENT] < c.offer_bp / fx.BP:
            offer = round(claim.merit * claim.size_cents * fx.uniform(u[U_OFFER], c.offer_share))
            claim = replace(
                claim, stage="offer", offer_cents=max(1, offer), offer_expires=turn + c.offer_window
            )
            books.inbox("claim_offer", claim.id, offer_cents=claim.offer_cents)
        return state, claim
    if claim.stage == "offer":
        state, claim = _defend(state, claim, books, balance)
        if claim.offer_expires is not None and turn >= claim.offer_expires:
            return answer_offer(state, claim, default_answer(claim), books)
        return state, claim
    if claim.stage == "trial":
        state, claim = _defend(state, claim, books, balance, c.trial_cost_mult)
        if due:
            if u[U_TRIAL] < claim.merit:
                return close_claim(state, claim, "lost", claim.size_cents, books)
            return close_claim(state, claim, "won", 0, books)
        return state, claim
    return state, claim


def claims_month(
    state: GameState, rng: RngFactory, books: Books, balance: Balance, data: GameData
) -> GameState:
    for claim in [
        x for x in state.risk.claims if x.firm_id == books.firm_id and x.stage != "closed"
    ]:
        state, claim = claim_month(state, claim, rng, books, balance, data)
        state = with_risk(state, with_claim(state.risk, claim))
    return state
