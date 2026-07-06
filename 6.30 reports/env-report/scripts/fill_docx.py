#!/usr/bin/env python3
"""Fill the sampling plan template with python-docx while preserving formatting."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


TABLE2_COLUMNS = ["检测项目", "检测依据", "样品保存条件和期限"]
TABLE3_KEYS = [
    "sampling_no",
    "workplace",
    "position",
    "people_per_shift",
    "job_type",
    "target",
    "project",
    "limit_type",
    "exposure_type",
    "sampling_mode",
    "time_type",
    "collector",
    "device",
    "flow_rate",
    "points_per_day",
    "times_per_day",
    "days",
    "sampling_time",
    "representative_time",
]


def import_docx():
    try:
        from docx import Document
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime env check
        raise RuntimeError("python-docx is not installed") from exc
    return Document


def set_cell_text(cell, text: str) -> None:
    text = text or ""
    paragraphs = cell.paragraphs
    if not paragraphs:
        paragraph = cell.add_paragraph()
        paragraph.add_run(text)
        return

    first_para = paragraphs[0]
    if first_para.runs:
        first_para.runs[0].text = text
        for run in first_para.runs[1:]:
            run.text = ""
    else:
        first_para.add_run(text)

    for paragraph in paragraphs[1:]:
        for run in paragraph.runs:
            run.text = ""


def append_cloned_row(table, template_row, insert_before_row_idx: int):
    new_tr = copy.deepcopy(template_row._tr)
    anchor = table.rows[insert_before_row_idx]._tr
    anchor.addprevious(new_tr)
    return table.rows[insert_before_row_idx]


def ensure_rows(
    table,
    start_row_idx: int,
    data_len: int,
    template_row_idx: int,
    note_row_idx: int,
) -> None:
    needed = start_row_idx + data_len
    while note_row_idx < needed:
        append_cloned_row(table, table.rows[template_row_idx], note_row_idx)
        note_row_idx += 1


def load_payload(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def set_paragraph_text(paragraph, text: str) -> None:
    text = text or ""
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(text)


def format_detection_type(value: str) -> str:
    options = ["委托检测", "定期检测", "评价检测"]
    normalized = (value or "").strip()
    parts = []
    for option in options:
        mark = "☑" if option == normalized else "□"
        parts.append(f"{mark}{option}")
    return "  ".join(parts)


def write_doc_meta(doc, header: Dict[str, str]) -> None:
    if len(doc.paragraphs) > 1:
        set_paragraph_text(doc.paragraphs[1], f"检测任务编号：{header.get('detection_task_no', '')}")


def write_header(table, header: Dict[str, str]) -> None:
    mapping: List[Tuple[Tuple[int, int], str]] = [
        ((0, 1), header.get("unit_name", "")),
        ((0, 5), header.get("contact", "")),
        ((1, 1), header.get("address", "")),
        ((1, 5), format_detection_type(header.get("detection_type", ""))),
    ]
    for (row_idx, cell_idx), value in mapping:
        set_cell_text(table.rows[row_idx].cells[cell_idx], value)


def write_table2(table, rows: List[Dict[str, str]]) -> None:
    start_row = 1
    template_row = 1
    note_row = len(table.rows) - 1
    ensure_rows(table, start_row, len(rows), template_row, note_row)
    for offset, row in enumerate(rows):
        target = table.rows[start_row + offset]
        set_cell_text(target.cells[0], row.get("检测项目", ""))
        set_cell_text(target.cells[1], row.get("检测依据", ""))
        set_cell_text(target.cells[2], row.get("样品保存条件和期限", ""))


def merge_vertical_same_value_cells(table, start_row: int, end_row: int, column_idx: int) -> None:
    if end_row <= start_row:
        return

    group_start = start_row
    current_value = table.rows[start_row].cells[column_idx].text.strip()

    for row_idx in range(start_row + 1, end_row + 1):
        row_value = table.rows[row_idx].cells[column_idx].text.strip()
        if row_value == current_value:
            continue
        if current_value and group_start < row_idx - 1:
            merged_cell = table.cell(group_start, column_idx).merge(table.cell(row_idx - 1, column_idx))
            set_cell_text(merged_cell, current_value)
        group_start = row_idx
        current_value = row_value

    if current_value and group_start < end_row:
        merged_cell = table.cell(group_start, column_idx).merge(table.cell(end_row, column_idx))
        set_cell_text(merged_cell, current_value)


def write_table3(table, rows: List[Dict[str, str]]) -> None:
    start_row = 1
    template_row = 1
    note_row = len(table.rows) - 1
    ensure_rows(table, start_row, len(rows), template_row, note_row)
    for offset, row in enumerate(rows):
        target = table.rows[start_row + offset]
        for idx, key in enumerate(TABLE3_KEYS):
            set_cell_text(target.cells[idx], row.get(key, ""))
    if rows:
        end_row = start_row + len(rows) - 1
        merge_vertical_same_value_cells(table, start_row, end_row, 1)
        merge_vertical_same_value_cells(table, start_row, end_row, 2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        Document = import_docx()
        payload = load_payload(args.payload)
        doc = Document(str(args.template))
    except Exception as exc:  # pragma: no cover - CLI error path
        print(str(exc), file=sys.stderr)
        return 1

    tables = doc.tables
    if len(tables) < 3:
        print("template does not contain the expected 3 tables", file=sys.stderr)
        return 1

    write_doc_meta(doc, payload.get("header", {}))
    write_header(tables[0], payload.get("header", {}))
    write_table2(tables[1], payload.get("table2", []))
    write_table3(tables[2], payload.get("table3", []))
    doc.save(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
