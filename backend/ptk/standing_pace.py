"""PT-M16's printed checks (the brief's sub-tasks 2 and 7): a scripted firm's climb in
reputation and its card, with the T3 and T4 readings, on seeds 1-10 to December 2015.

For each seed the steady strategy (the balance runner's script, read-only) plays 132 months;
each December records the firm's best practice, its reputation there, the market's top-decile
reputation in it (`reputation.card.top_quantile`) and its card. Read:

- **pace:** the first year the firm's reputation reaches the market's top decile in any
  practice (the brief: 8-12 years for a well-run firm);
- **card:** the highest share of the top card any practice reached in the first five years
  (acceptance: below the full card on every seed);
- **T3/T4:** lawyers, revenue and PEP in 2015, as `docs/balance-targets.md` measures them.

Not part of the sim (it plays games); `tools/reputation_pace.py` prints it and a nightly test
checks the card acceptance.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ptk.balance.game import start_game
from ptk.balance.report import SCENARIO
from ptk.balance.seats import fill_seats
from ptk.balance.seeds import SEEDS
from ptk.balance.strategies import PLAYABLE
from ptk.loader import load_balance, load_game_data
from ptk.sim.money import BP_DENOMINATOR

TURNS: Final = 132
FIRST_YEAR: Final = 2005
CARD_YEARS: Final = 5
DATA: Final = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True, slots=True)
class YearPoint:
    year: int
    practice: str
    reputation: float
    top: float  # the market's top-decile reputation there
    card_max_bp: int  # the firm's highest card share
    lawyers: int


@dataclass(frozen=True, slots=True)
class SeedPace:
    seed: int
    strategy: str
    game_state: str
    years: tuple[YearPoint, ...]
    lawyers_2015: int
    revenue_2015: int
    pep_2015: int | None

    @property
    def top_decile_year(self) -> int | None:
        return next((y.year for y in self.years if y.reputation >= y.top), None)

    @property
    def years_to_top(self) -> int | None:
        y = self.top_decile_year
        return None if y is None else y - FIRST_YEAR + 1

    @property
    def card_max_first_years(self) -> int:
        early = [y.card_max_bp for y in self.years if y.year < FIRST_YEAR + CARD_YEARS]
        return max(early, default=0)


def run_seed(seed: int, strategy: str = "steady", turns: int = TURNS) -> SeedPace:
    from ptk.sim.calendar import turn_to_ym
    from ptk.sim.reputation.formulas import market_quantile, player_lawyers

    data, balance = load_game_data(DATA), load_balance(DATA)
    game = start_game(data, balance, seed, SCENARIO, "standard")
    script = PLAYABLE[strategy]
    years: list[YearPoint] = []
    q = balance.reputation.card.top_quantile
    for _ in range(turns):
        if game.state.ended:
            break
        if strategy != "do_nothing":
            fill_seats(game)
        script(game)
        game.turn()
        state = game.state
        ym = turn_to_ym(state.turn - 1, state.save_meta.start_ym)
        if ym[1] == 12:  # tunable-exempt: December
            pid = state.player.id
            best = max(
                state.standing.reputation.of(pid),
                key=lambda e: (e.value - market_quantile(state, e.practice, q), e.practice),
            )
            card = max((bp for _, bp in state.player.rate_card), default=BP_DENOMINATOR)
            years.append(
                YearPoint(
                    year=ym[0],
                    practice=best.practice,
                    reputation=round(best.value, 1),
                    top=round(market_quantile(state, best.practice, q), 1),
                    card_max_bp=card,
                    lawyers=round(sum(player_lawyers(state, pid, data).values())),
                )
            )
    last = game.months[-1] if game.months else None
    dec = next((m for m in game.months if m.ym == (2015, 12)), last)  # tunable-exempt: T3's year
    revenue = sum(m.revenue_cents for m in game.months if m.ym[0] == 2015)  # tunable-exempt
    return SeedPace(
        seed=seed,
        strategy=strategy,
        game_state=game.state.save_meta.game_state,
        years=tuple(years),
        lawyers_2015=dec.lawyers if dec is not None else 0,
        revenue_2015=revenue,
        pep_2015=dec.pep_cents if dec is not None else None,
    )


def run_all(seeds: tuple[int, ...] = SEEDS, workers: int = 4) -> list[SeedPace]:  # PT-M18: 1-40
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(run_seed, seeds))
