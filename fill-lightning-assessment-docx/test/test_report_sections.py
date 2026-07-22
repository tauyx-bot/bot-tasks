import copy
import sys
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_from_json import NS, text
from extract_attachment1 import extract_attachment
from report_sections import (
    ATTACHMENT6,
    CHAPTER4,
    CHAPTER5,
    DOCUMENT_XML,
    extract_sections,
    fill_sections,
    find_report_table,
    manual_rows,
    row_values,
    validate_sections,
)


class ReportSectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / "test" / "data" / "QXRB506深圳市龙岗区坪山协力胶盒厂.docx"

    def root(self):
        with zipfile.ZipFile(self.source) as package:
            return ET.fromstring(package.read(DOCUMENT_XML))

    def completed_data(self):
        data = extract_sections(self.source, extract_attachment(self.source))
        units = [item["评估单元"] for item in data["人工填写"][CHAPTER5]]
        data["AI生成"][CHAPTER4]["企业概况"] = ["公司名称：测试单位", "地理位置：测试位置。"]
        for item in data["AI生成"][CHAPTER4]["现场检查情况"]:
            item["分析"] = f"{item['评估单元']}现场检查分析。"
        for item in data["AI生成"][CHAPTER5]["主要风险分析"]:
            item["分析"] = f"{item['评估单元']}主要风险分析。"
        data["AI生成"][CHAPTER5]["综合评估结论"] = "测试综合评估结论。"
        for item in data["AI生成"][ATTACHMENT6]:
            item["风险描述"] = f"{item['场所']}风险描述。"
            item["可能导致的事故类型"] = "火灾、设备损坏"
            item["管控措施"] = ["定期巡查。", "定期检测防雷装置。"]
        self.assertEqual(units, ["危化品中间仓", "油墨仓", "危废仓", "配电房", "生产车间"])
        return data

    def test_extracts_manual_chapter5_fields_and_builds_ai_template(self):
        data = extract_sections(self.source, extract_attachment(self.source))
        manual = data["人工填写"][CHAPTER5]
        self.assertEqual(len(manual), 5)
        self.assertEqual(
            manual[0],
            {"评估单元": "危化品中间仓", "雷击可能性（L）": "可能", "后果严重性（S）": "重大", "风险等级（R）": "较大风险"},
        )
        self.assertEqual(data["AI生成"][ATTACHMENT6][0]["标示颜色"], "橙色")
        self.assertEqual(data["AI生成"][ATTACHMENT6][3]["标示颜色"], "蓝色")
        self.assertEqual(data["validation_errors"], [])

    def test_rejects_any_change_to_manual_fields(self):
        root = self.root()
        data = self.completed_data()
        changed = copy.deepcopy(data)
        changed["人工填写"][CHAPTER5][0]["雷击可能性（L）"] = "频繁"
        with self.assertRaisesRegex(ValueError, "人工字段与DOCX不一致"):
            validate_sections(root, changed)

    def test_fills_subjective_fields_but_preserves_manual_values(self):
        root = self.root()
        before, errors = manual_rows(root)
        self.assertEqual(errors, [])
        data = self.completed_data()

        edits, recognized = fill_sections(root, data)

        after, errors = manual_rows(root)
        self.assertEqual(errors, [])
        self.assertEqual(after, before)
        self.assertGreater(edits, 0)
        self.assertEqual(recognized, {CHAPTER4, CHAPTER5, ATTACHMENT6})
        fifth_rows = find_report_table(root, "第五章").findall("w:tr", NS)[1:]
        self.assertEqual(text(fifth_rows[0].findall("w:tc", NS)[4]), "危化品中间仓主要风险分析。")
        attachment_rows = find_report_table(root, "附件6").findall("w:tr", NS)[1:]
        self.assertEqual(row_values(attachment_rows[3])[:6], ["4", "配电房", "配电房风险描述。", "火灾、设备损坏", "低", "蓝色"])
        self.assertIn("1.定期巡查。2.定期检测防雷装置。", row_values(attachment_rows[0])[6])


if __name__ == "__main__":
    unittest.main()
