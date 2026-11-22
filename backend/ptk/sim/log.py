"""Log items produced by turns and actions. The player firm's templated items become inbox
items when persisted.

Ported from tst/sim/log.py @ 02fba2aa; changed: link kinds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

type LinkKind = Literal[
    "person",
    "finance",
    "candidate",  # PT-M1b: the Recruitment screen's candidate
    "search",  # PT-M1b
    "matter",  # PT-M3a: a named matter
    "client",  # PT-M3a
    "rfp",  # PT-M5: the Market screen's RFP
    "rival",  # PT-M5: a rival firm's page
    "partnership",  # PT-M4: the Partnership screen
    "org",  # PT-M8: the Org screen's Leadership panel
    "pitch",  # PT-M8: a seat holder's pitch (answered in the inbox)
    "automation",  # PT-M9: the Automation screen (a proposal, or a month's digest)
    "event",  # PT-M9: an event an area's owner answered
]  # appended by each milestone that links a new screen
type ParamValue = str | int


@dataclass(frozen=True, slots=True)
class LogItem:
    turn: int
    firm_id: int | None
    kind: str
    message: str
    template: str | None = None  # inbox_templates.yaml key; None = turn log only
    params: tuple[tuple[str, ParamValue], ...] = ()  # names ending _cents render as money
    link_kind: LinkKind | None = None
    link_id: int | None = None
    in_digest: bool = False  # from an automated area; the digest links to it (TST 40.4)


def inbox_item(
    turn: int,
    firm_id: int,
    template: str,
    *,
    link_kind: LinkKind | None = None,
    link_id: int | None = None,
    **params: ParamValue,
) -> LogItem:
    """A log item that becomes an inbox entry for the player company."""
    return LogItem(
        turn=turn,
        firm_id=firm_id,
        kind=template,
        message=", ".join(f"{k}={v}" for k, v in sorted(params.items())),
        template=template,
        params=tuple(sorted(params.items())),
        link_kind=link_kind,
        link_id=link_id,
    )
