"""PT-M1b's implementation of the delegate hiring hook (ptk.sim.interfaces).

Placeholder until PT-M1b sub-task 1: the interface is fixed so PT-M2 can build against it.
"""

from __future__ import annotations

from typing import Any

from ptk.sim.interfaces import DelegateHiringHook


class _Pending:
    def __getattr__(self, name: str) -> Any:
        raise NotImplementedError(f"delegate hiring hook {name!r} arrives with PT-M1b sub-task 1")


HIRING_HOOK: DelegateHiringHook = _Pending()
