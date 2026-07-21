#!/usr/bin/env python3
"""Compare parsed survey-PDF results with their JSON fixtures."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_config(path: Path) -> Dict[str, List[str]]:
    if not path.exists():
        return {"global_ignore_paths": [], "sort_list_paths": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "global_ignore_paths": list(data.get("global_ignore_paths", [])),
        "sort_list_paths": list(data.get("sort_list_paths", [])),
    }


def normalize_string(value: str) -> str:
    return "".join(value.split())


def normalize_payload(value: Any, path: str, sort_list_paths: set[str]) -> Any:
    if isinstance(value, dict):
        return {key: normalize_payload(item, f"{path}.{key}" if path else key, sort_list_paths) for key, item in value.items()}
    if isinstance(value, list):
        normalized = [normalize_payload(item, f"{path}[{index}]", sort_list_paths) for index, item in enumerate(value)]
        if path in sort_list_paths:
            return sorted(normalized)
        return normalized
    if isinstance(value, str):
        return normalize_string(value)
    return value


def should_ignore(path: str, ignore_paths: set[str]) -> bool:
    return path in ignore_paths or any(path.startswith(f"{ignored}.") or path.startswith(f"{ignored}[") for ignored in ignore_paths)


def compare_values(expected: Any, result: Any, path: str, ignore_paths: set[str], diffs: List[str]) -> None:
    if should_ignore(path, ignore_paths):
        return
    if type(expected) is not type(result):
        diffs.append(f"{path or '<root>'}: expected {type(expected).__name__}, got {type(result).__name__}")
        return
    if isinstance(expected, dict):
        expected_keys = set(expected)
        result_keys = set(result)
        for key in sorted(expected_keys | result_keys):
            next_path = f"{path}.{key}" if path else key
            if key not in expected:
                diffs.append(f"{next_path}: missing from expected, result={result[key]!r}")
                continue
            if key not in result:
                diffs.append(f"{next_path}: missing from result, expected={expected[key]!r}")
                continue
            compare_values(expected[key], result[key], next_path, ignore_paths, diffs)
        return
    if isinstance(expected, list):
        if len(expected) != len(result):
            diffs.append(f"{path}: expected len {len(expected)}, got len {len(result)}")
            return
        for index, (expected_item, result_item) in enumerate(zip(expected, result)):
            compare_values(expected_item, result_item, f"{path}[{index}]", ignore_paths, diffs)
        return
    if expected != result:
        diffs.append(f"{path}: expected={expected!r} result={result!r}")


def run_example(
    script: Path,
    pdf_path: Path,
    result_json: Path,
    config: Path,
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--pdf",
            str(pdf_path),
            "--output",
            str(result_json),
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"parse_pdf failed for {pdf_path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    test_dir = Path(__file__).resolve().parent
    root_dir = test_dir.parent
    parser.add_argument("--examples-dir", type=Path, default=root_dir / "examples")
    parser.add_argument("--expected-dir", type=Path, default=test_dir / "expected")
    parser.add_argument("--results-dir", type=Path, default=test_dir / "results")
    parser.add_argument("--parser-config", type=Path, default=root_dir / "knowledge" / "report_rules.json")
    parser.add_argument("--config", type=Path, default=test_dir / "json_compare_config.json")
    parser.add_argument("--refresh-expected", action="store_true")
    args = parser.parse_args()

    script = root_dir / "scripts" / "parse_pdf.py"
    config = load_config(args.config)
    ignore_paths = set(config["global_ignore_paths"])
    sort_list_paths = set(config["sort_list_paths"])
    failures: List[str] = []
    args.expected_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(args.examples_dir.glob("*.pdf")):
        # Component-analysis reports have their own parser and regression test.
        if "组分报告" in pdf_path.stem:
            continue
        expected_json = args.expected_dir / f"{pdf_path.stem}.expected.json"
        result_json = args.results_dir / f"{pdf_path.stem}.result.json"
        run_example(script, pdf_path, result_json, args.parser_config)

        if args.refresh_expected:
            expected_json.write_text(result_json.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"refreshed {expected_json.name}")
            continue

        if not expected_json.exists():
            failures.append(f"{pdf_path.stem}: missing expected fixture {expected_json.name}")
            continue

        expected = normalize_payload(json.loads(expected_json.read_text(encoding="utf-8")), "", sort_list_paths)
        result = normalize_payload(json.loads(result_json.read_text(encoding="utf-8")), "", sort_list_paths)
        diffs: List[str] = []
        compare_values(expected, result, "", ignore_paths, diffs)
        if diffs:
            failures.append(f"{pdf_path.stem}:\n" + "\n".join(diffs[:20]))
        else:
            print(f"ok {pdf_path.stem}")

    if failures:
        print("\n\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
