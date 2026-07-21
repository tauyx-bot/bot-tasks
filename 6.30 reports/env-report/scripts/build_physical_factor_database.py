#!/usr/bin/env python3
"""Build direct physical-factor lookup names from GBZ 2.2."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


SECTION_SUFFIXES = (
    "职业接触限值",
    "的生理限值",
)

ALIASES: Dict[str, List[str]] = {
    "超高频辐射": [
        "超短波",
        "超高频电磁辐射",
        "连续波",
        "脉冲波",
        "超高频辐射功率密度",
        "超高频电场强度",
    ],
    "高频电磁场": ["高频电磁辐射", "高频电场强度", "高频磁场强度"],
    "工频电场": ["工频电磁场", "工频电场强度", "1Hz~100kHz电场"],
    "激光辐射": [
        "激光",
        "眼直视激光束",
        "激光照射皮肤",
        "可见光",
        "红外线",
        "远红外线",
        "照射量",
        "辐照度",
    ],
    "微波辐射": [
        "微波",
        "连续微波",
        "脉冲微波",
        "固定微波辐射",
        "非固定微波辐射",
        "肢体局部微波辐射",
        "全身微波辐射",
        "平均功率密度",
        "日剂量",
    ],
    "紫外辐射": ["紫外线", "中波紫外线", "短波紫外线", "电焊弧光"],
    "高温作业": ["高温", "WBGT", "WBGT指数", "湿球黑球温度"],
    "噪声": ["生产性噪声", "稳态噪声", "非稳态噪声", "脉冲噪声"],
    "手传振动": ["手臂振动"],
    "煤矿井下采掘工作场所气象条件": [
        "井下采掘工作场所气象条件",
        "干球温度",
        "相对湿度",
        "风速",
    ],
    "体力劳动强度分级": ["体力劳动强度", "能量代谢率", "劳动时间率"],
    "体力工作时心率和能量消耗": [
        "体力劳动时的心率",
        "体力劳动时心率",
        "体力工作时心率",
        "体力工作时能量消耗",
    ],
}


def section_names(source: Path) -> List[str]:
    names: List[str] = []
    pattern = re.compile(r"^(?:##\s*)?(?:[4-9]|1[0-5])\s+(.+)$")
    for line in source.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if not match:
            continue
        title = re.split(r"\s+[A-Za-z]", match.group(1), maxsplit=1)[0].strip()
        for suffix in SECTION_SUFFIXES:
            if title.endswith(suffix):
                title = title[: -len(suffix)].strip()
                break
        if title:
            names.append(title)
    return names


def build_database(source: Path) -> List[str]:
    names: List[str] = []
    for primary in section_names(source):
        names.append(primary)
        names.extend(ALIASES.get(primary, []))
    missing_alias_groups = sorted(set(ALIASES) - set(section_names(source)))
    if missing_alias_groups:
        raise RuntimeError(
            f"physical-factor alias groups absent from standard: {missing_alias_groups}"
        )
    return list(dict.fromkeys(names))


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=root / "knowledge" / "物理危害.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "knowledge" / "physical_factors.json",
    )
    args = parser.parse_args()
    database = build_database(args.source)
    args.output.write_text(
        json.dumps(database, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
