from __future__ import annotations

import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parse_rooms import _extract_area_values, build_report  # noqa: E402


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
    assert report["area_bucket_counts"] == {
        "lt_50": 0,
        "gte_50_lt_100": 0,
        "gte_100_lt_500": 0,
        "gte_500_lt_1000": 0,
    }
    assert report["area_bucket_calibration_applied"] is False
    assert report["named_room_counts"] == {}
    assert report["unnamed_room_count"] == 0


def test_extract_area_values_supports_bare_numeric_and_parenthetical_text() -> None:
    kwargs = {"layer": "05-辅助-面积文字", "allow_numeric_only": True}
    assert _extract_area_values(r" \W0.9;57.1 ", **kwargs) == [57.1]
    assert _extract_area_values(r" \W0.9;317.7（251） ", **kwargs) == [317.7, 251.0]
    assert _extract_area_values(r" \W0.9;327.1㎡(257.4) ", **kwargs) == [327.1, 257.4]


def test_extract_area_values_ignores_bare_numeric_text_on_non_area_layers() -> None:
    assert _extract_area_values(r" \W0.9;57.1 ", layer="A-ANNO-TEXT") == []
