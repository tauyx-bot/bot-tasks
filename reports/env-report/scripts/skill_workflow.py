#!/usr/bin/env python3
"""Public workflow entry point for the env-report skill."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import fill_docx
import generate_report
import parse_component_report
import parse_pdf
from prepare_reviewed_json import prepare_payload


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_ROOT / "template" / "plan_template.docx"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_command(args: argparse.Namespace) -> None:
    write_json(args.output, parse_pdf.build_payload(args.pdf))
    print(f"raw_json={args.output}")
    print("next=对照PDF审核此文件，另存为reviewed JSON；不要覆盖raw JSON")


def generate_command(args: argparse.Namespace) -> None:
    reviewed = json.loads(args.reviewed_json.read_text(encoding="utf-8"))
    normalized = prepare_payload(reviewed)
    normalized_out = args.normalized_out or args.output.with_suffix(".normalized.json")
    report_json = args.json_out or args.output.with_suffix(".json")
    write_json(normalized_out, normalized)
    component_payload = (
        parse_component_report.build_payload(args.component_report)
        if args.component_report
        else None
    )
    report_payload = generate_report.build_report_payload(normalized, component_payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fill_docx.fill_document(args.template, report_payload, args.output)
    write_json(report_json, report_payload)
    print(f"docx={args.output}")
    print(f"normalized_json={normalized_out}")
    print(f"report_json={report_json}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="调查表审核与采样计划生成")
    commands = parser.add_subparsers(dest="command", required=True)
    parse_parser = commands.add_parser("parse", help="解析PDF为待审核raw JSON")
    parse_parser.add_argument("--pdf", required=True, type=Path)
    parse_parser.add_argument("--output", required=True, type=Path)
    parse_parser.set_defaults(handler=parse_command)

    generate_parser = commands.add_parser("generate", help="校验reviewed JSON并生成报告")
    generate_parser.add_argument("--reviewed-json", required=True, type=Path)
    generate_parser.add_argument("--output", required=True, type=Path)
    generate_parser.add_argument("--component-report", type=Path)
    generate_parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    generate_parser.add_argument("--normalized-out", type=Path)
    generate_parser.add_argument("--json-out", type=Path)
    generate_parser.set_defaults(handler=generate_command)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
