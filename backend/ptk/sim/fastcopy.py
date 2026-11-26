"""A faster `dataclasses.replace` for the turn's hot paths (PT-M18, T12).

`dataclasses.replace` walks `fields()` and checks each field's kind on every call, then calls
the class with keywords. This keeps each class's init field names once and calls the class
positionally: the same `__init__` (and `__post_init__`) runs with the same values, so the
result is identical. Unknown names raise `TypeError`, as `replace` does. The sim's dataclasses
have no `InitVar` or `init=False` fields (a test checks), which `replace` treats specially.
"""

from __future__ import annotations

from dataclasses import fields
from typing import Any

_NAMES: dict[type, tuple[tuple[str, ...], frozenset[str]]] = {}


def replace[T](obj: T, /, **changes: Any) -> T:
    """`dataclasses.replace(obj, **changes)`, faster."""
    cls = type(obj)
    hit = _NAMES.get(cls)
    if hit is None:
        names = tuple(f.name for f in fields(cls))  # type: ignore[arg-type]
        hit = _NAMES[cls] = (names, frozenset(names))
    names, known = hit
    if not known.issuperset(changes):
        unknown = sorted(set(changes) - known)
        raise TypeError(f"{cls.__name__} has no fields {unknown}")
    return cls(*[changes[n] if n in changes else getattr(obj, n) for n in names])
