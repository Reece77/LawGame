"""FastAPI app. OpenAPI is the contract; the front end's client is generated (ADR-0009)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ptk import loader
from ptk.api import recruitment
from ptk.api.events import blocking_event_id, make_events_router
from ptk.api.finance import make_finance_router
from ptk.api.history import make_history_router
from ptk.api.market import make_market_router
from ptk.api.matters import make_matters_router
from ptk.api.org import make_org_router
from ptk.api.partnership import make_partnership_router
from ptk.api.people import make_router
from ptk.api.screens import make_screens_router
from ptk.config import get_settings
from ptk.db import saves
from ptk.holiday import REASON_TEXT, HolidayError, run_holiday
from ptk.sim.calendar import format_turn, ym_to_turn
from ptk.sim.errors import (
    BillingActionError,
    CampusSeasonError,
    ConflictError,
    CriticalEventOpenError,
    EventActionError,
    FamilyError,
    FounderLifeError,
    GameOverError,
    InsufficientCashError,
    InsufficientEnergyError,
    InterviewRequiredError,
    InvalidActionError,
    InvalidFounderError,
    InvalidSaveNameError,
    MatterActionError,
    NotFoundError,
    OfferExistsError,
    OverCapacityError,
    PartnershipError,
    SaveExistsError,
    SaveNotFoundError,
    SimError,
    StaffingError,
    SuccessionError,
    UnknownDifficultyError,
    UnknownScenarioError,
)
from ptk.sim.family.setup import FamilySpec
from ptk.sim.ledger import CASH
from ptk.sim.people.founder import FounderSpec

_STATUS: dict[type[SimError], int] = {
    HolidayError: 400,  # PT-M7a
    SaveNotFoundError: 404,
    NotFoundError: 404,
    InvalidFounderError: 400,
    SaveExistsError: 409,
    GameOverError: 409,
    InvalidSaveNameError: 400,
    UnknownScenarioError: 400,
    UnknownDifficultyError: 400,
    # PT-M1b: actions (ADR-0014, ADR-0016)
    InvalidActionError: 400,
    InsufficientEnergyError: 409,
    InsufficientCashError: 409,
    InterviewRequiredError: 409,
    OfferExistsError: 409,
    CampusSeasonError: 409,
    PartnershipError: 409,  # PT-M4: a partnership rule (votes, comp, capital, laterals)
    # PT-M3a: clients and matters
    ConflictError: 409,
    OverCapacityError: 409,
    StaffingError: 400,
    MatterActionError: 409,
    # PT-M6: events
    EventActionError: 409,
    CriticalEventOpenError: 409,
    # PT-M3b: billing
    BillingActionError: 409,
    # PT-M17: the founder's life, family and succession
    FounderLifeError: 409,
    FamilyError: 409,
    SuccessionError: 409,
}


class ErrorBody(BaseModel):
    code: str
    message: str


class ScenarioOut(BaseModel):
    id: str
    name: str
    description: str


class DifficultyOut(BaseModel):
    id: str
    name: str


class BackgroundOut(BaseModel):
    key: str
    label: str
    description: str


class MetaOut(BaseModel):
    scenarios: list[ScenarioOut]
    difficulties: list[DifficultyOut]
    backgrounds: list[BackgroundOut]  # the founding partner's (spec 2.1)


class SaveOut(BaseModel):
    slug: str
    name: str
    firm_name: str
    turn: int
    date_label: str
    game_state: str


class NewGameIn(BaseModel):
    slug: str = Field(min_length=1, max_length=63)
    firm_name: str = Field(min_length=1, max_length=120)
    scenario_id: str = "biglaw_spinout"
    difficulty: str = "standard"
    seed: int | None = Field(default=None, ge=0, le=2**64 - 1)
    background: str | None = None  # the founding partner's; None = the scenario's default
    founder_age: int | None = None  # PT-M17: the founding partner's age (founder.age_range)
    family: Literal["none", "partner", "children"] = "none"  # PT-M17 (TST 45.1)
    child_ages: list[int] = Field(default_factory=list)  # with "children": each child's age


class HolidayIn(BaseModel):
    """PT-M7a: Holiday (`months`) or continue until a month (`until_year`, `until_month`)."""

    months: int | None = None
    until_year: int | None = None
    until_month: int | None = Field(default=None, ge=1, le=12)


class HolidayOut(BaseModel):
    months_played: int
    reason: str
    reason_text: str
    from_label: str
    to_label: str
    max_months: int
    default_months: int


class GameOut(BaseModel):
    slug: str
    firm_name: str
    turn: int
    date_label: str
    cash_cents: int
    game_state: Literal["active", "campaign_complete", "dissolved", "election_lost"]
    turns_in_campaign: int
    blocking_event_id: int | None  # PT-M6: a critical event to answer before Continue


def _founder_spec(body: NewGameIn) -> FounderSpec | None:
    """The founding partner as chosen (PT-M17 adds the age); None: the scenario's default."""
    if body.background is None and body.founder_age is None:
        return None
    scenario = loader.game_data().scenario(body.scenario_id)
    background = body.background or (scenario.default_background if scenario else "")
    if body.founder_age is None:
        return FounderSpec(background=background)
    return FounderSpec(background=background, age=body.founder_age)


def _game(slug: str) -> GameOut:
    path = saves.open_save(get_settings().resolved_save_dir(), slug)
    state, balances = saves.read_state(path)
    firm = state.player
    return GameOut(
        slug=slug,
        firm_name=firm.name,
        turn=state.turn,
        date_label=format_turn(state.turn, state.save_meta.start_ym),
        cash_cents=balances.get((firm.id, CASH), 0),
        game_state=state.save_meta.game_state,
        turns_in_campaign=loader.balance().campaign.standard_turns,
        blocking_event_id=blocking_event_id(state),
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Partner Track", version="0.1.0")

    @app.exception_handler(SimError)
    async def _sim_error(_request: Request, exc: SimError) -> JSONResponse:
        status = next((s for cls, s in _STATUS.items() if isinstance(exc, cls)), 400)
        return JSONResponse(status_code=status, content={"code": exc.code, "message": exc.message})

    errors: dict[int | str, dict[str, Any]] = {
        400: {"model": ErrorBody},
        404: {"model": ErrorBody},
        409: {"model": ErrorBody},
    }

    @app.get("/api/meta", response_model=MetaOut, operation_id="getMeta")
    def get_meta() -> MetaOut:
        data = loader.game_data()
        return MetaOut(
            scenarios=[
                ScenarioOut(id=s.id, name=s.name, description=s.description)
                for s in data.scenarios
                if s.available
            ],
            difficulties=[DifficultyOut(id=d.id, name=d.name) for d in data.difficulties],
            backgrounds=[
                BackgroundOut(key=b.key, label=b.label, description=b.description)
                for b in data.backgrounds
                if b.selectable
            ],
        )

    @app.get("/api/saves", response_model=list[SaveOut], operation_id="listSaves")
    def list_saves() -> list[SaveOut]:
        return [
            SaveOut(
                slug=s.slug,
                name=s.name,
                firm_name=s.firm_name,
                turn=s.turn,
                date_label=s.date_label,
                game_state=s.game_state,
            )
            for s in saves.list_saves(get_settings().resolved_save_dir())
        ]

    @app.post("/api/saves", response_model=GameOut, responses=errors, operation_id="newGame")
    def new_game(body: NewGameIn) -> GameOut:
        saves.create_save(
            get_settings().resolved_save_dir(),
            body.slug,
            firm_name=body.firm_name,
            scenario_id=body.scenario_id,
            difficulty=body.difficulty,
            data=loader.game_data(),
            balance=loader.balance(),
            seed=body.seed,
            founder=_founder_spec(body),
            family=FamilySpec(body.family, tuple(body.child_ages))
            if body.family != "none"
            else None,
        )
        return _game(body.slug)

    @app.get(
        "/api/saves/{slug}/game", response_model=GameOut, responses=errors, operation_id="getGame"
    )
    def get_game(slug: str) -> GameOut:
        return _game(slug)

    @app.post(
        "/api/practice/{key}",
        response_model=GameOut,
        responses=errors,
        operation_id="createPracticeSave",
    )
    def create_practice(key: str) -> GameOut:
        """PT-M7: create a practice save (pt-2008: a 60-lawyer firm in June 2008); 404 for an
        unknown key, 409 if a save of that name exists."""
        from ptk.practice import PRACTICE_SAVES, create_practice_save

        if key not in PRACTICE_SAVES:
            raise NotFoundError(f"no practice save {key!r}")
        create_practice_save(
            get_settings().resolved_save_dir(), key, loader.game_data(), loader.balance()
        )
        return _game(key)

    @app.post(
        "/api/saves/{slug}/advance",
        response_model=GameOut,
        responses=errors,
        operation_id="advance",
    )
    def advance(slug: str) -> GameOut:
        path = saves.open_save(get_settings().resolved_save_dir(), slug)
        saves.run_turn(path, loader.balance(), loader.game_data())
        return _game(slug)

    @app.post(
        "/api/saves/{slug}/holiday",
        response_model=HolidayOut,
        responses=errors,
        operation_id="holiday",
    )
    def holiday(slug: str, body: HolidayIn) -> HolidayOut:
        """PT-M7a: one Continue a month until a stop reason (spec 4.2). 409 while a critical
        event waits; 400 for months or a date out of range."""
        path = saves.open_save(get_settings().resolved_save_dir(), slug)
        balance, data = loader.balance(), loader.game_data()
        until = None
        if body.until_year is not None and body.until_month is not None:
            start = saves.read_state(path)[0].save_meta.start_ym
            until = ym_to_turn(body.until_year, body.until_month, start)
        result = run_holiday(path, balance, data, months=body.months, until_turn=until)
        start = saves.read_state(path)[0].save_meta.start_ym
        return HolidayOut(
            months_played=result.months_played,
            reason=result.reason,
            reason_text=REASON_TEXT[result.reason],
            from_label=format_turn(result.start_turn, start),
            to_label=format_turn(result.end_turn, start),
            max_months=balance.holiday.max_months,
            default_months=balance.holiday.default_months,
        )

    app.include_router(make_router(errors))
    app.include_router(recruitment.make_router(errors))
    app.include_router(make_org_router(errors))
    app.include_router(make_matters_router(errors))
    app.include_router(make_events_router(errors))
    app.include_router(make_screens_router(errors))
    app.include_router(make_finance_router(errors))
    app.include_router(make_market_router(errors))  # PT-M5
    app.include_router(make_partnership_router(errors))
    app.include_router(make_history_router(errors))  # PT-M7
    return app


app = create_app()
