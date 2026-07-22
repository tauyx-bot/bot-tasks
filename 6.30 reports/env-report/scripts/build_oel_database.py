#!/usr/bin/env python3
"""Build the structured GBZ 2.1 occupational exposure limit database."""

from __future__ import annotations

import argparse
import html
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List

from render_python_data import render_record_mapping


MISSING_VALUES = {"", "-", "—", "——", "/"}

# Survey/detection-method names that are unambiguous synonyms of GBZ 2.1 names.
# Ambiguous groups (for example, generic "镍" versus soluble/insoluble nickel)
# are deliberately omitted so the report can request confirmation.
PROJECT_ALIASES = {
    "N,N-二甲基乙酰胺": "二甲基乙酰胺",
    "N,N-二甲基甲酰胺": "二甲基甲酰胺",
    "丁酮": "甲乙酮(2-丁酮)",
    "2-丁酮": "甲乙酮(2-丁酮)",
    "苯酚": "酚",
    "乙酸酐": "乙酐",
    "丙烯酸丁酯": "丙烯酸正丁酯",
    "氢氰酸": "氰化氢",
    "氯仿": "三氯甲烷",
    "光气": "碳酰氯",
    "盐酸": "氯化氢及盐酸",
    "氯化氢": "氯化氢及盐酸",
    "硫酸": "硫酸及三氧化硫",
    "三氧化硫": "硫酸及三氧化硫",
    "其他粉尘": "其他粉尘a",
    "其他粉尘（金属粉尘）": "其他粉尘a",
    "金属粉尘": "其他粉尘a",
    "矽尘": "矽尘10%≤游离 SiO2含量≤50%50%<游离 SiO2含量≤80%游离 SiO2含量>80%",
    "3-丁二烯": "1,3-丁二烯",
    "己烷": "正己烷",
    "庚烷": "正庚烷",
    "正戊烷": "戊烷(全部异构体)",
    "丁醇": "正丁醇",
    "丁醛": "正丁醛",
}

# Parentheses in GBZ names are semantic, not uniformly disposable. These
# entries contain aliases, abbreviations, enumerations, or structural names
# that must become independent lookup keys. Parentheses not listed here are
# accepted only when every group is a recognized applicability qualifier.
NAME_EXPANSIONS = {
    "巴豆醛(丁烯醛)": ["巴豆醛", "丁烯醛"],
    "苯基醚(二苯醚)": ["苯基醚", "二苯醚"],
    "o,o-二甲基-S-(甲基氨基甲酰甲基)二硫代磷酸酯(乐果)": [
        "o,o-二甲基-S-(甲基氨基甲酰甲基)二硫代磷酸酯",
        "乐果",
    ],
    "O,O-二甲基-(2,2,2-三氯-1-羟基乙基)磷酸酯(敌百虫)": [
        "O,O-二甲基-(2,2,2-三氯-1-羟基乙基)磷酸酯",
        "敌百虫",
    ],
    "N-3,4-二氯苯基-N',N'-二甲基脲(敌草隆)": [
        "N-3,4-二氯苯基-N',N'-二甲基脲",
        "敌草隆",
    ],
    "2,4-二氯苯氧基乙酸(2,4-滴)": ["2,4-二氯苯氧基乙酸", "2,4-滴"],
    "二氯二苯基三氯乙烷((滴滴涕,DDT)": [
        "二氯二苯基三氯乙烷",
        "滴滴涕",
        "DDT",
    ],
    "二丙二醇甲醚(2-甲氧基甲乙氧基丙醇)": [
        "二丙二醇甲醚",
        "2-甲氧基甲乙氧基丙醇",
    ],
    "1,3-二甲基丁基乙酸酯(仲-乙酸己酯)": [
        "1,3-二甲基丁基乙酸酯",
        "仲-乙酸己酯",
    ],
    "氮氧化物(一氧化氮和、二氧化氮)": ["氮氧化物", "一氧化氮", "二氧化氮"],
    "二异氰酸甲苯酯(TDI)": [
        "二异氰酸甲苯酯",
        "甲苯二异氰酸酯",
        "甲苯-2,4-二异氰酸酯",
        "TDI",
    ],
    "环三次甲基三硝铵(黑索今)": ["环三次甲基三硝铵", "黑索今"],
    "茴香胺(甲氧基苯胺)(包括邻-、对-)": [
        "茴香胺",
        "甲氧基苯胺",
        "邻-茴香胺",
        "对-茴香胺",
        "邻-甲氧基苯胺",
        "对-甲氧基苯胺",
    ],
    "2-己酮(甲基正丁基甲酮)": ["2-己酮", "甲基正丁基甲酮"],
    "18-甲基炔诺酮(炔诺孕酮)": ["18-甲基炔诺酮", "炔诺孕酮"],
    "甲乙酮(2-丁酮)": ["甲乙酮", "2-丁酮", "丁酮"],
    "苦味酸(2,4,6-三硝基苯酚)": ["苦味酸", "2,4,6-三硝基苯酚"],
    "六六六(六氯环己烷)": ["六六六", "六氯环己烷"],
    "γ-六六六(六六六氯环己烷)": ["γ-六六六", "六六六氯环己烷"],
    "氯化汞(升汞)": ["氯化汞", "升汞"],
    "三氯甲烷(氯仿)": ["三氯甲烷", "氯仿"],
    "三氧化铬、铬酸盐、重铬酸盐(按Cr计)": [
        "三氧化铬、铬酸盐、重铬酸盐",
        "三氧化铬",
        "铬酸盐",
        "重铬酸盐",
    ],
    "杀鼠灵(3-(1-丙酮基苄基)-4-羟基香豆素)": [
        "杀鼠灵",
        "3-(1-丙酮基苄基)-4-羟基香豆素",
    ],
    "砷化氢(肿)": ["砷化氢"],
    "双(巯基乙酸)二辛基锡": ["双(巯基乙酸)二辛基锡"],
    "碳酰氯(光气)": ["碳酰氯", "光气"],
    "硒及其化合物(按Se计)六氟化硒、硒化氢)": ["硒及其化合物"],
    "乙酰水杨酸(阿司匹林)": ["乙酰水杨酸", "阿司匹林"],
    "沉淀 SiO2(白炭黑)": ["沉淀SiO2", "白炭黑", "白炭黑粉尘"],
    "大理石粉尘(碳酸钙)": ["大理石粉尘", "碳酸钙", "碳酸钙粉尘"],
    "铝金属、铝合金粉尘": [
        "铝金属、铝合金粉尘",
        "铝金属粉尘",
        "铝合金粉尘",
    ],
    "人造矿物纤维绝热棉粉尘(玻璃棉、矿渣棉、岩棉)": [
        "人造矿物纤维绝热棉粉尘",
        "玻璃棉粉尘",
        "矿渣棉粉尘",
        "岩棉粉尘",
    ],
}


class TableParser(HTMLParser):
    """Collect the simple HTML tables embedded in the Markdown source."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[List[Dict[str, object]]]] = []
        self.table: List[List[Dict[str, object]]] | None = None
        self.row: List[Dict[str, object]] | None = None
        self.cell: Dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {
                "text": "",
                "rowspan": int(attributes.get("rowspan") or "1"),
                "colspan": int(attributes.get("colspan") or "1"),
            }

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["text"] = str(self.cell["text"]) + data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_name(value: str) -> str:
    """Ignore nested, mixed-width and unmatched parenthetical qualifiers."""
    outside: List[str] = []
    depth = 0
    for character in value:
        if character in "（(":
            depth += 1
        elif character in "）)":
            if depth:
                depth -= 1
        elif depth == 0:
            outside.append(character)
    return "".join("".join(outside).split())


def parenthetical_groups(value: str) -> List[str]:
    """Return top-level parenthetical text while accepting mixed-width pairs."""
    groups: List[str] = []
    current: List[str] = []
    depth = 0
    for character in value:
        if character in "（(":
            if depth:
                current.append(character)
            depth += 1
        elif character in "）)":
            if depth > 1:
                current.append(character)
            if depth:
                depth -= 1
                if depth == 0:
                    groups.append("".join(current))
                    current = []
        elif depth:
            current.append(character)
    if current:
        groups.append("".join(current))
    return groups


def is_applicability_qualifier(value: str) -> bool:
    compact = "".join(value.split())
    return (
        compact.startswith(("按", "不含", "游离SiO2含量", "石棉含量"))
        or compact == "全部异构体"
        or compact in {"蒸气", "硬"}
        or bool(re.fullmatch(r"\d+(?:\.\d+)?%[^、]*", compact))
        or "°C" in compact
    )


def project_names_for(source_name: str) -> List[str]:
    """Classify parentheses and return every meaningful lookup name."""
    if source_name in NAME_EXPANSIONS:
        return NAME_EXPANSIONS[source_name]
    groups = parenthetical_groups(source_name)
    unclassified = [group for group in groups if not is_applicability_qualifier(group)]
    if unclassified:
        raise RuntimeError(
            f"unclassified parenthetical content for {source_name}: {unclassified}"
        )
    return [normalize_name(source_name)]


def optional_text(value: str) -> str | None:
    value = clean_text(value)
    return None if value in MISSING_VALUES else value


def expand_rows(rows: List[List[Dict[str, object]]]) -> List[List[str]]:
    """Expand rowspans/colspans into a rectangular grid."""
    expanded: List[List[str]] = []
    active: Dict[int, tuple[str, int]] = {}
    for source_row in rows:
        values: Dict[int, str] = {column: value for column, (value, _) in active.items()}
        next_active = {
            column: (value, remaining - 1)
            for column, (value, remaining) in active.items()
            if remaining > 1
        }
        column = 0
        for cell in source_row:
            while column in values:
                column += 1
            value = clean_text(str(cell["text"]))
            colspan = int(cell["colspan"])
            rowspan = int(cell["rowspan"])
            for offset in range(colspan):
                values[column + offset] = value
                if rowspan > 1:
                    next_active[column + offset] = (value, rowspan - 1)
            column += colspan
        width = max(values, default=-1) + 1
        expanded.append([values.get(index, "") for index in range(width)])
        active = next_active
    return expanded


def limit(limit_type: str, value: str, unit: str, fraction: str = "") -> Dict[str, str] | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    result = {"type": limit_type, "value": cleaned, "unit": unit}
    if fraction:
        result["fraction"] = fraction
    return result


def base_entry(
    row: List[str],
    source_table: str,
    english_index: int,
    cas_index: int,
) -> Dict[str, object]:
    return {
        "source_table": source_table,
        "serial": clean_text(row[0]),
        "chinese_name": clean_text(row[1]),
        "english_name": clean_text(row[english_index]),
        "cas": optional_text(row[cas_index]),
    }


def build_database(source: Path) -> Dict[str, List[str]]:
    parser = TableParser()
    parser.feed(source.read_text(encoding="utf-8"))
    entries: List[Dict[str, object]] = []

    # Tables 1, 2 and 3 are the first 30 HTML tables in GBZ 2.1—2019.
    for table_number, raw_table in enumerate(parser.tables[:30]):
        rows = expand_rows(raw_table)
        if not rows:
            continue
        heading = " ".join(rows[0])
        if table_number <= 24 and "OEL" in heading:
            for row in rows[2:]:
                if len(row) < 9 or not row[0].rstrip(".").isdigit():
                    continue
                entry = base_entry(row, "表1", -7, -6)
                entry["category"] = "chemical"
                entry["limits"] = [
                    item
                    for item in (
                        limit("MAC", row[-5], "mg/m³"),
                        limit("PC-TWA", row[-4], "mg/m³"),
                        limit("PC-STEL", row[-3], "mg/m³"),
                    )
                    if item is not None
                ]
                entry["critical_health_effect"] = optional_text(row[-2])
                entry["remarks"] = optional_text(row[-1])
                entries.append(entry)
        elif 25 <= table_number <= 28 and "PC-TWA" in heading:
            for row in rows[2:]:
                if len(row) < 8 or not row[0].rstrip(".").isdigit():
                    continue
                entry = base_entry(row, "表2", -6, -5)
                entry["category"] = "dust"
                entry["limits"] = [
                    item
                    for item in (
                        limit("PC-TWA", row[-4], "mg/m³", "总尘"),
                        limit("PC-TWA", row[-3], "mg/m³", "呼尘"),
                    )
                    if item is not None
                ]
                entry["critical_health_effect"] = optional_text(row[-2])
                entry["remarks"] = optional_text(row[-1])
                entries.append(entry)
        elif table_number == 29 and "OEL" in heading:
            for row in rows[2:]:
                if len(row) < 9 or not row[0].rstrip(".").isdigit():
                    continue
                entry = base_entry(row, "表3", -7, -6)
                entry["category"] = "biological"
                entry["limits"] = [
                    item
                    for item in (
                        limit("MAC", row[-5], "按原表"),
                        limit("PC-TWA", row[-4], "按原表"),
                        limit("PC-STEL", row[-3], "按原表"),
                    )
                    if item is not None
                ]
                entry["critical_health_effect"] = optional_text(row[-2])
                entry["remarks"] = optional_text(row[-1])
                entries.append(entry)

    database: Dict[str, List[str]] = {}
    for entry in entries:
        limit_types = [
            limit_type
            for limit_type in ("MAC", "PC-TWA", "PC-STEL")
            if any(item["type"] == limit_type for item in entry["limits"])
        ]
        if limit_types:
            source_name = str(entry["chinese_name"])
            for project_name in project_names_for(source_name):
                existing = database.get(project_name)
                if existing is not None and existing != limit_types:
                    raise RuntimeError(
                        f"conflicting OEL types for expanded name {project_name}"
                    )
                database[project_name] = limit_types
    for alias, canonical_name in PROJECT_ALIASES.items():
        normalized_canonical = normalize_name(canonical_name)
        match = database.get(normalized_canonical)
        if match is None:
            raise RuntimeError(f"OEL alias target not found: {alias} -> {canonical_name}")
        database[normalize_name(alias)] = match
    return database


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=root / "knowledge" / "化学有害因素.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "scripts" / "data_store" / "oel_limits.py",
    )
    args = parser.parse_args()
    database = build_database(args.source)
    records = {
        project: {
            "project": project,
            "limit_types": tuple(limit_types),
        }
        for project, limit_types in database.items()
    }
    output = (
        '"""Direct project-to-GBZ 2.1 occupational exposure-limit types."""\n\n'
        "from typing import Final\n\n"
        "from .models import OELRule\n\n\n"
        + render_record_mapping(
            "OEL_INDEX",
            "dict[str, OELRule]",
            "OELRule",
            records,
            ("project", "limit_types"),
        )
    )
    args.output.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
