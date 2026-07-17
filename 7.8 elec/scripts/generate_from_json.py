#!/usr/bin/env python3
"""Generate assessment JSON files and populated ledger DOCX files from attachment JSON.

The input JSON schema is the one produced by ``extract_attachment1.py``.  The
script deliberately uses only the standard library so it can run alongside the
existing extraction script without installing python-docx.

Example:
    python3 scripts/generate_from_json.py --input-dir test/try
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from extract_attachment1 import A4_JSON_KEY, a4_review_overrides, calculate_assessment  # noqa: E402


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
ET.register_namespace("w", W)


def qn(name: str) -> str:
    return f"{{{W}}}{name}"


def norm(value: str) -> str:
    return re.sub(r"[\s：:（）()、，,。；;\-]", "", value or "")


def text(element: ET.Element) -> str:
    return "".join(element.itertext()).replace("\u00a0", " ").strip()


def value_text(value: object) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}：{item}" for key, item in value.items())
    return "" if value is None else str(value)


def street_from_address(address: str) -> str:
    match = re.search(r"([^，,；;]*?(?:街道|办事处))", address)
    return match.group(1).split("区")[-1] if match else ""


def set_paragraph(paragraph: ET.Element, value: str) -> None:
    """Replace a paragraph's displayed value while retaining its first run style."""
    runs = paragraph.findall("w:r", NS)
    if runs:
        run = runs[0]
        for extra in runs[1:]:
            paragraph.remove(extra)
    else:
        run = ET.SubElement(paragraph, qn("r"))
    for node in list(run):
        if node.tag == qn("t"):
            run.remove(node)
    t = ET.SubElement(run, qn("t"))
    if value.startswith(" ") or value.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = value


def set_cell(cell: ET.Element, value: str) -> None:
    paragraphs = cell.findall("w:p", NS)
    if paragraphs:
        set_paragraph(paragraphs[0], value)
        for paragraph in paragraphs[1:]:
            set_paragraph(paragraph, "")
    else:
        paragraph = ET.SubElement(cell, qn("p"))
        set_paragraph(paragraph, value)


def append_cell(cell: ET.Element, value: str) -> None:
    """Append result text to a labelled cell without removing its label."""
    paragraphs = cell.findall("w:p", NS)
    if not paragraphs:
        set_cell(cell, value)
        return
    paragraph = paragraphs[0]
    runs = paragraph.findall("w:r", NS)
    run = copy.deepcopy(runs[-1]) if runs else ET.SubElement(paragraph, qn("r"))
    if runs:
        paragraph.append(run)
    for node in list(run):
        if node.tag in {qn("t"), qn("sym")}:
            run.remove(node)
    node = ET.SubElement(run, qn("t"))
    node.text = value


def all_tables(parent: ET.Element):
    for table in parent.findall(".//w:tbl", NS):
        yield table


def build_values(fields: dict[str, object], assessment: dict[str, object], stem: str) -> dict[str, str]:
    building = fields.get("区域建筑物", {})
    building = building if isinstance(building, dict) else {}
    today = date.today()
    unit = value_text(fields.get("单位名称（盖章）") or fields.get("单位名称") or stem)
    phone = value_text(fields.get("联系电话"))
    leader = value_text(fields.get("法定代表人(负责人)"))
    address = value_text(fields.get("单位地址"))
    values: dict[str, str] = {
        "单位名称": unit,
        "单位名称盖章": unit,
        "地址": address,
        "单位地址": address,
        "负责人": leader,
        "法定代表人负责人": leader,
        "负责人及电话": " ".join(item for item in (leader, phone) if item),
        "联系电话": phone,
        "应急联系人": value_text(fields.get("应急联系人")),
        "安全员": value_text(fields.get("安全员")),
        "统一社会信用代码": value_text(fields.get("社会统一信用代码")),
        "经纬度": value_text(fields.get("经纬度")),
        "所属街道": street_from_address(address),
        "建档日期": f"{today.year}年{today.month}月{today.day}日",
        "区域建筑物": value_text(building),
        "面积": value_text(building.get("面积")),
        "建筑高度": value_text(building.get("建筑高度")),
        "等效高度": value_text(building.get("等效高度")),
        "相对高度": value_text(building.get("相对高度")),
    }
    for key, value in fields.items():
        values[norm(key)] = value_text(value)

    # Add the calculation factors so tables in the risk-assessment chapter are
    # filled even where the table labels omit the A.x section number.
    for section in ("A.1", "A.2", "A.5", "A.6"):
        for item in assessment.get(section, {}).get(next(iter(assessment.get(section, {})), ""), []):
            if isinstance(item, dict) and item.get("因子"):
                label = re.sub(r"^[PLSM]\d\s*", "", str(item["因子"])).replace("等级", "")
                values[norm(label)] = value_text(item.get("分值"))
    for key, section in (("雷击发生可能性分级", "A.3"), ("化学品固有危险性等级", "A.7"), ("风险等级", "A.8")):
        result = assessment.get(section, {})
        if isinstance(result, dict):
            values[norm(key)] = value_text(result.get(key))
    values["风险值"] = value_text(assessment.get("A.8", {}).get("R"))
    return values


def assessment_scores(assessment: dict[str, object]) -> dict[str, str]:
    scores: dict[str, str] = {}
    for section in ("A.1", "A.2", "A.5", "A.6"):
        data = assessment.get(section, {})
        if not isinstance(data, dict):
            continue
        for value in data.values():
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("因子"), str):
                    match = re.match(r"([PLSM]\d)", item["因子"])
                    if match:
                        # A conflicted checkbox selection has no defensible
                        # numeric score.  Make that explicit in the form
                        # instead of silently leaving a score cell blank.
                        score = item.get("分值")
                        scores[match.group(1)] = value_text(score) if score is not None else "待确认"
    return scores


def populate_assessment_tables(root: ET.Element, assessment: dict[str, object]) -> None:
    """Write every derived Attachment 2 result from calculated assessment data."""
    scores = assessment_scores(assessment)
    a1 = assessment.get("A.1", {})
    a2 = assessment.get("A.2", {})
    a3 = assessment.get("A.3", {})
    a5 = assessment.get("A.5", {})
    a7 = assessment.get("A.7", {})
    a8 = assessment.get("A.8", {})
    l_items = a1.get("雷击发生可能性", []) if isinstance(a1, dict) else []
    l_scores = {str(item.get("因子", "")).split()[0]: item.get("分值") for item in l_items if isinstance(item, dict)}
    weights = {"L1": 0.2, "L2": 0.4, "L3": 0.4}
    p_total = a2.get("结果") if isinstance(a2, dict) else None
    l_grade = a3.get("雷击发生可能性分级") if isinstance(a3, dict) else None
    consequence = a5.get("结果") if isinstance(a5, dict) else None
    chemical_grade = a7.get("化学品固有危险性等级") if isinstance(a7, dict) else None
    risk = a8.get("R") if isinstance(a8, dict) else None
    risk_level = a8.get("风险等级") if isinstance(a8, dict) else None

    for table in all_tables(root):
        rows = table.findall("w:tr", NS)
        table_text = text(table)
        for row in rows:
            cells = row.findall("w:tc", NS)
            contents = [text(cell).strip() for cell in cells]
            # P1 ... M4 score columns.
            for index, code in enumerate(contents[:-1]):
                if code in scores and not contents[index + 1]:
                    set_cell(cells[index + 1], scores[code])
            # L1 ... L3: the last cell is weight × level score.
            for code, weight in weights.items():
                if code in contents and contents and not contents[-1]:
                    score = l_scores.get(code)
                    if score is not None:
                        set_cell(cells[-1], f"{float(score) * weight:g}")

        if "雷击发生可能性分值" in table_text and p_total is not None:
            # The L1 grading table records P, then derives its grade.  Select
            # the row from the calculated P range instead of hard-coding it.
            for row in rows[1:]:
                cells = row.findall("w:tc", NS)
                if len(cells) < 3:
                    continue
                bounds = [int(number) for number in re.findall(r"\d+", text(cells[0]))]
                if len(bounds) == 2 and bounds[0] <= int(p_total) <= bounds[1]:
                    set_cell(cells[-1], str(p_total))
                    break
        if "综合评估（R）及对应风险" in table_text and risk is not None:
            for row in rows:
                cells = row.findall("w:tc", NS)
                if len(cells) == 1 and "综合评估（R）及对应风险" in text(cells[0]):
                    append_cell(cells[0], f"：R = {risk}，{risk_level}")
                    break

    # Keep these values available for template variants that label result cells
    # rather than using the Pn/Sn/Mn code columns.
    result_values = {
        "雷击发生可能性等级": value_text(l_grade),
        "后果严重性": value_text(consequence),
        "化学品固有危险性等级": value_text(chemical_grade),
        "风险等级": value_text(risk_level),
        "R值": value_text(risk),
    }
    for table in all_tables(root):
        for row in table.findall("w:tr", NS):
            cells = row.findall("w:tc", NS)
            for index, cell in enumerate(cells[:-1]):
                label = norm(text(cell))
                if label in result_values and not text(cells[index + 1]):
                    set_cell(cells[index + 1], result_values[label])


def populate_attachment1(table: ET.Element, fields: dict[str, object]) -> None:
    """Fill the fixed-layout Attachment 1 table, including checkbox fields."""
    rows = table.findall("w:tr", NS)
    by_label: dict[str, list[ET.Element]] = {}
    for row in rows:
        for cell in row.findall("w:tc", NS):
            by_label.setdefault(norm(text(cell)), []).append(row)

    def row(label: str) -> ET.Element | None:
        matches = by_label.get(norm(label), [])
        return matches[0] if matches else None

    def cells(label: str) -> list[ET.Element]:
        found = row(label)
        return found.findall("w:tc", NS) if found is not None else []

    # The four telephone blanks are distinct fields, although the printed
    # label is repeated three times in the first row.
    phones = [value_text(fields[key]) for key in sorted(fields) if key == "联系电话" or key.startswith("联系电话_")]
    phone_cells = []
    for candidate in (row("联系电话"), row("经营状态")):
        if candidate is not None:
            row_cells = candidate.findall("w:tc", NS)
            phone_cells.extend(cell for index, cell in enumerate(row_cells[:-1]) if norm(text(cell)) == "联系电话" for cell in [row_cells[index + 1]])
    for cell, phone in zip(phone_cells, phones):
        set_cell(cell, phone)

    coordinate_cells = cells("经纬度")
    coordinate = value_text(fields.get("经纬度"))
    if len(coordinate_cells) >= 3 and "；" in coordinate:
        east, north = coordinate.split("；", 1)
        set_cell(coordinate_cells[1], east)
        set_cell(coordinate_cells[2], north)

    def set_options(label: str, options: list[str]) -> None:
        row_cells = cells(label)
        for index, cell in enumerate(row_cells[:-1]):
            if norm(text(cell)) == norm(label):
                set_cell(row_cells[index + 1], "；".join(options))
                return

    set_options("雷电监测设备", ["☑ " + value_text(fields.get("雷电监测设备"))])
    set_options("是否正常运行", ["☑ " + value_text(fields.get("是否正常运行"))])
    set_options("存放危险化学品", ["☑ " + value_text(fields.get("存放危险化学品"))])
    set_options("危险化学品存放区域", ["☑ " + value_text(fields.get("危险化学品存放区域"))])
    set_options("火灾危险性类别", ["☑ " + value_text(fields.get("火灾危险性类别"))])
    set_options("防雷装置", ["☑ " + value_text(fields.get("防雷装置"))])
    set_options("毒性危害性类别", ["☑ " + value_text(fields.get("毒性危害性类别"))])
    set_options("危险工艺", ["☑ " + value_text(fields.get("危险工艺"))])
    set_options("重大危险源", ["☑ " + value_text(fields.get("重大危险源"))])
    set_options("风险单元现场最大人数", ["☑ " + value_text(fields.get("风险单元现场最大人数"))])
    set_options("周边地理情况", ["☑ " + value_text(fields.get("周边地理情况"))])
    set_options("是否有历史灾情", ["☑ " + value_text(fields.get("是否有历史灾情"))])
    building = fields.get("区域建筑物", {})
    if isinstance(building, dict):
        set_options("区域建筑物", [
            f"区域建筑物面积：{building.get('面积', '')}；建筑高度：{building.get('建筑高度', '')}；"
            f"等效高度：{building.get('等效高度', '')}；相对高度：{building.get('相对高度', '')}。"
        ])


def populate_a4_checkmarks(root: ET.Element, assessment: dict[str, object]) -> None:
    """Reflect manually reviewed A.4 findings in the direct-assignment table."""
    a4 = assessment.get("A.4", {})
    if not isinstance(a4, dict) or a4.get("人工复核") is not True:
        return
    selected = {norm(str(value)) for value in a4.get("直接赋值条件", [])}
    for table in all_tables(root):
        table_text = text(table)
        if "防雷安全管理" not in table_text or "雷电灾害历史" not in table_text:
            continue
        for cell in table.findall(".//w:tc", NS):
            pending_symbol: ET.Element | None = None
            for run in cell.findall(".//w:r", NS):
                symbol = run.find("w:sym", NS)
                if symbol is not None:
                    pending_symbol = symbol
                    continue
                label = text(run)
                if pending_symbol is not None and label:
                    pending_symbol.set(qn("char"), "00FE" if norm(label) in selected else "00A8")
                    pending_symbol = None


def populate_docx(template: Path, destination: Path, values: dict[str, str], fields: dict[str, object], assessment: dict[str, object]) -> None:
    """Copy template then fill blank value cells and cover-page value runs."""
    with TemporaryDirectory() as tmp:
        unpacked = Path(tmp) / "docx"
        with zipfile.ZipFile(template) as source:
            source.extractall(unpacked)
        document_path = unpacked / "word" / "document.xml"
        root = ET.parse(document_path).getroot()

        attachment_tables = [table for table in all_tables(root) if "单位名称（盖章）" in text(table) and "经纬度" in text(table)]
        if attachment_tables:
            populate_attachment1(attachment_tables[0], fields)
        populate_a4_checkmarks(root, assessment)
        populate_assessment_tables(root, assessment)

        # Tables: a label cell followed by an empty cell is the template's
        # standard form layout.  Only empty value cells are changed, so fixed
        # instructions and pre-filled checklists remain intact.
        for table in all_tables(root):
            for row in table.findall("w:tr", NS):
                cells = row.findall("w:tc", NS)
                for index, cell in enumerate(cells[:-1]):
                    label = norm(text(cell))
                    if label in values and not text(cells[index + 1]):
                        set_cell(cells[index + 1], values[label])

        # A.2/A.5/A.6 tables use P1…M4 in one cell and leave the following
        # cell blank for the score.  This is more reliable than matching their
        # long descriptive factor labels.
        scores = assessment_scores(assessment)
        for table in all_tables(root):
            for row in table.findall("w:tr", NS):
                cells = row.findall("w:tc", NS)
                for index, cell in enumerate(cells[:-1]):
                    code = text(cell).strip()
                    if code in scores and not text(cells[index + 1]):
                        set_cell(cells[index + 1], scores[code])

        # Cover-page fields are ordinary paragraphs rather than table cells.
        for paragraph in root.findall(".//w:p", NS):
            visible = text(paragraph)
            for label in ("单位名称：", "所属街道：", "建档日期："):
                if visible.startswith(label) and visible[len(label):].strip() == "":
                    runs = paragraph.findall("w:r", NS)
                    if runs:
                        target = runs[-1]
                        for node in list(target):
                            if node.tag == qn("t"):
                                target.remove(node)
                        node = ET.SubElement(target, qn("t"))
                        node.text = values[norm(label)]
                    break

        ET.ElementTree(root).write(document_path, encoding="UTF-8", xml_declaration=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output:
            for path in unpacked.rglob("*"):
                if path.is_file():
                    output.write(path, path.relative_to(unpacked))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assessment_from_attachment(attachment: dict[str, object], fields: dict[str, object], stem: str) -> dict[str, object]:
    """Calculate from Attachment 1 and separately parsed A.4 review data."""
    review = attachment.get(A4_JSON_KEY, {})
    review = review if isinstance(review, dict) else {}
    return calculate_assessment(fields, stem, a4_review_overrides(stem, review))


def main() -> int:
    parser = argparse.ArgumentParser(description="从附件1 JSON生成assessment JSON和填好的台账DOCX")
    parser.add_argument("--input-dir", type=Path, default=Path("test/try"))
    parser.add_argument("--output-dir", type=Path, default=Path("test/try/results"))
    parser.add_argument("--template", type=Path, default=None)
    args = parser.parse_args()
    template = args.template or args.input_dir / "template.docx"
    if not template.is_file():
        raise SystemExit(f"模板不存在：{template}")
    inputs = sorted(args.input_dir.glob("*.attachment1.json"))
    if not inputs:
        raise SystemExit(f"未找到附件 JSON：{args.input_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in inputs:
        attachment = json.loads(input_path.read_text(encoding="utf-8"))
        fields = attachment.get("附件1：企业基础信息收集表")
        if not isinstance(fields, dict):
            raise SystemExit(f"附件字段缺失：{input_path}")
        stem = input_path.name.removesuffix(".attachment1.json")
        assessment = assessment_from_attachment(attachment, fields, stem)
        write_json(args.output_dir / f"{stem}.assessment.json", assessment)
        populate_docx(template, args.output_dir / f"{stem}.docx", build_values(fields, assessment, stem), fields, assessment)
        print(f"已生成：{stem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
