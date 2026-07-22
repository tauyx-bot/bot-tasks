"""Stable rendering helpers for generated Python data modules."""

from __future__ import annotations

import pprint
from typing import Any


def render_frozenset_module(docstring: str, name: str, values: set[str]) -> str:
    rendered = pprint.pformat(tuple(sorted(values)), width=120, compact=False)
    return (
        f'"""{docstring}"""\n\n'
        "from typing import Final\n\n\n"
        f"{name}: Final[frozenset[str]] = frozenset({rendered})\n"
    )


def render_record_mapping(
    name: str,
    annotation: str,
    class_name: str,
    records: dict[str, dict[str, Any]],
    fields: tuple[str, ...],
    defaults: dict[str, Any] | None = None,
) -> str:
    defaults = defaults or {}
    lines = [f"{name}: Final[{annotation}] = {{"]
    for key, record in records.items():
        lines.append(f"    {key!r}: {class_name}(")
        for field in fields:
            value = record[field]
            if field in defaults and value == defaults[field]:
                continue
            lines.append(f"        {field}={value!r},")
        lines.append("    ),")
    lines.append("}")
    return "\n".join(lines) + "\n"
