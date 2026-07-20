import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_attachment1 import calculate_assessment, extract_a4_review, extract_attachment


class AttachmentAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = ROOT / "test" / "data"

    def assessment_for(self, prefix):
        path = next(self.data_dir.glob(f"{prefix}*.docx"))
        fields = extract_attachment(path)
        return fields, calculate_assessment(fields, path.stem, extract_a4_review(path))

    def test_extracts_variant_unit_name_header(self):
        fields, _ = self.assessment_for("QXRB527")
        self.assertEqual(fields["单位名称（盖章）"], "深圳大铲湾现代港口发展有限公司")
        self.assertEqual(fields["火灾危险性类别"], ["乙、丙类"])

    def test_calculates_known_reference_result(self):
        _, assessment = self.assessment_for("QXRB527")
        self.assertEqual(assessment["A.2"]["结果"], 22)
        self.assertEqual(assessment["A.1"]["结果"], 2)
        self.assertEqual(assessment["A.5"]["结果"], 3)
        self.assertEqual(assessment["A.8"], {"公式": "R = L * S", "R": 6, "风险等级": "较高风险"})

    def test_preserves_ambiguous_checkbox_data_as_validation_error(self):
        _, assessment = self.assessment_for("QXRB506")
        self.assertIsNone(assessment["A.5"]["后果严重性因子"][0]["分值"])
        self.assertTrue(any("风险单元现场最大人数" in error for error in assessment["validation_errors"]))

    def test_result_files_are_valid_json_pairs(self):
        results = ROOT / "test" / "expected"
        attachment_files = sorted(results.glob("*.attachment1.json"))
        assessment_files = sorted(results.glob("*.assessment.json"))
        self.assertEqual(len(attachment_files), 10)
        self.assertEqual(len(assessment_files), 10)
        for path in attachment_files + assessment_files:
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
