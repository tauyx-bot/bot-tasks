import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_attachment1 import calculate_assessment, p3_score, s2_score


class AttachmentOneScoringRuleTests(unittest.TestCase):
    def test_a4_condition_directly_assigns_a1_likelihood_to_three(self):
        fields = {
            "周边地理情况": ["周边高层建筑物"],
            "区域建筑物": {"面积": "1000㎡", "建筑高度": "10m", "等效高度": "10m", "相对高度": "0m"},
            "风险单元现场最大人数": ["（0-10）人"],
            "火灾危险性类别": ["丁、戊类及其他"],
            "毒性危害性类别": ["类别5 及其他"],
            "危险工艺": ["不涉及"],
            "重大危险源": ["不涉及"],
        }
        a4_review = {"人工复核": True, "直接赋值条件": ["防雷装置未定期检测"]}

        assessment = calculate_assessment(fields, "unit", a4_review)

        self.assertEqual(assessment["A.1"]["加权原值"], 1.0)
        self.assertEqual(assessment["A.1"]["结果"], 3)
        self.assertEqual(assessment["A.4"]["结果"], 3)
        self.assertEqual(assessment["A.8"]["R"], 3)

    def test_p3_uses_relative_height_relation(self):
        self.assertEqual(p3_score({"相对高度": "14.5m", "等效高度": "3.5m"}, ["周边高层建筑物"])[0], 2)
        self.assertEqual(p3_score({"相对高度": "15m", "等效高度": "30m"}, ["临海"])[0], 3)
        self.assertEqual(p3_score({"相对高度": "0m"}, ["孤立空旷"])[0], 3)
        self.assertEqual(p3_score({"相对高度": "-2m"}, ["周边高层建筑物"])[0], 4)

    def test_s2_separates_terrain_from_protection_targets(self):
        self.assertEqual(s2_score(["孤立空旷"], {"建筑高度": "5m"})[0], 1)
        self.assertEqual(s2_score(["孤立空旷", "其它"], {"建筑高度": "5m"})[0], 1)
        self.assertEqual(s2_score(["孤立空旷", "其它"], {"建筑高度": "36m"})[0], 2)
        self.assertEqual(s2_score(["临海", "其它"], {"建筑高度": "3m"})[0], 2)
        self.assertEqual(s2_score(["孤立空旷", "小区", "其它"], {"建筑高度": "6m"})[0], 2)
        self.assertEqual(s2_score(["学校", "机场", "小区"], {})[0], 3)


if __name__ == "__main__":
    unittest.main()
