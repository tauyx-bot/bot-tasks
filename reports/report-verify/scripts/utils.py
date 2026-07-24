from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


SPACE_RE = re.compile(r"\s+")


def normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\xa0", " ")
    translations = str.maketrans(
        {
            "，": ",",
            "。": ".",
            "：": ":",
            "（": "(",
            "）": ")",
            "＜": "<",
            "＞": ">",
            "≤": "<=",
            "≥": ">=",
            "—": "-",
            "－": "-",
        }
    )
    return SPACE_RE.sub("", text.translate(translations)).strip()


def compact(value: Any) -> str:
    return normalize(value).lower()


def unique(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=json_value) + "\n",
        encoding="utf-8",
    )


def decimal_value(value: Any) -> Decimal | None:
    match = re.search(r"-?\d+(?:\.\d+)?", normalize(value))
    if not match:
        return None
    try:
        return Decimal(match.group())
    except InvalidOperation:
        return None


def masked_name_matches(masked: str, full: str) -> bool:
    pattern = re.escape(normalize(masked)).replace(r"\*", ".+")
    return bool(re.fullmatch(pattern, normalize(full)))


def rows_contain(source_rows: list[list[str]], target_rows: list[list[str]]) -> tuple[bool, list[str]]:
    target_text = compact("|".join(cell for row in target_rows for cell in row))
    missing: list[str] = []
    for row in source_rows:
        meaningful = [compact(cell) for cell in row if compact(cell) not in {"", "/"}]
        absent = [cell for cell in meaningful if cell not in target_text]
        if absent:
            missing.append(" / ".join(absent[:4]))
    return not missing, missing

