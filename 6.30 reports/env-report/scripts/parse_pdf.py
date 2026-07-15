#!/usr/bin/env python3
"""Parse the survey PDF into a stable JSON payload for report filling."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


HEADER_KEYS = ["detection_task_no", "unit_name", "contact", "address", "detection_type"]
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
SPLIT_PATTERN = re.compile(r"[、，,；;\n]+")
PARSING_RULES: Dict[str, Any] = {}


def import_pdfplumber():
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime env check
        raise RuntimeError("pdfplumber is not installed") from exc
    return pdfplumber


def load_parsing_rules(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"report rules file not found: {path}")
    rules = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rules, dict) or not isinstance(rules.get("parsing"), dict):
        raise RuntimeError("report rules file must contain a parsing object")
    return rules["parsing"]


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


def extract_field_map(raw_tables: List[List[List[str]]]) -> Dict[str, str]:
    field_map: Dict[str, str] = {}
    for table in raw_tables:
        for row in table:
            if len(row) < 2:
                continue
            for index in range(0, len(row) - 1, 2):
                label = normalize_text(row[index])
                value = normalize_text(row[index + 1])
                if label and value and label not in field_map:
                    field_map[label] = value
    return field_map


def extract_table1_title(raw_tables: List[List[List[str]]]) -> str:
    if not raw_tables:
        return ""
    for row in raw_tables[0][:3]:
        joined = "".join(row)
        if "职业卫生现场调查记录表" in joined:
            return joined
    return ""


def extract_header(full_text: str, raw_tables: List[List[List[str]]]) -> Dict[str, str]:
    field_map = extract_field_map(raw_tables)
    title_text = normalize_text(extract_table1_title(raw_tables))
    compact = re.sub(r"\s+", " ", full_text)

    def search(pattern: str) -> str:
        match = re.search(pattern, compact)
        if not match:
            return ""
        return normalize_text(match.group(1))

    def search_title(pattern: str) -> str:
        match = re.search(pattern, title_text)
        if not match:
            return ""
        return normalize_text(match.group(1))

    detection_task_no = search_title(r"检测任务编号(.+?)调查日期") or search(r"检测任务编号\s+(.+?)\s+调查日期")
    unit_name = field_map.get("用人单位") or search(r"用人单位\s+(.+?)\s+统一社会信用代码")
    service_address = field_map.get("技术服务地址（多个地址应逐一详细填写）")
    register_address = field_map.get("单位注册地址") or search(r"单位注册地址\s+(.+?)\s+技术服务地址")
    contact_name = field_map.get("职业卫生管理联系人") or search(r"职业卫生管理联系人\s+(.+?)\s+联系人电话")
    contact_phone = field_map.get("联系人电话") or search(r"联系人电话\s+(.+?)\s+联系人邮箱")
    detection_type = (
        field_map.get("检测类型")
        or search_title(r"职业卫生现场调查记录表[（(](.+?)[）)]")
        or search(r"检测类型\s+(.+?)\s+是否存在射线装置")
    )

    contact = " ".join(part for part in (contact_name, contact_phone) if part).strip()
    return {
        "detection_task_no": detection_task_no,
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
            if any(row[0].startswith(marker) for marker in PARSING_RULES["detail_stop_markers"]):
                if section == "detail":
                    section = None
                continue
            if len(row) <= 3 and any(marker in joined for marker in PARSING_RULES["detail_stop_markers"]):
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
    ignored_projects = set(PARSING_RULES["ignored_projects"])
    if normalized in ignored_projects:
        return []
    items = [normalize_text(part) for part in SPLIT_PATTERN.split(normalized)]
    return [item for item in items if item not in ignored_projects]


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


def work_duration(work_time: str) -> str:
    """Convert a survey shift schedule such as 08:00-12:00 13:30-17:30 to hours."""
    values = re.findall(r"(\d{1,2})[：:](\d{2})", work_time or "")
    if len(values) < 2:
        return ""

    minutes = [int(hour) * 60 + int(minute) for hour, minute in values]
    total = sum(end - start for start, end in zip(minutes[::2], minutes[1::2]) if end >= start)
    if not total:
        return ""
    hours = total / 60
    return f"{hours:g}h"


def sampling_target(value: str) -> str:
    """Keep the sampling object/location and drop the repeated operation wording."""
    target = normalize_text(value)
    suffix_name = PARSING_RULES["workbench_suffix"]
    workbench_end = target.find(suffix_name)
    if workbench_end < 0:
        return target

    workbench_end += len(suffix_name)
    suffix = target[workbench_end:]
    # A parenthetical process moment is meaningful sampling information; ordinary
    # action text such as "扪鞋工位扪鞋" merely repeats the location.
    if suffix.startswith("（") or suffix.startswith("("):
        return target
    return target[:workbench_end]


def sampling_targets(value: str) -> List[str]:
    """Extract every explicit sampling location from an overall exposure row."""
    targets = [sampling_target(part) for part in re.split(r"[；;]", value or "")]
    return dedupe(target for target in targets if target)


def build_table3(overall_rows: List[Dict[str, str]], detail_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    matched_overall_rows: set[int] = set()
    if detail_rows:
        for detail_row in detail_rows:
            projects = split_projects(detail_row.get("project_raw", ""))
            if not projects:
                continue
            overall_row = match_overall_row(detail_row, overall_rows) or {}
            if overall_row in overall_rows:
                overall_index = overall_rows.index(overall_row)
                # The overall table is authoritative when it explicitly lists
                # multiple locations.  Its full hazard-factor list applies to
                # every listed location, while the detail table supplies timing.
                if len(sampling_targets(overall_row.get("target", ""))) > 1:
                    continue
                matched_overall_rows.add(overall_index)
            people_per_shift = overall_row.get("people_per_shift", "")
            overall_job_type = overall_row.get("job_type", "")
            exposure_type = overall_row.get("exposure_type", "")
            target = sampling_target(detail_row.get("target", ""))
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
    for index, overall_row in enumerate(overall_rows):
        targets = sampling_targets(overall_row.get("target", ""))
        if index in matched_overall_rows and overall_row.get("exposure_type", "") == PARSING_RULES["detail_preferred_exposure_type"]:
            continue
        projects = split_projects(overall_row.get("project_raw", ""))
        for target in targets or [sampling_target(overall_row.get("target", ""))]:
            for project in projects:
                rows.append(
                    make_table3_row(
                        workplace=overall_row.get("workplace", ""),
                        position=overall_row.get("position", ""),
                        people_per_shift=overall_row.get("people_per_shift", ""),
                        job_type=overall_row.get("job_type", ""),
                        target=target,
                        project=project,
                        exposure_type=overall_row.get("exposure_type", ""),
                        representative_time=work_duration(overall_row.get("work_time", "")),
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


def build_payload(pdf_path: Path, config_path: Path) -> Dict[str, Any]:
    global PARSING_RULES
    PARSING_RULES = load_parsing_rules(config_path)
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
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()

    try:
        config_path = args.config or Path(__file__).resolve().parent.parent / "knowledge" / "report_rules.json"
        payload = build_payload(args.pdf, config_path)
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
