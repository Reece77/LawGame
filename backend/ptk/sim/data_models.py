"""Pydantic schemas for balance and seed data (ADR-0008). Invalid data fails at load."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

type AccountType = Literal["asset", "liability", "equity", "income", "expense"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Account(_Strict):
    code: str
    name: str
    type: AccountType
    book: Literal["firm", "client"] = "firm"

    @model_validator(mode="after")
    def _code_matches_book(self) -> Account:
        if (self.book == "client") != self.code.startswith("C"):
            raise ValueError(f"account {self.code}: client-book codes start with C, others not")
        return self


class Scenario(_Strict):
    id: str
    name: str
    description: str
    available: bool = True
    start_ym: tuple[int, int] = (2005, 1)  # ADR PT-0002: turn 0
    home_city: str
    partners_capital_cents: int = Field(ge=0)  # founders' capital paid in at turn 0
    revolver_limit_cents: int = Field(ge=0)  # used from PT-M4

    @field_validator("start_ym")
    @classmethod
    def _month(cls, value: tuple[int, int]) -> tuple[int, int]:
        if not 1 <= value[1] <= 12:  # tunable-exempt: months in a year
            raise ValueError("start month must be 1..12")
        return value


class Difficulty(_Strict):
    id: str
    name: str
    capital_mult_bp: int = Field(gt=0)


class CampaignBalance(_Strict):
    standard_turns: int = Field(gt=0)  # 360: January 2005 to December 2034


class BackupBalance(_Strict):
    every_turns: int = Field(gt=0)
    keep_periodic: int = Field(gt=0)


class Balance(_Strict):
    campaign: CampaignBalance
    backups: BackupBalance


class GameData(_Strict):
    accounts: tuple[Account, ...]
    scenarios: tuple[Scenario, ...]
    difficulties: tuple[Difficulty, ...]

    @model_validator(mode="after")
    def _unique(self) -> GameData:
        for name, keys in (
            ("account", [a.code for a in self.accounts]),
            ("scenario", [s.id for s in self.scenarios]),
            ("difficulty", [d.id for d in self.difficulties]),
        ):
            if len(keys) != len(set(keys)):
                raise ValueError(f"duplicate {name} keys")
        return self

    def scenario(self, scenario_id: str) -> Scenario | None:
        return next((s for s in self.scenarios if s.id == scenario_id), None)

    def difficulty(self, difficulty_id: str) -> Difficulty | None:
        return next((d for d in self.difficulties if d.id == difficulty_id), None)

    def account_types(self) -> dict[str, AccountType]:
        return {a.code: a.type for a in self.accounts}
