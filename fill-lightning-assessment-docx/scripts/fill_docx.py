#!/usr/bin/env python3
"""Fill only Attachment 2 assessment cells in one existing DOCX."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SCRIPTS = PROJECT_ROOT / "scripts"
if not (PROJECT_SCRIPTS / "extract_attachment1.py").is_file():
    raise SystemExit(f"找不到项目评分脚本：{PROJECT_SCRIPTS}")
sys.path.insert(0, str(PROJECT_SCRIPTS))

from extract_attachment1 import calculate_assessment, extract_a4_review, extract_attachment  # noqa: E402
from generate_from_json import NS, all_tables, append_cell, assessment_scores, set_cell, text, value_text  # noqa: E402


DOCUMENT_XML = "word/document.xml"


def target_section(table_text: str) -> str | None:
    """Identify only the Attachment 2 tables this script may edit."""
    markers = (
        ("A.1", ("雷击发生可能性等级", "权重赋值")),
        ("A.2", ("雷击密度", "相对高度", "Pn")),
        ("A.3", ("雷击发生可能性分值", "L1分值")),
        ("A.5", ("风险单元现场人数最大值", "Sn")),
        ("A.6", ("化学品急性毒性危害类别", "Mn")),
        ("A.7", ("化学品固有危险性分值", "化学品固有危险性等级")),
        ("A.8", ("综合评估（R）及对应风险",)),
    )
    for section, required in markers:
        if all(marker in table_text for marker in required):
            return section
    return None


def fill_target_tables(root: ET.Element, assessment: dict[str, object]) -> tuple[int, set[str]]:
    """Fill blank result cells and return the edit count and recognized sections."""
    scores = assessment_scores(assessment)
    a1 = assessment.get("A.1", {})
    a2 = assessment.get("A.2", {})
    a3 = assessment.get("A.3", {})
    a5 = assessment.get("A.5", {})
    a7 = assessment.get("A.7", {})
    a8 = assessment.get("A.8", {})
    l_items = a1.get("雷击发生可能性", []) if isinstance(a1, dict) else []
    l_scores = {str(item.get("因子", "")).split()[0]: item.get("分值") for item in l_items if isinstance(item, dict)}
    p_total = a2.get("结果") if isinstance(a2, dict) else None
    l_grade = a3.get("雷击发生可能性分级") if isinstance(a3, dict) else None
    consequence = a5.get("结果") if isinstance(a5, dict) else None
    chemical_grade = a7.get("化学品固有危险性等级") if isinstance(a7, dict) else None
    risk = a8.get("R") if isinstance(a8, dict) else None
    risk_level = a8.get("风险等级") if isinstance(a8, dict) else None
    weights = {"L1": 0.2, "L2": 0.4, "L3": 0.4}
    result_values = {
        "雷击发生可能性等级": value_text(l_grade),
        "后果严重性": value_text(consequence),
        "化学品固有危险性等级": value_text(chemical_grade),
        "风险等级": value_text(risk_level),
        "R值": value_text(risk),
    }

    edits = 0
    recognized: set[str] = set()
    for table in all_tables(root):
        table_text = text(table)
        section = target_section(table_text)
        if section is None:
            continue
        recognized.add(section)
        rows = table.findall("w:tr", NS)

        if section in {"A.2", "A.5", "A.6"}:
            for row in rows:
                cells = row.findall("w:tc", NS)
                contents = [text(cell).strip() for cell in cells]
                for index, code in enumerate(contents[:-1]):
                    if code in scores and not contents[index + 1]:
                        set_cell(cells[index + 1], scores[code])
                        edits += 1

        if section == "A.1":
            for row in rows:
                cells = row.findall("w:tc", NS)
                contents = [text(cell).strip() for cell in cells]
                for code, weight in weights.items():
                    if code in contents and contents and not contents[-1]:
                        score = l_scores.get(code)
                        if score is not None:
                            set_cell(cells[-1], f"{float(score) * weight:g}")
                            edits += 1

        if section == "A.3" and p_total is not None:
            for row in rows[1:]:
                cells = row.findall("w:tc", NS)
                if len(cells) < 3:
                    continue
                bounds = [int(number) for number in re.findall(r"\d+", text(cells[0]))]
                if len(bounds) == 2 and bounds[0] <= int(p_total) <= bounds[1] and not text(cells[-1]).strip():
                    set_cell(cells[-1], str(p_total))
                    edits += 1
                    break

        if section == "A.8" and risk is not None:
            for row in rows:
                cells = row.findall("w:tc", NS)
                if len(cells) != 1:
                    continue
                visible = text(cells[0]).strip()
                if visible == "综合评估（R）及对应风险":
                    append_cell(cells[0], f"：R = {risk}，{risk_level}")
                    edits += 1
                    break

        for row in rows:
            cells = row.findall("w:tc", NS)
            for index, cell in enumerate(cells[:-1]):
                label = text(cell).replace(" ", "").strip("：:")
                if label in result_values and result_values[label] and not text(cells[index + 1]).strip():
                    set_cell(cells[index + 1], result_values[label])
                    edits += 1

    return edits, recognized


def write_docx(source_path: Path, output_path: Path, document_xml: bytes) -> None:
    """Copy the OOXML package while replacing only word/document.xml."""
    with zipfile.ZipFile(source_path) as source, zipfile.ZipFile(output_path, "w") as output:
        for info in source.infolist():
            payload = document_xml if info.filename == DOCUMENT_XML else source.read(info.filename)
            output.writestr(info, payload)


def verify_package(source_path: Path, output_path: Path) -> None:
    """Ensure every package member except document.xml is byte-identical."""
    with zipfile.ZipFile(source_path) as source, zipfile.ZipFile(output_path) as output:
        source_names = source.namelist()
        if source_names != output.namelist():
            raise ValueError("输出 DOCX 的 ZIP 成员列表发生变化")
        for name in source_names:
            if name != DOCUMENT_XML and source.read(name) != output.read(name):
                raise ValueError(f"非目标内容发生变化：{name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="读取附件1和A.4，仅填写附件2其他评估表")
    parser.add_argument("input", type=Path, help="输入 DOCX")
    parser.add_argument("--output", type=Path, help="输出 DOCX；默认添加 .filled 后缀")
    parser.add_argument("--report", type=Path, help="可选的 assessment JSON 审计文件")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的输出文件（不能覆盖输入）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.input.resolve()
    output_path = (args.output or source_path.with_name(f"{source_path.stem}.filled.docx")).resolve()
    if not source_path.is_file() or source_path.suffix.lower() != ".docx":
        raise SystemExit(f"输入不是有效的 DOCX 文件：{source_path}")
    if source_path.name.startswith("~$"):
        raise SystemExit(f"拒绝处理 Word 临时锁文件：{source_path.name}")
    if output_path == source_path:
        raise SystemExit("拒绝覆盖输入 DOCX；请指定不同的输出路径")
    if output_path.exists() and not args.force:
        raise SystemExit(f"输出文件已存在：{output_path}；明确允许后可使用 --force")

    temporary_output: Path | None = None
    try:
        fields = extract_attachment(source_path)
        a4_review = extract_a4_review(source_path)
        if a4_review.get("人工复核") is not True:
            raise ValueError("未找到表 A.4 雷电灾害事故发生可能性直接赋值“3”的情况列表")
        assessment = calculate_assessment(fields, source_path.stem, a4_review)
        with zipfile.ZipFile(source_path) as source:
            root = ET.fromstring(source.read(DOCUMENT_XML))
        original_non_targets = [
            ET.tostring(table, encoding="utf-8")
            for table in all_tables(root)
            if target_section(text(table)) is None
        ]
        edits, recognized = fill_target_tables(root, assessment)
        required = {"A.1", "A.2", "A.3", "A.5", "A.6", "A.7", "A.8"}
        if missing := sorted(required - recognized):
            raise ValueError(f"未识别附件2目标表：{', '.join(missing)}")
        current_non_targets = [
            ET.tostring(table, encoding="utf-8")
            for table in all_tables(root)
            if target_section(text(table)) is None
        ]
        if original_non_targets != current_non_targets:
            raise ValueError("检测到附件2目标表之外的表格发生变化")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=output_path.parent,
            prefix=f".{output_path.stem}.",
            suffix=".tmp.docx",
        )
        os.close(descriptor)
        temporary_output = Path(temporary_name)
        if edits:
            document_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            write_docx(source_path, temporary_output, document_xml)
        else:
            shutil.copyfile(source_path, temporary_output)
        verify_package(source_path, temporary_output)
        temporary_output.replace(output_path)
        temporary_output = None
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(assessment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, KeyError) as error:
        if temporary_output is not None and temporary_output.exists():
            temporary_output.unlink()
        raise SystemExit(f"处理失败：{error}") from error

    warnings = assessment.get("validation_errors", [])
    print(f"已生成：{output_path}")
    print(f"填写单元格：{edits}")
    print(f"validation_errors：{json.dumps(warnings, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
