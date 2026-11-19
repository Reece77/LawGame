"""Headless commands: new-game, advance, inspect, saves."""

from __future__ import annotations

import typer

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.calendar import format_turn
from ptk.sim.ledger import CASH
from ptk.sim.money import format_money
from ptk.sim.people.founder import FounderSpec

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("new-game")
def new_game_cmd(
    name: str = typer.Option(..., help="Save name (lower-case, digits, hyphens)"),
    firm: str = typer.Option("Founders LLP", help="The firm's name"),
    scenario: str = typer.Option("biglaw_spinout"),
    difficulty: str = typer.Option("standard"),
    seed: int | None = typer.Option(None, help="Master seed; random if omitted"),
    background: str | None = typer.Option(
        None, help="The founding partner's background (backgrounds.yaml); scenario default"
    ),
) -> None:
    state = saves.create_save(
        get_settings().resolved_save_dir(),
        name,
        firm_name=firm,
        scenario_id=scenario,
        difficulty=difficulty,
        data=loader.game_data(),
        balance=loader.balance(),
        seed=seed,
        founder=FounderSpec(background=background) if background else None,
    )
    typer.echo(f"Created {name}: {state.player.name}, {format_turn(0, state.save_meta.start_ym)}")


@app.command()
def advance(save: str = typer.Option(...), turns: int = typer.Option(1, min=1)) -> None:
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    result = None
    for _ in range(turns):
        state, _balances = saves.read_state(path)
        if state.ended:
            break
        result = saves.run_turn(path, loader.balance(), loader.game_data())
    state, _ = saves.read_state(path)
    typer.echo(
        f"{save}: now {format_turn(state.turn, state.save_meta.start_ym)}"
        f" ({state.save_meta.game_state})" + ("" if result else " (no turn played)")
    )


@app.command()
def inspect(save: str = typer.Option(...)) -> None:
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, balances = saves.read_state(path)
    firm = state.player
    typer.echo(f"{firm.name} ({state.save_meta.scenario_id}, {state.save_meta.difficulty})")
    typer.echo(f"Date: {format_turn(state.turn, state.save_meta.start_ym)}")
    typer.echo(f"Cash: {format_money(balances.get((firm.id, CASH), 0))}")
    typer.echo(f"State: {state.save_meta.game_state}")


@app.command()
def people(save: str = typer.Option(...)) -> None:
    """The firm's people as the firm sees them (revealed ranges only)."""
    from ptk.api.people import people_rows

    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    for row in people_rows(state, loader.game_data(), loader.balance()):
        strain = "" if row.strain is None else f"\tstrain {row.strain:.0f}"
        typer.echo(
            f"{row.id}\t{row.name}\t{row.level}\t{row.role_label}\tage {row.age}"
            f"\tCA {row.ability.lo}-{row.ability.hi}\t{row.potential}{strain}"
        )


@app.command("saves")
def list_cmd() -> None:
    for s in saves.list_saves(get_settings().resolved_save_dir()):
        typer.echo(f"{s.slug}\t{s.firm_name}\t{s.date_label}\t{s.game_state}")


if __name__ == "__main__":
    app()
