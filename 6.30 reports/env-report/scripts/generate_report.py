#!/usr/bin/env python3
"""Generate a filled workplace sampling plan DOCX from a survey PDF."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import fill_docx
import parse_component_report
import parse_pdf
from data_store.hazards import COLLECTOR_INDEX, RULE_INDEX
from data_store.oel_limits import OEL_INDEX
from data_store.physical_factors import PHYSICAL_FACTOR_INDEX
from data_store.report_rules import REPORT_RULES



def normalize_lookup(value: str) -> str:
    """Normalize names while ignoring Chinese/English parenthetical qualifiers."""
    outside: List[str] = []
    depth = 0
    for character in value or "":
        if character in "（(":
            depth += 1
        elif character in "）)":
            if depth:
                depth -= 1
        elif depth == 0:
            outside.append(character)
    return "".join("".join(outside).split())


def configured_flow_rates(value: str) -> Dict[str, str]:
    """Parse ``短时间:0.1L/min; 长时间:0.05L/min`` rule data."""
    rates: Dict[str, str] = {}
    for item in re.split(r"[;；]", value or ""):
        parts = re.split(r"[:：]", item, maxsplit=1)
        if len(parts) != 2:
            continue
        time_type, rate = (part.strip() for part in parts)
        if not time_type or not rate:
            continue
        # The report column already carries the L/min unit, so retain the
        # Keep the numeric value/range without the column's L/min unit.
        rates[time_type] = re.sub(
            r"\s*L\s*/\s*min", "", rate, flags=re.IGNORECASE
        ).strip()
    return rates


def flow_rate_for_project(
    project: str,
    sampling_mode: str,
    time_type: str,
    rule_index: Dict[str, Dict[str, str]],
    fallback: str = "",
) -> str:
    """Choose flow from the project's rule and its sampling-time type."""
    rule = rule_index.get(normalize_lookup(project), {})
    return flow_rate_for_rule(rule, sampling_mode, time_type, fallback)


def flow_rate_for_rule(
    rule: Dict[str, str],
    sampling_mode: str,
    time_type: str,
    fallback: str = "",
) -> str:
    """Choose flow from an already resolved project rule."""
    rates = configured_flow_rates(rule.get("flow_rates", ""))
    if sampling_mode == "个体" and rates.get("个体"):
        return rates["个体"]
    return rates.get(time_type, fallback)


def display_project_name(project: str, rule_index: Dict[str, Dict[str, str]]) -> str:
    rule = rule_index.get(normalize_lookup(project), {})
    return rule.get("display_name", "") or project


def default_oel_index() -> Dict[str, Dict[str, object]]:
    return OEL_INDEX


def normalize_physical_lookup(value: str) -> str:
    return normalize_lookup(value).replace("～", "~").casefold()


def default_physical_factor_index() -> frozenset[str]:
    return PHYSICAL_FACTOR_INDEX


def is_physical_factor(
    project: str,
    project_rule: Dict[str, str] | None = None,
    physical_factor_index: set[str] | frozenset[str] | None = None,
) -> bool:
    if (project_rule or {}).get("category") == "physical":
        return True
    index = (
        default_physical_factor_index()
        if physical_factor_index is None
        else physical_factor_index
    )
    return normalize_physical_lookup(project) in index


def oel_limit_types(
    project: str,
    oel_index: Dict[str, Dict[str, object]] | None = None,
) -> set[str]:
    index = default_oel_index() if oel_index is None else oel_index
    entry = index.get(normalize_lookup(project), {})
    return set(entry.get("limit_types", set()))


def dedupe(items: List[str]) -> List[str]:
    seen: List[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def replace_component_placeholders(
    parsed: Dict[str, object],
    component_payload: Dict[str, object],
    report_rules: Dict[str, object],
) -> List[str]:
    """Replace sampled-material placeholders with reportable analyzed components."""
    composition_rules = report_rules.get("composition", {})
    markers = [str(value) for value in composition_rules.get("placeholder_markers", [])]
    ignored = {
        normalize_lookup(str(value))
        for value in composition_rules.get("ignored_components", [])
    }
    components_by_sample: Dict[str, List[str]] = {}
    for sample in component_payload.get("samples", []):
        if not isinstance(sample, dict):
            continue
        names = dedupe(
            [
                str(component.get("name", "")).strip()
                for component in sample.get("components", [])
                if isinstance(component, dict)
                and normalize_lookup(str(component.get("name", ""))) not in ignored
            ]
        )
        components_by_sample[normalize_lookup(str(sample.get("sample_name", "")))] = names

    unresolved: List[str] = []

    def replacements(project: str) -> List[str]:
        if not any(marker and marker in project for marker in markers):
            return [project]
        sample_name = project
        for marker in markers:
            sample_name = sample_name.replace(marker, "")
        components = components_by_sample.get(normalize_lookup(sample_name), [])
        if components:
            return components
        unresolved.append(project)
        return [project]

    projects: List[str] = []
    for project in parsed.get("projects", []):
        projects.extend(replacements(str(project)))
    parsed["projects"] = dedupe(projects)

    table3: List[Dict[str, str]] = []
    for row in parsed.get("table3", []):
        if not isinstance(row, dict):
            continue
        for project in replacements(str(row.get("project", ""))):
            replacement = row.copy()
            replacement["project"] = project
            table3.append(replacement)
    parsed["table3"] = table3
    return dedupe([f"ComponentReport {project}" for project in unresolved])


def build_table2(
    projects: List[str],
    table3_rows: List[Dict[str, str]],
    rule_index: Dict[str, Dict[str, str]],
    report_rules: Dict[str, object],
) -> Tuple[List[Dict[str, str]], List[str]]:
    source_projects = dedupe(projects)
    if not source_projects:
        source_projects = dedupe([row.get("project", "") for row in table3_rows])

    rows: List[Dict[str, str]] = []
    missing: List[str] = []
    for project in source_projects:
        matched_rule = rule_index.get(normalize_lookup(project))
        if matched_rule:
            storage = matched_rule["storage"]
            rows.append(
                {
                    "检测项目": display_project_name(project, rule_index),
                    "检测依据": matched_rule["basis"],
                    "样品保存条件和期限": storage,
                }
            )
            continue
        storage = ""
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
) -> Dict[str, object]:
    """Choose a collector by project, then choose its device by sampling mode."""
    sampling_rules = report_rules["sampling"]
    rule = rule_index.get(normalize_lookup(project))
    if not rule or not rule.get("collector"):
        # Unknown projects are retained in the form for later manual completion.
        return {"collector": "", "device": "", "flow_rate": "", "supports_individual": False}
    collector = rule["collector"]
    collector_capabilities = collector_index.get(collector, {})
    supports_individual = bool(
        collector_capabilities.get("supports_individual", True)
    )
    point_sampling_time = str(
        collector_capabilities.get("point_sampling_time", "") or ""
    ).strip()

    # Direct-reading factors are recorded as the shared collector "直读", but
    # their instruments are factor-specific (for example, noise). Prefer a
    # project-specific configuration when one exists, while retaining the
    # configured collector text in the generated form.
    equipment = (
        collector_index.get(project)
        or collector_index.get(normalize_lookup(project))
        or collector_index.get(collector)
    )
    if not hasattr(equipment, "get"):
        return {
            "collector": collector,
            "device": "",
            "flow_rate": "",
            "supports_individual": supports_individual,
            "point_sampling_time": point_sampling_time,
        }
    device_key = "个体采样设备" if sampling_mode == sampling_rules["individual_mode"] else "定点采样设备"
    flow_rate_key = "个体采样流量" if sampling_mode == sampling_rules["individual_mode"] else "定点采样流量"
    return {
        "collector": collector,
        "device": str(equipment.get(device_key, "") or "").strip(),
        "flow_rate": str(equipment.get(flow_rate_key, "") or "").strip(),
        "supports_individual": supports_individual,
        "point_sampling_time": point_sampling_time,
    }


def apply_collector_sampling_capabilities(
    parameters: Dict[str, str],
    collector_info: Dict[str, object],
    job_type: str,
    exposure_type: str,
    report_rules: Dict[str, object],
) -> Dict[str, str]:
    """Apply sampling-medium capabilities without project or company exceptions."""
    sampling_rules = report_rules["sampling"]
    if parameters.get("sampling_mode") != sampling_rules["point_mode"]:
        return parameters
    point_time = str(collector_info.get("point_sampling_time", "") or "")
    if point_time:
        parameters["sampling_time"] = point_time
    return parameters


def sampling_mode_for(
    project: str,
    job_type: str,
    target: str,
    collector: str,
    collector_supports_individual: bool,
    exposure_type: str,
    project_rule: Dict[str, str],
    report_rules: Dict[str, object],
) -> str:
    """Choose individual sampling for mobile jobs when the collector permits it."""
    sampling_rules = report_rules["sampling"]
    if project_rule.get("category") == "physical":
        if (
            project_rule.get("sampling_policy") == "mobile_individual"
            and job_type == sampling_rules["mobile_job_type"]
        ):
            return sampling_rules["individual_mode"]
        return sampling_rules["point_mode"]
    if not collector_supports_individual:
        return sampling_rules["point_mode"]
    # A stable fixed job is represented by a long-duration worker sample.
    # Unstable jobs retain their location samples and receive an individual
    # sample through the supplemental logic below.
    if exposure_type == "①":
        return sampling_rules["individual_mode"]
    if target == sampling_rules["individual_target"] or job_type == sampling_rules["mobile_job_type"]:
        return sampling_rules["individual_mode"]
    return sampling_rules["point_mode"]


def points_per_day(
    people_per_shift: str,
    sampling_mode: str,
    sampling_rules: Dict[str, object],
    workstation_count: str = "",
) -> str:
    """Select sampling objects separately from fixed-location point counts."""
    match = re.search(r"\d+", people_per_shift or "")
    people = int(match.group()) if match else 1
    if sampling_mode == sampling_rules["individual_mode"]:
        for threshold in sampling_rules["daily_objects_by_people_per_shift"]:
            maximum_people = threshold["maximum_people"]
            if maximum_people is None or people <= maximum_people:
                return str(threshold["objects"])
        raise RuntimeError("daily_objects_by_people_per_shift must include an open-ended threshold")
    workstation_match = re.search(r"\d+", workstation_count or "")
    count = int(workstation_match.group()) if workstation_match else people
    for threshold in sampling_rules["daily_points_by_people_per_shift"]:
        maximum_people = threshold["maximum_people"]
        if maximum_people is None or count <= maximum_people:
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
    project_rule: Dict[str, str],
) -> str:
    """Calculate a compliant long-duration sample from the survey duration."""
    hours = duration_hours(representative_time)
    if hours is None:
        return (
            project_rule.get("default_individual_sampling_time", "")
            or sampling_rules["individual_sampling_time"]
        )

    is_mobile = job_type == sampling_rules["mobile_job_type"]
    minimum_fraction = 0.5 if is_mobile else 0.25
    full_measure_below = duration_hours(
        f"{project_rule.get('full_measure_below_hours', '')}h"
    )
    if full_measure_below is not None and hours < full_measure_below:
        return format_duration(hours)
    return format_duration(max(hours * minimum_fraction, 1))


def limit_type_for(
    project: str,
    sampling_mode: str,
    collector: str,
    collector_supports_individual: bool,
    report_rules: Dict[str, object],
    project_rule: Dict[str, str],
    oel_index: Dict[str, Dict[str, object]] | None = None,
) -> str:
    """Resolve the plan limit type from sampling mode and the GBZ 2.1 OELs."""
    sampling_rules = report_rules["sampling"]
    if is_physical_factor(project, project_rule):
        return sampling_rules["physical_limit_type"]
    limit_types = oel_limit_types(project, oel_index)
    if sampling_mode == sampling_rules["individual_mode"]:
        return sampling_rules["individual_limit_type"] if "PC-TWA" in limit_types else ""
    if "PC-STEL" in limit_types:
        return sampling_rules["point_limit_type"]
    if "MAC" in limit_types:
        return "MAC"
    if "PC-TWA" in limit_types:
        return "PE"
    return ""


def sampling_parameters(
    project: str,
    sampling_mode: str,
    collector: str,
    collector_supports_individual: bool,
    collector_flow_rate: str,
    people_per_shift: str,
    job_type: str,
    representative_time: str,
    detection_type: str,
    report_rules: Dict[str, object],
    project_rule: Dict[str, str] | None = None,
    workstation_count: str = "",
    oel_index: Dict[str, Dict[str, object]] | None = None,
) -> Dict[str, str]:
    sampling_rules = report_rules["sampling"]
    project_rule = project_rule or {}
    is_physical = is_physical_factor(project, project_rule)
    daily_times = sampling_rules["daily_times"]
    times_per_day = str(daily_times["default"])
    # A long-duration individual measurement is one continuous measurement;
    # the three readings configured for noise and vibration apply to fixed
    # point direct-reading measurements.
    if sampling_mode == sampling_rules["individual_mode"]:
        times_per_day = str(daily_times["default"])
    days = str(sampling_rules["detection_days"].get(detection_type, sampling_rules["detection_days"]["default"]))
    point_count = points_per_day(
        people_per_shift,
        sampling_mode,
        sampling_rules,
        workstation_count,
    )
    limit_type = limit_type_for(
        project,
        sampling_mode,
        collector,
        collector_supports_individual,
        report_rules,
        project_rule,
        oel_index,
    )
    if is_physical:
        is_individual = sampling_mode == sampling_rules["individual_mode"]
        time_type = (
            sampling_rules["long_time_type"]
            if is_individual
            else sampling_rules["short_time_type"]
        )
        sampling_time = "/"
        if (
            project_rule.get("sampling_policy") == "mobile_individual"
            and is_individual
        ):
            sampling_time = individual_sampling_time(
                project,
                job_type,
                representative_time,
                sampling_rules,
                project_rule,
            )
        return {
            "limit_type": limit_type,
            "sampling_mode": sampling_mode,
            "time_type": time_type,
            "flow_rate": flow_rate_for_rule(
                project_rule, sampling_mode, time_type, collector_flow_rate
            ),
            "points_per_day": point_count,
            "times_per_day": times_per_day,
            "days": days,
            "sampling_time": sampling_time,
        }

    is_short_term = not collector_supports_individual or sampling_mode == sampling_rules["point_mode"]
    time_type = sampling_rules["short_time_type"] if is_short_term else sampling_rules["long_time_type"]
    return {
        "limit_type": limit_type,
        "sampling_mode": sampling_mode,
        "time_type": time_type,
        "flow_rate": flow_rate_for_rule(
            project_rule, sampling_mode, time_type, collector_flow_rate
        ),
        "points_per_day": point_count,
        "times_per_day": times_per_day,
        "days": days,
        "sampling_time": (
            sampling_rules["point_sampling_time"]
            if is_short_term
            else individual_sampling_time(
                project,
                job_type,
                representative_time,
                sampling_rules,
                project_rule,
            )
        ),
    }


def merge_projects_by_collector(
    rows: List[Dict[str, str]],
    collector_index: Dict[str, object],
    rule_index: Dict[str, Dict[str, str]],
    table3_keys: Tuple[str, ...],
    detection_type: str,
    report_rules: Dict[str, object],
    oel_index: Dict[str, Dict[str, object]] | None = None,
) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    grouped: Dict[Tuple[str, ...], Dict[str, str]] = {}
    project_orders: Dict[Tuple[str, ...], List[str]] = {}
    sampling_rules = report_rules["sampling"]
    main_mobile_duration: Dict[str, float] = {}
    filter_duration_by_target: Dict[Tuple[str, str], float] = {}
    job_overall_duration: Dict[str, float] = {}
    for row in rows:
        if row.get("job_type", "") != sampling_rules["mobile_job_type"]:
            continue
        duration = duration_hours(row.get("representative_time", ""))
        if duration is None:
            continue
        job_group = row.get("job_group_id", "") or "|".join(
            (row.get("job_workplace", "") or row.get("workplace", ""), row.get("position", ""))
        )
        main_mobile_duration[job_group] = max(main_mobile_duration.get(job_group, 0), duration)
        overall_duration = duration_hours(row.get("job_representative_time", ""))
        if overall_duration is not None:
            job_overall_duration[job_group] = overall_duration
        point_collector = collector_for_project(
            row.get("project", ""),
            sampling_rules["point_mode"],
            collector_index,
            rule_index,
            report_rules,
        )["collector"]
        if sampling_rules["dust_filter_keyword"] in point_collector:
            target_key = (job_group, row.get("target", ""))
            filter_duration_by_target[target_key] = max(
                filter_duration_by_target.get(target_key, 0),
                duration,
            )

    full_shift_filter_jobs = {
        job_group
        for job_group, overall_duration in job_overall_duration.items()
        if abs(
            sum(
                duration
                for (candidate_group, _target), duration in filter_duration_by_target.items()
                if candidate_group == job_group
            )
            - overall_duration
        )
        <= 0.25
    }

    for row in rows:
        source = {key: row.get(key, "") for key in table3_keys}
        sampling_context = source.get("target", "")
        project = source.get("project", "")
        project_rule = rule_index.get(normalize_lookup(project), {})
        if (
            is_physical_factor(project, project_rule)
            and project_rule.get("category") != "physical"
        ):
            project_rule = {
                **project_rule,
                "category": "physical",
                "sampling_policy": "point_only",
            }
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
            bool(initial_collector.get("supports_individual", False)),
            source.get("exposure_type", ""),
            project_rule,
            report_rules,
        )
        project_limit_types = oel_limit_types(project, oel_index)
        if (
            project_rule.get("category") != "physical"
            and point_or_individual == sampling_rules["individual_mode"]
            and "PC-TWA" not in project_limit_types
        ):
            point_or_individual = sampling_rules["point_mode"]
        modes = [point_or_individual]

        if source.get("job_type", "") == sampling_rules["mobile_job_type"]:
            # Every mobile-work location is a sampling point. Projects from the
            # job's longest representative segment also receive a worker-worn
            # sample; its duration is calculated from the overall job below.
            modes = [sampling_rules["point_mode"]]
            job_group = source.get("job_group_id", "") or "|".join(
                (
                    source.get("job_workplace", "") or source.get("workplace", ""),
                    source.get("position", ""),
                )
            )
            duration = duration_hours(source.get("representative_time", ""))
            uses_dust_filter = (
                sampling_rules["dust_filter_keyword"] in initial_collector["collector"]
            )
            if (
                point_or_individual == sampling_rules["individual_mode"]
                and duration is not None
                and (
                    uses_dust_filter
                    and job_group in full_shift_filter_jobs
                    or duration == main_mobile_duration.get(job_group)
                )
            ):
                modes.append(sampling_rules["individual_mode"])

        base_collector = collector_for_project(project, point_or_individual, collector_index, rule_index, report_rules)
        base_parameters = sampling_parameters(
            project,
            point_or_individual,
            base_collector["collector"],
            bool(base_collector.get("supports_individual", False)),
            base_collector["flow_rate"],
            source.get("people_per_shift", ""),
            source.get("job_type", ""),
            source.get("representative_time", ""),
            detection_type,
            report_rules,
            project_rule,
            workstation_count=source.get("workstation_count", ""),
            oel_index=oel_index,
        )
        # Every fixed workplace record with a PC limit is supplemented with a
        # worker-worn PC-TWA sample. Physical factors have a blank limit type
        # and do not qualify.
        if (
            point_or_individual == sampling_rules["point_mode"]
            and source.get("job_type", "") != sampling_rules["mobile_job_type"]
            and bool(base_collector.get("supports_individual", False))
            and "PC-TWA" in project_limit_types
        ):
            modes.append(sampling_rules["individual_mode"])

        for sampling_mode in modes:
            filled = source.copy()
            filled["_is_physical"] = project_rule.get("category") == "physical"
            filled["_analysis_group"] = project_rule.get("analysis_group", "")
            parameter_time = source.get("representative_time", "")
            if sampling_mode == sampling_rules["individual_mode"]:
                filled["workplace"] = (
                    source.get("job_workplace", "")
                    or source.get("workplace", "")
                )
                parameter_time = (
                    source.get("job_representative_time", "")
                    or source.get("representative_time", "")
                )
                filled["representative_time"] = parameter_time
            collector_info = collector_for_project(project, sampling_mode, collector_index, rule_index, report_rules)
            filled["collector"] = collector_info.get("collector", "")
            filled["device"] = collector_info.get("device", "")
            filled.update(
                apply_collector_sampling_capabilities(
                    sampling_parameters(
                        project,
                        sampling_mode,
                        filled["collector"],
                        bool(collector_info.get("supports_individual", False)),
                        collector_info["flow_rate"],
                        source.get("people_per_shift", ""),
                        source.get("job_type", ""),
                        parameter_time,
                        detection_type,
                        report_rules,
                        project_rule,
                        workstation_count=source.get("workstation_count", ""),
                        oel_index=oel_index,
                    ),
                    collector_info,
                    source.get("job_type", ""),
                    source.get("exposure_type", ""),
                    report_rules,
                )
            )
            filled["target"] = (
                sampling_rules["individual_target"]
                if sampling_mode == sampling_rules["individual_mode"]
                else sampling_context
            )

            grouping_context = sampling_context if sampling_mode == sampling_rules["point_mode"] else ""
            group_key = (
                grouping_context,
                sampling_mode,
                filled["_analysis_group"],
            ) + tuple(
                filled[key]
                for key in table3_keys
                # Representative time documents the source activity. It must
                # not split otherwise identical sampling records when their
                # calculated sampling duration is already the same.
                if key
                not in {
                    "project",
                    "representative_time",
                    "workstation_count",
                    "workstation_count_source",
                }
            )
            if group_key not in grouped:
                grouped[group_key] = filled
                project_orders[group_key] = []
                merged.append(grouped[group_key])

            display_project = display_project_name(project, rule_index)
            if display_project and display_project not in project_orders[group_key]:
                project_orders[group_key].append(display_project)

    for group_key, target in grouped.items():
        target["project"] = "、".join(project_orders[group_key])
    return merged


def sort_table3_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return sorted(
        rows,
        key=lambda row: (
            row.get("job_workplace", "") or row.get("workplace", ""),
            row.get("position", ""),
            row.get("job_group_id", ""),
            0 if row.get("sampling_mode", "") == "个体" else 1,
            row.get("workplace", ""),
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
    oel_index: Dict[str, Dict[str, object]] | None = None,
) -> Tuple[List[Dict[str, str]], List[str]]:
    output: List[Dict[str, str]] = []
    missing: List[str] = []
    table3_keys = (
        "job_group_id",
        "_is_physical",
        "job_workplace",
        "job_work_content",
        "job_representative_time",
        "source_job_type",
        "job_type_inference_reason",
        "sampling_no",
        "workplace",
        "position",
        "people_per_shift",
        "workstation_count",
        "workstation_count_source",
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
        merge_projects_by_collector(
            rows,
            collector_index,
            rule_index,
            table3_keys,
            detection_type,
            report_rules,
            oel_index,
        )
    )
    sampling_numbers: Dict[Tuple[str, str, str], str] = {}
    for filled in merged_rows:
        sampling_context = (
            filled.get("job_group_id", ""),
            filled.get("workplace", ""),
            filled.get("target", ""),
        )
        if sampling_context not in sampling_numbers:
            sampling_numbers[sampling_context] = str(len(sampling_numbers) + 1)
        filled["sampling_no"] = sampling_numbers[sampling_context]
        project = filled.get("project", "") or "未命名项目"
        for key in ("workplace", "position", "target", "project"):
            if not filled.get(key):
                missing.append(f"Table3 {project} {key}")
        if not filled.get("limit_type") and not filled.get("_is_physical"):
            missing.append(f"Table3 {project} GBZ 2.1 OEL")
        if not filled.get("limit_type"):
            filled["limit_type"] = "/"
        people_match = re.search(r"\d+", filled.get("people_per_shift", ""))
        if (
            people_match
            and int(people_match.group()) > 3
            and filled.get("workstation_count_source", "") == "岗位接触表列出1个明确工位"
            and filled.get("sampling_mode", "") == report_rules["sampling"]["point_mode"]
        ):
            missing.append(
                "Table3 {workplace} {position} 相同工位数量".format(
                    workplace=filled.get("workplace", ""),
                    position=filled.get("position", ""),
                )
            )
        filled.pop("_is_physical", None)
        filled.pop("_analysis_group", None)
        output.append(filled)
    return output, missing


def build_report_payload(
    parsed: Dict[str, object],
    component_payload: Dict[str, object] | None = None,
) -> Dict[str, object]:
    """Build the final report payload entirely from in-memory Python objects."""
    component_missing: List[str] = []
    if component_payload is not None:
        component_missing = replace_component_placeholders(
            parsed,
            component_payload,
            REPORT_RULES,
        )

    table2, missing2 = build_table2(
        parsed.get("projects", []),
        parsed.get("table3", []),
        RULE_INDEX,
        REPORT_RULES,
    )
    table3, missing3 = build_table3(
        parsed.get("table3", []),
        COLLECTOR_INDEX,
        RULE_INDEX,
        parsed.get("header", {}).get("detection_type", ""),
        REPORT_RULES,
        OEL_INDEX,
    )
    payload: Dict[str, object] = {
        "header": parsed.get("header", {}),
        "projects": parsed.get("projects", []),
        "table2": table2,
        "table3": table3,
        "missing_fields": dedupe(
            parsed.get("missing_fields", []) + component_missing + missing2 + missing3
        ),
        "survey_tables": parsed.get("survey_tables", {}),
        "inference_notes": dedupe(
            [
                "{position}: {reason}".format(
                    position=row.get("position", ""),
                    reason=row.get("job_type_inference_reason", ""),
                )
                for row in parsed.get("table3", [])
                if row.get("job_type_inference_reason", "")
            ]
        ),
    }
    if component_payload is not None:
        payload["component_analysis"] = component_payload
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--pdf", type=Path)
    source_group.add_argument(
        "--parsed-json",
        type=Path,
        help="调查表解析并经大模型规范后的 JSON；使用时不再重复解析 PDF",
    )
    parser.add_argument("--component-report", type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    try:
        if args.parsed_json:
            parsed = json.loads(args.parsed_json.read_text(encoding="utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("--parsed-json 的顶层必须是 JSON 对象")
        else:
            parsed = parse_pdf.build_payload(args.pdf)
        component_payload = (
            parse_component_report.build_payload(args.component_report)
            if args.component_report
            else None
        )
        payload = build_report_payload(parsed, component_payload)
        fill_docx.fill_document(args.template, payload, args.output)
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
