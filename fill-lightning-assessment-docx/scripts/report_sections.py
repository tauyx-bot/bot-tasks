#!/usr/bin/env python3
"""Extract and fill narrative report fields embedded in assessment JSON.

The manual values in Chapter 5 (assessment unit, L, S and R) are treated as
immutable source facts.  These fields are nested under ``报告章节`` in the
ordinary assessment JSON; no separate sections JSON is created.
"""

from __future__ import annotations

import copy
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from generate_from_json import NS, qn, set_cell, set_paragraph, text


DOCUMENT_XML = "word/document.xml"
CHAPTER4 = "第四章：企业概况与现场勘查情况"
CHAPTER5 = "第五章：雷电灾害风险识别与评估"
ATTACHMENT6 = "附件6：防雷安全重点单位“重点部位”风险分类分级管控清单"
CHAPTER5_HEADERS = ("评估单元", "雷击可能性（L）", "后果严重性（S）", "风险等级（R）", "主要风险分析")
ATTACHMENT6_HEADERS = ("序号", "场所", "风险描述", "可能导致的事故类型", "风险等级", "标示颜色", "管控措施")


def compact(value: str) -> str:
    return re.sub(r"[\s\u200b\ufeff]", "", value or "")


def body_of(root: ET.Element) -> ET.Element:
    body = root.find("w:body", NS)
    if body is None:
        raise ValueError("DOCX 缺少正文 body")
    return body


def table_headers(table: ET.Element) -> tuple[str, ...]:
    first_row = table.find("w:tr", NS)
    if first_row is None:
        return ()
    return tuple(text(cell).strip() for cell in first_row.findall("w:tc", NS))


def report_table_kind(table: ET.Element) -> str | None:
    headers = table_headers(table)
    if headers[: len(CHAPTER5_HEADERS)] == CHAPTER5_HEADERS:
        return "第五章"
    if headers[: len(ATTACHMENT6_HEADERS)] == ATTACHMENT6_HEADERS:
        return "附件6"
    return None


def find_top_level_heading(body: ET.Element, marker: str) -> ET.Element:
    wanted = compact(marker)
    for node in list(body):
        if node.tag == qn("p") and wanted in compact(text(node)):
            return node
    raise ValueError(f"未找到章节标题：{marker}")


def elements_between(body: ET.Element, start_marker: str, end_marker: str) -> list[ET.Element]:
    children = list(body)
    start = children.index(find_top_level_heading(body, start_marker))
    end = children.index(find_top_level_heading(body, end_marker))
    if end <= start:
        raise ValueError(f"章节顺序异常：{start_marker} / {end_marker}")
    return children[start + 1 : end]


def split_chapter4(body: ET.Element) -> tuple[list[str], list[str]]:
    nodes = elements_between(body, CHAPTER4, CHAPTER5)
    overview_index = next((i for i, node in enumerate(nodes) if compact(text(node)).startswith("1、企业概况")), None)
    inspection_index = next((i for i, node in enumerate(nodes) if compact(text(node)).startswith("2、现场检查情况")), None)
    if overview_index is None or inspection_index is None or inspection_index <= overview_index:
        raise ValueError("第四章缺少“企业概况”或“现场检查情况”小节")

    def visible_paragraphs(items: list[ET.Element]) -> list[str]:
        return [text(node).strip() for node in items if node.tag == qn("p") and text(node).strip()]

    return (
        visible_paragraphs(nodes[overview_index + 1 : inspection_index]),
        visible_paragraphs(nodes[inspection_index + 1 :]),
    )


def find_report_table(root: ET.Element, kind: str) -> ET.Element:
    matches = [table for table in root.findall(".//w:tbl", NS) if report_table_kind(table) == kind]
    if len(matches) != 1:
        raise ValueError(f"{kind}目标表数量应为1，实际为{len(matches)}")
    return matches[0]


def row_values(row: ET.Element) -> list[str]:
    return [text(cell).strip() for cell in row.findall("w:tc", NS)]


def manual_rows(root: ET.Element) -> tuple[list[dict[str, str]], list[str]]:
    table = find_report_table(root, "第五章")
    result: list[dict[str, str]] = []
    errors: list[str] = []
    for index, row in enumerate(table.findall("w:tr", NS)[1:], 1):
        values = row_values(row)
        if not any(values):
            continue
        if len(values) < 5:
            errors.append(f"第五章第{index}行不足5列")
            continue
        item = dict(zip(CHAPTER5_HEADERS[:4], values[:4]))
        missing = [name for name, value in item.items() if not value]
        if missing:
            errors.append(f"第五章第{index}行人工字段缺失：{'、'.join(missing)}")
        result.append(item)
    if not result:
        errors.append("第五章没有可识别的人工评估行")
    units = [item["评估单元"] for item in result]
    if len(units) != len(set(units)):
        errors.append("第五章评估单元存在重复值")
    return result, errors


def existing_chapter5_analysis(root: ET.Element) -> list[dict[str, str]]:
    rows = find_report_table(root, "第五章").findall("w:tr", NS)[1:]
    return [
        {"评估单元": values[0], "主要风险分析": values[4]}
        for row in rows
        if len(values := row_values(row)) >= 5 and any(values)
    ]


def existing_attachment6(root: ET.Element) -> list[dict[str, str]]:
    rows = find_report_table(root, "附件6").findall("w:tr", NS)[1:]
    return [dict(zip(ATTACHMENT6_HEADERS, values[:7])) for row in rows if len(values := row_values(row)) >= 7 and any(values)]


def conclusion_text(body: ET.Element) -> str:
    for node in elements_between(body, CHAPTER5, "第六章"):
        value = text(node).strip()
        if value.startswith("综合评估结论"):
            return re.sub(r"^综合评估结论\s*[：:]\s*", "", value)
    return ""


def risk_display(value: str) -> tuple[str, str] | None:
    normalized = compact(value)
    mappings = (
        (("重大风险", "高风险"), ("重大", "红色")),
        (("较大风险", "较高风险"), ("较大", "橙色")),
        (("一般风险", "中等风险"), ("一般", "黄色")),
        (("低风险", "较低风险"), ("低", "蓝色")),
    )
    for names, display in mappings:
        if normalized in names:
            return display
    return None


def extract_sections(docx_path: Path, attachment_fields: dict[str, Any]) -> dict[str, Any]:
    with zipfile.ZipFile(docx_path) as package:
        root = ET.fromstring(package.read(DOCUMENT_XML))
    body = body_of(root)
    manual, errors = manual_rows(root)
    overview, inspections = split_chapter4(body)
    units = [item["评估单元"] for item in manual]
    attachment_rows: list[dict[str, Any]] = []
    for index, item in enumerate(manual, 1):
        display = risk_display(item["风险等级（R）"])
        if display is None:
            errors.append(f"评估单元“{item['评估单元']}”的风险等级无法映射颜色：{item['风险等级（R）']}")
            level, color = "", ""
        else:
            level, color = display
        attachment_rows.append({
            "序号": index,
            "场所": item["评估单元"],
            "风险描述": "",
            "可能导致的事故类型": "",
            "风险等级": level,
            "标示颜色": color,
            "管控措施": [],
        })
    return {
        "schema_version": 1,
        "source_document": docx_path.name,
        "人工填写": {CHAPTER5: manual},
        "资料上下文": {
            "附件1：企业基础信息收集表": attachment_fields,
            "原第四章企业概况": overview,
            "原第四章现场检查情况": inspections,
            "原第五章主要风险分析": existing_chapter5_analysis(root),
            "原第五章综合评估结论": conclusion_text(body),
            "原附件6": existing_attachment6(root),
        },
        "AI生成": {
            CHAPTER4: {
                "企业概况": [],
                "现场检查情况": [{"评估单元": unit, "分析": ""} for unit in units],
            },
            CHAPTER5: {
                "主要风险分析": [{"评估单元": unit, "分析": ""} for unit in units],
                "综合评估结论": "",
            },
            ATTACHMENT6: attachment_rows,
        },
        "validation_errors": errors,
    }


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label}必须是JSON对象")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label}必须是JSON数组")
    return value


def validate_sections(root: ET.Element, data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != 1:
        raise ValueError("章节JSON的schema_version必须为1")
    recorded_errors = data.get("validation_errors", [])
    if not isinstance(recorded_errors, list):
        raise ValueError("章节JSON的validation_errors必须是数组")
    if recorded_errors:
        raise ValueError(f"章节JSON仍有未解决的提取错误：{'；'.join(map(str, recorded_errors))}")
    actual_manual, actual_errors = manual_rows(root)
    if actual_errors:
        raise ValueError("；".join(actual_errors))
    manual_root = _require_dict(data.get("人工填写"), "人工填写")
    supplied_manual = _require_list(manual_root.get(CHAPTER5), f"人工填写/{CHAPTER5}")
    if supplied_manual != actual_manual:
        raise ValueError("章节JSON中的第五章人工字段与DOCX不一致，拒绝改写人工值")

    units = [item["评估单元"] for item in actual_manual]
    generated = _require_dict(data.get("AI生成"), "AI生成")
    chapter4 = _require_dict(generated.get(CHAPTER4), f"AI生成/{CHAPTER4}")
    overview = _require_list(chapter4.get("企业概况"), "第四章/企业概况")
    if not overview or any(not isinstance(value, str) or not value.strip() for value in overview):
        raise ValueError("第四章/企业概况必须包含非空段落")

    def indexed(items: Any, label: str, value_key: str) -> dict[str, dict[str, Any]]:
        rows = _require_list(items, label)
        result: dict[str, dict[str, Any]] = {}
        for item in rows:
            row = _require_dict(item, f"{label}行")
            unit = row.get("评估单元")
            value = row.get(value_key)
            if not isinstance(unit, str) or not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}中的评估单元和{value_key}必须非空")
            if unit in result:
                raise ValueError(f"{label}存在重复评估单元：{unit}")
            result[unit] = row
        if list(result) != units:
            raise ValueError(f"{label}的评估单元及顺序必须与第五章人工字段一致")
        return result

    inspections = indexed(chapter4.get("现场检查情况"), "第四章/现场检查情况", "分析")
    chapter5 = _require_dict(generated.get(CHAPTER5), f"AI生成/{CHAPTER5}")
    risk_analysis = indexed(chapter5.get("主要风险分析"), "第五章/主要风险分析", "分析")
    conclusion = chapter5.get("综合评估结论")
    if not isinstance(conclusion, str) or not conclusion.strip():
        raise ValueError("第五章/综合评估结论不能为空")

    attachment = _require_list(generated.get(ATTACHMENT6), f"AI生成/{ATTACHMENT6}")
    if len(attachment) != len(units):
        raise ValueError("附件6行数必须与第五章评估单元数一致")
    for index, (row_value, manual) in enumerate(zip(attachment, actual_manual), 1):
        row = _require_dict(row_value, f"附件6第{index}行")
        expected = risk_display(manual["风险等级（R）"])
        if expected is None:
            raise ValueError(f"无法映射风险等级：{manual['风险等级（R）']}")
        immutable = (row.get("序号"), row.get("场所"), row.get("风险等级"), row.get("标示颜色"))
        wanted = (index, manual["评估单元"], expected[0], expected[1])
        if immutable != wanted:
            raise ValueError(f"附件6第{index}行的序号、场所、风险等级或颜色与人工R值不一致")
        for key in ("风险描述", "可能导致的事故类型"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"附件6第{index}行/{key}不能为空")
        measures = row.get("管控措施")
        if isinstance(measures, list):
            if not measures or any(not isinstance(value, str) or not value.strip() for value in measures):
                raise ValueError(f"附件6第{index}行/管控措施必须包含非空条目")
        elif not isinstance(measures, str) or not measures.strip():
            raise ValueError(f"附件6第{index}行/管控措施不能为空")
    return {
        "manual": actual_manual,
        "units": units,
        "overview": [value.strip() for value in overview],
        "inspections": inspections,
        "risk_analysis": risk_analysis,
        "conclusion": conclusion.strip(),
        "attachment": attachment,
    }


def replace_paragraph_block(body: ET.Element, start_marker: str, end_marker: str, values: list[str]) -> int:
    children = list(body)
    start = children.index(find_top_level_heading(body, start_marker))
    end = children.index(find_top_level_heading(body, end_marker))
    candidates = [node for node in children[start + 1 : end] if node.tag == qn("p") and text(node).strip()]
    template = candidates[0] if candidates else find_top_level_heading(body, start_marker)
    edits = 0
    for index, value in enumerate(values):
        if index < len(candidates):
            paragraph = candidates[index]
        else:
            paragraph = copy.deepcopy(template)
            set_paragraph(paragraph, "")
            body.insert(list(body).index(find_top_level_heading(body, end_marker)), paragraph)
        if text(paragraph).strip() != value:
            set_paragraph(paragraph, value)
            edits += 1
    for paragraph in candidates[len(values) :]:
        body.remove(paragraph)
        edits += 1
    return edits


def set_conclusion(body: ET.Element, value: str) -> int:
    desired = f"综合评估结论：{value}"
    for node in elements_between(body, CHAPTER5, "第六章"):
        if node.tag == qn("p") and text(node).strip().startswith("综合评估结论"):
            if text(node).strip() == desired:
                return 0
            set_paragraph(node, desired)
            return 1
    chapter6 = find_top_level_heading(body, "第六章")
    paragraph = copy.deepcopy(chapter6)
    set_paragraph(paragraph, desired)
    body.insert(list(body).index(chapter6), paragraph)
    return 1


def measures_text(value: Any) -> str:
    if isinstance(value, list):
        return "".join(f"{index}.{item.strip()}" for index, item in enumerate(value, 1))
    return str(value).strip()


def fill_sections(root: ET.Element, data: dict[str, Any]) -> tuple[int, set[str]]:
    values = validate_sections(root, data)
    body = body_of(root)
    edits = 0
    edits += replace_paragraph_block(body, "1、企业概况", "2、现场检查情况", values["overview"])
    inspection_lines = [f"{unit}：{values['inspections'][unit]['分析'].strip()}" for unit in values["units"]]
    edits += replace_paragraph_block(body, "2、现场检查情况", CHAPTER5, inspection_lines)

    chapter5_table = find_report_table(root, "第五章")
    for row in chapter5_table.findall("w:tr", NS)[1:]:
        cells = row.findall("w:tc", NS)
        if len(cells) < 5 or not text(cells[0]).strip():
            continue
        unit = text(cells[0]).strip()
        desired = values["risk_analysis"][unit]["分析"].strip()
        if text(cells[4]).strip() != desired:
            set_cell(cells[4], desired)
            edits += 1
    edits += set_conclusion(body, values["conclusion"])

    attachment_table = find_report_table(root, "附件6")
    rows = attachment_table.findall("w:tr", NS)
    if len(rows) < 2:
        raise ValueError("附件6缺少可复制的数据行样式")
    template = rows[1]
    wanted_count = len(values["attachment"])
    while len(rows) - 1 < wanted_count:
        attachment_table.append(copy.deepcopy(template))
        rows = attachment_table.findall("w:tr", NS)
    while len(rows) - 1 > wanted_count:
        attachment_table.remove(rows[-1])
        rows = attachment_table.findall("w:tr", NS)
        edits += 1
    for row, item in zip(rows[1:], values["attachment"]):
        cells = row.findall("w:tc", NS)
        if len(cells) < 7:
            raise ValueError("附件6数据行不足7列")
        cell_values = [
            str(item["序号"]), item["场所"], item["风险描述"], item["可能导致的事故类型"],
            item["风险等级"], item["标示颜色"], measures_text(item["管控措施"]),
        ]
        for cell, desired in zip(cells[:7], cell_values):
            if text(cell).strip() != desired:
                set_cell(cell, desired)
                edits += 1
    return edits, {CHAPTER4, CHAPTER5, ATTACHMENT6}
