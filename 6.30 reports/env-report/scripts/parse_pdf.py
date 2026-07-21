#!/usr/bin/env python3
"""Parse the survey PDF into a stable JSON payload for report filling."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


HEADER_KEYS = [
    "detection_task_no",
    "unit_name",
    "contact",
    "address",
    "detection_type",
    "expected_sampling_time",
]
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
    "job_group_id",
    "job_workplace",
    "job_work_content",
    "job_representative_time",
    "source_job_type",
    "job_type_inference_reason",
    "workplace",
    "position",
    "people_per_shift",
    "workstation_count",
    "workstation_count_source",
    "job_type",
    "target",
    "project",
    "exposure_type",
    "sampling_time",
    "representative_time",
]
SPLIT_PATTERN = re.compile(r"[、，,；;\n]+")
WORK_CONTENT_SPLIT_PATTERN = re.compile(r"\s*(?:、|，|,|；|;|/|\n)+\s*")
LOCATION_MARKERS = ("工位", "岗位", "车间", "区域", "区", "营业厅", "库", "房")
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

    # The target form has one compact contact cell; source fields already carry
    # any punctuation needed inside a name or phone number.
    contact = "".join(part for part in (contact_name, contact_phone) if part).strip()
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


def parse_equipment_rows(raw_tables: List[List[List[str]]]) -> List[Dict[str, str]]:
    """Extract the production-equipment section, including page continuations."""
    rows: List[Dict[str, str]] = []
    in_section = False
    saw_header = False
    for table in raw_tables:
        for row in table:
            if not row:
                continue
            joined = "".join(row)
            if "三、主要生产设备情况" in joined:
                in_section = True
                saw_header = False
                continue
            if not in_section:
                continue
            if "设备名称" in joined and "运行数" in joined and "使用岗位" in joined:
                saw_header = True
                continue
            if "设备布局：" in joined or "四、职业病防护设施" in joined:
                in_section = False
                saw_header = False
                continue
            if not saw_header or len(row) < 7:
                continue
            values = row[:7]
            if not re.fullmatch(r"\d+(?:\.\d+)?", values[2]) or not re.fullmatch(
                r"\d+(?:\.\d+)?", values[3]
            ):
                continue
            rows.append(
                {
                    "name": values[0],
                    "model": values[1],
                    "total_count": values[2],
                    "running_count": values[3],
                    "workplace": values[4],
                    "position": values[5],
                    "layout": values[6],
                }
            )
    return rows


def parse_rows_after_header(
    raw_tables: List[List[List[str]]],
    required_header_terms: tuple[str, ...],
    fields: tuple[str, ...],
    stop_terms: tuple[str, ...],
    minimum_fields: int | None = None,
) -> List[Dict[str, str]]:
    """Extract a survey section that may continue in a new PDF table/page."""
    parsed: List[Dict[str, str]] = []
    in_section = False
    for table in raw_tables:
        for row in table:
            if not row:
                continue
            joined = "".join(row)
            if all(term in joined for term in required_header_terms):
                in_section = True
                continue
            if not in_section:
                continue
            if joined.startswith("注：") or any(term in joined for term in stop_terms):
                in_section = False
                continue
            required_count = minimum_fields if minimum_fields is not None else len(fields)
            if len(row) < required_count:
                continue
            values = row[: len(fields)] + [""] * max(0, len(fields) - len(row))
            parsed.append(dict(zip(fields, values)))
    return parsed


def parse_supporting_survey_tables(
    raw_tables: List[List[List[str]]],
) -> Dict[str, List[Dict[str, str]]]:
    """Extract supporting tables that can inform current or future plan rules."""
    return {
        "materials": parse_rows_after_header(
            raw_tables,
            ("原辅材料名称", "主要成分", "使用岗位"),
            ("name", "annual_use", "physical_state", "components", "workplace", "position"),
            ("产品名称", "三、主要生产设备情况"),
        ),
        "products": parse_rows_after_header(
            raw_tables,
            ("产品名称", "年产量", "包装方式"),
            ("name", "annual_output", "physical_state", "packaging"),
            ("三、主要生产设备情况",),
        ),
        "protection_facilities": parse_rows_after_header(
            raw_tables,
            ("设置地点或岗位", "防护设施名称", "运行数"),
            ("workplace", "target", "name", "type", "total_count", "running_count", "notes"),
            ("防护用品分类", "五、职业病防护用品"),
            minimum_fields=6,
        ),
        "ppe": parse_rows_after_header(
            raw_tables,
            ("防护用品分类", "生产厂家", "使用岗位"),
            (
                "classification",
                "category",
                "manufacturer",
                "model",
                "workplace",
                "position",
                "replacement_cycle",
                "wearing_status",
                "notes",
            ),
            ("六、岗位设置和接触情况",),
            minimum_fields=8,
        ),
    }


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
            continue
        if len(values) == 5:
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
                    "frequency": "",
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
    projects = dedupe(projects)
    # A detail row can repeat the parenthetical component of an overall-table
    # factor, e.g. "金属粉尘" after "其他粉尘（金属粉尘）".  The complete
    # overall factor is the reportable project; do not list both in Table 2.
    return [
        project
        for project in projects
        if not any(
            project != candidate
            and (f"（{project}）" in candidate or f"({project})" in candidate)
            for candidate in projects
        )
    ]


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
    job_group_id: str,
    job_workplace: str,
    job_work_content: str,
    job_representative_time: str,
    source_job_type: str,
    job_type_inference_reason: str,
    workplace: str,
    position: str,
    people_per_shift: str,
    workstation_count: str,
    workstation_count_source: str,
    job_type: str,
    target: str,
    project: str,
    exposure_type: str,
    sampling_time: str = "",
    representative_time: str = "",
) -> Dict[str, str]:
    job_type = {"固定作业": "固定", "流动作业": "流动"}.get(job_type, job_type)
    row = {key: "" for key in TABLE3_KEYS}
    row.update(
        {
            "job_group_id": job_group_id,
            "job_workplace": job_workplace,
            "job_work_content": job_work_content,
            "job_representative_time": job_representative_time,
            "source_job_type": source_job_type,
            "job_type_inference_reason": job_type_inference_reason,
            "workplace": workplace,
            "position": position,
            "people_per_shift": people_per_shift,
            "workstation_count": workstation_count,
            "workstation_count_source": workstation_count_source,
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


def overall_representative_time(overall_row: Dict[str, str]) -> str:
    """Prefer the surveyed daily exposure and fall back to the shift schedule."""
    match = re.search(r"(\d+(?:\.\d+)?)", overall_row.get("daily_exposure", ""))
    if match:
        hours = float(match.group(1))
        if hours > 0:
            return f"{hours:g}h"
    return work_duration(overall_row.get("work_time", ""))


def normalize_work_time_window(value: str) -> str:
    """Normalize every shift interval while discarding summary annotations."""
    intervals = re.findall(
        r"(\d{1,2})[：:](\d{2})\s*[-－—]\s*(\d{1,2})[：:](\d{2})",
        value or "",
    )
    return "，".join(
        f"{int(start_hour)}:{start_minute}-{int(end_hour)}:{end_minute}"
        for start_hour, start_minute, end_hour, end_minute in intervals
    )


def expected_sampling_time(overall_rows: List[Dict[str, str]]) -> str:
    """Use the common work window when all detected positions share one shift."""
    detected_rows = [
        row for row in overall_rows if split_projects(row.get("project_raw", ""))
    ]
    candidate_rows = detected_rows or overall_rows
    windows = dedupe(
        normalize_work_time_window(row.get("work_time", ""))
        for row in candidate_rows
    )
    return windows[0] if len(windows) == 1 else ""


def parsed_duration_hours(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|小时)", value or "", re.IGNORECASE)
    return float(match.group(1)) if match else None


def inferred_job_context(
    overall_index: int,
    overall_row: Dict[str, str],
    detail_rows: List[Dict[str, str]],
    overall_rows: List[Dict[str, str]],
) -> Dict[str, str]:
    """Infer mobile work only when detailed locations cover the full workday."""
    source_job_type = overall_row.get("job_type", "")
    matched_details = [
        detail
        for detail in detail_rows
        if match_overall_row(detail, overall_rows) is overall_row
    ]
    work_contents = dedupe(
        detail_work_content(detail.get("target", ""), detail.get("job_type", ""))
        for detail in matched_details
    )
    overall_work_content = normalize_text(overall_row.get("target", ""))
    work_contents.sort(
        key=lambda content: (
            overall_work_content.find(content)
            if content and content in overall_work_content
            else len(overall_work_content)
        )
    )
    duration_by_target: Dict[str, float] = {}
    for detail in matched_details:
        target = sampling_target(detail.get("target", ""))
        duration = parsed_duration_hours(detail.get("duration", ""))
        if target and duration is not None:
            duration_by_target[target] = max(duration_by_target.get(target, 0), duration)

    effective_job_type = source_job_type
    inference_reason = ""
    overall_hours = parsed_duration_hours(overall_representative_time(overall_row))
    detailed_hours = sum(duration_by_target.values())
    if (
        source_job_type == "固定作业"
        and len(duration_by_target) >= 2
        and overall_hours is not None
        and abs(detailed_hours - overall_hours) <= 0.25
    ):
        effective_job_type = "流动作业"
        inference_reason = (
            f"详细接触记录包含{len(duration_by_target)}个工位，"
            f"工位时长合计{detailed_hours:g}h，与每日接触时间{overall_hours:g}h一致"
        )
    return {
        "job_group_id": f"overall:{overall_index}",
        "source_job_type": source_job_type,
        "job_type": effective_job_type,
        "job_type_inference_reason": inference_reason,
        "job_work_content": "、".join(work_contents),
    }


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


def detail_work_content(target: str, activity: str) -> str:
    """Combine the detailed location and its work content without duplication."""
    locations = [
        normalize_text(part)
        for part in WORK_CONTENT_SPLIT_PATTERN.split(target or "")
        if normalize_text(part) not in {"", "/"}
    ]
    actions = [
        normalize_text(part)
        for part in WORK_CONTENT_SPLIT_PATTERN.split(activity or "")
        if normalize_text(part) not in {"", "/"}
    ]
    if len(locations) > 1 and len(locations) == len(actions):
        return "、".join(
            detail_work_content(location, action)
            for location, action in zip(locations, actions)
        )
    location = "、".join(locations) or normalize_text(target)
    action = "、".join(actions) or normalize_text(activity)
    if not action or action in {"/", "固定", "固定作业", "流动", "流动作业"}:
        return location
    if location.endswith(action):
        return location
    return f"{location}{action}"


def sampling_targets(value: str) -> List[str]:
    """Extract every explicit sampling location from an overall exposure row."""
    targets: List[str] = []
    previous_was_location = False
    for raw_part in WORK_CONTENT_SPLIT_PATTERN.split(value or ""):
        part = normalize_text(raw_part)
        if not part:
            continue
        is_location = any(marker in part for marker in LOCATION_MARKERS)
        # PDF cells often wrap "location/action" across a slash or newline.
        # A standalone non-location token immediately after a location is its
        # work content, not a second sampling point.
        if previous_was_location and not is_location:
            previous_was_location = False
            continue
        targets.append(sampling_target(part))
        previous_was_location = is_location
    return dedupe(target for target in targets if target)


def workstation_context(
    workplace: str,
    position: str,
    target: str,
    equipment_rows: List[Dict[str, str]],
) -> tuple[str, str]:
    """Infer the number of equivalent fixed workstations from running equipment."""
    matches = [
        equipment
        for equipment in equipment_rows
        if equipment.get("position", "") == position
        and (
            not workplace
            or not equipment.get("workplace", "")
            or equipment.get("workplace", "") in workplace
            or workplace in equipment.get("workplace", "")
        )
    ]
    target_core = re.sub(r"(?:工作)?工位|操作|作业", "", sampling_target(target))

    def matches_target(equipment: Dict[str, str]) -> bool:
        equipment_core = re.sub(
            r"(?:生产线|交流机|压合机|机|台|槽|炉|枪|床|箱)$",
            "",
            equipment.get("name", ""),
        )
        return bool(
            equipment_core
            and target_core
            and (equipment_core in target_core or target_core in equipment_core)
        )

    target_matches = [equipment for equipment in matches if matches_target(equipment)]
    countable_matches = target_matches or (matches if len(matches) == 1 else [])
    running = sum(
        int(float(equipment.get("running_count", "0")))
        for equipment in countable_matches
        if re.fullmatch(r"\d+(?:\.\d+)?", equipment.get("running_count", ""))
    )
    if running:
        names = "、".join(equipment.get("name", "") for equipment in countable_matches)
        return str(running), f"设备表运行数：{names}共{running}台"
    if sampling_target(target):
        return "1", "岗位接触表列出1个明确工位"
    return "", ""


def workplace_and_target(workplace: str, target: str) -> tuple[str, str]:
    """Assign a mobile-work target to its specific workplace when stated."""
    normalized_target = normalize_text(target)
    workplaces = [part.strip() for part in re.split(r"[、，,]", workplace or "") if part.strip()]
    matched_workplace = next(
        (part for part in sorted(workplaces, key=len, reverse=True) if normalized_target.startswith(part)),
        "",
    )
    if not matched_workplace:
        target_core = re.sub(r"(?:工作)?工位.*$", "", normalized_target)
        matched_workplace = next(
            (
                part
                for part in sorted(workplaces, key=len, reverse=True)
                if target_core
                and re.sub(r"(?:区域|区|车间|场所)$", "", part) == target_core
            ),
            "",
        )
    if not matched_workplace:
        return workplace, normalized_target
    if normalized_target.startswith(matched_workplace):
        normalized_target = normalized_target[len(matched_workplace) :].strip()
    return matched_workplace, normalized_target


def build_table3(
    overall_rows: List[Dict[str, str]],
    detail_rows: List[Dict[str, str]],
    equipment_rows: List[Dict[str, str]] | None = None,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    equipment_rows = equipment_rows or []
    matched_overall_rows: set[int] = set()
    job_contexts = {
        index: inferred_job_context(index, overall_row, detail_rows, overall_rows)
        for index, overall_row in enumerate(overall_rows)
    }
    if detail_rows:
        for detail_row in detail_rows:
            projects = split_projects(detail_row.get("project_raw", ""))
            if not projects:
                continue
            overall_row = match_overall_row(detail_row, overall_rows) or {}
            if overall_row in overall_rows:
                overall_index = overall_rows.index(overall_row)
                # For unstable exposure, the detail table specifies the actual
                # factor and representative time at each individual location.
                matched_overall_rows.add(overall_index)
                job_context = job_contexts[overall_index]
            else:
                source_job_type = detail_row.get("job_type", "")
                job_context = {
                    "job_group_id": "detail:{workplace}:{position}:{worker}".format(
                        workplace=detail_row.get("workplace", ""),
                        position=detail_row.get("position", ""),
                        worker=detail_row.get("worker_name", ""),
                    ),
                    "source_job_type": source_job_type,
                    "job_type": source_job_type,
                    "job_type_inference_reason": "",
                }
            people_per_shift = overall_row.get("people_per_shift", "")
            exposure_type = (
                PARSING_RULES.get("detail_preferred_exposure_type", "")
                or overall_row.get("exposure_type", "")
            )
            job_workplace = overall_row.get("workplace", "") or detail_row.get("workplace", "")
            job_time = overall_representative_time(overall_row) if overall_row else ""
            detail_workplace, target = workplace_and_target(
                detail_row.get("workplace", "") or overall_row.get("workplace", ""),
                detail_row.get("target", ""),
            )
            workstation_count, workstation_count_source = workstation_context(
                detail_workplace,
                detail_row.get("position", "") or overall_row.get("position", ""),
                target,
                equipment_rows,
            )
            for project in projects:
                rows.append(
                    make_table3_row(
                        job_group_id=job_context["job_group_id"],
                        job_workplace=job_workplace,
                        job_work_content=job_context.get("job_work_content", ""),
                        job_representative_time=job_time,
                        source_job_type=job_context["source_job_type"],
                        job_type_inference_reason=job_context["job_type_inference_reason"],
                        workplace=detail_workplace,
                        position=detail_row.get("position", "") or overall_row.get("position", ""),
                        people_per_shift=people_per_shift,
                        workstation_count=workstation_count,
                        workstation_count_source=workstation_count_source,
                        job_type=job_context["job_type"],
                        target=sampling_target(target),
                        project=project,
                        exposure_type=exposure_type,
                        sampling_time=detail_row.get("duration", ""),
                        representative_time=detail_row.get("duration", ""),
                    )
                )
    for index, overall_row in enumerate(overall_rows):
        targets = sampling_targets(overall_row.get("target", ""))
        # Detailed exposure records supply the location, factor, and
        # representative time for their matched overall row. Never append the
        # broad overall row as well, regardless of its exposure-type label.
        if index in matched_overall_rows:
            continue
        projects = split_projects(overall_row.get("project_raw", ""))
        for target in targets or [sampling_target(overall_row.get("target", ""))]:
            target_workplace, target_location = workplace_and_target(
                overall_row.get("workplace", ""), target
            )
            workstation_count, workstation_count_source = workstation_context(
                target_workplace,
                overall_row.get("position", ""),
                target_location,
                equipment_rows,
            )
            for project in projects:
                rows.append(
                    make_table3_row(
                        job_group_id=job_contexts[index]["job_group_id"],
                        job_workplace=overall_row.get("workplace", ""),
                        job_work_content=job_contexts[index].get("job_work_content", ""),
                        job_representative_time=overall_representative_time(overall_row),
                        source_job_type=job_contexts[index]["source_job_type"],
                        job_type_inference_reason=job_contexts[index]["job_type_inference_reason"],
                        workplace=target_workplace,
                        position=overall_row.get("position", ""),
                        people_per_shift=overall_row.get("people_per_shift", ""),
                        workstation_count=workstation_count,
                        workstation_count_source=workstation_count_source,
                        job_type=job_contexts[index]["job_type"],
                        target=target_location,
                        project=project,
                        exposure_type=overall_row.get("exposure_type", ""),
                        representative_time=overall_representative_time(overall_row),
                    )
                )
    return rows


def build_survey_tables(
    overall_rows: List[List[str]],
    detail_rows: List[List[str]],
    equipment_rows: List[Dict[str, str]],
    supporting_tables: Dict[str, List[Dict[str, str]]],
) -> Dict[str, List[Any]]:
    survey_tables: Dict[str, List[Any]] = {key: [] for key in SURVEY_TABLE_KEYS}
    survey_tables["overall_exposure"] = overall_rows
    survey_tables["detail_exposure"] = detail_rows
    survey_tables["equipment"] = equipment_rows
    for key, rows in supporting_tables.items():
        survey_tables[key] = rows
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
    header["expected_sampling_time"] = expected_sampling_time(overall_rows)
    detail_rows = parse_detail_rows(detail_raw_rows)
    equipment_rows = parse_equipment_rows(raw_tables)
    supporting_tables = parse_supporting_survey_tables(raw_tables)
    projects = build_projects(overall_rows, detail_rows)
    table3 = build_table3(overall_rows, detail_rows, equipment_rows)
    survey_tables = build_survey_tables(
        overall_raw_rows,
        detail_raw_rows,
        equipment_rows,
        supporting_tables,
    )
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
