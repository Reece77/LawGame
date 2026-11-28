"""Inbox: render templated log items for the player's firm, list them, mark them read.

Ported from backend/tst/db/inbox.py @ 02fba2aa (Tech Startup Tycoon); changed: firms; no
archive, bookmarks, digest or event links (later milestones); reading is UI state (no
energy, no game effect, not in decision_log).
"""

from __future__ import annotations

import string
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from simcore.kernel.money import format_money
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ptk.db.models import InboxItemRow
from ptk.sim.data_models import InboxTemplate
from ptk.sim.log import LogItem

MONEY_SUFFIX = "_cents"
ARTICLE_SPEC = "a"  # "{role:a}" renders "a Corporate lawyer" or "an IP lawyer"
CONSONANT_SOUND = ("uni", "use", "usu", "eu", "one")
VOWEL_SOUND = ("hour", "honest", "heir")


def indefinite_article(word: str) -> str:
    """'a' or 'an' by the sound of the first word (simple English rules)."""
    lower = word.strip().lower()
    if lower.startswith(VOWEL_SOUND):
        return "an"
    if lower.startswith(CONSONANT_SOUND):
        return "a"
    return "an" if lower[:1] in {"a", "e", "i", "o", "u"} else "a"


class _TemplateFormatter(string.Formatter):
    def format_field(self, value: Any, format_spec: str) -> Any:
        if format_spec == ARTICLE_SPEC:
            text = str(value)
            return f"{indefinite_article(text)} {text}"
        return super().format_field(value, format_spec)


_FORMATTER = _TemplateFormatter()


@dataclass(frozen=True, slots=True)
class InboxMessage:
    id: int
    turn: int
    template: str
    title: str
    body: str
    link_kind: str | None
    link_id: int | None
    read: bool
    in_digest: bool = False  # PT-M9: from an automated area (the digest links to it)


def render(item: LogItem, templates: Mapping[str, InboxTemplate]) -> tuple[str, str]:
    """Title and body for a templated log item; *_cents parameters are shown as money."""
    assert item.template is not None
    template = templates[item.template]
    params = {
        key: format_money(int(value)) if key.endswith(MONEY_SUFFIX) else value
        for key, value in item.params
    }
    return (
        _FORMATTER.vformat(template.title, (), params),
        _FORMATTER.vformat(template.body, (), params),
    )


def inbox_rows(
    items: Iterable[LogItem], player_id: int, templates: Mapping[str, InboxTemplate]
) -> list[InboxItemRow]:
    """Rows for the player firm's templated items, in emission order."""
    rows = []
    for item in items:
        if item.template is None or item.firm_id != player_id:
            continue
        title, body = render(item, templates)
        rows.append(
            InboxItemRow(
                turn=item.turn,
                firm_id=player_id,
                template=item.template,
                title=title,
                body=body,
                link_kind=item.link_kind,
                link_id=item.link_id,
                read=False,
                in_digest=item.in_digest,  # PT-M9
            )
        )
    return rows


def list_inbox(session: Session, firm_id: int, *, limit: int = 200) -> list[InboxMessage]:
    """Newest first."""
    stmt = (
        select(InboxItemRow)
        .where(InboxItemRow.firm_id == firm_id)
        .order_by(InboxItemRow.id.desc())
        .limit(limit)
    )
    return [
        InboxMessage(
            id=r.id,
            turn=r.turn,
            template=r.template,
            title=r.title,
            body=r.body,
            link_kind=r.link_kind,
            link_id=r.link_id,
            read=r.read,
            in_digest=r.in_digest,
        )
        for r in session.scalars(stmt)
    ]


def mark_all_read(session: Session, firm_id: int) -> None:
    session.execute(update(InboxItemRow).where(InboxItemRow.firm_id == firm_id).values(read=True))
