#!/usr/bin/env python3
"""Validate model-reviewed survey rows and rebuild all derived report data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import parse_pdf


def prepare_payload(payload: object) -> dict[str, object]:
    """Validate reviewed source data and return its canonical payload."""
    if not isinstance(payload, dict):
        raise ValueError("审核 JSON 顶层必须是对象")
    errors, warnings = parse_pdf.validate_reviewed_payload(payload)
    if errors:
        raise ValueError("审核门禁未通过：\n- " + "\n- ".join(errors))
    rebuilt = parse_pdf.rebuild_reviewed_payload(payload)
    rebuilt["review_status"] = {
        "normalized": True,
        "workflow_version": parse_pdf.REVIEW_WORKFLOW_VERSION,
        "warnings": warnings,
    }
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        rebuilt = prepare_payload(payload)
        args.output.write_text(
            json.dumps(rebuilt, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        for warning in rebuilt["review_status"]["warnings"]:
            print(f"warning: {warning}", file=sys.stderr)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
