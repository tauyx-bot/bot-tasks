#!/usr/bin/env python3
"""Extract "附件1：企业基础信息收集表" from DOCX files into JSON files.

Usage:
    python3 extract_attachment1.py
    python3 extract_attachment1.py --input-dir /path/to/docx --output-dir test/results

The script only uses the Python standard library.  It identifies the table by
the distinctive "单位名称（盖章）" field, so it does not depend on a fixed table
position in the document.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
TARGET_FIELD = "单位名称（盖章）"
CHECKED_SYMBOL = "00FE"  # Wingdings: checked box; 00A8 is the empty box


@dataclass
class Cell:
    text: str
    selected_options: list[str] | None = None


def cell_text(cell: ET.Element) -> str:
    """Return all displayed text in a Word table cell."""
    return "".join(cell.itertext()).replace("\u00a0", " ").strip()


def cell_info(cell: ET.Element) -> Cell:
    """Read text and, where present, selected Wingdings checkbox options."""
    selected: list[str] = []
    contains_checkbox = False
    selected_marker_seen = False

    # In these forms each option is a Wingdings symbol followed by its label.
    # 00FE denotes a selected box, while 00A8 denotes an empty one.
    for run in cell.findall(".//w:r", NS):
        symbol = run.find("w:sym", NS)
        if symbol is not None:
            contains_checkbox = True
            selected_marker_seen = symbol.get(f"{{{W_NS}}}char", "").upper() == CHECKED_SYMBOL
            continue
        run_text = "".join(run.itertext()).strip()
        if selected_marker_seen and run_text:
            # A semicolon is visual punctuation between checkbox options, not
            # part of the selected value.
            option = run_text.strip(" ；;")
            if option:
                selected.append(option)
            selected_marker_seen = False

    return Cell(cell_text(cell), selected if contains_checkbox else None)


def top_level_tables(docx_path: Path) -> Iterable[list[list[Cell]]]:
    """Yield body-level tables as rows of cell strings from a DOCX archive."""
    with zipfile.ZipFile(docx_path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))

    body = document.find("w:body", NS)
    if body is None:
        return
    for table in body.findall("w:tbl", NS):
        rows = []
        for row in table.findall("w:tr", NS):
            rows.append([cell_info(cell) for cell in row.findall("w:tc", NS)])
        yield rows


def put_value(fields: dict[str, object], label: str, value: object) -> None:
    """Add a field without silently discarding duplicate labels."""
    # Spaces inside labels are only Word's visual table spacing (for example
    # "防雷装                  置"), not part of the field name.
    label = "".join(label.split())
    if label == "区域建筑物" and isinstance(value, str):
        value = parse_building_info(value)
    if not label:
        return
    if label not in fields:
        fields[label] = value
        return
    if fields[label] == value:
        return
    suffix = 2
    while f"{label}_{suffix}" in fields:
        suffix += 1
    fields[f"{label}_{suffix}"] = value


def parse_building_info(text: str) -> dict[str, str]:
    """Split the compound 区域建筑物 cell into its four form fields."""
    field_patterns = {
        "面积": r"(?:区域建筑物)?面积\s*[：:]\s*([^；;。]+)",
        "建筑高度": r"建筑高度\s*[：:]\s*([^；;。]+)",
        "等效高度": r"等效高度\s*[：:]\s*([^；;。]+)",
        "相对高度": r"相对高度\s*[：:]\s*([^；;。]+)",
    }
    result = {
        name: match.group(1).strip()
        for name, pattern in field_patterns.items()
        if (match := re.search(pattern, text))
    }
    return result or {"原始值": text}


def rows_to_fields(rows: list[list[Cell]]) -> dict[str, object]:
    """Convert the label/value layout of the collection form to flat fields."""
    fields: dict[str, object] = {}
    for row in rows:
        if not any(cell.text.strip() for cell in row) or [cell.text for cell in row] == ["基本情况", TARGET_FIELD]:
            continue

        # The form starts with a vertically merged "基本情况" cell.  In XML it
        # appears only in the first row; the remaining cells are normal pairs.
        cells = row[:]
        if cells and cells[0].text == "基本情况":
            cells = cells[1:]
        cells = [cell for cell in cells if cell.text.strip()]
        if not cells:
            continue

        # Most rows contain alternating label/value cells.  An odd last group
        # (for example 经纬度) is one label with several displayed value cells.
        pair_count = len(cells) - (len(cells) % 2)
        for index in range(0, pair_count, 2):
            value_cell = cells[index + 1]
            value: object = value_cell.selected_options if value_cell.selected_options is not None else value_cell.text
            put_value(fields, cells[index].text, value)
        if len(cells) % 2:
            if pair_count:
                # A trailing unmatched cell is normally continuation text for
                # the preceding value; retain it instead of losing data.
                previous_label = cells[pair_count - 2].text
                fields[previous_label] = f"{fields[previous_label]}；{cells[-1].text}"
            else:
                put_value(fields, cells[0].text, "")
    return fields


def extract_attachment(docx_path: Path) -> dict[str, object]:
    for rows in top_level_tables(docx_path):
        if any(TARGET_FIELD in cell.text for row in rows for cell in row):
            return rows_to_fields(rows)
    raise ValueError("未找到附件1表格（缺少“单位名称（盖章）”字段）")


def main() -> int:
    parser = argparse.ArgumentParser(description="提取 DOCX 中的附件1企业基础信息表")
    parser.add_argument("--input-dir", type=Path, default=Path.cwd(), help="DOCX 所在目录")
    parser.add_argument("--output-dir", type=Path, default=Path("test/results"), help="JSON 输出目录")
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    docx_files = sorted(path for path in input_dir.rglob("*.docx") if output_dir not in path.parents)
    if not docx_files:
        print(f"未在 {input_dir} 找到 DOCX 文件")
        return 1

    failed = 0
    for docx_path in docx_files:
        try:
            fields = extract_attachment(docx_path)
            result = {
                "source_file": str(docx_path.relative_to(input_dir)),
                "附件1：企业基础信息收集表": fields,
            }
            output_path = output_dir / f"{docx_path.stem}.json"
            output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"已写入: {output_path}")
        except (OSError, ET.ParseError, ValueError, zipfile.BadZipFile) as error:
            failed += 1
            print(f"处理失败: {docx_path} ({error})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
