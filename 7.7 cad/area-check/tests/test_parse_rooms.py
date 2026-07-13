from __future__ import annotations

import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parse_rooms import _is_plausible_area_record, build_report  # noqa: E402


def _write_fixture(path: Path) -> Path:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (22, 0), (22, 10), (0, 10)], close=True)
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 8), (0, 8)], close=True)
    msp.add_lwpolyline([(12, 0), (20, 0), (20, 6), (12, 6)], close=True)
    doc.saveas(path)
    return path


def test_simple_fixture_counts_two_rooms(tmp_path: Path) -> None:
    fixture = _write_fixture(tmp_path / "simple_rooms.dxf")
    report = build_report(fixture, tmp_path)

    assert report["room_count_total"] == 2
    assert report["region_count_raw"] == 3
    assert report["regions_discarded"] == 1
    assert report["polygon_area_bucket_counts"] == {
        "lt_50": 2,
        "gte_50_lt_100": 0,
        "gte_100_lt_500": 0,
        "gte_500_lt_1000": 0,
    }
    assert report["area_text_count"] == 0
    assert report["closed_space_labeled_count"] == 0
    assert report["closed_space_unlabeled_count"] == 2


def test_numeric_area_record_requires_area_layer_and_safe_source() -> None:
    safe_record = {
        "value": 57.1,
        "layer": "05-辅助-面积文字",
        "source": "modelspace",
        "context": r" \W0.9;57.1 ",
        "parse_kind": "pure_numeric_text",
    }
    assert _is_plausible_area_record(safe_record) is True


def test_numeric_area_record_rejects_door_and_pressure_numbers() -> None:
    door_record = {
        "value": 800.0,
        "layer": "05-辅助-说明注释",
        "source": "block:door800",
        "context": "800",
        "parse_kind": "pure_numeric_text",
    }
    pressure_record = {
        "value": 700.0,
        "layer": "06-建-标注-文字",
        "source": "block:20F22F24F26F28F31F34F36F38F40F楼梯正压",
        "context": "700",
        "parse_kind": "pure_numeric_text",
    }
    assert _is_plausible_area_record(door_record) is False
    assert _is_plausible_area_record(pressure_record) is False
