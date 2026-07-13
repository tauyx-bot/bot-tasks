#!/usr/bin/env python3
"""Parse a DWG/DXF floor plan into a neutral closed-space inventory."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

import ezdxf
from ezdxf.math import Vec3
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

from convert_dwg import convert_dwg_to_dxf

EPSILON = 1e-6
MIN_AREA = 1.0
AREA_SCALE = 1_000_000.0
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
PURE_NUMERIC_TEXT_PATTERN = re.compile(
    r"^\s*(?P<primary>\d+(?:\.\d+)?)\s*(?:㎡)?\s*(?:[（(]\s*(?P<secondary>\d+(?:\.\d+)?)\s*[）)])?\s*$"
)
LABEL_TO_POLYGON_MAX_DISTANCE = 12000.0
AREA_TO_POLYGON_MAX_DISTANCE = 12000.0
LABEL_SEARCH_RADIUS = 12000.0
NUMERIC_ONLY_AREA_LAYERS = {
    "05-辅助-建筑指标",
    "05-辅助-面积文字",
    "05-辅助-防火分区",
}
NUMERIC_ONLY_AREA_SOURCE_PREFIXES = ("modelspace", "block:核心筒", "block:卫生间")
AREA_CONTEXT_EXCLUDE_KEYWORDS = (
    "楼梯正压",
    "分户墙",
    "door",
)
MEANINGFUL_LABEL_KEYWORDS = (
    "商业",
    "商铺",
    "店铺",
    "餐饮",
    "办公",
    "办公室",
    "办公区",
    "预留餐饮条件",
    "预留机房",
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
    "变电",
    "排烟机房",
    "排风机房",
    "排风小室",
    "排烟小室",
    "进风小室",
    "报警阀间",
    "高位消防水箱",
    "给水泵房",
    "中水泵房",
    "服务电梯机房",
    "膨胀水箱间",
)
NOISE_LABEL_EXACT = {
    "×",
    "高",
    "结",
    "余同",
}
NOISE_LABEL_KEYWORDS = (
    "挡烟垂壁",
    "洞底标高",
    "墙洞",
    "层高线以上",
    "填充区域",
    "设备基础",
    "楼梯平台",
    "外轮廓线",
)
NOISE_LABEL_PATTERNS = (
    re.compile(r"^\d+(?:\.\d+)?%?$"),
    re.compile(r"^\d+(?:\.\d+)?m(?:m)?$"),
    re.compile(r"^[A-Z]{1,4}\d+[A-Z0-9\-]*$"),
    re.compile(r"^[A-Z]{1,3}-\d+$"),
    re.compile(r"^\+?\d+(?:\.\d+)?m$"),
)


def _rounded_point(point: Sequence[float], precision: int = 6) -> tuple[float, float]:
    return (round(float(point[0]), precision), round(float(point[1]), precision))


def _linestring_from_points(points: Iterable[Sequence[float]]) -> LineString | None:
    coords = [_rounded_point(point) for point in points]
    if len(coords) < 2 or len(set(coords)) < 2:
        return None
    return LineString(coords)


def _arc_to_lines(entity, segments: int = 32) -> list[LineString]:
    center = entity.dxf.center
    radius = float(entity.dxf.radius)
    start = math.radians(float(entity.dxf.start_angle))
    end = math.radians(float(entity.dxf.end_angle))
    if end <= start:
        end += math.tau

    points = []
    for index in range(segments + 1):
        ratio = index / segments
        angle = start + (end - start) * ratio
        points.append((center.x + radius * math.cos(angle), center.y + radius * math.sin(angle)))
    line = _linestring_from_points(points)
    return [line] if line else []


def _polyline_to_polygon(entity) -> Polygon | None:
    if entity.dxftype() == "LWPOLYLINE":
        points = [tuple(point[:2]) for point in entity.get_points("xy")]
        is_closed = entity.closed
    else:
        points = []
        for vertex in entity.vertices:
            location = getattr(vertex.dxf, "location", None)
            if location is not None:
                points.append((location.x, location.y))
        is_closed_attr = getattr(entity, "is_closed", False)
        is_closed = bool(is_closed_attr() if callable(is_closed_attr) else is_closed_attr)

    if not is_closed or len(points) < 3:
        return None
    if points[0] != points[-1]:
        points.append(points[0])

    polygon = Polygon(points)
    if polygon.is_empty or polygon.area <= MIN_AREA:
        return None
    return polygon.buffer(0)


def _collect_candidate_polygons(modelspace) -> tuple[list[Polygon], list[str]]:
    warnings: list[str] = []
    polygons: list[Polygon] = []
    loose_segments: list[LineString] = []
    entity_counter: Counter[str] = Counter()

    for entity in modelspace:
        entity_type = entity.dxftype()
        entity_counter[entity_type] += 1
        try:
            if entity_type in {"LWPOLYLINE", "POLYLINE"}:
                polygon = _polyline_to_polygon(entity)
                if polygon:
                    polygons.append(polygon)
                    continue

                if entity_type == "LWPOLYLINE":
                    points = [tuple(point[:2]) for point in entity.get_points("xy")]
                else:
                    points = []
                    for vertex in entity.vertices:
                        location = getattr(vertex.dxf, "location", None)
                        if location is not None:
                            points.append((location.x, location.y))
                line = _linestring_from_points(points)
                if line:
                    loose_segments.append(line)
            elif entity_type == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                line = _linestring_from_points([(start.x, start.y), (end.x, end.y)])
                if line:
                    loose_segments.append(line)
            elif entity_type == "ARC":
                loose_segments.extend(_arc_to_lines(entity))
            elif entity_type == "HATCH":
                for path in entity.paths:
                    if not hasattr(path, "vertices"):
                        continue
                    points = [(vertex[0], vertex[1]) for vertex in path.vertices]
                    if len(points) < 3:
                        continue
                    if points[0] != points[-1]:
                        points.append(points[0])
                    polygon = Polygon(points)
                    if not polygon.is_empty and polygon.area > MIN_AREA:
                        polygons.append(polygon.buffer(0))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Skipped {entity_type} entity: {exc}")

    if loose_segments:
        merged = unary_union(loose_segments)
        polygons.extend(poly.buffer(0) for poly in polygonize(merged) if not poly.is_empty and poly.area > MIN_AREA)

    warnings.append(f"Entity summary: {dict(entity_counter)}")
    return polygons, warnings


def _clean_text(text: str) -> str:
    return text.replace("\\P", " ").replace("{", " ").replace("}", " ")


def _normalize_text(text: str) -> str:
    normalized = re.sub(r"\\[A-Za-z][^;]*;", "", text)
    normalized = normalized.replace("\\", "")
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.strip(" -()（）[]，。；：,.;:")


def _strip_mtext_formatting(text: str) -> str:
    return re.sub(r"\\[A-Za-z][^;]*;", "", text)


def _text_insert_point(entity) -> tuple[float, float] | None:
    if entity.dxftype() == "TEXT":
        point = entity.dxf.insert
    elif entity.dxf.hasattr("insert"):
        point = entity.dxf.insert
    else:
        return None
    return (float(point.x), float(point.y))


def _extract_explicit_area_values(text: str) -> list[float]:
    values: list[float] = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*㎡", text):
        values.append(float(match.group(1)))
    return values


def _parse_pure_numeric_text(text: str) -> dict[str, float | None] | None:
    match = PURE_NUMERIC_TEXT_PATTERN.match(text)
    if match is None:
        return None
    primary = float(match.group("primary"))
    secondary = match.group("secondary")
    return {
        "primary": primary,
        "secondary": float(secondary) if secondary is not None else None,
    }


def _extract_area_candidates(clean_text: str, *, allow_numeric_only: bool = False) -> list[dict]:
    normalized_text = _strip_mtext_formatting(clean_text).strip()
    candidates: list[dict] = []
    explicit_values = _extract_explicit_area_values(normalized_text)
    for value in explicit_values:
        candidates.append({"value": value, "kind": "explicit_area"})

    if not candidates and allow_numeric_only:
        parsed_numeric = _parse_pure_numeric_text(normalized_text)
        if parsed_numeric is not None:
            candidates.append(
                {
                    "value": parsed_numeric["primary"],
                    "kind": "pure_numeric_text",
                    "secondary_value": parsed_numeric["secondary"],
                }
            )

    deduped: list[dict] = []
    seen: set[tuple[float, str]] = set()
    for candidate in candidates:
        rounded = round(float(candidate["value"]), 3)
        key = (rounded, str(candidate["kind"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _allow_numeric_only_area(layer: str, source: str) -> bool:
    if layer not in NUMERIC_ONLY_AREA_LAYERS:
        return False
    return source.startswith(NUMERIC_ONLY_AREA_SOURCE_PREFIXES)


def _is_plausible_area_record(record: dict) -> bool:
    value = float(record["value"])
    if not (0.9 <= value < 1000) or math.isclose(value, 1.0):
        return False
    parse_kind = str(record.get("parse_kind") or "")
    if parse_kind != "pure_numeric_text":
        return True
    if not _allow_numeric_only_area(str(record["layer"]), str(record.get("source") or "")):
        return False
    source = str(record.get("source") or "").lower()
    context = str(record.get("context") or "").lower()
    return not any(keyword.lower() in source or keyword.lower() in context for keyword in AREA_CONTEXT_EXCLUDE_KEYWORDS)


def _dedupe_area_records(records: list[dict]) -> list[dict]:
    deduped: dict[tuple[float, float, float], dict] = {}
    for record in records:
        key = (round(record["x"], 1), round(record["y"], 1), round(record["value"], 1))
        current = deduped.get(key)
        if current is None:
            aggregated = record.copy()
            aggregated["evidence"] = [
                {
                    "layer": record["layer"],
                    "source": record["source"],
                    "context": record["context"],
                    "parse_kind": record.get("parse_kind"),
                    "secondary_value": record.get("secondary_value"),
                }
            ]
            deduped[key] = aggregated
            continue

        current["evidence"].append(
            {
                "layer": record["layer"],
                "source": record["source"],
                "context": record["context"],
                "parse_kind": record.get("parse_kind"),
                "secondary_value": record.get("secondary_value"),
            }
        )
    return list(deduped.values())


def _dedupe_labels(labels: list[dict]) -> list[dict]:
    deduped: dict[tuple[str, float, float], dict] = {}
    for label in labels:
        key = (label["text"], round(label["x"], 1), round(label["y"], 1))
        deduped[key] = label
    return list(deduped.values())


def _is_meaningful_label(text: str) -> bool:
    return any(keyword in text for keyword in MEANINGFUL_LABEL_KEYWORDS)


def _is_noise_label(text: str) -> bool:
    if text in NOISE_LABEL_EXACT:
        return True
    if any(keyword in text for keyword in NOISE_LABEL_KEYWORDS):
        return True
    return any(pattern.match(text) for pattern in NOISE_LABEL_PATTERNS)


def _label_priority(label: dict) -> tuple[int, float, str]:
    text = str(label["text"])
    if _is_meaningful_label(text):
        category = 0
    elif _is_noise_label(text):
        category = 2
    else:
        category = 1
    return (category, round(float(label["distance"]), 3), text)


def _bucket_counts(records: list[dict], *, field: str = "value") -> dict:
    values = [record[field] for record in records]
    return {
        "lt_50": sum(value < 50 for value in values),
        "gte_50_lt_100": sum(50 <= value < 100 for value in values),
        "gte_100_lt_500": sum(100 <= value < 500 for value in values),
        "gte_500_lt_1000": sum(500 <= value < 1000 for value in values),
    }


def _collect_text_records(document) -> tuple[list[dict], list[dict]]:
    area_records: list[dict] = []
    label_records: list[dict] = []
    modelspace = document.modelspace()

    def append_entity_text(entity, x: float, y: float, source: str) -> None:
        if entity.dxftype() == "TEXT":
            text = entity.dxf.text or ""
        else:
            text = entity.text or ""
        clean = _clean_text(text)
        matches = _extract_area_candidates(clean, allow_numeric_only=_allow_numeric_only_area(entity.dxf.layer, source))
        if matches:
            for candidate in matches:
                area_records.append(
                    {
                        "value": candidate["value"],
                        "layer": entity.dxf.layer,
                        "x": x,
                        "y": y,
                        "source": source,
                        "context": clean[:160],
                        "parse_kind": candidate["kind"],
                        "secondary_value": candidate.get("secondary_value"),
                    }
                )
            return

        normalized = _normalize_text(clean)
        if normalized:
            label_records.append(
                {
                    "text": normalized[:160],
                    "layer": entity.dxf.layer,
                    "x": x,
                    "y": y,
                    "source": source,
                    "context": clean[:160],
                }
            )

    for entity in modelspace.query("TEXT MTEXT"):
        point = _text_insert_point(entity)
        if point is not None:
            append_entity_text(entity, point[0], point[1], "modelspace")

    for insert in modelspace.query("INSERT"):
        try:
            block = document.blocks.get(insert.dxf.name)
        except Exception:  # noqa: BLE001
            continue
        transform = insert.matrix44()
        for entity in block.query("TEXT MTEXT"):
            point = _text_insert_point(entity)
            if point is None:
                continue
            world_point = transform.transform(Vec3(point[0], point[1], 0.0))
            append_entity_text(entity, float(world_point.x), float(world_point.y), f"block:{insert.dxf.name}")

    filtered_area_records = [record for record in area_records if _is_plausible_area_record(record)]
    return _dedupe_area_records(filtered_area_records), _dedupe_labels(label_records)


def _polygon_match(
    point: Point,
    polygons: list[Polygon],
    tree: STRtree,
    representative_points: list[Point],
    max_distance: float,
) -> tuple[int, float] | None:
    candidate_indexes = tree.query(point, predicate="within")
    if len(candidate_indexes) == 0:
        candidate_indexes = tree.query(point)
    containing_indexes = [int(index) for index in candidate_indexes if polygons[int(index)].contains(point)]
    if containing_indexes:
        polygon_index = min(containing_indexes, key=lambda index: polygons[index].area)
        return polygon_index, 0.0

    nearest_candidates = tree.query(point.buffer(max_distance))
    if len(nearest_candidates) == 0:
        return None
    ranked = sorted(
        ((point.distance(representative_points[int(index)]), int(index)) for index in nearest_candidates),
        key=lambda item: (item[0], polygons[item[1]].area),
    )
    distance, polygon_index = ranked[0]
    if distance > max_distance:
        return None
    return polygon_index, distance


def _build_closed_space_inventory(polygons: list[Polygon], area_records: list[dict], labels: list[dict]) -> list[dict]:
    if not polygons:
        return []

    tree = STRtree(polygons)
    representative_points = [polygon.representative_point() for polygon in polygons]
    spaces: list[dict] = []

    area_links: dict[int, list[dict]] = defaultdict(list)
    for record in area_records:
        match = _polygon_match(Point(record["x"], record["y"]), polygons, tree, representative_points, AREA_TO_POLYGON_MAX_DISTANCE)
        if match is None:
            continue
        polygon_index, distance = match
        linked = record.copy()
        linked["distance"] = distance
        area_links[polygon_index].append(linked)

    label_links: dict[int, list[dict]] = defaultdict(list)
    for label in labels:
        match = _polygon_match(Point(label["x"], label["y"]), polygons, tree, representative_points, LABEL_TO_POLYGON_MAX_DISTANCE)
        if match is None:
            continue
        polygon_index, distance = match
        linked = label.copy()
        linked["distance"] = distance
        label_links[polygon_index].append(linked)

    for polygon_index, polygon in enumerate(polygons):
        centroid = polygon.representative_point()
        matched_areas = sorted(
            area_links.get(polygon_index, []),
            key=lambda record: (record["distance"], abs(record["value"] - polygon.area / AREA_SCALE), record["value"]),
        )
        matched_labels = sorted(label_links.get(polygon_index, []), key=_label_priority)
        nearby_labels = [
            {
                "text": label["text"],
                "layer": label["layer"],
                "x": label["x"],
                "y": label["y"],
                "distance": round(label["distance"], 3),
            }
            for label in matched_labels
            if label["distance"] <= LABEL_SEARCH_RADIUS
        ]
        meaningful_labels = [label for label in nearby_labels if _is_meaningful_label(label["text"])]
        primary_label = meaningful_labels[0]["text"] if meaningful_labels else (nearby_labels[0]["text"] if nearby_labels else None)
        primary_area_text = matched_areas[0]["value"] if matched_areas else None

        spaces.append(
            {
                "space_id": polygon_index,
                "polygon_area": round(polygon.area / AREA_SCALE, 3),
                "centroid": [round(centroid.x, 3), round(centroid.y, 3)],
                "primary_label": primary_label,
                "labels": nearby_labels,
                "meaningful_labels": meaningful_labels,
                "primary_area_text": primary_area_text,
                "area_text_candidates": [
                    {
                        "value": record["value"],
                        "layer": record["layer"],
                        "x": round(record["x"], 3),
                        "y": round(record["y"], 3),
                        "distance": round(record["distance"], 3),
                        "context": record["context"],
                        "source": record["source"],
                        "parse_kind": record.get("parse_kind"),
                        "secondary_value": record.get("secondary_value"),
                        "evidence": record.get("evidence", []),
                    }
                    for record in matched_areas
                ],
            }
        )
    return spaces


def _deduplicate_polygons(polygons: list[Polygon]) -> tuple[list[Polygon], int]:
    unique: list[Polygon] = []
    discarded = 0
    for polygon in sorted(polygons, key=lambda geom: geom.area):
        if polygon.is_empty or polygon.area <= MIN_AREA:
            discarded += 1
            continue

        polygon = polygon.buffer(0)
        duplicate = False
        for existing in unique:
            if polygon.equals(existing):
                duplicate = True
                break
            area_gap = polygon.symmetric_difference(existing).area
            if area_gap <= EPSILON and abs(polygon.area - existing.area) <= EPSILON:
                duplicate = True
                break
        if duplicate:
            discarded += 1
            continue
        unique.append(polygon)
    return unique, discarded


def _select_leaf_regions(polygons: list[Polygon]) -> tuple[list[Polygon], int]:
    kept: list[Polygon] = []
    discarded = 0
    for index, polygon in enumerate(polygons):
        contains_smaller = False
        for other_index, other in enumerate(polygons):
            if index == other_index or other.area >= polygon.area:
                continue
            if polygon.contains(other.representative_point()) and not polygon.equals(other):
                contains_smaller = True
                break
        if contains_smaller:
            discarded += 1
            continue
        kept.append(polygon)
    return kept, discarded


def load_polygons(input_path: Path, workdir: Path) -> tuple[list[Polygon], dict]:
    warnings: list[str] = []
    converted_dxf = input_path
    if input_path.suffix.lower() == ".dwg":
        converted_dxf = convert_dwg_to_dxf(input_path, workdir / "converted")

    document = ezdxf.readfile(converted_dxf)
    raw_polygons, collect_warnings = _collect_candidate_polygons(document.modelspace())
    warnings.extend(collect_warnings)

    unique_polygons, dedup_discarded = _deduplicate_polygons(raw_polygons)
    leaf_polygons, containment_discarded = _select_leaf_regions(unique_polygons)
    warnings.append(
        "Filtering summary: " f"raw={len(raw_polygons)} unique={len(unique_polygons)} leaf={len(leaf_polygons)}"
    )
    return leaf_polygons, {
        "converted_dxf": str(converted_dxf),
        "region_count_raw": len(raw_polygons),
        "regions_discarded": dedup_discarded + containment_discarded,
        "warnings": warnings,
    }


def build_report(input_path: Path, workdir: Path) -> dict:
    polygons, metadata = load_polygons(input_path, workdir)
    document = ezdxf.readfile(metadata["converted_dxf"])
    area_records, label_records = _collect_text_records(document)
    closed_spaces = _build_closed_space_inventory(polygons, area_records, label_records)

    labeled_spaces = [space for space in closed_spaces if space["primary_label"]]
    unlabeled_spaces = [space for space in closed_spaces if not space["primary_label"]]
    spaces_with_area_text = [space for space in closed_spaces if space["primary_area_text"] is not None]
    polygon_area_records = [{"value": space["polygon_area"]} for space in closed_spaces]

    return {
        "source_file": str(input_path),
        "converted_dxf": metadata["converted_dxf"],
        "room_count_total": len(polygons),
        "region_count_raw": metadata["region_count_raw"],
        "regions_discarded": metadata["regions_discarded"],
        "polygon_area_bucket_counts": _bucket_counts(polygon_area_records),
        "area_text_bucket_counts": _bucket_counts(area_records),
        "area_text_count": len(area_records),
        "label_count": len(label_records),
        "closed_space_count": len(closed_spaces),
        "closed_space_labeled_count": len(labeled_spaces),
        "closed_space_unlabeled_count": len(unlabeled_spaces),
        "closed_space_with_area_text_count": len(spaces_with_area_text),
        "closed_space_label_counts": dict(
            sorted(Counter(space["primary_label"] for space in labeled_spaces).items(), key=lambda item: (-item[1], item[0]))
        ),
        "closed_spaces": closed_spaces,
        "area_text_records": area_records,
        "label_records": label_records,
        "warnings": metadata["warnings"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a neutral closed-space inventory from a DWG or DXF floor plan.")
    parser.add_argument("--input-dwg", required=True, type=Path, help="Input DWG or DXF file.")
    parser.add_argument("--workdir", required=True, type=Path, help="Temporary working directory.")
    parser.add_argument("--output-json", required=True, type=Path, help="Report output path.")
    args = parser.parse_args()

    try:
        report = build_report(args.input_dwg.resolve(), args.workdir.resolve())
    except Exception as exc:  # noqa: BLE001
        error_report = {"source_file": str(args.input_dwg.resolve()), "error": str(exc)}
        print(json.dumps(error_report, ensure_ascii=False))
        return 1

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
