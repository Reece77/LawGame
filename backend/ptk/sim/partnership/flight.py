"""Partner flight (spec 8.7): the `PartnerFlightHook` of `ptk.sim.interfaces`.

PT-M4 sub-task 8 builds the body; until then the hook's methods raise NotImplementedError,
so PT-M5 can code against the interface's types from the first commit.
"""

from __future__ import annotations

from typing import Any

from ptk.sim.interfaces import PartnerFlightHook


class _PendingFlightHook:
    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"PartnerFlightHook.{name} arrives in PT-M4 sub-task 8")


FLIGHT_HOOK: PartnerFlightHook = _PendingFlightHook()
