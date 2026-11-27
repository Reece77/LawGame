"""PT-M14's readings (the brief's acceptance criteria, printed for seeds 1-10).

For each seed: steady to December 2015 (all of PT-M14's scripts are steady until 2016), then
three branches to December 2030: `never`, `ai-hourly` and `ai-fixed` (`ptk/balance/tech.py`).
Prints PEP summed over 2026-2030, realisation, RFP results from 2023, lawyers, products and
clients' AI cuts; a fully adopted firm's saving on exposed tasks in 2030; and the learning
reading: from `ai-hourly`'s January 2030, three branches for 12 months (AI off, AI without
training, AI with training) and the growth in current ability of the juniors (associates in
years 1-3) present all year.

    uv run --project backend python tools/tech_readings.py --seeds 1-10 --jobs 4 > out.txt
"""

from __future__ import annotations

import argparse
import copy
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

JUNIORS = ("associate_1", "associate_2", "associate_3")
DECEMBER = 12


@dataclass
class Branch:
    name: str
    pep_2026_30: int
    peps: tuple[int, ...]
    realisation_bp: int
    rfp_won: int
    rfp_lost: int
    lawyers: int
    stage: int
    products: int
    ai_cut_cents: int
    dissolved: bool
    genai: float = 0.0  # the firm's generative-AI adoption at the end
    rolled_out: bool = False


@dataclass
class SeedResult:
    seed: int
    branches: tuple[Branch, ...]
    saving_full: float
    learn: tuple[float, float, float]  # growth: AI off, AI untrained, AI trained
    cohort: int


def _play(game, script, until: tuple[int, int], tally: dict[str, int]) -> None:  # type: ignore[no-untyped-def]
    from ptk.balance.seats import fill_seats

    while not game.state.ended and game.ym <= until:
        fill_seats(game)
        script(game)
        game.turn()
        if game.ym[0] >= 2023:
            for item in game.logs:
                if item.firm_id == 1 and item.kind in ("rfp_won", "rfp_lost"):
                    tally[item.kind] = tally.get(item.kind, 0) + 1


def _branch(name: str, game) -> Branch:  # type: ignore[no-untyped-def]
    decembers = [m for m in game.months if m.ym[1] == DECEMBER and 2026 <= m.ym[0] <= 2030]
    peps = tuple(m.pep_cents or 0 for m in decembers)
    late = [m for m in game.months if 2026 <= m.ym[0] <= 2030 and m.realisation_bp]
    real = round(sum(m.realisation_bp for m in late) / len(late)) if late else 0
    cut = sum(
        x.ai_cut_cents
        for x in game.state.billing.months
        if x.firm_id == 1
    )
    firm = game.state.tech.firm(1)
    return Branch(
        name=name,
        pep_2026_30=sum(peps),
        peps=peps,
        realisation_bp=real,
        rfp_won=game.notes.get("rfp_won", 0),
        rfp_lost=game.notes.get("rfp_lost", 0),
        lawyers=len(game.lawyers()),
        stage=game.state.player.stage,
        products=0 if firm is None else sum(1 for p in firm.products if p.active),
        ai_cut_cents=cut,
        dissolved=game.state.ended and game.state.save_meta.game_state != "campaign_complete",
        genai=0.0 if firm is None or firm.era("genai") is None else firm.era("genai").adoption,
        rolled_out=firm is not None and firm.era("genai") is not None and firm.era("genai").rolled_out,
    )


def _juniors(game) -> dict[int, float]:  # type: ignore[no-untyped-def]
    from ptk.sim.people.models import current_ability

    return {
        p.id: current_ability(p, game.data) for p in game.lawyers() if p.level in JUNIORS
    }


def run_seed(seed: int) -> SeedResult:
    from ptk.balance.game import start_game
    from ptk.balance.report import SCENARIO
    from ptk.balance.strategies import PLAYABLE
    from ptk.loader import load_balance, load_game_data
    from ptk.sim.tech import efficiency as ef

    data_dir = ROOT / "backend" / "data"
    data, balance = load_game_data(data_dir), load_balance(data_dir)
    base = start_game(data, balance, seed, SCENARIO, "standard")
    tally: dict[str, int] = {}
    _play(base, PLAYABLE["steady"], (2015, 12), tally)
    branches = []
    stash = None
    for name in ("never", "ai-hourly", "ai-fixed"):
        g = copy.deepcopy(base)
        t: dict[str, int] = {}
        script = PLAYABLE[name]
        if name == "ai-hourly":
            _play(g, script, (2029, 12), t)
            stash = copy.deepcopy(g)
        _play(g, script, (2030, 12), t)
        g.notes.update(t)
        branches.append(_branch(name, g))
    full = ef.full_efficiency(base.state, data, (2030, 12))
    exposed = [x.key for x in data.market.tasks if x.ai_exposure >= balance.tech.exposed_min]
    saving = 1 - sum(full[x] for x in exposed) / len(exposed)
    assert stash is not None
    start = _juniors(stash)
    learn = []
    for name in ("off", "ai-untrained", "ai-hourly"):
        g = copy.deepcopy(stash)
        if name == "off":
            g.state = replace(g.state, tech=type(g.state.tech)())
            script = PLAYABLE["never"]
        else:
            script = PLAYABLE[name]
        _play(g, script, (2030, 12), {})
        end = _juniors(g)
        both = [pid for pid in start if pid in end]
        learn.append((both, {pid: end[pid] - start[pid] for pid in both}))
    common = set(learn[0][0]) & set(learn[1][0]) & set(learn[2][0])
    growth = tuple(
        sum(d[pid] for pid in common) / len(common) if common else 0.0 for _, d in learn
    )
    return SeedResult(seed, tuple(branches), saving, growth, len(common))  # type: ignore[arg-type]


def run_c3(seed: int) -> tuple[int, Branch, Branch]:
    """Criterion 3 only: `ai-hourly` to December 2030, and `ai-fixed` forked from it at the
    first month the firm could launch a product (the two scripts are identical until then)."""
    from ptk.balance.game import start_game
    from ptk.balance.report import SCENARIO
    from ptk.balance.seats import fill_seats
    from ptk.balance.strategies import PLAYABLE
    from ptk.loader import load_balance, load_game_data

    data_dir = ROOT / "backend" / "data"
    data, balance = load_game_data(data_dir), load_balance(data_dir)
    g = start_game(data, balance, seed, SCENARIO, "standard")
    _play(g, PLAYABLE["steady"], (2015, 12), {})
    hourly, fixed = PLAYABLE["ai-hourly"], PLAYABLE["ai-fixed"]
    t: dict[str, int] = {}
    fork = None
    while not g.state.ended and g.ym <= (2030, 12):
        if fork is None and g.state.player.stage >= balance.tech.products.stage:
            fork = (copy.deepcopy(g), dict(t))
        fill_seats(g)
        hourly(g)
        g.turn()
        if g.ym[0] >= 2023:
            for item in g.logs:
                if item.firm_id == 1 and item.kind in ("rfp_won", "rfp_lost"):
                    t[item.kind] = t.get(item.kind, 0) + 1
    g.notes.update(t)
    h = _branch("ai-hourly", g)
    if fork is None:
        return seed, h, h
    f, ft = fork
    _play(f, fixed, (2030, 12), ft)
    f.notes.update(ft)
    return seed, h, _branch("ai-fixed", f)


def _seeds(text: str) -> list[int]:
    lo, _, hi = text.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="1-40")  # PT-M18: ptk.balance.seeds.SEEDS
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--criterion3", action="store_true", help="ai-hourly against ai-fixed only")
    parser.add_argument("--out", default="", help="criterion 3: a JSON-lines file of seeds read")
    args = parser.parse_args()
    seeds = _seeds(args.seeds)
    if args.criterion3:
        import json
        from dataclasses import asdict

        done: dict[int, tuple[Branch, Branch]] = {}
        out = Path(args.out) if args.out else None
        if out is not None and out.exists():  # resume: seeds already read are kept
            for line in out.read_text().splitlines():
                rec = json.loads(line)
                done[rec["seed"]] = (Branch(**rec["hourly"]), Branch(**rec["fixed"]))
        todo = [x for x in seeds if x not in done]
        with ProcessPoolExecutor(args.jobs) as pool:
            for seed, h, f in pool.map(run_c3, todo):
                done[seed] = (h, f)
                if out is not None:
                    with out.open("a") as fh:
                        rec = {"seed": seed, "hourly": asdict(h), "fixed": asdict(f)}
                        fh.write(json.dumps(rec) + "\n")
        rows = sorted((x, *done[x]) for x in seeds)
        print("Criterion 3: PEP 2026-2030 (sum of December PEP, $M), ai-hourly against ai-fixed")
        print("seed | ai-hourly PEP real lawyers | ai-fixed PEP real lawyers products | fixed>hourly")
        wins = 0
        for seed, h, f in rows:
            better = f.pep_2026_30 > h.pep_2026_30
            wins += better
            print(
                f"{seed:>4} | {h.pep_2026_30 / 1e8:6.2f} {h.realisation_bp / 100:5.1f}% {h.lawyers}"
                f" | {f.pep_2026_30 / 1e8:6.2f} {f.realisation_bp / 100:5.1f}% {f.lawyers} {f.products}"
                f" | {'yes' if better else 'no'}{' (dissolved)' if h.dissolved or f.dissolved else ''}"
            )
        print(f"ai-fixed beats ai-hourly on {wins} of {len(rows)} seeds")
        return
    with ProcessPoolExecutor(args.jobs) as pool:
        results = sorted(pool.map(run_seed, seeds), key=lambda r: r.seed)
    m = 1e8  # cents to $M
    print("PEP 2026-2030 (sum of December PEP, $M), realisation 2026-2030, RFPs from 2023")
    print("seed | never PEP real won/lost | ai-hourly PEP real won/lost | ai-fixed PEP real won/lost prod | fixed>hourly")
    wins = 0
    for r in results:
        n, h, f = r.branches
        better = f.pep_2026_30 > h.pep_2026_30
        wins += better
        print(
            f"{r.seed:>4} | {n.pep_2026_30 / m:6.2f} {n.realisation_bp / 100:5.1f}% {n.rfp_won}/{n.rfp_lost}"
            f" | {h.pep_2026_30 / m:6.2f} {h.realisation_bp / 100:5.1f}% {h.rfp_won}/{h.rfp_lost}"
            f" | {f.pep_2026_30 / m:6.2f} {f.realisation_bp / 100:5.1f}% {f.rfp_won}/{f.rfp_lost} {f.products}"
            f" | {'yes' if better else 'no'}"
        )
    print(f"ai-fixed beats ai-hourly on {wins} of {len(results)} seeds (target: at least 70% of them)")
    print()
    print("seed | lawyers 2030 never/hourly/fixed | stage | AI cuts 2030 never/hourly/fixed ($M, trailing months) | dissolved")
    for r in results:
        n, h, f = r.branches
        print(
            f"{r.seed:>4} | {n.lawyers}/{h.lawyers}/{f.lawyers} | {n.stage}/{h.stage}/{f.stage}"
            f" | {n.ai_cut_cents / m:.2f}/{h.ai_cut_cents / m:.2f}/{f.ai_cut_cents / m:.2f}"
            f" | {n.dissolved}/{h.dissolved}/{f.dissolved}"
            f" | genai adoption hourly/fixed {h.genai:.2f}/{f.genai:.2f}"
            f" rolled out {h.rolled_out}/{f.rolled_out}"
        )
    print()
    print("A fully adopted firm's exposed tasks (review, diligence, research, drafting), December 2030")
    for r in results:
        print(f"{r.seed:>4} | {100 * r.saving_full:.1f}% fewer hours (target 40-70%)")
    print()
    print("Learning: juniors' (years 1-3) growth in CA over 2030, from ai-hourly's January 2030")
    print("seed | cohort | AI off | AI, no training | AI, training | restored share")
    for r in results:
        off, untrained, trained = r.learn
        lost = off - untrained
        share = (trained - untrained) / lost if lost > 0 else float("nan")
        print(
            f"{r.seed:>4} | {r.cohort:>6} | {off:6.3f} | {untrained:15.3f} | {trained:12.3f}"
            f" | {share:.2f}"
        )


if __name__ == "__main__":
    main()
