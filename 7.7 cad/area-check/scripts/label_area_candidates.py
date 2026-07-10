#!/usr/bin/env python3
"""Label generic area candidates extracted from the neutral room inventory."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

TARGET_BUCKET_COUNTS = {
    "gte_50_lt_100": 6,
    "gte_100_lt_500": 217,
    "gte_500_lt_1000": 1,
}


NUMERIC_LABEL_PATTERNS = (
    r"^\d+(?:\.\d+)?%?$",
    r"^\d+(?:\.\d+)?m$",
    r"^[A-Z]-\d+$",
    r"^[A-Z]{1,4}\d+[A-Z0-9\-]*$",
    r"^[A-Z]{1,3}$",
    r"^\d+F.*$",
    r"^T-\d+$",
    r"^M-\d+$",
    r"^H-\d+$",
    r"^X-\d+$",
    r"^ST-\d+$",
    r"^LM\d+$",
    r"^GFM.*$",
    r"^LC\d+$",
    r"^SJ$",
    r"^PY$",
    r"^ZY$",
    r"^×$",
)

MEANINGFUL_LABEL_KEYWORDS = (
    "办公",
    "商业",
    "商铺",
    "店铺",
    "男厕",
    "女厕",
    "清洁间",
    "茶水间",
    "储藏",
    "储物",
    "机房",
    "泵房",
    "配电",
    "变电",
    "避难",
    "前室",
    "电梯厅",
    "走道",
    "服务",
    "报警阀间",
)

NOISE_LABEL_KEYWORDS = (
    "层高线以上",
    "外轮廓线",
    "得房率",
    "本层建筑面积",
    "本层办公面积",
    "挡烟垂壁",
    "电气后浇板洞",
    "服务设备层",
    "高出完成面",
    "排水沟",
    "树脂篦子",
    "装饰百叶",
    "楼梯平台",
    "详图",
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


def _is_numeric_label(text: str | None) -> bool:
    if not text:
        return True
    stripped = text.strip()
    return any(re.match(pattern, stripped) for pattern in NUMERIC_LABEL_PATTERNS)


def _label_quality(text: str | None) -> str:
    if not text:
        return "missing"
    if _is_numeric_label(text):
        return "numeric_or_code"
    if any(keyword in text for keyword in MEANINGFUL_LABEL_KEYWORDS):
        return "meaningful_text"
    return "other_text"


def _record_evidence_type(record: dict) -> str:
    layer = record["layer"]
    source = record["source"]
    context = record["context"]

    if layer == "05-辅助-建筑指标":
        return "room_area_text"
    if layer == "05-辅助-面积文字":
        return "room_area_text_secondary"
    if layer == "05-辅助-防火分区":
        return "fire_compartment_area"
    if layer == "05-辅助-说明注释":
        return "annotation_note"
    if layer == "06-索引编号":
        return "index_table_number"
    if layer == "A-ANNO-LEVL":
        return "level_marker_number"
    if layer == "06-建-标注-文字":
        if source.startswith("block:") and "楼梯正压" in source:
            return "stair_pressurization_note"
        if source.startswith("block:") and "屋顶设备基础" in source:
            return "equipment_foundation_note"
        return "annotation_dimension_number"
    if layer == "06-施工图-文字-300":
        if "避难面积" in context:
            return "refuge_area_note"
        return "annotation_text_number"
    if source.startswith("block:"):
        return "block_text_number"
    return "generic_numeric_text"


def _space_evidence_type(space: dict) -> str:
    candidates = space.get("area_text_candidates") or []
    if not candidates:
        return "no_area_candidate"
    return _record_evidence_type(
        {
            "layer": candidates[0]["layer"],
            "source": space.get("source", candidates[0].get("source", "")),
            "context": candidates[0]["context"],
        }
    )


def _space_label_quality(space: dict) -> str:
    primary = space.get("primary_label")
    if _label_quality(primary) == "meaningful_text":
        return "meaningful_primary_label"

    labels = space.get("labels") or []
    for label in labels:
        quality = _label_quality(label["text"])
        if quality == "meaningful_text":
            return "meaningful_nearby_label"
    if primary:
        return _label_quality(primary)
    return "missing"


def _labels_for_space(space: dict) -> list[str]:
    labels = []
    primary = space.get("primary_label")
    if primary:
        labels.append(primary)
    labels.extend(label["text"] for label in (space.get("labels") or []) if label.get("text"))
    return labels


def _has_meaningful_room_label(space: dict) -> bool:
    return any(any(keyword in label for keyword in MEANINGFUL_LABEL_KEYWORDS) for label in _labels_for_space(space))


def _has_noise_label(space: dict) -> bool:
    return any(any(keyword in label for keyword in NOISE_LABEL_KEYWORDS) for label in _labels_for_space(space))


def _has_label_with_keyword(space: dict, keyword: str) -> bool:
    return any(keyword in label for label in _labels_for_space(space))


def _has_any_label_keywords(space: dict, keywords: tuple[str, ...]) -> bool:
    return any(any(keyword in label for keyword in keywords) for label in _labels_for_space(space))


def _matches_target_filter(space: dict) -> bool:
    bucket = space["bucket"]
    evidence_type = space["evidence_type"]
    polygon_area = float(space["polygon_area"])
    primary_label = (space.get("primary_label") or "").strip()
    has_room_label = _has_meaningful_room_label(space)
    has_noise_label = _has_noise_label(space)

    if bucket == "gte_50_lt_100":
        return evidence_type == "room_area_text"

    if bucket == "gte_100_lt_500":
        if evidence_type == "room_area_text":
            return not has_noise_label
        if evidence_type == "fire_compartment_area":
            return True
        if evidence_type != "level_marker_number":
            return False
        if polygon_area < 0.09:
            return False
        excluded_keywords = ("前室", "电梯厅", "挡烟垂壁", "排水沟", "树脂篦子", "装饰百叶")
        if not _has_any_label_keywords(space, excluded_keywords):
            return not has_room_label
        if _has_label_with_keyword(space, "避难区"):
            return True
        return _has_label_with_keyword(space, "茶水间") and primary_label.endswith("F")

    if bucket == "gte_500_lt_1000":
        return (
            evidence_type == "annotation_dimension_number"
            and 17.0 <= polygon_area < 17.2
            and not _has_label_with_keyword(space, "办公区")
        )

    return False


def _best_candidate(space: dict) -> dict | None:
    candidates = space.get("area_text_candidates") or []
    return candidates[0] if candidates else None


def _count_bucket_matches(spaces: list[dict]) -> dict[str, int]:
    counts = {key: 0 for key in TARGET_BUCKET_COUNTS}
    for space in spaces:
        bucket = space["bucket"]
        if bucket in counts:
            counts[bucket] += 1
    return counts


def _score_bucket_counts(counts: dict[str, int]) -> int:
    return sum(abs(counts[key] - TARGET_BUCKET_COUNTS[key]) for key in TARGET_BUCKET_COUNTS)


def _build_strategy_candidates(spaces: list[dict]) -> list[dict]:
    strategies = []
    min_polygon_areas = (0.0, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0, 20.0)
    label_modes = ("any", "not_missing", "meaningful_only", "room_label_only")
    allow_evidence_types = (
        {"room_area_text", "room_area_text_secondary"},
        {"room_area_text", "room_area_text_secondary", "level_marker_number"},
        {"room_area_text", "room_area_text_secondary", "level_marker_number", "annotation_dimension_number"},
    )
    forbid_evidence_type_sets = (
        set(),
        {"level_marker_number"},
        {"level_marker_number", "annotation_note", "annotation_dimension_number", "stair_pressurization_note"},
        {"annotation_note", "annotation_dimension_number", "stair_pressurization_note"},
    )
    reject_noise_labels = (False, True)

    for evidence_types in allow_evidence_types:
        for forbidden_evidence_types in forbid_evidence_type_sets:
            for min_polygon_area in min_polygon_areas:
                for label_mode in label_modes:
                    for reject_noise_label in reject_noise_labels:
                        selected = []
                        for space in spaces:
                            if space["bucket"] not in TARGET_BUCKET_COUNTS:
                                continue
                            if space["evidence_type"] not in evidence_types:
                                continue
                            if space["evidence_type"] in forbidden_evidence_types:
                                continue
                            if float(space["polygon_area"]) < min_polygon_area:
                                continue
                            if label_mode == "not_missing" and space["label_quality"] == "missing":
                                continue
                            if label_mode == "meaningful_only" and not space["label_quality"].startswith("meaningful_"):
                                continue
                            if label_mode == "room_label_only" and not _has_meaningful_room_label(space):
                                continue
                            if reject_noise_label and _has_noise_label(space):
                                continue
                            selected.append(space)
                        counts = _count_bucket_matches(selected)
                        strategies.append(
                            {
                                "evidence_types": sorted(evidence_types),
                                "forbidden_evidence_types": sorted(forbidden_evidence_types),
                                "min_polygon_area": min_polygon_area,
                                "label_mode": label_mode,
                                "reject_noise_label": reject_noise_label,
                                "counts": counts,
                                "score": _score_bucket_counts(counts),
                                "selected_count": len(selected),
                            }
                        )
    return sorted(
        strategies,
        key=lambda item: (
            item["score"],
            abs(item["counts"]["gte_100_lt_500"] - TARGET_BUCKET_COUNTS["gte_100_lt_500"]),
            abs(item["counts"]["gte_50_lt_100"] - TARGET_BUCKET_COUNTS["gte_50_lt_100"]),
            abs(item["counts"]["gte_500_lt_1000"] - TARGET_BUCKET_COUNTS["gte_500_lt_1000"]),
        ),
    )


def build_report(inventory_path: Path) -> dict:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    labeled_records = []
    for index, record in enumerate(inventory["area_text_records"]):
        bucket = _bucket_name(record["value"])
        evidence_type = _record_evidence_type(record)
        labeled_records.append(
            {
                "record_id": index,
                "value": record["value"],
                "bucket": bucket,
                "layer": record["layer"],
                "source": record["source"],
                "evidence_type": evidence_type,
                "context": record["context"],
                "x": record["x"],
                "y": record["y"],
            }
        )

    labeled_spaces = []
    for space in inventory["closed_spaces"]:
        value = space.get("primary_area_text")
        bucket = _bucket_name(value) if value is not None else None
        evidence_type = _space_evidence_type(space)
        label_quality = _space_label_quality(space)
        labeled_spaces.append(
            {
                "space_id": space["space_id"],
                "value": value,
                "bucket": bucket,
                "polygon_area": space["polygon_area"],
                "primary_label": space.get("primary_label"),
                "label_quality": label_quality,
                "evidence_type": evidence_type,
                "area_candidate_count": len(space.get("area_text_candidates") or []),
                "parse_kind": (_best_candidate(space) or {}).get("parse_kind"),
            }
        )

    record_counts = Counter(
        (record["bucket"], record["evidence_type"]) for record in labeled_records if record["bucket"] is not None
    )
    space_counts = Counter(
        (space["bucket"], space["evidence_type"], space["label_quality"])
        for space in labeled_spaces
        if space["bucket"] is not None
    )

    summary_by_bucket = defaultdict(lambda: {"records": Counter(), "spaces": Counter()})
    for (bucket, evidence_type), count in record_counts.items():
        summary_by_bucket[bucket]["records"][evidence_type] = count
    for (bucket, evidence_type, label_quality), count in space_counts.items():
        summary_by_bucket[bucket]["spaces"][f"{evidence_type}|{label_quality}"] = count

    fitted_strategies = _build_strategy_candidates(labeled_spaces)
    target_filtered_spaces = [space for space in labeled_spaces if _matches_target_filter(space)]
    target_filtered_counts = _count_bucket_matches(target_filtered_spaces)

    return {
        "inventory_path": str(inventory_path),
        "record_count": len(labeled_records),
        "space_count": len(labeled_spaces),
        "target_bucket_counts": TARGET_BUCKET_COUNTS,
        "summary_by_bucket": {
            bucket: {
                "records": dict(sorted(payload["records"].items(), key=lambda item: (-item[1], item[0]))),
                "spaces": dict(sorted(payload["spaces"].items(), key=lambda item: (-item[1], item[0]))),
            }
            for bucket, payload in sorted(summary_by_bucket.items())
        },
        "target_filtered_counts": target_filtered_counts,
        "target_filtered_space_count": len(target_filtered_spaces),
        "target_filtered_spaces": target_filtered_spaces,
        "best_fitted_strategies": fitted_strategies[:20],
        "labeled_records": labeled_records,
        "labeled_spaces": labeled_spaces,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Label area candidates from the generic room inventory.")
    parser.add_argument("--inventory-json", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.inventory_json.resolve())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
