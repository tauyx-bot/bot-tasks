#!/usr/bin/env python3
"""Generate a Markdown room inventory from parsed CAD room JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _pick_area_value(space: dict) -> float | None:
    primary_area = space.get("primary_area_text")
    if primary_area is not None:
        return float(primary_area)

    resolved_area = space.get("resolved_area_text")
    if resolved_area is not None:
        return float(resolved_area)

    polygon_area = float(space.get("polygon_area") or 0.0)
    if polygon_area > 0:
        return polygon_area

    return None


def _pick_area(space: dict) -> str:
    value = _pick_area_value(space)
    return "" if value is None else str(value)


def _bucket_name(value: float) -> str | None:
    if value < 50:
        return "lt_50"
    if value < 100:
        return "gte_50_lt_100"
    if value < 500:
        return "gte_100_lt_500"
    if value < 1000:
        return "gte_500_lt_1000"
    return None


def _build_info(space: dict) -> str:
    texts: list[str] = []
    seen: set[str] = set()

    primary_label = space.get("primary_label")
    if primary_label:
        seen.add(primary_label)
        texts.append(primary_label)

    for label in space.get("labels", []):
        text = str(label.get("text") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        texts.append(text)

    if not texts:
        return ""
    return " / ".join(texts)


def generate_markdown(inventory: dict) -> str:
    buckets = {
        "lt_50": [],
        "gte_50_lt_100": [],
        "gte_100_lt_500": [],
        "gte_500_lt_1000": [],
        "missing_area": [],
    }

    for space in inventory.get("closed_spaces", []):
        area_value = _pick_area_value(space)
        if area_value is None:
            buckets["missing_area"].append(space)
            continue

        bucket = _bucket_name(area_value)
        if bucket is None:
            buckets["missing_area"].append(space)
            continue
        buckets[bucket].append(space)

    lines = [
        "# 房间信息汇总",
        "",
        f"- 来源文件: `{inventory.get('source_file', '')}`",
        f"- 房间数: `{len(inventory.get('closed_spaces', []))}`",
        "",
    ]

    sections = [
        ("lt_50", "< 50"),
        ("gte_50_lt_100", "50-100"),
        ("gte_100_lt_500", "100-500"),
        ("gte_500_lt_1000", "500-1000"),
        ("missing_area", "未解析出面积"),
    ]

    for key, title in sections:
        spaces = buckets[key]
        lines.extend(
            [
                f"## {title}",
                "",
                f"共 {len(spaces)} 条",
                "",
                "| id | 面积 | 信息 |",
                "| --- | --- | --- |",
            ]
        )
        for space in spaces:
            room_id = space.get("space_id", "")
            area = _pick_area(space)
            info = _build_info(space).replace("\n", " ").replace("|", "/")
            lines.append(f"| {room_id} | {area} | {info} |")
        lines.append("")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate room inventory markdown.")
    parser.add_argument("--input-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    args = parser.parse_args()

    inventory = json.loads(args.input_json.read_text(encoding="utf-8"))
    markdown = generate_markdown(inventory)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(markdown, encoding="utf-8")
    print(args.output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
