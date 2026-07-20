#!/usr/bin/env python3
"""Compare calculated Attachment 2 score cells in reference and generated DOCX files."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
CODES = ("P1", "P2", "P3", "P4", "P5", "P6", "S1", "S2", "S3", "M1", "M2", "M3", "M4")


def cell_text(cell: ET.Element) -> str:
    return "".join(cell.itertext()).strip()


def extract(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    scores: dict[str, str] = {}
    weighted: dict[str, str] = {}
    p_total: str | None = None
    for row in root.findall(".//w:tr", NS):
        cells = row.findall("w:tc", NS)
        values = [cell_text(cell) for cell in cells]
        for index, value in enumerate(values[:-1]):
            if value in CODES:
                scores[value] = values[index + 1]
            if value in {"L1", "L2", "L3"} and values[-1]:
                weighted[value] = values[-1]
        if len(values) >= 3 and values[0].startswith("[") and values[1] in {"Ⅲ", "Ⅱ", "I"} and values[2]:
            p_total = values[2]
    return {"scores": scores, "weighted": weighted, "P": p_total}


def main() -> int:
    parser = argparse.ArgumentParser(description="对比原始与生成DOCX的附件2计算单元格")
    parser.add_argument("--reference-dir", type=Path, default=Path("data"))
    parser.add_argument("--generated-dir", type=Path, default=Path("test/try/results"))
    parser.add_argument("--output", type=Path, default=Path("test/try/results/attachment2_comparison.json"))
    args = parser.parse_args()
    report: dict[str, object] = {}
    for reference in sorted(args.reference_dir.glob("*.docx")):
        if reference.name.startswith("~$"):
            continue
        generated = args.generated_dir / reference.name
        if not generated.exists():
            report[reference.name] = {"status": "missing_generated_file"}
            continue
        original = extract(reference)
        created = extract(generated)
        report[reference.name] = {
            "status": "match" if original == created else "different",
            "original": original,
            "generated": created,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
