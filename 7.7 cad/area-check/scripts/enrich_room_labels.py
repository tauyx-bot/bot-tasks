#!/usr/bin/env python3
"""Enrich neutral room inventory with better room-label and area-candidate ranking."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


MEANINGFUL_ROOM_LABEL_KEYWORDS = (
    "办公",
    "办公室",
    "男厕",
    "女厕",
    "厕所",
    "卫生间",
    "茶水间",
    "清洁间",
    "储藏",
    "储物",
    "前室",
    "电梯厅",
    "避难",
    "机房",
    "泵房",
    "配电",
    "配电间",
    "配电室",
    "配电柜",
    "变电",
    "变电室",
    "排烟机房",
    "排风机房",
    "排风小室",
    "排烟小室",
    "进风小室",
    "中水泵房",
    "给水泵房",
    "空调机房",
    "报警阀间",
    "观光前厅",
    "观光电梯厅",
    "合用前室",
    "储藏间",
    "储藏室",
    "储物间",
    "电梯机房",
    "高位消防水箱",
    "不上人屋面",
    "屋面",
)

SECONDARY_LABEL_SEARCH_RADIUS = 20000.0

SPECIFIC_ROOM_LABEL_KEYWORDS = (
    "男厕",
    "女厕",
    "厕所",
    "卫生间",
    "茶水间",
    "清洁间",
    "储藏",
    "储物",
    "避难",
    "机房",
    "泵房",
    "配电",
    "变电",
    "排风小室",
    "排烟小室",
    "进风小室",
    "报警阀间",
    "观光前厅",
    "观光电梯厅",
    "储藏间",
    "储藏室",
    "储物间",
    "电梯机房",
)

GENERIC_ROOM_LABEL_KEYWORDS = (
    "办公",
    "办公室",
)

CIRCULATION_LABEL_KEYWORDS = (
    "前室",
    "合用前室",
    "电梯厅",
)

NOISE_LABEL_EXACT = (
    "高",
    "余同",
    "LM0823",
    "底部标高",
    "基础顶标高",
)

NOISE_LABEL_KEYWORDS = (
    "挡烟垂壁",
    "楼板边线",
    "消防救援窗",
    "洞底标高",
    "层高线以上",
    "外轮廓线",
    "处建筑",
    "完成面",
    "排水沟",
    "树脂篦子",
    "设备板洞",
    "设备基础",
    "详图",
    "钢斜梯",
    "钢直梯",
    "墙洞",
    "填充区域",
    "通信机房室外机",
    "预留室外机",
    "防火固定窗",
    "可开启乙级防火窗",
    "本层建筑面积",
    "屋面完成面",
)

NON_ROOM_MEANINGFUL_EXCLUDES = (
    "办公用",
    "服务2-19层",
    "服务20层至屋顶",
    "服务31至电梯机房层",
    "服务设备层",
    "电梯机房层塔",
    "此段墙变电室机",
    "注：",
    "防火固定窗",
    "可开启乙级防火窗",
    "设备基础高出完成面",
    "室外机设备基础",
    "屋面完成面",
    "洞底标高为屋面完成面",
)

NOISE_LABEL_PATTERNS = (
    re.compile(r"^\d+(?:\.\d+)?%?$"),
    re.compile(r"^\d+(?:\.\d+)?m(?:m)?$"),
    re.compile(r"^\d+F$"),
    re.compile(r"^[A-Z]{1,4}\d+[A-Z0-9\-]*$"),
    re.compile(r"^[A-Z]{1,3}-\d+$"),
    re.compile(r"^[A-Z]{1,4}$"),
)


def _is_noise_label(text: str) -> bool:
    if text in NOISE_LABEL_EXACT:
        return True
    if any(keyword in text for keyword in NOISE_LABEL_KEYWORDS):
        return True
    return any(pattern.match(text) for pattern in NOISE_LABEL_PATTERNS)


def _is_meaningful_room_label(text: str) -> bool:
    if any(keyword in text for keyword in NON_ROOM_MEANINGFUL_EXCLUDES):
        return False
    return any(keyword in text for keyword in MEANINGFUL_ROOM_LABEL_KEYWORDS)


def _is_preferred_layer(layer: str) -> bool:
    return layer in {"06-施工图-文字-200", "06-施工图-文字-400"}


def _meaningful_label_priority(text: str) -> int:
    if any(keyword in text for keyword in SPECIFIC_ROOM_LABEL_KEYWORDS):
        return 0
    if any(keyword in text for keyword in GENERIC_ROOM_LABEL_KEYWORDS):
        return 1
    if any(keyword in text for keyword in CIRCULATION_LABEL_KEYWORDS):
        return 2
    return 3


def _label_score(label: dict) -> tuple[int, int, float, int, str]:
    text = label["text"]
    if _is_meaningful_room_label(text):
        category = 0
        meaningful_priority = _meaningful_label_priority(text)
    elif _is_noise_label(text):
        category = 3
        meaningful_priority = 9
    elif any(char.isalpha() for char in text) or any("\u4e00" <= char <= "\u9fff" for char in text):
        category = 1
        meaningful_priority = 9
    else:
        category = 2
        meaningful_priority = 9
    layer_bonus = 0 if _is_preferred_layer(label["layer"]) else 1
    return (category, meaningful_priority, round(float(label["distance"]), 3), layer_bonus, text)


def _global_label_score(label: dict) -> tuple[int, int, float, int, str]:
    text = label["text"]
    if _is_meaningful_room_label(text):
        category = 0
        meaningful_priority = _meaningful_label_priority(text)
    elif _is_noise_label(text):
        category = 3
        meaningful_priority = 9
    elif any(char.isalpha() for char in text) or any("\u4e00" <= char <= "\u9fff" for char in text):
        category = 1
        meaningful_priority = 9
    else:
        category = 2
        meaningful_priority = 9
    layer_bonus = 0 if _is_preferred_layer(label["layer"]) else 1
    return (category, meaningful_priority, round(float(label["distance"]), 3), layer_bonus, text)


def _area_candidate_score(candidate: dict, polygon_area: float) -> tuple[int, float, float, float]:
    layer_priority = {
        "05-辅助-建筑指标": 0,
        "05-辅助-面积文字": 1,
        "05-辅助-防火分区": 2,
        "A-ANNO-LEVL": 3,
        "06-施工图-文字-300": 4,
        "06-施工图-文字-200": 5,
        "06-施工图-文字-400": 5,
        "06-建-标注-文字": 6,
        "05-辅助-说明注释": 7,
    }
    source_penalty = 1 if str(candidate.get("source", "")).startswith("block:分户墙") else 0
    return (
        layer_priority.get(candidate["layer"], 99) + source_penalty,
        round(float(candidate["distance"]), 3),
        abs(float(candidate["value"]) - float(polygon_area)),
        float(candidate["value"]),
    )


def _collect_global_nearby_labels(space: dict, label_records: list[dict]) -> list[dict]:
    cx, cy = space["centroid"]
    nearby = []
    for label in label_records:
        distance = math.hypot(float(label["x"]) - float(cx), float(label["y"]) - float(cy))
        if distance > SECONDARY_LABEL_SEARCH_RADIUS:
            continue
        nearby.append(
            {
                "text": label["text"],
                "layer": label["layer"],
                "x": label["x"],
                "y": label["y"],
                "distance": round(distance, 3),
                "source": label.get("source"),
            }
        )
    nearby.sort(key=_global_label_score)
    deduped = []
    seen = set()
    for label in nearby:
        key = (label["text"], round(float(label["x"]), 1), round(float(label["y"]), 1))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(label)
    return deduped


def _infer_room_label(sorted_labels: list[dict], global_nearby_labels: list[dict]) -> str | None:
    merged_labels = sorted_labels + [
        label
        for label in global_nearby_labels
        if (label["text"], round(float(label["x"]), 1), round(float(label["y"]), 1))
        not in {(item["text"], round(float(item["x"]), 1), round(float(item["y"]), 1)) for item in sorted_labels}
    ]
    meaningful_labels = [label for label in merged_labels if _is_meaningful_room_label(label["text"])]
    if meaningful_labels:
        return meaningful_labels[0]["text"]

    merged_texts = [label["text"] for label in merged_labels]
    if any("不上人屋面" in text for text in merged_texts):
        return "不上人屋面"
    if any(text.startswith("E-RF-") for text in merged_texts):
        return "屋面"
    return None


def enrich_inventory(inventory: dict) -> dict:
    spaces = []
    label_records = inventory.get("label_records", [])
    for space in inventory["closed_spaces"]:
        polygon_area = float(space["polygon_area"])
        sorted_labels = sorted(space.get("labels", []), key=_label_score)
        sorted_areas = sorted(space.get("area_text_candidates", []), key=lambda item: _area_candidate_score(item, polygon_area))
        global_nearby_labels = _collect_global_nearby_labels(space, label_records)
        enriched = dict(space)
        enriched["ranked_labels"] = sorted_labels
        enriched["global_nearby_labels"] = global_nearby_labels
        enriched["ranked_area_text_candidates"] = sorted_areas
        enriched["resolved_room_label"] = _infer_room_label(sorted_labels, global_nearby_labels)
        enriched["resolved_area_text"] = sorted_areas[0]["value"] if sorted_areas else None
        spaces.append(enriched)

    result = dict(inventory)
    result["closed_spaces"] = spaces
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich neutral room inventory with downstream label ranking.")
    parser.add_argument("--inventory-json", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    inventory = json.loads(args.inventory_json.read_text(encoding="utf-8"))
    enriched = enrich_inventory(inventory)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "space_count": len(enriched["closed_spaces"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
