"""FastAPI app. OpenAPI is the contract; the front end's client is generated (ADR-0009)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ptk import loader
from ptk.config import get_settings
from ptk.db import saves
from ptk.sim.calendar import format_turn
from ptk.sim.errors import (
    GameOverError,
    InvalidSaveNameError,
    SaveExistsError,
    SaveNotFoundError,
    SimError,
    UnknownDifficultyError,
    UnknownScenarioError,
)
from ptk.sim.ledger import CASH

_STATUS: dict[type[SimError], int] = {
    SaveNotFoundError: 404,
    SaveExistsError: 409,
    GameOverError: 409,
    InvalidSaveNameError: 400,
    UnknownScenarioError: 400,
    UnknownDifficultyError: 400,
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


class MetaOut(BaseModel):
    scenarios: list[ScenarioOut]
    difficulties: list[DifficultyOut]


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


class GameOut(BaseModel):
    slug: str
    firm_name: str
    turn: int
    date_label: str
    cash_cents: int
    game_state: Literal["active", "campaign_complete", "dissolved"]
    turns_in_campaign: int


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
        )
        return _game(body.slug)

    @app.get(
        "/api/saves/{slug}/game", response_model=GameOut, responses=errors, operation_id="getGame"
    )
    def get_game(slug: str) -> GameOut:
        return _game(slug)

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

    return app


app = create_app()
