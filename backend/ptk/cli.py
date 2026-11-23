"""Headless commands: new-game, advance, inspect, people, hire, matters, staff, saves."""

from __future__ import annotations

from collections.abc import Callable

import typer

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.actions import Action
from ptk.sim.calendar import format_turn
from ptk.sim.errors import SimError
from ptk.sim.events.actions import ChooseEvent
from ptk.sim.events.effects import critical_open
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
from ptk.sim.matters.actions import (
    AssignToMatter,
    DefaultStaffing,
    RemoveFromMatter,
    SetMatterHours,
    SetMatterLead,
)
from ptk.sim.money import cents, format_money
from ptk.sim.people.founder import FounderSpec

app = typer.Typer(no_args_is_help=True, add_completion=False)
hire_app = typer.Typer(no_args_is_help=True, help="Recruitment: searches, interviews, offers, pay")
app.add_typer(hire_app, name="hire")
staff_app = typer.Typer(no_args_is_help=True, help="Named matters' teams (spec 7.5)")
app.add_typer(staff_app, name="staff")


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
def holiday(
    save: str = typer.Option(...),
    months: int = typer.Option(6, min=1),
    until: str | None = typer.Option(None, help="Continue until this month, YYYY-MM"),
) -> None:
    """PT-M7a: Holiday or continue until a month; stops for what needs you (spec 4.2)."""
    from ptk.holiday import REASON_TEXT, run_holiday
    from ptk.sim.calendar import ym_to_turn

    path = saves.open_save(get_settings().resolved_save_dir(), save)
    start = saves.read_state(path)[0].save_meta.start_ym
    until_turn = None
    if until is not None:
        year, month = (int(x) for x in until.split("-"))
        until_turn = ym_to_turn(year, month, start)
    result = run_holiday(
        path,
        loader.balance(),
        loader.game_data(),
        months=None if until_turn is not None else months,
        until_turn=until_turn,
    )
    typer.echo(
        f"{save}: {result.months_played} months, now {format_turn(result.end_turn, start)}; "
        f"stopped because {REASON_TEXT[result.reason]}"
    )


@app.command()
def advance(
    save: str = typer.Option(...),
    turns: int = typer.Option(1, min=1),
    answer_first: bool = typer.Option(
        False, help="Answer a waiting critical event with its first choice instead of stopping"
    ),
) -> None:
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    result = None
    for _ in range(turns):
        state, _balances = saves.read_state(path)
        if state.ended:
            break
        waiting = critical_open(state)
        if waiting and not answer_first:
            typer.echo(
                f"Stopped: answer the critical event {waiting[0].title!r} (id {waiting[0].id})"
            )
            break
        result = saves.run_turn(
            path, loader.balance(), loader.game_data(), answer_critical=answer_first
        )
    state, _ = saves.read_state(path)
    typer.echo(
        f"{save}: now {format_turn(state.turn, state.save_meta.start_ym)}"
        f" ({state.save_meta.game_state})" + ("" if result else " (no turn played)")
    )


@app.command()
def events(save: str = typer.Option(...)) -> None:
    """The month's open events and their choices (PT-M6)."""
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    from ptk.sim.events.describe import choice_texts

    for event in state.events.open_events(state.player.id):
        typer.echo(f"[{event.id}] {event.severity}: {event.title}")
        for choice in event.choices:
            effects = "; ".join(choice_texts(state, event, choice, loader.balance()))
            typer.echo(f"   {choice.key}. {choice.label} ({effects})")


@app.command()
def choose(
    save: str = typer.Option(...), event: int = typer.Option(...), choice: str = typer.Option(...)
) -> None:
    """Answer an open event (PT-M6)."""
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    try:
        saves.run_action(path, ChooseEvent(event, choice), loader.balance(), loader.game_data())
    except SimError as exc:
        typer.echo(f"error ({exc.code}): {exc.message}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Answered event {event} with {choice}")


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


# --- Matters and staffing (PT-M3a) ---------------------------------------------------------


def _print_matters(save: str, status: str) -> None:
    from ptk.api.matters import matters_view

    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    rows = matters_view(state, loader.game_data(), status)
    if not rows:
        typer.echo("no matters")
    for m in rows:
        lead = m.lead.name if m.lead else "-"
        offer = f"\toffer {format_money(m.settlement.offer_cents)}" if m.settlement else ""
        typer.echo(
            f"matter {m.id}\t{m.name}\t{m.status}{'/' + m.outcome if m.outcome else ''}"
            f"\t{m.phase or '-'} {m.progress_pct}%\tlead {lead}"
            f"\t{m.worked_hours:.0f}/{m.budget_hours:.0f}h\tWIP {format_money(m.wip_cents)}"
            f"\tdue {m.due_label}{offer}"
        )


@app.command()
def matters(
    save: str = typer.Option(...),
    status: str = typer.Option("open", help="open, conflicted, closed, declined or all"),
) -> None:
    """Named matters: phase, progress, lead, hours against budget, WIP at standard value."""
    _print_matters(save, status)


def _print_team(save: str, matter: int) -> None:
    from ptk.api.matters import matter_view

    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    view = matter_view(state, matter, loader.game_data(), loader.balance())
    typer.echo(f"{view.name}\t{view.status}\t{view.phase or '-'} {view.progress_pct}%")
    for t in view.team:
        typer.echo(
            f"  {t.person.id}\t{t.person.name}\t{t.role}\t{t.level}"
            f"\tplanned {t.planned_hours:.0f}h\tlast month {t.hours_last_month:.0f}h"
        )


def _staff(save: str, matter: int, make: Callable[[int], Action]) -> None:
    path = saves.open_save(get_settings().resolved_save_dir(), save)
    state, _ = saves.read_state(path)
    founder = next(p.id for p in state.people if p.is_founder)
    try:
        saves.run_action(path, make(founder), loader.balance(), loader.game_data())
    except SimError as exc:
        typer.echo(f"error ({exc.code}): {exc.message}", err=True)
        raise typer.Exit(1) from exc
    _print_team(save, matter)


@staff_app.command("show")
def staff_show(save: str = typer.Option(...), matter: int = typer.Option(...)) -> None:
    """A matter's team with planned and last month's hours."""
    _print_team(save, matter)


@staff_app.command("assign")
def staff_assign(
    save: str = typer.Option(...),
    matter: int = typer.Option(...),
    person: int = typer.Option(...),
    hours: int = typer.Option(..., help="planned hours a month"),
) -> None:
    """Add a person to a matter's team."""
    _staff(save, matter, lambda a: AssignToMatter(a, matter, person, hours))


@staff_app.command("hours")
def staff_hours(
    save: str = typer.Option(...),
    matter: int = typer.Option(...),
    person: int = typer.Option(...),
    hours: int = typer.Option(...),
) -> None:
    """Change a team member's planned hours a month."""
    _staff(save, matter, lambda a: SetMatterHours(a, matter, person, hours))


@staff_app.command("remove")
def staff_remove(
    save: str = typer.Option(...), matter: int = typer.Option(...), person: int = typer.Option(...)
) -> None:
    """Take a person off a matter (not the lead)."""
    _staff(save, matter, lambda a: RemoveFromMatter(a, matter, person))


@staff_app.command("lead")
def staff_lead(
    save: str = typer.Option(...), matter: int = typer.Option(...), person: int = typer.Option(...)
) -> None:
    """Make a partner the matter's lead."""
    _staff(save, matter, lambda a: SetMatterLead(a, matter, person))


@staff_app.command("default")
def staff_default(save: str = typer.Option(...), matter: int = typer.Option(...)) -> None:
    """Re-staff a matter by the default rule."""
    _staff(save, matter, lambda a: DefaultStaffing(a, matter))


@app.command("practice-save")
def practice_save_cmd(
    key: str = typer.Argument("pt-2008", help="The practice save (pt-2008, pt-2022)"),
    name: str | None = typer.Option(None, help="Save name; the practice save's key if omitted"),
    year: int | None = typer.Option(None, help="PT-M14: the practice save of a year (2008, 2022)"),
) -> None:
    """Create a practice save (PT-M7): pt-2008 is a 60-lawyer firm in June 2008; pt-2022
    (PT-M14) a 120-lawyer firm in December 2022."""
    from ptk.practice import PRACTICE_SAVES, create_practice_save

    if year is not None:
        key = f"pt-{year}"

    if key not in PRACTICE_SAVES:
        raise typer.BadParameter(f"choose from {sorted(PRACTICE_SAVES)}")
    path = create_practice_save(
        get_settings().resolved_save_dir(), key, loader.game_data(), loader.balance(), name
    )
    typer.echo(f"Created {path.name}: {PRACTICE_SAVES[key].label}")


@app.command("saves")
def list_cmd() -> None:
    for s in saves.list_saves(get_settings().resolved_save_dir()):
        typer.echo(f"{s.slug}\t{s.firm_name}\t{s.date_label}\t{s.game_state}")


if __name__ == "__main__":
    app()
