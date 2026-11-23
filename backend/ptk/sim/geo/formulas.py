"""Office and lease arithmetic (PT-M11; spec 8.8). Pure; money in integer cents.

Ported from backend/tst/sim/geo/formulas.py @ 718997f0 (Tech Startup Tycoon); changed: a law
firm's lease is priced per lawyer seat in each city (cities.yaml `rent_per_seat_cents`) over a
term (balance `geo.lease_months`) rather than TST's $600 a head x a rent index; the lease is
recognised as a liability (2500) against a right-of-use asset (1510), undiscounted, and fit-out
is capitalised (1500) and amortised straight-line over the term; TST's localisation, regional
market sizes, prices and talent bonuses have no counterpart (a city's market is its clients).
"""

from __future__ import annotations

from ptk.sim.geo.data import CityDef, GeoBalance
from ptk.sim.money import BP_DENOMINATOR, Cents, pct_of


def lease_rent_cents(seats: int, city: CityDef) -> Cents:
    """A lease's monthly rent: seats x the city's rent per lawyer seat, full or not."""
    return seats * city.rent_per_seat_cents


def fit_out_cents(seats: int, geo: GeoBalance) -> Cents:
    """Fit-out: seats x `geo.fit_out_per_seat_cents`, once."""
    return seats * geo.fit_out_per_seat_cents


def lease_liability_cents(rent_cents: Cents, months: int) -> Cents:
    """The term's rent, undiscounted (the liability and the right-of-use asset)."""
    return rent_cents * months


def straight_line(total: Cents, months: int, month: int) -> Cents:
    """Month `month` (0-based) of `total` spread over `months` with no remainder left: the
    months sum to `total` exactly (integer cents, ADR-0003)."""
    if month < 0 or month >= months:
        return 0
    return total * (month + 1) // months - total * month // months


def amortised_cents(total: Cents, months: int, through: int) -> Cents:
    """How much of `total` the first `through` months amortised."""
    through = max(0, min(through, months))
    return total * through // months


def close_penalty_cents(rent_cents: Cents, geo: GeoBalance) -> Cents:
    """Breaking a lease: `geo.close_penalty_months` of rent, once."""
    return rent_cents * geo.close_penalty_months


def local_bp(value: Cents, bp: int) -> Cents:
    """A New York amount at a city's bp (pay or rates)."""
    return value if bp == BP_DENOMINATOR else pct_of(value, bp)


def rate_factor(city: CityDef) -> float:
    """The local card over the firm's: 1.0 exactly in the home market (v1 unchanged)."""
    return 1.0 if city.rate_bp == BP_DENOMINATOR else city.rate_bp / BP_DENOMINATOR
