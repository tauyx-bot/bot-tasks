#!/usr/bin/env python3
"""Regression tests for volatile-organic-component report parsing."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import parse_component_report  # noqa: E402


class ComponentReportTest(unittest.TestCase):
    def test_zhuoyi_component_report(self) -> None:
        expected = json.loads(
            (ROOT / "test" / "expected" / "焯奕组分报告.expected.json").read_text(
                encoding="utf-8"
            )
        )
        result = parse_component_report.build_payload(ROOT / "examples" / "焯奕组分报告.pdf")
        self.assertEqual(expected, result)


if __name__ == "__main__":
    unittest.main()
