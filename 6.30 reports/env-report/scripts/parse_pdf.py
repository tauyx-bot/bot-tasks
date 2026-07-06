#!/usr/bin/env python3
"""Parse the survey PDF into a stable JSON payload for report filling."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


HEADER_KEYS = ["unit_name", "contact", "address", "detection_type"]
SURVEY_TABLE_KEYS = [
    "basic_info",
    "materials",
    "products",
    "equipment",
    "protection_facilities",
    "ppe",
    "overall_exposure",
    "detail_exposure",
    "attachments",
]
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
IGNORE_PROJECTS = {"", "/", "无"}
STOP_DETAIL_MARKERS = ("七、其他附件", "工艺名称")
SPLIT_PATTERN = re.compile(r"[、，,；;\n]+")


def import_pdfplumber():
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime env check
        raise RuntimeError("pdfplumber is not installed") from exc
    return pdfplumber


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\xa0", " ")
    text = text.replace("\r", "").replace("\t", " ").replace("\n", "")
    text = re.sub(r"\s+", "", text)
    return text.strip()


def dedupe(items: Iterable[str]) -> List[str]:
    seen: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def read_pdf_tables(path: Path) -> tuple[str, List[List[List[str]]]]:
    pdfplumber = import_pdfplumber()
    full_text_parts: List[str] = []
    raw_tables: List[List[List[str]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            full_text_parts.append(page.extract_text() or "")
            for table in page.extract_tables():
                collapsed_rows: List[List[str]] = []
                for row in table:
                    collapsed = [normalize_text(cell) for cell in row if normalize_text(cell)]
                    collapsed_rows.append(collapsed)
                if any(collapsed_rows):
                    raw_tables.append(collapsed_rows)
    return "\n".join(full_text_parts), raw_tables


def extract_header(full_text: str, raw_tables: List[List[List[str]]]) -> Dict[str, str]:
    field_map: Dict[str, str] = {}
    for table in raw_tables[:2]:
        for row in table:
            if len(row) < 2:
                continue
            for index in range(0, len(row) - 1, 2):
                label = normalize_text(row[index])
                value = normalize_text(row[index + 1])
                if label and value and label not in field_map:
                    field_map[label] = value

    compact = re.sub(r"\s+", " ", full_text)

    def search(pattern: str) -> str:
        match = re.search(pattern, compact)
        if not match:
            return ""
        return normalize_text(match.group(1))

    unit_name = field_map.get("用人单位") or search(r"用人单位\s+(.+?)\s+统一社会信用代码")
    service_address = field_map.get("技术服务地址（多个地址应逐一详细填写）")
    register_address = field_map.get("单位注册地址") or search(r"单位注册地址\s+(.+?)\s+技术服务地址")
    contact_name = field_map.get("职业卫生管理联系人") or search(r"职业卫生管理联系人\s+(.+?)\s+联系人电话")
    contact_phone = field_map.get("联系人电话") or search(r"联系人电话\s+(.+?)\s+联系人邮箱")
    detection_type = field_map.get("检测类型") or search(r"检测类型\s+(.+?)\s+是否存在射线装置")

    contact = " ".join(part for part in (contact_name, contact_phone) if part).strip()
    return {
        "unit_name": unit_name,
        "contact": contact,
        "address": service_address or register_address,
        "detection_type": detection_type,
    }


def is_overall_header(row: List[str]) -> bool:
    joined = "".join(row)
    return "单元或工作" in joined and "职业病危害因素" in joined and "劳动者姓名" in joined


def is_detail_header(row: List[str]) -> bool:
    joined = "".join(row)
    return "劳动者姓名" in joined and "接触的职业病危害因素" in joined


def parse_exposure_rows(raw_tables: List[List[List[str]]]) -> tuple[List[List[str]], List[List[str]]]:
    overall_rows: List[List[str]] = []
    detail_rows: List[List[str]] = []
    section: str | None = None

    for table in raw_tables:
        for row in table:
            if not row:
                continue
            joined = "".join(row)
            if "劳动定员和接触情况（总体情况）" in joined:
                section = "overall"
                continue
            if "详细接触情况（针对接触水平相对不稳定因素）" in joined:
                section = "detail"
                continue
            if row[0].startswith("七、其他附件") or row[0].startswith("工艺名称"):
                if section == "detail":
                    section = None
                continue
            if len(row) <= 3 and any(marker in joined for marker in STOP_DETAIL_MARKERS):
                if section == "detail":
                    section = None
                continue
            if joined.startswith("注："):
                continue
            if is_overall_header(row) or is_detail_header(row):
                continue
            if section == "overall" and len(row) >= 10:
                overall_rows.append(row)
            elif section == "detail" and len(row) >= 5:
                detail_rows.append(row)
    return overall_rows, detail_rows


def parse_overall_rows(rows: List[List[str]]) -> List[Dict[str, str]]:
    parsed: List[Dict[str, str]] = []
    for row in rows:
        values = row[:]
        if len(values) < 14:
            continue
        strength = ""
        worker = values[-1]
        if len(values) >= 16:
            strength = values[-2]
        parsed.append(
            {
                "workplace": values[0],
                "position": values[1],
                "shift": values[2],
                "total_people": values[3],
                "people_per_shift": values[4],
                "work_time": values[5],
                "job_type": values[6],
                "target": values[7],
                "project_raw": values[8],
                "source": values[9],
                "exposure_type": values[10],
                "daily_exposure": values[11],
                "weekly_days": values[12],
                "weekly_exposure": values[13],
                "strength": strength,
                "worker_name": worker,
            }
        )
    return parsed


def parse_detail_rows(rows: List[List[str]]) -> List[Dict[str, str]]:
    parsed: List[Dict[str, str]] = []
    context = {"worker_name": "", "workplace": "", "position": ""}
    for row in rows:
        values = row[:]
        if len(values) >= 9:
            record = {
                "worker_name": values[0],
                "workplace": values[1],
                "position": values[2],
                "trigger": values[3],
                "target": values[4],
                "job_type": values[5],
                "project_raw": values[6],
                "duration": values[7],
                "frequency": values[8],
            }
            context = {
                "worker_name": record["worker_name"],
                "workplace": record["workplace"],
                "position": record["position"],
            }
            parsed.append(record)
            continue
        if len(values) == 7:
            parsed.append(
                {
                    "worker_name": context["worker_name"],
                    "workplace": context["workplace"],
                    "position": context["position"],
                    "trigger": values[1],
                    "target": values[2],
                    "job_type": values[3],
                    "project_raw": values[4],
                    "duration": values[5],
                    "frequency": values[6],
                }
            )
            continue
        if len(values) == 6:
            parsed.append(
                {
                    "worker_name": context["worker_name"],
                    "workplace": context["workplace"],
                    "position": context["position"],
                    "trigger": values[0],
                    "target": values[1],
                    "job_type": values[2],
                    "project_raw": values[3],
                    "duration": values[4],
                    "frequency": values[5],
                }
            )
    return parsed


def split_projects(value: str) -> List[str]:
    normalized = normalize_text(value)
    if normalized in IGNORE_PROJECTS:
        return []
    items = [normalize_text(part) for part in SPLIT_PATTERN.split(normalized)]
    return [item for item in items if item not in IGNORE_PROJECTS]


def build_projects(overall_rows: List[Dict[str, str]], detail_rows: List[Dict[str, str]]) -> List[str]:
    projects: List[str] = []
    for row in overall_rows:
        projects.extend(split_projects(row.get("project_raw", "")))
    for row in detail_rows:
        projects.extend(split_projects(row.get("project_raw", "")))
    return dedupe(projects)


def match_overall_row(detail_row: Dict[str, str], overall_rows: List[Dict[str, str]]) -> Dict[str, str] | None:
    detail_workplace = detail_row.get("workplace", "")
    detail_position = detail_row.get("position", "")
    for row in overall_rows:
        same_position = row.get("position", "") == detail_position
        overlapping_workplace = detail_workplace in row.get("workplace", "") or row.get("workplace", "") in detail_workplace
        if same_position and overlapping_workplace:
            return row
    for row in overall_rows:
        if row.get("position", "") == detail_position:
            return row
    return None


def make_table3_row(
    workplace: str,
    position: str,
    people_per_shift: str,
    job_type: str,
    target: str,
    project: str,
    exposure_type: str,
    sampling_time: str = "",
    representative_time: str = "",
) -> Dict[str, str]:
    row = {key: "" for key in TABLE3_KEYS}
    row.update(
        {
            "workplace": workplace,
            "position": position,
            "people_per_shift": people_per_shift,
            "job_type": job_type,
            "target": target,
            "project": project,
            "exposure_type": exposure_type,
            "sampling_time": sampling_time,
            "representative_time": representative_time,
        }
    )
    return row


def build_table3(overall_rows: List[Dict[str, str]], detail_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if detail_rows:
        for detail_row in detail_rows:
            projects = split_projects(detail_row.get("project_raw", ""))
            if not projects:
                continue
            overall_row = match_overall_row(detail_row, overall_rows) or {}
            people_per_shift = overall_row.get("people_per_shift", "")
            overall_job_type = overall_row.get("job_type", "")
            exposure_type = overall_row.get("exposure_type", "")
            target_prefix = detail_row.get("trigger", "")
            target_value = detail_row.get("target", "")
            target = f"{target_prefix}:{target_value}" if target_prefix and target_value else target_value or target_prefix
            for project in projects:
                rows.append(
                    make_table3_row(
                        workplace=detail_row.get("workplace", "") or overall_row.get("workplace", ""),
                        position=detail_row.get("position", "") or overall_row.get("position", ""),
                        people_per_shift=people_per_shift,
                        job_type=overall_job_type or detail_row.get("job_type", ""),
                        target=target,
                        project=project,
                        exposure_type=exposure_type,
                        sampling_time=detail_row.get("duration", ""),
                        representative_time=detail_row.get("duration", ""),
                    )
                )
        if rows:
            return rows

    for overall_row in overall_rows:
        projects = split_projects(overall_row.get("project_raw", ""))
        for project in projects:
            rows.append(
                make_table3_row(
                    workplace=overall_row.get("workplace", ""),
                    position=overall_row.get("position", ""),
                    people_per_shift=overall_row.get("people_per_shift", ""),
                    job_type=overall_row.get("job_type", ""),
                    target=overall_row.get("target", ""),
                    project=project,
                    exposure_type=overall_row.get("exposure_type", ""),
                )
            )
    return rows


def build_survey_tables(
    overall_rows: List[List[str]],
    detail_rows: List[List[str]],
) -> Dict[str, List[Any]]:
    survey_tables: Dict[str, List[Any]] = {key: [] for key in SURVEY_TABLE_KEYS}
    survey_tables["overall_exposure"] = overall_rows
    survey_tables["detail_exposure"] = detail_rows
    return survey_tables


def build_missing_fields(header: Dict[str, str], overall_rows: List[Dict[str, str]], projects: List[str]) -> List[str]:
    missing: List[str] = []
    for key in HEADER_KEYS:
        if not header.get(key):
            missing.append(f"header.{key}")
    if not overall_rows:
        missing.append("survey_tables.overall_exposure")
    if not projects:
        missing.append("table2.projects")
    return missing


def build_payload(pdf_path: Path) -> Dict[str, Any]:
    full_text, raw_tables = read_pdf_tables(pdf_path)
    header = extract_header(full_text, raw_tables)
    overall_raw_rows, detail_raw_rows = parse_exposure_rows(raw_tables)
    overall_rows = parse_overall_rows(overall_raw_rows)
    detail_rows = parse_detail_rows(detail_raw_rows)
    projects = build_projects(overall_rows, detail_rows)
    table3 = build_table3(overall_rows, detail_rows)
    survey_tables = build_survey_tables(overall_raw_rows, detail_raw_rows)
    missing_fields = build_missing_fields(header, overall_rows, projects)
    return {
        "header": header,
        "survey_tables": survey_tables,
        "projects": projects,
        "table3": table3,
        "missing_fields": dedupe(missing_fields),
    }


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
