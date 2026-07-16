#!/usr/bin/env python3
"""Generate a filled workplace sampling plan DOCX from a survey PDF."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_lookup(value: str) -> str:
    value = re.sub(r"[（(][^（）()]*[）)]", "", value or "")
    return "".join(value.split())


def load_rule_index(index_path: Path) -> Dict[str, Dict[str, str]]:
    if not index_path.exists():
        raise RuntimeError(f"rule data file not found: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("rule data file must be a JSON object")

    index: Dict[str, Dict[str, str]] = {}
    for name, payload in data.items():
        if not isinstance(payload, list) or len(payload) < 2:
            continue
        basis = "" if payload[0] is None else str(payload[0]).strip()
        storage = "" if payload[1] is None else str(payload[1]).strip()
        collector = "" if len(payload) < 3 or payload[2] is None else str(payload[2]).strip()
        index[normalize_lookup(name)] = {
            "basis": basis,
            "storage": storage,
            "collector": collector,
        }
    return index


def load_collector_index(index_path: Path) -> Dict[str, object]:
    if not index_path.exists():
        raise RuntimeError(f"collector data file not found: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("collector data file must be a JSON object")

    collector_devices = data
    if not collector_devices or not all(isinstance(values, dict) for values in collector_devices.values()):
        raise RuntimeError("collector data must map each collector directly to its equipment object")

    return collector_devices


def load_report_rules(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise RuntimeError(f"report rules file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("report rules file must be a JSON object")
    return data


def run_parse_script(script: Path, pdf: Path, output: Path, config: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script), "--pdf", str(pdf), "--output", str(output), "--config", str(config)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "parse_pdf.py failed")


def dedupe(items: List[str]) -> List[str]:
    seen: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def build_table2(
    projects: List[str],
    table3_rows: List[Dict[str, str]],
    rule_index: Dict[str, Dict[str, str]],
    report_rules: Dict[str, object],
) -> Tuple[List[Dict[str, str]], List[str]]:
    categories = report_rules["project_categories"]
    physical_projects = set(categories["physical"])
    powder_projects = set(categories["powder"])
    source_projects = dedupe(projects)
    if not source_projects:
        source_projects = dedupe([row.get("project", "") for row in table3_rows])

    rows: List[Dict[str, str]] = []
    missing: List[str] = []
    for project in source_projects:
        matched_rule = rule_index.get(normalize_lookup(project))
        if matched_rule:
            storage = matched_rule["storage"]
            if not storage and project in physical_projects:
                storage = "/"
            elif not storage and project in powder_projects:
                storage = "长期"
            rows.append(
                {
                    "检测项目": project,
                    "检测依据": matched_rule["basis"],
                    "样品保存条件和期限": storage,
                }
            )
            continue
        storage = "/" if project in physical_projects else "长期" if project in powder_projects else ""
        rows.append(
            {
                "检测项目": project,
                "检测依据": "",
                "样品保存条件和期限": storage,
            }
        )
        missing.append(f"Table2 {project} 检测依据")
        if not storage:
            missing.append(f"Table2 {project} 样品保存条件和期限")
    grouped_rows: List[Dict[str, str]] = []
    grouped_by_rule: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in rows:
        basis = row["检测依据"]
        storage = row["样品保存条件和期限"]
        # A blank basis represents missing data rather than a common standard.
        if not basis:
            grouped_rows.append(row)
            continue
        group_key = (basis, storage)
        group = grouped_by_rule.get(group_key)
        if group is None:
            group = {
                "检测项目": [],
                "检测依据": basis,
                "样品保存条件和期限": storage,
            }
            grouped_by_rule[group_key] = group
            grouped_rows.append(group)
        group["检测项目"].append(row["检测项目"])

    table_rows = []
    for row in grouped_rows:
        if isinstance(row["检测项目"], list):
            table_rows.append(
                {
                    "检测项目": "、".join(row["检测项目"]),
                    "检测依据": row["检测依据"],
                    "样品保存条件和期限": row["样品保存条件和期限"],
                }
            )
        else:
            table_rows.append(row)
    return table_rows, missing


def collector_for_project(
    project: str,
    sampling_mode: str,
    collector_index: Dict[str, object],
    rule_index: Dict[str, Dict[str, str]],
    report_rules: Dict[str, object],
) -> Dict[str, str]:
    """Choose a collector by project, then choose its device by sampling mode."""
    sampling_rules = report_rules["sampling"]
    aliases = report_rules["project_aliases"]
    candidates = [normalize_lookup(project), normalize_lookup(aliases.get(project, ""))]

    for candidate in candidates:
        rule = rule_index.get(candidate)
        if rule and rule.get("collector"):
            collector = rule["collector"]
            break
    else:
        # Unknown projects are retained in the form for later manual completion.
        return {"collector": "", "device": "", "flow_rate": ""}

    # Direct-reading factors are recorded as the shared collector "直读", but
    # their instruments are factor-specific (for example, noise). Prefer a
    # project-specific configuration when one exists, while retaining the
    # configured collector text in the generated form.
    equipment = collector_index.get(normalize_lookup(project)) or collector_index.get(collector)
    if not isinstance(equipment, dict):
        return {"collector": collector, "device": "", "flow_rate": ""}
    device_key = "个体采样设备" if sampling_mode == sampling_rules["individual_mode"] else "定点采样设备"
    flow_rate_key = "个体采样流量" if sampling_mode == sampling_rules["individual_mode"] else "定点采样流量"
    return {
        "collector": collector,
        "device": str(equipment.get(device_key, "") or "").strip(),
        "flow_rate": str(equipment.get(flow_rate_key, "") or "").strip(),
    }


def sampling_mode_for(
    project: str,
    job_type: str,
    target: str,
    collector: str,
    report_rules: Dict[str, object],
) -> str:
    """Choose individual sampling for mobile jobs when the collector permits it."""
    sampling_rules = report_rules["sampling"]
    if project in set(report_rules["project_categories"]["physical"]):
        # The physical-factor rules require separate fixed-location readings for
        # high temperature and hand-arm vibration. Mobile noise is the exception
        # and requires an individual measurement.
        if project == "噪声" and job_type == sampling_rules["mobile_job_type"]:
            return sampling_rules["individual_mode"]
        return sampling_rules["point_mode"]
    if "粉尘" in project:
        # Mobile workers still need the individual work locations represented
        # as sampling points; dust has no separate worker-worn requirement here.
        return sampling_rules["point_mode"]
    if collector in {
        sampling_rules["sample_bag_collector"],
        sampling_rules["absorption_solution_collector"],
    }:
        return sampling_rules["point_mode"]
    if target == sampling_rules["individual_target"] or job_type == sampling_rules["mobile_job_type"]:
        return sampling_rules["individual_mode"]
    return sampling_rules["point_mode"]


def points_per_day(people_per_shift: str, sampling_rules: Dict[str, object]) -> str:
    """Select the GBZ 159 sampling-point/object count from the shift headcount."""
    match = re.search(r"\d+", people_per_shift or "")
    people = int(match.group()) if match else 1
    for threshold in sampling_rules["daily_points_by_people_per_shift"]:
        maximum_people = threshold["maximum_people"]
        if maximum_people is None or people <= maximum_people:
            return str(threshold["points"])
    raise RuntimeError("daily_points_by_people_per_shift must include an open-ended threshold")


def duration_hours(value: str) -> float | None:
    """Read the survey's representative time such as ``8h`` or ``0.5h``."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|小时)", value or "", re.IGNORECASE)
    return float(match.group(1)) if match else None


def format_duration(hours: float) -> str:
    return f"{hours:g}h"


def individual_sampling_time(
    project: str,
    job_type: str,
    representative_time: str,
    sampling_rules: Dict[str, object],
) -> str:
    """Calculate a compliant long-duration sample from the survey duration."""
    hours = duration_hours(representative_time)
    if hours is None:
        return (
            sampling_rules["individual_noise_sampling_time"]
            if project == "噪声"
            else sampling_rules["individual_sampling_time"]
        )

    is_mobile = job_type == sampling_rules["mobile_job_type"]
    minimum_fraction = 0.5 if is_mobile else 0.25
    if project == "噪声" and hours < 1:
        # For less than one hour of noise exposure, measure the whole exposure.
        return format_duration(hours)
    return format_duration(max(hours * minimum_fraction, 1))


def limit_type_for(
    project: str,
    sampling_mode: str,
    collector: str,
    report_rules: Dict[str, object],
) -> str:
    """Resolve the exposure-limit type independently of sampling duration."""
    sampling_rules = report_rules["sampling"]
    categories = report_rules["project_categories"]
    if project in set(categories["physical"]):
        return sampling_rules["physical_limit_type"]
    if sampling_mode == sampling_rules["individual_mode"]:
        return sampling_rules["individual_limit_type"]
    if collector in {
        sampling_rules["sample_bag_collector"],
        sampling_rules["absorption_solution_collector"],
    }:
        # These media cannot be used for individual long-duration sampling;
        # multiple fixed-point samples are combined for the PC-TWA result.
        return sampling_rules["individual_limit_type"]
    if project in set(categories["powder"]) or "粉尘" in project:
        return "PE"
    return sampling_rules["point_limit_type"]


def sampling_parameters(
    project: str,
    sampling_mode: str,
    collector: str,
    collector_flow_rate: str,
    people_per_shift: str,
    job_type: str,
    representative_time: str,
    detection_type: str,
    report_rules: Dict[str, object],
) -> Dict[str, str]:
    sampling_rules = report_rules["sampling"]
    is_physical = project in set(report_rules["project_categories"]["physical"])
    daily_times = sampling_rules["daily_times"]
    times_per_day = str(daily_times["project_overrides"].get(project, daily_times["default"]))
    # A long-duration individual measurement is one continuous measurement;
    # the three readings configured for noise and vibration apply to fixed
    # point direct-reading measurements.
    if sampling_mode == sampling_rules["individual_mode"]:
        times_per_day = str(daily_times["default"])
    days = str(sampling_rules["detection_days"].get(detection_type, sampling_rules["detection_days"]["default"]))
    point_count = points_per_day(people_per_shift, sampling_rules)
    limit_type = limit_type_for(project, sampling_mode, collector, report_rules)
    if is_physical:
        sampling_time = "/"
        if project == "噪声" and sampling_mode == sampling_rules["individual_mode"]:
            sampling_time = individual_sampling_time(
                project,
                job_type,
                representative_time,
                sampling_rules,
            )
        return {
            "limit_type": limit_type,
            "sampling_mode": sampling_mode,
            "time_type": sampling_rules["direct_read_time_type"],
            "flow_rate": collector_flow_rate,
            "points_per_day": point_count,
            "times_per_day": times_per_day,
            "days": days,
            "sampling_time": sampling_time,
        }

    is_short_term = collector in {
        sampling_rules["sample_bag_collector"],
        sampling_rules["absorption_solution_collector"],
    } or sampling_mode == sampling_rules["point_mode"]
    return {
        "limit_type": limit_type,
        "sampling_mode": sampling_mode,
        "time_type": sampling_rules["short_time_type"] if is_short_term else sampling_rules["long_time_type"],
        "flow_rate": collector_flow_rate,
        "points_per_day": point_count,
        "times_per_day": times_per_day,
        "days": days,
        "sampling_time": (
            sampling_rules["point_sampling_time"]
            if is_short_term
            else individual_sampling_time(project, job_type, representative_time, sampling_rules)
        ),
    }


def merge_projects_by_collector(
    rows: List[Dict[str, str]],
    collector_index: Dict[str, object],
    rule_index: Dict[str, Dict[str, str]],
    table3_keys: Tuple[str, ...],
    detection_type: str,
    report_rules: Dict[str, object],
) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    grouped: Dict[Tuple[str, ...], Dict[str, str]] = {}
    project_orders: Dict[Tuple[str, ...], List[str]] = {}
    sampling_rules = report_rules["sampling"]
    main_mobile_duration: Dict[Tuple[str, str], float] = {}
    for row in rows:
        if row.get("job_type", "") != sampling_rules["mobile_job_type"]:
            continue
        duration = duration_hours(row.get("representative_time", ""))
        if duration is None:
            continue
        context = (row.get("workplace", ""), row.get("position", ""))
        main_mobile_duration[context] = max(main_mobile_duration.get(context, 0), duration)

    for row in rows:
        source = {key: row.get(key, "") for key in table3_keys}
        sampling_context = source.get("target", "")
        project = source.get("project", "")
        initial_collector = collector_for_project(
            project,
            sampling_rules["point_mode"],
            collector_index,
            rule_index,
            report_rules,
        )
        point_or_individual = sampling_mode_for(
            project,
            source.get("job_type", ""),
            sampling_context,
            initial_collector["collector"],
            report_rules,
        )
        modes = [point_or_individual]

        if source.get("job_type", "") == sampling_rules["mobile_job_type"]:
            # Every mobile-work location is a sampling point. Only the longest
            # representative work segment also receives a worker-worn sample.
            modes = [sampling_rules["point_mode"]]
            context = (source.get("workplace", ""), source.get("position", ""))
            duration = duration_hours(source.get("representative_time", ""))
            if (
                point_or_individual == sampling_rules["individual_mode"]
                and duration is not None
                and duration == main_mobile_duration.get(context)
            ):
                modes.append(sampling_rules["individual_mode"])

        base_collector = collector_for_project(project, point_or_individual, collector_index, rule_index, report_rules)
        base_parameters = sampling_parameters(
            project,
            point_or_individual,
            base_collector["collector"],
            base_collector["flow_rate"],
            source.get("people_per_shift", ""),
            source.get("job_type", ""),
            source.get("representative_time", ""),
            detection_type,
            report_rules,
        )
        # Every fixed workplace record with a PC limit is supplemented with a
        # worker-worn PC-TWA sample. Physical factors use "/" and do not qualify.
        if (
            point_or_individual == sampling_rules["point_mode"]
            and source.get("job_type", "") != sampling_rules["mobile_job_type"]
            and base_collector["collector"] not in {
                sampling_rules["sample_bag_collector"],
                sampling_rules["absorption_solution_collector"],
            }
            and base_parameters["limit_type"] != sampling_rules["physical_limit_type"]
        ):
            modes.append(sampling_rules["individual_mode"])

        for sampling_mode in modes:
            filled = source.copy()
            collector_info = collector_for_project(project, sampling_mode, collector_index, rule_index, report_rules)
            filled["collector"] = collector_info.get("collector", "")
            filled["device"] = collector_info.get("device", "")
            filled.update(
                sampling_parameters(
                    project,
                    sampling_mode,
                    filled["collector"],
                    collector_info["flow_rate"],
                    source.get("people_per_shift", ""),
                    source.get("job_type", ""),
                    source.get("representative_time", ""),
                    detection_type,
                    report_rules,
                )
            )
            filled["target"] = (
                sampling_rules["individual_target"]
                if sampling_mode == sampling_rules["individual_mode"]
                else sampling_context
            )

            grouping_context = sampling_context if sampling_mode == sampling_rules["point_mode"] else ""
            group_key = (grouping_context, sampling_mode) + tuple(
                filled[key]
                for key in table3_keys
                # Representative time documents the source activity. It must
                # not split otherwise identical sampling records when their
                # calculated sampling duration is already the same.
                if key not in {"project", "representative_time"}
            )
            if group_key not in grouped:
                grouped[group_key] = filled
                project_orders[group_key] = []
                merged.append(grouped[group_key])

            if project and project not in project_orders[group_key]:
                project_orders[group_key].append(project)

    for group_key, target in grouped.items():
        target["project"] = "、".join(project_orders[group_key])
    return merged


def sort_table3_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("workplace", ""),
            row.get("position", ""),
            row.get("target", ""),
            row.get("job_type", ""),
            row.get("project", ""),
            row.get("collector", ""),
        ),
    )


def build_table3(
    rows: List[Dict[str, str]],
    collector_index: Dict[str, object],
    rule_index: Dict[str, Dict[str, str]],
    detection_type: str,
    report_rules: Dict[str, object],
) -> Tuple[List[Dict[str, str]], List[str]]:
    output: List[Dict[str, str]] = []
    missing: List[str] = []
    table3_keys = (
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
    )

    merged_rows = sort_table3_rows(
        merge_projects_by_collector(rows, collector_index, rule_index, table3_keys, detection_type, report_rules)
    )
    sampling_numbers: Dict[Tuple[str, str, str], str] = {}
    for filled in merged_rows:
        sampling_context = (
            filled.get("workplace", ""),
            filled.get("position", ""),
            filled.get("target", ""),
        )
        if sampling_context not in sampling_numbers:
            sampling_numbers[sampling_context] = str(len(sampling_numbers) + 1)
        filled["sampling_no"] = sampling_numbers[sampling_context]
        project = filled.get("project", "") or "未命名项目"
        for key in ("workplace", "position", "target", "project"):
            if not filled.get(key):
                missing.append(f"Table3 {project} {key}")
        output.append(filled)
    return output, missing


def run_fill_script(script: Path, template: Path, payload: Path, output: Path, config: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--template",
            str(template),
            "--payload",
            str(payload),
            "--output",
            str(output),
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "fill_docx.py failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root_dir = scripts_dir.parent
    parse_script = scripts_dir / "parse_pdf.py"
    fill_script = scripts_dir / "fill_docx.py"
    collector_path = root_dir / "knowledge" / "collector.json"
    config_path = args.config or root_dir / "knowledge" / "report_rules.json"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_payload_path = Path(tmpdir) / "parsed.json"
            final_payload_path = Path(tmpdir) / "payload.json"
            run_parse_script(parse_script, args.pdf, raw_payload_path, config_path)
            parsed = json.loads(raw_payload_path.read_text(encoding="utf-8"))
            rule_index = load_rule_index(args.rules)
            collector_index = load_collector_index(collector_path)
            report_rules = load_report_rules(config_path)
            table2, missing2 = build_table2(
                parsed.get("projects", []),
                parsed.get("table3", []),
                rule_index,
                report_rules,
            )
            table3, missing3 = build_table3(
                parsed.get("table3", []),
                collector_index,
                rule_index,
                parsed.get("header", {}).get("detection_type", ""),
                report_rules,
            )
            missing_fields = dedupe(parsed.get("missing_fields", []) + missing2 + missing3)
            payload = {
                "header": parsed.get("header", {}),
                "projects": parsed.get("projects", []),
                "table2": table2,
                "table3": table3,
                "missing_fields": missing_fields,
                "survey_tables": parsed.get("survey_tables", {}),
            }
            final_payload_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            run_fill_script(fill_script, args.template, final_payload_path, args.output, config_path)
            if args.json_out:
                args.json_out.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                print(json.dumps(payload["missing_fields"], ensure_ascii=False, indent=2))
    except Exception as exc:  # pragma: no cover - CLI error path
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
