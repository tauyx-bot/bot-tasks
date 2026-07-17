import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_attachment1 import p3_score, s2_score


class AttachmentOneScoringRuleTests(unittest.TestCase):
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
