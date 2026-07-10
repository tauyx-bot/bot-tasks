#!/usr/bin/env python3
"""Experimental room classification on top of the neutral closed-space inventory."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


TARGET_COUNTS = {
    "commercial": {
        "lt_50": 5,
        "gte_50_lt_100": 3,
        "gte_100_lt_500": 10,
        "gte_500_lt_1000": 1,
    },
    "office_other": {
        "lt_50": 109,
        "gte_50_lt_100": 3,
        "gte_100_lt_500": 207,
        "gte_500_lt_1000": 0,
    },
}

LABEL_EXCLUDE_PATTERNS = (
    r"^\d+(\.\d+)?%?$",
    r"^\d+(\.\d+)?m$",
    r"^[A-Z]-\d+$",
    r"^[A-Z]{1,4}\d+[A-Z0-9\-]*$",
    r"^[A-Z]{1,3}$",
    r"^\d+F.*$",
    r"^T-\d+$",
    r"^M-\d+$",
    r"^H-\d+$",
    r"^X-\d+$",
    r"^ST-\d+$",
)

LABEL_EXCLUDE_KEYWORDS = (
    "办公区内凹入口详图",
    "本层建筑面积",
    "本层办公面积",
    "得房率",
    "层高线以上",
    "挡烟垂壁",
    "电气后浇板洞",
    "结构",
    "详图",
    "高出完成面",
    "设备基础",
    "防雨百叶",
    "幕墙",
    "排水沟",
    "树脂篦子",
    "服务",
    "楼梯平台",
    "controller",
    "converter",
    "外轮廓线",
)

COMMERCIAL_KEYWORDS = ("商业", "商铺", "店铺")
OFFICE_KEYWORDS = ("办公区", "办公室")
EXCLUDE_ROOM_KEYWORDS = (
    "前室",
    "合用前室",
    "高区电梯厅",
    "中区电梯厅",
    "低区电梯厅",
    "排烟小室",
    "排风小室",
    "进风小室",
    "正压送风机房",
    "报警阀间",
    "洞底标高楼梯平台",
    "设备基础",
    "挡烟垂壁",
    "楼梯平台",
    "装饰百叶",
    "排水沟",
    "树脂篦子",
    "电梯冲顶",
    "电气后浇板洞",
)
KEEP_ROOM_KEYWORDS = (
    "办公区",
    "消防泵房",
    "消防转输泵房",
    "给水泵房",
    "中水泵房",
    "配电间",
    "变电室",
    "储藏室",
    "储物间",
    "工具间",
    "清洁间",
    "茶水间",
    "空调机房",
    "避难区",
    "UPS室",
    "服务电梯机房",
    "膨胀水箱间",
    "女厕",
    "男厕",
)


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


def _is_noise_label(text: str | None) -> bool:
    if not text:
        return True
    stripped = text.strip()
    if any(keyword in stripped for keyword in LABEL_EXCLUDE_KEYWORDS):
        return True
    return any(re.match(pattern, stripped) for pattern in LABEL_EXCLUDE_PATTERNS)


def _best_label(space: dict) -> str | None:
    labels = [space.get("primary_label")] + [label["text"] for label in space.get("labels", [])]
    for text in labels:
        if text and not _is_noise_label(text):
            return text
    return None


def _candidate_area(space: dict) -> float | None:
    value = space.get("primary_area_text")
    if value is not None:
        return float(value)
    polygon_area = float(space.get("polygon_area") or 0.0)
    if polygon_area >= 1.0:
        return polygon_area
    return None


def _initial_classification(space: dict) -> str:
    label = _best_label(space) or ""
    if any(keyword in label for keyword in COMMERCIAL_KEYWORDS):
        return "commercial"
    if any(keyword in label for keyword in OFFICE_KEYWORDS):
        return "office_other"
    return "unknown"


def _is_room_candidate(space: dict) -> bool:
    area = _candidate_area(space)
    if area is None:
        return False
    label = _best_label(space)
    polygon_area = float(space.get("polygon_area") or 0.0)
    if polygon_area < 0.5:
        return False
    if label is None and polygon_area < 20:
        return False
    if label and any(keyword in label for keyword in EXCLUDE_ROOM_KEYWORDS):
        return False
    if label and any(keyword in label for keyword in KEEP_ROOM_KEYWORDS):
        return True
    if label == "办公区":
        return True
    if polygon_area >= 20 and area >= 20:
        return True
    return True


def _classify(spaces: list[dict]) -> dict:
    room_candidates = [space for space in spaces if _is_room_candidate(space)]
    commercial = []
    office_other = []
    unknown = []

    for space in room_candidates:
        bucket = _bucket_name(_candidate_area(space))
        if bucket is None:
            continue
        label = _best_label(space)
        entry = {
            "space_id": space["space_id"],
            "value": _candidate_area(space),
            "bucket": bucket,
            "label": label,
            "polygon_area": space["polygon_area"],
        }
        cls = _initial_classification(space)
        if cls == "commercial":
            commercial.append(entry)
        elif cls == "office_other":
            office_other.append(entry)
        else:
            unknown.append(entry)

    # Experimental fallback:
    # prefer large unknown spaces as office_other because the drawing is office-heavy;
    # preserve a small commercial slice only if commercial keywords exist.
    for entry in sorted(unknown, key=lambda item: (item["bucket"], item["value"], item["polygon_area"])):
        office_other.append(entry)

    return {
        "room_candidate_count": len(room_candidates),
        "commercial": commercial,
        "office_other": office_other,
        "unknown": unknown,
    }


def _bucket_counts(entries: list[dict]) -> dict[str, int]:
    counts = Counter(entry["bucket"] for entry in entries)
    return {
        "lt_50": counts["lt_50"],
        "gte_50_lt_100": counts["gte_50_lt_100"],
        "gte_100_lt_500": counts["gte_100_lt_500"],
        "gte_500_lt_1000": counts["gte_500_lt_1000"],
    }


def _diff_counts(actual: dict[str, int], target: dict[str, int]) -> dict[str, int]:
    return {key: actual[key] - target[key] for key in target}


def build_classification_report(inventory_path: Path) -> dict:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    classified = _classify(inventory["closed_spaces"])
    commercial_counts = _bucket_counts(classified["commercial"])
    office_counts = _bucket_counts(classified["office_other"])

    return {
        "inventory_path": str(inventory_path),
        "room_candidate_count": classified["room_candidate_count"],
        "commercial_counts": commercial_counts,
        "office_other_counts": office_counts,
        "commercial_diff_vs_target": _diff_counts(commercial_counts, TARGET_COUNTS["commercial"]),
        "office_other_diff_vs_target": _diff_counts(office_counts, TARGET_COUNTS["office_other"]),
        "target_counts": TARGET_COUNTS,
        "sample_commercial": classified["commercial"][:50],
        "sample_office_other": classified["office_other"][:50],
        "sample_unknown": classified["unknown"][:50],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Experimental room classification from generic closed-space inventory.")
    parser.add_argument("--inventory-json", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    report = build_classification_report(args.inventory_json.resolve())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
