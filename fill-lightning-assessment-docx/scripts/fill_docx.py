#!/usr/bin/env python3
"""Fill only Attachment 2 assessment cells in one existing DOCX."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_SCRIPTS = PROJECT_ROOT / "scripts"
if not (PROJECT_SCRIPTS / "extract_attachment1.py").is_file():
    raise SystemExit(f"找不到项目评分脚本：{PROJECT_SCRIPTS}")
sys.path.insert(0, str(PROJECT_SCRIPTS))

from extract_attachment1 import calculate_assessment, extract_a4_review, extract_attachment  # noqa: E402
from generate_from_json import NS, all_tables, assessment_scores, qn, set_cell, set_fill_fonts, set_paragraph, text, value_text  # noqa: E402
from report_sections import extract_sections, fill_sections, report_table_kind  # noqa: E402


DOCUMENT_XML = "word/document.xml"


FORMULA_PATTERNS = (
    ("A.1", re.compile(r"^L=W1×L1\+W2×L2\+W3×L3=")),
    ("A.2", re.compile(r"^P=P1\+P2\+P3\+P4\+P5\+P6=")),
    ("A.5", re.compile(r"^S=MAX\(S1,S2,S3\)(?:=|…|\.|$)")),
    ("A.6", re.compile(r"^M=MAX\(M1,M2,M3,M4\)=")),
    ("R", re.compile(r"^R=L×S=")),
)


def canonical_formula_text(value: str) -> str:
    """Normalize harmless Word/template variants without weakening structure."""
    canonical = unicodedata.normalize("NFKC", value).upper()
    canonical = re.sub(r"\s+", "", canonical)
    canonical = canonical.replace("十", "+").replace("、", ",").replace("，", ",")
    canonical = canonical.replace("*", "×")
    # Treat x as multiplication only between formula operands; do not alter
    # the X in MAX.
    canonical = re.sub(r"(?<=[A-Z0-9])X(?=[A-Z0-9])", "×", canonical)
    return canonical


def formula_key(value: str) -> str | None:
    """Classify one formula line by its normalized mathematical structure."""
    canonical = canonical_formula_text(value)
    for key, pattern in FORMULA_PATTERNS:
        if pattern.match(canonical):
            return key
    return None


def set_checkbox(cell: ET.Element, checked: bool) -> bool:
    """Set every checkbox symbol in a cell and report whether it changed."""
    changed = False
    for symbol in cell.findall(".//w:sym", NS):
        font = symbol.get(qn("font"), "")
        checked_char, unchecked_char = (("0052", "00A3") if font == "Wingdings 2" else ("00FE", "00A8"))
        desired = checked_char if checked else unchecked_char
        if symbol.get(qn("char")) != desired:
            symbol.set(qn("char"), desired)
            changed = True
    return changed


def mark_score(row: ET.Element, score: object, option_columns: range) -> int:
    """Mark the option column whose printed numeric heading equals score."""
    cells = row.findall("w:tc", NS)
    if score is None:
        return 0
    try:
        selected = int(score)
    except (TypeError, ValueError):
        # An unresolved source selection is written as “待确认” in the result
        # cell.  Clear all option checks instead of guessing a numeric score.
        selected = -1
    edits = 0
    for index in option_columns:
        if index >= len(cells):
            continue
        edits += int(set_checkbox(cells[index], index == selected))
    return edits


def normalized(value: object) -> str:
    return re.sub(r"[\s，、,（）()、：:]", "", value_text(value))


def mark_a6_options(row: ET.Element, item: dict[str, object]) -> int:
    """Mark all source selections in A.6, retaining valid multi-selections."""
    cells = row.findall("w:tc", NS)
    raw_input = item.get("输入")
    inputs = raw_input if isinstance(raw_input, list) else [raw_input] if raw_input is not None else []
    selected_columns: set[int] = set()
    for value in inputs:
        wanted = normalized(value)
        if not wanted:
            continue
        for index in range(1, min(4, len(cells))):
            candidate = normalized(text(cells[index]))
            if wanted in candidate or candidate in wanted:
                selected_columns.add(index)
    if not selected_columns and item.get("分值") is not None:
        selected_columns.add(int(item["分值"]))
    edits = 0
    for index in range(1, min(4, len(cells))):
        edits += int(set_checkbox(cells[index], index in selected_columns))
    return edits


def set_result_cell(cell: ET.Element, value: object) -> int:
    desired = value_text(value)
    if text(cell).strip() == desired:
        return 0
    set_cell(cell, desired)
    return 1


def set_run_text(run: ET.Element, value: str, *, filled: bool = False) -> None:
    """Replace run text without disturbing its existing emphasis and sizing."""
    for node in list(run):
        if node.tag == qn("t"):
            run.remove(node)
    if filled:
        set_fill_fonts(run)
    node = ET.SubElement(run, qn("t"))
    if value.startswith(" ") or value.endswith(" "):
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = value


def insert_styled_run(
    paragraph: ET.Element,
    after: ET.Element,
    value: str,
    *,
    filled: bool,
    style_source: ET.Element | None = None,
) -> ET.Element:
    run = copy.deepcopy(style_source if style_source is not None else after)
    set_run_text(run, value, filled=filled)
    paragraph.insert(list(paragraph).index(after) + 1, run)
    return run


def set_run_bold(run: ET.Element) -> None:
    properties = run.find("w:rPr", NS)
    if properties is None:
        properties = ET.Element(qn("rPr"))
        run.insert(0, properties)
    for name in ("b", "bCs"):
        element = properties.find(f"w:{name}", NS)
        if element is None:
            element = ET.SubElement(properties, qn(name))
        element.set(qn("val"), "1")


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
    """Fill scores and check the selected options in Attachment 2 tables."""
    scores = assessment_scores(assessment)
    a1 = assessment.get("A.1", {})
    a2 = assessment.get("A.2", {})
    a3 = assessment.get("A.3", {})
    a5 = assessment.get("A.5", {})
    a6 = assessment.get("A.6", {})
    a7 = assessment.get("A.7", {})
    l_items = a1.get("雷击发生可能性", []) if isinstance(a1, dict) else []
    l_scores = {str(item.get("因子", "")).split()[0]: item.get("分值") for item in l_items if isinstance(item, dict)}
    p_total = a2.get("结果") if isinstance(a2, dict) else None
    chemical_grade = a7.get("化学品固有危险性等级") if isinstance(a7, dict) else None
    weights = {"L1": 0.2, "L2": 0.4, "L3": 0.4}
    a6_items = a6.get("化学品固有危险性因子", []) if isinstance(a6, dict) else []
    a6_by_code = {
        str(item.get("因子", "")).split()[0]: item
        for item in a6_items if isinstance(item, dict)
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
                    if code not in scores:
                        continue
                    edits += set_result_cell(cells[index + 1], scores[code])
                    if section == "A.2":
                        edits += mark_score(row, scores[code], range(1, 6))
                    elif section == "A.5":
                        edits += mark_score(row, scores[code], range(1, 4))
                    elif code in a6_by_code:
                        edits += mark_a6_options(row, a6_by_code[code])

        if section == "A.1":
            for row in rows:
                cells = row.findall("w:tc", NS)
                contents = [text(cell).strip() for cell in cells]
                for code, weight in weights.items():
                    if code in contents and contents:
                        score = l_scores.get(code)
                        if score is not None:
                            edits += set_result_cell(cells[-1], f"{float(score) * weight:g}")
                            edits += mark_score(row, score, range(1, 4))

        if section == "A.3" and p_total is not None:
            for row in rows[1:]:
                cells = row.findall("w:tc", NS)
                if len(cells) < 3:
                    continue
                bounds = [int(number) for number in re.findall(r"\d+", text(cells[0]))]
                selected = len(bounds) == 2 and bounds[0] <= int(p_total) <= bounds[1]
                edits += int(set_checkbox(cells[1], selected))
                edits += set_result_cell(cells[-1], p_total if selected else "")

        if section == "A.7" and chemical_grade and isinstance(a7, dict):
            chemical_score = a7.get("化学品固有危险性分值")
            for row in rows[1:]:
                cells = row.findall("w:tc", NS)
                if len(cells) < 2:
                    continue
                selected = text(cells[0]).strip() == value_text(chemical_score)
                edits += int(set_checkbox(cells[1], selected))

    return edits, recognized


def fill_formula_paragraphs(root: ET.Element, assessment: dict[str, object]) -> tuple[int, set[str]]:
    """Fill the five printed calculation lines following A.1/A.2/A.5/A.6/A.7."""
    a1 = assessment.get("A.1", {})
    a2 = assessment.get("A.2", {})
    a5 = assessment.get("A.5", {})
    a6 = assessment.get("A.6", {})
    a8 = assessment.get("A.8", {})
    l = a1.get("结果") if isinstance(a1, dict) else None
    p = a2.get("结果") if isinstance(a2, dict) else None
    s = a5.get("结果") if isinstance(a5, dict) else None
    m = a6.get("结果") if isinstance(a6, dict) else None
    r = a8.get("R") if isinstance(a8, dict) else None
    values = {
        "A.1": f"L = W1×L1十W2×L2十W3×L3  ={value_text(l)}……………(A. 1)",
        "A.2": f"P = P1十 P2 十 P3 十 P4 十 P5 十 P6 = {value_text(p)}",
        "A.5": f"S=MAX(S1，S2，S3 )={value_text(s)} ………………(A. 3)",
        "A.6": f"M=MAX(M1，M2，M3，M4 ) ={value_text(m)}   ………………(A. 4)",
        "R": f"R=L×S={value_text(l)}×{value_text(s)}={value_text(r)}",
    }
    edits = 0
    recognized: set[str] = set()
    for paragraph in root.findall(".//w:p", NS):
        key = formula_key(text(paragraph))
        if key is not None:
            recognized.add(key)
            if text(paragraph) != values[key]:
                runs = paragraph.findall("w:r", NS)
                visible = text(paragraph)
                already_filled = (
                    key in {"A.1", "A.2", "A.6"} and "？" not in visible and "?" not in visible
                ) or (
                    key == "A.5" and re.search(r"\)\s*=\s*[^…\s]", visible) is not None
                ) or (
                    key == "R" and not canonical_formula_text(visible).endswith("=")
                )
                if already_filled:
                    # Some source reports contain stale completed formula
                    # values instead of question-mark placeholders.  Replace
                    # that target paragraph atomically so reruns can correct it.
                    set_paragraph(paragraph, values[key])
                    edits += 1
                    continue
                if key == "A.1":
                    result_run = next(run for run in runs if "？" in text(run) or "?" in text(run))
                    set_run_text(result_run, re.sub(r"[？?]", value_text(l), text(result_run)), filled=True)
                    result_index = runs.index(result_run)
                    suffix_run = next(run for run in runs[result_index + 1:] if "…" in text(run))
                    for run in runs[result_index + 1:runs.index(suffix_run)]:
                        set_run_text(run, "")
                    set_run_text(suffix_run, text(suffix_run).replace("………………", "……………"))
                elif key == "A.2":
                    result_run = next(run for run in runs if "？" in text(run) or "?" in text(run))
                    set_run_text(result_run, re.sub(r"[？?]", value_text(p), text(result_run)), filled=True)
                elif key == "A.5":
                    tail_run = next(run for run in runs if ")" in text(run) and "…" in text(run))
                    set_run_text(tail_run, " )")
                    equals_run = insert_styled_run(paragraph, tail_run, "=", filled=False)
                    result_run = insert_styled_run(paragraph, equals_run, value_text(s), filled=True)
                    set_run_bold(result_run)
                    insert_styled_run(
                        paragraph,
                        result_run,
                        " ………………(A. 3)",
                        filled=False,
                        style_source=tail_run,
                    )
                elif key == "A.6":
                    result_run = next(run for run in runs if "？" in text(run) or "?" in text(run))
                    set_run_text(result_run, re.sub(r"[？?]", value_text(m), text(result_run)), filled=True)
                elif key == "R":
                    base_run = next(run for run in runs if "R=L×S=" in text(run))
                    insert_styled_run(
                        paragraph,
                        base_run,
                        f"{value_text(l)}×{value_text(s)}={value_text(r)}",
                        filled=True,
                    )
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
    parser = argparse.ArgumentParser(description="读取附件1和A.4并填写附件2；可从完整assessment JSON填写报告主观分析")
    parser.add_argument("input", type=Path, help="输入 DOCX")
    parser.add_argument("--output", type=Path, help="输出 DOCX；默认添加 .filled 后缀")
    parser.add_argument("--report", type=Path, help="可选的 assessment JSON 审计文件")
    parser.add_argument("--assessment-json", type=Path, help="包含报告章节AI生成字段的完整assessment JSON")
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
        calculated_assessment = calculate_assessment(fields, source_path.stem, a4_review)
        assessment = dict(calculated_assessment)
        assessment["报告章节"] = extract_sections(source_path, fields)
        with zipfile.ZipFile(source_path) as source:
            root = ET.fromstring(source.read(DOCUMENT_XML))
        sections_data: dict[str, object] | None = None
        reviewed_assessment: dict[str, object] | None = None
        if args.assessment_json:
            try:
                loaded = json.loads(args.assessment_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(f"无法读取assessment JSON：{error}") from error
            if not isinstance(loaded, dict):
                raise ValueError("assessment JSON顶层必须是对象")
            for key, expected in calculated_assessment.items():
                if loaded.get(key) != expected:
                    raise ValueError(f"assessment JSON中的客观评估字段“{key}”与DOCX重新计算结果不一致")
            raw_sections = loaded.get("报告章节")
            if not isinstance(raw_sections, dict):
                raise ValueError("assessment JSON缺少“报告章节”对象")
            if raw_sections.get("source_document") != source_path.name:
                raise ValueError("assessment JSON的报告章节来源文件与当前DOCX不一致")
            sections_data = raw_sections
            reviewed_assessment = loaded
        original_non_targets = [
            ET.tostring(table, encoding="utf-8")
            for table in all_tables(root)
            if target_section(text(table)) is None
            and not (sections_data is not None and report_table_kind(table) is not None)
        ]
        edits, recognized = fill_target_tables(root, assessment)
        required = {"A.1", "A.2", "A.3", "A.5", "A.6", "A.7", "A.8"}
        if missing := sorted(required - recognized):
            raise ValueError(f"未识别附件2目标表：{', '.join(missing)}")
        formula_edits, recognized_formulas = fill_formula_paragraphs(root, assessment)
        edits += formula_edits
        required_formulas = {"A.1", "A.2", "A.5", "A.6", "R"}
        if missing := sorted(required_formulas - recognized_formulas):
            raise ValueError(f"未识别附件2计算公式：{', '.join(missing)}")
        if sections_data is not None:
            section_edits, recognized_sections = fill_sections(root, sections_data)
            edits += section_edits
            required_sections = {"第四章：企业概况与现场勘查情况", "第五章：雷电灾害风险识别与评估", "附件6：防雷安全重点单位“重点部位”风险分类分级管控清单"}
            if missing := sorted(required_sections - recognized_sections):
                raise ValueError(f"未识别报告章节目标：{', '.join(missing)}")
        current_non_targets = [
            ET.tostring(table, encoding="utf-8")
            for table in all_tables(root)
            if target_section(text(table)) is None
            and not (sections_data is not None and report_table_kind(table) is not None)
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
            report_data = reviewed_assessment if reviewed_assessment is not None else assessment
            args.report.write_text(json.dumps(report_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile, KeyError) as error:
        if temporary_output is not None and temporary_output.exists():
            temporary_output.unlink()
        raise SystemExit(f"处理失败：{error}") from error

    warnings = calculated_assessment.get("validation_errors", [])
    print(f"已生成：{output_path}")
    print(f"填写单元格：{edits}")
    print(f"validation_errors：{json.dumps(warnings, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
