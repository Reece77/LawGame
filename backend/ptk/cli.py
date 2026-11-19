"""Headless commands: new-game, advance, inspect, people, hire, saves."""

from __future__ import annotations

from collections.abc import Callable

import typer

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.actions import Action
from ptk.sim.calendar import format_turn
from ptk.sim.errors import SimError
from ptk.sim.hiring.actions import (
    CloseSearch,
    Interview,
    MakeOffer,
    OpenSearch,
    ReferenceCheck,
    Scout,
    SetPayPolicy,
    WithdrawOffer,
)
from ptk.sim.ledger import CASH
from ptk.sim.money import cents, format_money
from ptk.sim.people.founder import FounderSpec

app = typer.Typer(no_args_is_help=True, add_completion=False)
hire_app = typer.Typer(no_args_is_help=True, help="Recruitment: searches, interviews, offers, pay")
app.add_typer(hire_app, name="hire")


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
    from ptk.api.recruitment import payroll_view

    payroll = payroll_view(state, loader.game_data(), loader.balance())
    typer.echo(
        f"Payroll: {format_money(payroll.total_cents)} this month for {payroll.headcount} people"
    )


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


def _act(save: str, make: Callable[[int], Action]) -> None:
    """Run one action as the player's founding partner, then print the recruitment view."""
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    founder = next(p.id for p in state.people if p.is_founder)
    try:
        saves.run_action(path, make(founder), loader.balance(), loader.game_data())
    except SimError as exc:
        typer.echo(f"error ({exc.code}): {exc.message}", err=True)
        raise typer.Exit(1) from exc
    _print_hiring(save)


def _print_hiring(save: str) -> None:
    from ptk.api.recruitment import recruitment_view

    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    view = recruitment_view(state, loader.game_data(), loader.balance())
    campus = view.campus
    typer.echo(f"{view.date_label}: energy {view.energy}/{view.energy_per_month}")
    typer.echo(
        f"Campus: registration {campus.registration_label}"
        f" ({'open' if campus.registration_open else 'closed'}), summer {campus.summer_label},"
        f" offers {campus.offer_label}, start {campus.start_label}; registered:"
        f" {', '.join(campus.registered_roles) or 'none'}; signed {len(campus.signed)}"
    )
    for s in view.searches:
        typer.echo(
            f"search {s.id}\t{s.channel_label}\t{s.role_label}\t{s.status}"
            f"\t{s.open_candidates} open"
        )
    for c in view.candidates:
        flag = "interviewed" if c.interviewed else "-"
        typer.echo(
            f"candidate {c.id}\t{c.name}\t{c.level}\t{c.school_tier or ''}"
            f"\tCA {c.ability.lo}-{c.ability.hi}\t{c.potential}\task {format_money(c.ask_cents)}"
            f"\t{flag}\tuntil {c.expires_label}"
        )
    for o in view.offers:
        typer.echo(f"offer {o.id}\t{o.name}\t{format_money(o.salary_cents)}\t{o.status}")
    for signed in campus.signed:
        typer.echo(f"signed\t{signed.name}\tstarts {signed.start_label}")


@hire_app.command("list")
def hire_list(save: str = typer.Option(...)) -> None:
    """Searches, candidates (revealed ranges only), offers, the campus season and energy."""
    _print_hiring(save)


@hire_app.command("search")
def hire_search(
    save: str = typer.Option(...),
    role: str = typer.Option(..., help="roles.yaml key, e.g. corporate_ma"),
    channel: str = typer.Option(..., help="campus, recruiter, job_post or referral"),
    level: str | None = typer.Option(None, help="a lateral target level, e.g. associate_4"),
    tier: list[str] = typer.Option([], help="law school tier filter (repeat)"),  # noqa: B008
) -> None:
    _act(
        save,
        lambda a: OpenSearch(a, role, channel, level=level, school_tiers=tuple(tier)),  # type: ignore[arg-type]
    )


@hire_app.command("close")
def hire_close(save: str = typer.Option(...), search: int = typer.Option(...)) -> None:
    _act(save, lambda a: CloseSearch(a, search))


@hire_app.command("scout")
def hire_scout(save: str = typer.Option(...), search: int = typer.Option(...)) -> None:
    _act(save, lambda a: Scout(a, search))


@hire_app.command("interview")
def hire_interview(save: str = typer.Option(...), candidate: int = typer.Option(...)) -> None:
    _act(save, lambda a: Interview(a, candidate))


@hire_app.command("references")
def hire_references(save: str = typer.Option(...), candidate: int = typer.Option(...)) -> None:
    _act(save, lambda a: ReferenceCheck(a, candidate))


@hire_app.command("offer")
def hire_offer(
    save: str = typer.Option(...),
    candidate: int = typer.Option(...),
    salary: int = typer.Option(..., help="annual salary in whole dollars"),
) -> None:
    _act(save, lambda a: MakeOffer(a, candidate, cents(salary)))


@hire_app.command("withdraw")
def hire_withdraw(save: str = typer.Option(...), offer: int = typer.Option(...)) -> None:
    _act(save, lambda a: WithdrawOffer(a, offer))


@hire_app.command("pay")
def hire_pay(
    save: str = typer.Option(...),
    mode: str = typer.Option(..., help="match, lag or lead"),
    pct: int = typer.Option(100, help="percent of the market scale (lag < 100 < lead)"),
) -> None:
    """The firm's pay policy against the market scale (spec 5.4)."""
    _act(save, lambda a: SetPayPolicy(a, mode, pct * 100))  # type: ignore[arg-type]


@app.command("saves")
def list_cmd() -> None:
    for s in saves.list_saves(get_settings().resolved_save_dir()):
        typer.echo(f"{s.slug}\t{s.firm_name}\t{s.date_label}\t{s.game_state}")


if __name__ == "__main__":
    app()
