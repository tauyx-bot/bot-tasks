#!/usr/bin/env python3
"""Parse volatile-organic-component analysis PDFs into structured JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


def import_pdfplumber():
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime env check
        raise RuntimeError("pdfplumber is not installed") from exc
    return pdfplumber


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", "", str(value).replace("\u3000", " ").replace("\xa0", " ")).strip()


def first_index(row: List[str], *markers: str) -> int | None:
    for index, value in enumerate(row):
        if all(marker in value for marker in markers):
            return index
    return None


def last_index(row: List[str], *markers: str) -> int | None:
    indexes = [
        index
        for index, value in enumerate(row)
        if all(marker in value for marker in markers)
    ]
    return indexes[-1] if indexes else None


def dedupe_components(components: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: List[Dict[str, str]] = []
    for component in components:
        key = (
            component.get("name", ""),
            component.get("cas_no", ""),
            component.get("percentage", ""),
        )
        if not key[0] or key in seen:
            continue
        seen.add(key)
        result.append(component)
    return result


def parse_tables(raw_tables: List[List[List[str]]]) -> Dict[str, object]:
    sample_meta: Dict[tuple[str, str], Dict[str, str]] = {}
    samples: Dict[tuple[str, str], Dict[str, object]] = {}

    for table in raw_tables:
        normalized = [[normalize_text(cell) for cell in row] for row in table]

        basic_header_index = next(
            (
                index
                for index, row in enumerate(normalized)
                if first_index(row, "样品名称") is not None
                and first_index(row, "样品性状") is not None
                and first_index(row, "使用岗位") is not None
            ),
            None,
        )
        if basic_header_index is not None and basic_header_index + 1 < len(normalized):
            header = normalized[basic_header_index]
            name_idx = first_index(header, "样品名称")
            number_idx = first_index(header, "样品编号")
            workplace_idx = first_index(header, "使用", "工作场所")
            position_idx = first_index(header, "使用岗位")
            target_idx = first_index(header, "取样场所", "地点")
            for row in normalized[basic_header_index + 1 :]:
                if any("样品分析结果" in value for value in row):
                    break
                name = row[name_idx] if name_idx is not None and name_idx < len(row) else ""
                number = row[number_idx] if number_idx is not None and number_idx < len(row) else ""
                if not name or not number:
                    continue
                sample_meta[(name, number)] = {
                    "workplace": row[workplace_idx] if workplace_idx is not None and workplace_idx < len(row) else "",
                    "position": row[position_idx] if position_idx is not None and position_idx < len(row) else "",
                    "target": row[target_idx] if target_idx is not None and target_idx < len(row) else "",
                }

        analysis_header_index = next(
            (
                index
                for index, row in enumerate(normalized)
                if first_index(row, "样品名称") is not None
                and first_index(row, "检出的挥发性有机组分名称") is not None
                and first_index(row, "CAS号") is not None
                and first_index(row, "峰面积百分比") is not None
            ),
            None,
        )
        if analysis_header_index is None:
            continue

        header = normalized[analysis_header_index]
        name_idx = first_index(header, "样品名称")
        number_idx = first_index(header, "样品编号")
        component_idx = first_index(header, "检出的挥发性有机组分名称")
        cas_idx = first_index(header, "CAS号")
        # The table also contains total volatile/inorganic percentages before
        # the per-component result; the component percentage is the last one.
        percentage_idx = last_index(header, "峰面积百分比")
        current_key: tuple[str, str] | None = None

        for row in normalized[analysis_header_index + 1 :]:
            sample_number = row[number_idx] if number_idx is not None and number_idx < len(row) else ""
            sample_name = row[name_idx] if name_idx is not None and name_idx < len(row) else ""
            if sample_number:
                current_key = (sample_name, sample_number)
                meta = sample_meta.get(current_key, {})
                samples.setdefault(
                    current_key,
                    {
                        "sample_name": sample_name,
                        "sample_no": sample_number,
                        "workplace": meta.get("workplace", ""),
                        "position": meta.get("position", ""),
                        "target": meta.get("target", ""),
                        "components": [],
                    },
                )
            if current_key is None:
                continue
            component = row[component_idx] if component_idx is not None and component_idx < len(row) else ""
            cas_no = row[cas_idx] if cas_idx is not None and cas_idx < len(row) else ""
            percentage = row[percentage_idx] if percentage_idx is not None and percentage_idx < len(row) else ""
            if component:
                samples[current_key]["components"].append(
                    {"name": component, "cas_no": cas_no, "percentage": percentage}
                )

    result = list(samples.values())
    for sample in result:
        sample["components"] = dedupe_components(sample.get("components", []))
    return {"samples": result}


def build_payload(pdf_path: Path) -> Dict[str, object]:
    pdfplumber = import_pdfplumber()
    raw_tables: List[List[List[str]]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_tables.extend(page.extract_tables())
    payload = parse_tables(raw_tables)
    if not payload["samples"]:
        raise RuntimeError("component report does not contain a recognizable analysis table")
    if any(not sample.get("components") for sample in payload["samples"]):
        raise RuntimeError("component report contains a sample without detected components")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = build_payload(args.pdf)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(str(exc), file=sys.stderr)
        return 1
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
