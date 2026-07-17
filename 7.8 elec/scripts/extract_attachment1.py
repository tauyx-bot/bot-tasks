#!/usr/bin/env python3
"""Extract attachment 1 and calculate attachment 2 assessment tables.

The program intentionally uses only the Python standard library so it can run
in the assessment delivery environment without a DOCX dependency.

Usage:
    python3 scripts/extract_attachment1.py
    python3 scripts/extract_attachment1.py --input-dir data --output-dir test/results
"""

from __future__ import annotations

import argparse
import json
import math
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
IDENTITY_FIELDS = ("单位名称（盖章）", "单位名称")
CHECKED_SYMBOL = "00FE"  # Wingdings checked box; 00A8 is an empty box.

FIELD_ALIASES = {
    "单位名称": "单位名称（盖章）",
    "危险性类别": "火灾危险性类别",
    "毒性危害类别": "毒性危害性类别",
    "风险单元现场最大人": "风险单元现场最大人数",
}
DEFAULTS = {"P1": 5, "P6": 3, "L2": 1, "L3": 1}


@dataclass
class Cell:
    text: str
    selected_options: list[str] | None = None


def cell_text(cell: ET.Element) -> str:
    return "".join(cell.itertext()).replace("\u00a0", " ").strip()


def cell_info(cell: ET.Element) -> Cell:
    """Read displayed text and selected Wingdings checkbox labels."""
    selected: list[str] = []
    contains_checkbox = False
    selected_marker_seen = False
    for run in cell.findall(".//w:r", NS):
        symbol = run.find("w:sym", NS)
        if symbol is not None:
            contains_checkbox = True
            selected_marker_seen = symbol.get(f"{{{W_NS}}}char", "").upper() == CHECKED_SYMBOL
            continue
        run_text = "".join(run.itertext()).strip()
        if selected_marker_seen and run_text:
            option = run_text.strip(" ；;")
            if option:
                selected.append(option)
            selected_marker_seen = False
    return Cell(cell_text(cell), selected if contains_checkbox else None)


def top_level_tables(docx_path: Path) -> Iterable[list[list[Cell]]]:
    with zipfile.ZipFile(docx_path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    body = document.find("w:body", NS)
    if body is None:
        return
    for table in body.findall("w:tbl", NS):
        yield [[cell_info(cell) for cell in row.findall("w:tc", NS)] for row in table.findall("w:tr", NS)]


def put_value(fields: dict[str, Any], label: str, value: Any) -> None:
    label = FIELD_ALIASES.get("".join(label.split()), "".join(label.split()))
    if label == "区域建筑物" and isinstance(value, str):
        value = parse_building_info(value)
    if not label:
        return
    if label not in fields:
        fields[label] = value
        return
    if fields[label] != value:
        suffix = 2
        while f"{label}_{suffix}" in fields:
            suffix += 1
        fields[f"{label}_{suffix}"] = value


def parse_building_info(text: str) -> dict[str, str]:
    patterns = {
        "面积": r"(?:区域建筑物)?面积\s*[：:]\s*([^；;。]+)",
        "建筑高度": r"建筑高度\s*[：:]\s*([^；;。]+)",
        "等效高度": r"等效高度\s*[：:]\s*([^；;。]+)",
        "相对高度": r"相对高度\s*[：:]\s*([^；;。]+)",
    }
    result = {name: match.group(1).strip() for name, pattern in patterns.items() if (match := re.search(pattern, text))}
    return result or {"原始值": text}


def rows_to_fields(rows: list[list[Cell]]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for row in rows:
        cells = row[:]
        if cells and cells[0].text == "基本情况":
            cells = cells[1:]
        cells = [cell for cell in cells if cell.text.strip()]
        if not cells:
            continue
        pair_count = len(cells) - (len(cells) % 2)
        for index in range(0, pair_count, 2):
            value_cell = cells[index + 1]
            put_value(fields, cells[index].text, value_cell.selected_options if value_cell.selected_options is not None else value_cell.text)
        if len(cells) % 2:
            if pair_count:
                label = FIELD_ALIASES.get("".join(cells[pair_count - 2].text.split()), "".join(cells[pair_count - 2].text.split()))
                fields[label] = f"{fields[label]}；{cells[-1].text}"
            else:
                put_value(fields, cells[0].text, "")
    return fields


def extract_attachment(docx_path: Path) -> dict[str, Any]:
    for rows in top_level_tables(docx_path):
        text = " ".join(cell.text for row in rows for cell in row)
        if "经纬度" in text and any(field in text for field in IDENTITY_FIELDS):
            return rows_to_fields(rows)
    raise ValueError("未找到附件1表格（缺少单位名称或经纬度字段）")


def number(value: Any) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    result = float(match.group())
    # Forms may use Chinese large-number units, for example "227万㎡".
    return result * 10000 if "万" in str(value) else result


def options(fields: dict[str, Any], field: str) -> list[str]:
    value = fields.get(field, [])
    return value if isinstance(value, list) else [str(value)] if value else []


def factor(name: str, score: int | None, source: str, input_value: Any, selected: str | None = None, error: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"因子": name, "输入": input_value, "命中选项": selected, "分值": score, "来源": source}
    if error:
        item["校验错误"] = error
    return item


def single_score(values: list[str], mapping: dict[str, int], name: str) -> tuple[int | None, str | None, str | None]:
    matches = [(value, mapping[value]) for value in values if value in mapping]
    if not matches:
        return None, None, f"{name}缺少可识别的选择"
    scores = {score for _, score in matches}
    if len(scores) != 1:
        return None, None, f"{name}存在冲突选择：{', '.join(values)}"
    return matches[0][1], matches[0][0], None


def max_score(values: list[str], mapping: dict[str, int], name: str, default: int | None = None) -> tuple[int | None, str | None, str | None]:
    matches = [(value, mapping[value]) for value in values if value in mapping]
    if not matches and default is not None:
        return default, None, f"{name}未选择，使用默认值{default}"
    if not matches:
        return None, None, f"{name}缺少可识别的选择"
    value, score = max(matches, key=lambda item: item[1])
    return score, value, None


def area_score(area: float | None) -> int | None:
    if area is None:
        return None
    return 1 if area <= 2500 else 2 if area <= 5000 else 3 if area <= 7500 else 4 if area <= 10000 else 5


def height_score(height: float | None) -> int | None:
    if height is None:
        return None
    return 1 if height < 30 else 2 if height < 45 else 3 if height < 60 else 4 if height < 100 else 5


def p2_score(values: list[str]) -> tuple[int | None, str | None, str | None]:
    mapping = {"周边高层建筑物": 1, "山坡": 3, "临海": 4, "孤立空旷": 5}
    return max_score(values, mapping, "周边地理情况")


def risk_level(value: int | None) -> str | None:
    if value is None:
        return None
    if value < 2:
        return "低风险"
    if value < 4:
        return "较低风险"
    if value < 6:
        return "中等风险"
    if value < 8:
        return "较高风险"
    return "高风险"


def calculate_assessment(fields: dict[str, Any], stem: str, overrides: dict[str, Any]) -> dict[str, Any]:
    defaults = {**DEFAULTS, **overrides.get("defaults", {})}
    unit = overrides.get("units", {}).get(stem, {})
    errors: list[str] = []

    building = fields.get("区域建筑物", {})
    building = building if isinstance(building, dict) else {}
    geography = options(fields, "周边地理情况")

    p1 = int(unit.get("P1", defaults["P1"]))
    p2, p2_selected, p2_error = p2_score(geography)
    p3 = unit.get("P3")
    p4 = area_score(number(building.get("面积")))
    p5 = height_score(number(building.get("等效高度")))
    p6 = int(unit.get("P6", defaults["P6"]))
    if p2_error:
        errors.append(p2_error)
    if p3 is None:
        errors.append("P3无法由附件1唯一推导；请在覆盖配置中提供")
    p_values = [p1, p2, p3, p4, p5, p6]
    if any(value is None for value in p_values):
        p_total = None
        l1 = None
        l1_grade = None
    else:
        p_total = sum(int(value) for value in p_values)
        l1_grade = "Ⅲ" if p_total <= 18 else "Ⅱ" if p_total <= 29 else "I" if p_total <= 40 else None
        l1 = {"Ⅲ": 1, "Ⅱ": 2, "I": 3}.get(l1_grade)

    a4_conditions = unit.get("A4_conditions", [])
    l2 = int(unit.get("L2", defaults["L2"]))
    l3 = int(unit.get("L3", defaults["L3"]))
    l_raw = None if l1 is None else 0.2 * l1 + 0.4 * l2 + 0.4 * l3
    l = 3 if a4_conditions else math.ceil(l_raw) if l_raw is not None else None

    s1, s1_selected, s1_error = single_score(options(fields, "风险单元现场最大人数"), {"（0-10）人": 1, "（10-30）人": 2, "30人及以上": 3}, "风险单元现场最大人数")
    s2_default, s2_selected, _ = max_score(geography, {"学校": 2, "机场": 2, "小区": 2, "加（充）油（气）站": 2}, "周边防护目标")
    s2 = int(unit.get("S2", s2_default if s2_default is not None else 1))

    m1, m1_selected, m1_error = max_score(options(fields, "火灾危险性类别"), {"甲类": 3, "乙、丙类": 2, "丁、戊类及其他": 1}, "火灾危险性类别")
    m2, m2_selected, m2_error = max_score(options(fields, "毒性危害性类别"), {"类别1": 3, "类别 2": 2, "类别3": 2, "类别 4": 1, "类别5 及其他": 1}, "毒性危害性类别")
    m3, m3_selected, m3_error = max_score(options(fields, "危险工艺"), {"不涉及": 1, "连续操作": 2, "间歇操作": 3}, "危险工艺", default=1)
    m4, m4_selected, m4_error = max_score(options(fields, "重大危险源"), {"不涉及": 1, "三级": 2, "四级": 2, "二级": 3, "一级": 3}, "重大危险源")
    for error in (s1_error, m1_error, m2_error, m3_error, m4_error):
        if error:
            errors.append(error)
    m_values = [m1, m2, m3, m4]
    m = max(m_values) if all(value is not None for value in m_values) else None
    chemical_grade = {1: "Ⅲ", 2: "Ⅱ", 3: "I"}.get(m)
    s3 = m
    s_values = [s1, s2, s3]
    # Formula (A.3) is S = MAX(S1, S2, S3).  A missing factor normally keeps
    # S indeterminate, except when a known factor has already reached the
    # table's maximum score (3); then no unresolved 1–3 score can change S.
    known_s_values = [int(value) for value in s_values if value is not None]
    s = max(known_s_values) if len(known_s_values) == len(s_values) or max(known_s_values, default=0) == 3 else None
    r = l * s if l is not None and s is not None else None

    return {
        "source_unit": fields.get("单位名称（盖章）", stem),
        "A.1": {
            "雷击发生可能性": [
                factor("L1 雷击发生可能性等级", l1, "A.2/A.3计算", {"P": p_total, "等级": l1_grade}, l1_grade),
                factor("L2 雷电防护装置现状", l2, "覆盖配置" if "L2" in unit else "默认配置", None, "正常运行"),
                factor("L3 防雷安全管理制度", l3, "覆盖配置" if "L3" in unit else "默认配置", None, "完善且执行到位"),
            ],
            "公式": "L = ceil(0.2*L1 + 0.4*L2 + 0.4*L3)，A.4命中时L=3",
            "加权原值": l_raw,
            "结果": l,
        },
        "A.2": {
            "雷击发生可能性因子": [
                factor("P1 雷击密度", p1, "覆盖配置" if "P1" in unit else "默认配置", None),
                factor("P2 地形地貌", p2, "附件1：周边地理情况", geography, p2_selected, p2_error),
                factor("P3 相对高度", int(p3) if p3 is not None else None, "覆盖配置" if p3 is not None else "待人工提供", building.get("相对高度"), error=None if p3 is not None else "无法唯一推导"),
                factor("P4 占地面积", p4, "附件1：区域建筑物面积", building.get("面积")),
                factor("P5 等效高度", p5, "附件1：区域建筑物等效高度", building.get("等效高度")),
                factor("P6 防雷分类", p6, "覆盖配置" if "P6" in unit else "默认配置", None),
            ],
            "公式": "P = P1 + P2 + P3 + P4 + P5 + P6",
            "结果": p_total,
        },
        "A.3": {"雷击发生可能性分级": l1_grade, "L1分值": l1},
        "A.4": {"直接赋值条件": a4_conditions, "命中": bool(a4_conditions), "结果": 3 if a4_conditions else None},
        "A.5": {
            "后果严重性因子": [
                factor("S1 风险单元现场人数最大值", s1, "附件1：风险单元现场最大人数", options(fields, "风险单元现场最大人数"), s1_selected, s1_error),
                factor("S2 500m范围内防护目标", s2, "覆盖配置" if "S2" in unit else "附件1推断/默认值", geography, s2_selected),
                factor("S3 化学品固有危险性等级", s3, "A.6/A.7计算", {"M": m, "等级": chemical_grade}, chemical_grade),
            ],
            "公式": "S = max(S1, S2, S3)",
            "结果": s,
        },
        "A.6": {
            "化学品固有危险性因子": [
                factor("M1 火灾危险性类别", m1, "附件1：火灾危险性类别", options(fields, "火灾危险性类别"), m1_selected, m1_error),
                factor("M2 急性毒性危害类别", m2, "附件1：毒性危害性类别", options(fields, "毒性危害性类别"), m2_selected, m2_error),
                factor("M3 危险工艺和操作", m3, "附件1" if m3_selected else "默认值", options(fields, "危险工艺"), m3_selected, m3_error),
                factor("M4 重大危险源等级", m4, "附件1：重大危险源", options(fields, "重大危险源"), m4_selected, m4_error),
            ],
            "公式": "M = max(M1, M2, M3, M4)",
            "结果": m,
        },
        "A.7": {"化学品固有危险性分值": m, "化学品固有危险性等级": chemical_grade},
        "A.8": {"公式": "R = L * S", "R": r, "风险等级": risk_level(r)},
        "validation_errors": errors,
    }


def load_overrides(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("覆盖配置必须为 JSON 对象")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="提取附件1并生成附件2表A.1-A.8评估JSON")
    parser.add_argument("--input-dir", type=Path, default=Path("data"), help="DOCX所在目录")
    parser.add_argument("--output-dir", type=Path, default=Path("test/results"), help="JSON输出目录")
    parser.add_argument("--overrides", type=Path, default=Path("test/assessment_overrides.json"), help="不可从附件1推导的因子覆盖配置")
    args = parser.parse_args()
    input_dir, output_dir = args.input_dir.resolve(), args.output_dir.resolve()
    docx_files = sorted(path for path in input_dir.rglob("*.docx") if output_dir not in path.parents)
    if not docx_files:
        print(f"未在 {input_dir} 找到 DOCX 文件")
        return 1
    try:
        overrides = load_overrides(args.overrides.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"读取覆盖配置失败: {error}")
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for docx_path in docx_files:
        try:
            fields = extract_attachment(docx_path)
            attachment = {"source_file": str(docx_path.relative_to(input_dir)), "附件1：企业基础信息收集表": fields}
            assessment = calculate_assessment(fields, docx_path.stem, overrides)
            write_json(output_dir / f"{docx_path.stem}.attachment1.json", attachment)
            write_json(output_dir / f"{docx_path.stem}.assessment.json", assessment)
            print(f"已写入: {docx_path.stem}")
        except (OSError, ET.ParseError, ValueError, zipfile.BadZipFile) as error:
            failed += 1
            print(f"处理失败: {docx_path} ({error})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
