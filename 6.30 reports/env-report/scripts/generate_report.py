#!/usr/bin/env python3
"""Generate a filled workplace sampling plan DOCX from a survey PDF."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple


def normalize_lookup(value: str) -> str:
    return "".join((value or "").split())


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
        index[normalize_lookup(name)] = {
            "basis": basis,
            "storage": storage,
        }
    return index


def load_collector_index(index_path: Path) -> Dict[str, Dict[str, str]]:
    if not index_path.exists():
        raise RuntimeError(f"collector data file not found: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("collector data file must be a JSON object")

    index: Dict[str, Dict[str, str]] = {}
    for name, collector in data.items():
        normalized_name = normalize_lookup(name)
        if not normalized_name:
            continue

        if isinstance(collector, dict):
            collector_value = str(collector.get("空气收集器", "") or "").strip()
            device_value = str(collector.get("采样测量设备", "") or "").strip()
        else:
            collector_value = "" if collector is None else str(collector).strip()
            device_value = ""

        if collector_value or device_value:
            index[normalized_name] = {
                "collector": collector_value,
                "device": device_value,
            }
    return index


def run_parse_script(script: Path, pdf: Path, output: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script), "--pdf", str(pdf), "--output", str(output)],
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
) -> Tuple[List[Dict[str, str]], List[str]]:
    source_projects = dedupe(projects)
    if not source_projects:
        source_projects = dedupe([row.get("project", "") for row in table3_rows])

    rows: List[Dict[str, str]] = []
    missing: List[str] = []
    for project in source_projects:
        matched_rule = rule_index.get(normalize_lookup(project))
        if matched_rule:
            rows.append(
                {
                    "检测项目": project,
                    "检测依据": matched_rule["basis"],
                    "样品保存条件和期限": matched_rule["storage"],
                }
            )
            continue
        rows.append(
            {
                "检测项目": project,
                "检测依据": "",
                "样品保存条件和期限": "",
            }
        )
        missing.append(f"Table2 {project} 检测依据")
        missing.append(f"Table2 {project} 样品保存条件和期限")
    return rows, missing


def merge_projects_by_collector(
    rows: List[Dict[str, str]],
    collector_index: Dict[str, Dict[str, str]],
    table3_keys: Tuple[str, ...],
) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    grouped: Dict[Tuple[str, ...], Dict[str, str]] = {}
    project_orders: Dict[Tuple[str, ...], List[str]] = {}

    for row in rows:
        filled = {key: row.get(key, "") for key in table3_keys}
        project = filled.get("project", "")
        collector_info = collector_index.get(normalize_lookup(project), {})
        filled["collector"] = collector_info.get("collector", "")
        filled["device"] = collector_info.get("device", "")

        group_key = tuple(
            filled[key]
            for key in table3_keys
            if key not in {"project"}
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


def build_table3(rows: List[Dict[str, str]], collector_index: Dict[str, Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[str]]:
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

    merged_rows = sort_table3_rows(merge_projects_by_collector(rows, collector_index, table3_keys))
    for index, filled in enumerate(merged_rows, start=1):
        filled["sampling_no"] = str(index)
        project = filled.get("project", "") or "未命名项目"
        for key in ("workplace", "position", "target", "project"):
            if not filled.get(key):
                missing.append(f"Table3 {project} {key}")
        output.append(filled)
    return output, missing


def run_fill_script(script: Path, template: Path, payload: Path, output: Path) -> None:
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
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root_dir = scripts_dir.parent
    parse_script = scripts_dir / "parse_pdf.py"
    fill_script = scripts_dir / "fill_docx.py"
    collector_path = root_dir / "knowledge" / "collector.json"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_payload_path = Path(tmpdir) / "parsed.json"
            final_payload_path = Path(tmpdir) / "payload.json"
            run_parse_script(parse_script, args.pdf, raw_payload_path)
            parsed = json.loads(raw_payload_path.read_text(encoding="utf-8"))
            rule_index = load_rule_index(args.rules)
            collector_index = load_collector_index(collector_path)
            table2, missing2 = build_table2(
                parsed.get("projects", []),
                parsed.get("table3", []),
                rule_index,
            )
            table3, missing3 = build_table3(parsed.get("table3", []), collector_index)
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
            run_fill_script(fill_script, args.template, final_payload_path, args.output)
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
