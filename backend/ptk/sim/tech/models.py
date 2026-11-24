"""The firm's technology (PT-M14; ADR PT-0011 3, 5, 6; spec 13): adoption by era, the training
programme and fixed-fee products. The player's firm only: rivals' adoption is the market's
(`legal_eras.yaml` `market`), which client expectations read.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class EraAdoption:
    """A firm's adoption of one era's tools (0-1) and what it pays for them."""

    era: str  # legal_eras.yaml key
    adoption: float = 0.0  # 0-1
    platform: bool = False  # the platform was bought (capex to 1500)
    platform_turn: int | None = None
    capex_left_cents: int = 0  # unamortised platform cost (1500), amortised to 6100
    amortise_cents: int = 0  # a month's amortisation
    subscription_bp: int = 0  # coverage: bp of the era's per-lawyer subscription paid
    rolled_out: bool = False  # a firm-wide rollout passed the partners' vote
    vote_turn: int | None = None  # the last rollout vote


@dataclass(frozen=True, slots=True)
class Product:
    """A fixed-price product for a matter kind (spec 13, 7.7; from stage 3): new matters of
    the kind are priced at `price_bp` of what the market expects the work to cost."""

    id: int
    kind_key: str  # practices.yaml matter_kinds key
    practice: str
    price_bp: int
    launched_turn: int
    retired_turn: int | None = None

    @property
    def active(self) -> bool:
        return self.retired_turn is None


@dataclass(frozen=True, slots=True)
class FirmTech:
    firm_id: int
    eras: tuple[EraAdoption, ...] = ()  # in legal_eras.yaml order, once touched
    training_hours: int = 0  # the programme: hours a lawyer a year (non-billable)
    products: tuple[Product, ...] = ()  # sorted by id
    next_product_id: int = 1

    def era(self, key: str) -> EraAdoption | None:
        for e in self.eras:
            if e.era == key:
                return e
        return None

    @property
    def idle(self) -> bool:
        """Nothing adopted, trained or offered: the hooks return exact no-ops."""
        return (
            not any(e.adoption > 0 for e in self.eras)
            and self.training_hours == 0
            and not any(p.active for p in self.products)
        )


@dataclass(frozen=True, slots=True)
class TechState:
    firms: tuple[FirmTech, ...] = ()  # sorted by firm id

    def firm(self, firm_id: int) -> FirmTech | None:
        for f in self.firms:
            if f.firm_id == firm_id:
                return f
        return None


EMPTY_TECH = TechState()


def with_firm(tech: TechState, firm: FirmTech) -> TechState:
    others = tuple(f for f in tech.firms if f.firm_id != firm.firm_id)
    return TechState(firms=tuple(sorted((*others, firm), key=lambda f: f.firm_id)))


def with_era(firm: FirmTech, era: EraAdoption, order: tuple[str, ...]) -> FirmTech:
    others = [e for e in firm.eras if e.era != era.era]
    eras = sorted((*others, era), key=lambda e: order.index(e.era))
    return replace(firm, eras=tuple(eras))
