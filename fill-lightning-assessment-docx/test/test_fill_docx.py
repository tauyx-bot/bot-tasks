import re
import sys
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_attachment1 import calculate_assessment, extract_a4_review, extract_attachment
from fill_docx import DOCUMENT_XML, fill_formula_paragraphs, fill_target_tables, target_section
from generate_from_json import NS, all_tables, qn, text


def document_root(path):
    with zipfile.ZipFile(path) as package:
        return ET.fromstring(package.read(DOCUMENT_XML))


def section(root, name):
    return next(table for table in all_tables(root) if target_section(text(table)) == name)


def checkbox_signature(table):
    return [
        (symbol.get(qn("font")), symbol.get(qn("char")))
        for symbol in table.findall(".//w:sym", NS)
    ]


def formula_lines(root):
    found = {}
    for paragraph in root.findall(".//w:p", NS):
        visible = text(paragraph)
        compact = re.sub(r"\s+", "", visible)
        if compact.startswith("L=W1×L1十W2×L2十W3×L3="):
            found["A.1"] = visible
        elif compact.startswith("P=P1十P2十P3十P4十P5十P6="):
            found["A.2"] = visible
        elif compact.startswith("S=MAX(S1，S2，S3)"):
            found["A.5"] = visible
        elif compact.startswith("M=MAX(M1，M2，M3，M4)="):
            found["A.6"] = visible
        elif compact.startswith("R=L×S="):
            found["R"] = visible
    return found


def formula_paragraphs(root):
    lines = formula_lines(root)
    return {
        key: next(paragraph for paragraph in root.findall(".//w:p", NS) if text(paragraph) == value)
        for key, value in lines.items()
    }


def run_property_signature(paragraph):
    signatures = []
    for run in paragraph.findall("w:r", NS):
        properties = run.find("w:rPr", NS)
        signatures.append(tuple(
            None if properties is None or properties.find(f"w:{name}", NS) is None
            else properties.find(f"w:{name}", NS).get(qn("val"), "1")
            for name in ("b", "bCs", "i", "iCs", "sz", "szCs")
        ))
    return signatures


def is_bold(run):
    bold = run.find("w:rPr/w:b", NS)
    return bold is not None and bold.get(qn("val"), "1") not in {"0", "false", "off"}


def visible_bold_signature(element):
    return [(text(run), is_bold(run)) for run in element.findall(".//w:r", NS) if text(run)]


class FillDocxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / "test" / "case" / "test.docx"
        cls.reference = document_root(ROOT / "test" / "data" / "QXRB566深圳市欣峰热处理有限公司.docx")
        fields = extract_attachment(cls.source)
        cls.assessment = calculate_assessment(fields, cls.source.stem, extract_a4_review(cls.source))
        cls.original = document_root(cls.source)
        cls.root = document_root(cls.source)
        cls.table_edits, cls.recognized = fill_target_tables(cls.root, cls.assessment)
        cls.formula_edits, cls.recognized_formulas = fill_formula_paragraphs(cls.root, cls.assessment)

    def test_reference_calculation_values(self):
        self.assertEqual(self.assessment["A.1"]["结果"], 1)
        self.assertEqual(self.assessment["A.2"]["结果"], 18)
        self.assertEqual(self.assessment["A.5"]["结果"], 3)
        self.assertEqual(self.assessment["A.6"]["结果"], 3)
        self.assertEqual(self.assessment["A.8"]["R"], 3)

    def test_recognizes_all_tables_and_formula_lines(self):
        self.assertEqual(self.recognized, {"A.1", "A.2", "A.3", "A.5", "A.6", "A.7", "A.8"})
        self.assertEqual(self.recognized_formulas, {"A.1", "A.2", "A.5", "A.6", "R"})
        self.assertGreater(self.table_edits, 0)
        self.assertEqual(self.formula_edits, 5)

    def test_checkbox_selections_match_completed_reference(self):
        for name in ("A.1", "A.2", "A.3", "A.5", "A.6", "A.7"):
            with self.subTest(section=name):
                self.assertEqual(
                    checkbox_signature(section(self.root, name)),
                    checkbox_signature(section(self.reference, name)),
                )

    def test_score_cells_match_completed_reference(self):
        result_columns = {"A.1": 7, "A.2": 7, "A.3": 2, "A.5": 5, "A.6": 5}
        for name, column in result_columns.items():
            actual_rows = section(self.root, name).findall("w:tr", NS)
            reference_rows = section(self.reference, name).findall("w:tr", NS)
            actual = [text(row.findall("w:tc", NS)[column]).strip() for row in actual_rows[2 if name not in {"A.3"} else 1:]]
            expected = [text(row.findall("w:tc", NS)[column]).strip() for row in reference_rows[2 if name not in {"A.3"} else 1:]]
            with self.subTest(section=name):
                self.assertEqual(actual, expected)

    def test_formula_results_match_completed_reference(self):
        self.assertEqual(formula_lines(self.root), formula_lines(self.reference))

    def test_inserted_text_uses_requested_latin_and_cjk_fonts(self):
        paragraph = next(
            paragraph for paragraph in self.root.findall(".//w:p", NS)
            if re.sub(r"\s+", "", text(paragraph)).startswith("R=L×S=")
        )
        run = next(run for run in paragraph.findall("w:r", NS) if "1×3=3" in text(run))
        fonts = run.find("w:rPr/w:rFonts", NS)
        self.assertIsNotNone(fonts)
        self.assertEqual(fonts.get(qn("ascii")), "仿宋")
        self.assertEqual(fonts.get(qn("hAnsi")), "仿宋")
        self.assertEqual(fonts.get(qn("cs")), "仿宋")
        self.assertEqual(fonts.get(qn("eastAsia")), "微软雅黑")

    def test_formula_prefix_run_styles_are_preserved(self):
        original = formula_paragraphs(self.original)
        actual = formula_paragraphs(self.root)
        preserved_run_counts = {"A.1": 22, "A.2": 27, "A.5": 10, "A.6": 15, "R": 1}
        for key, count in preserved_run_counts.items():
            with self.subTest(formula=key):
                self.assertEqual(
                    run_property_signature(actual[key])[:count],
                    run_property_signature(original[key])[:count],
                )

    def test_a6_result_values_preserve_bold_paragraph_style(self):
        rows = section(self.root, "A.6").findall("w:tr", NS)[2:]
        for row in rows:
            result_cell = row.findall("w:tc", NS)[5]
            result_run = next(run for run in result_cell.findall(".//w:r", NS) if text(run))
            with self.subTest(value=text(result_run)):
                self.assertIsNotNone(result_run.find("w:rPr/w:b", NS))
                self.assertIsNotNone(result_run.find("w:rPr/w:bCs", NS))

    def test_all_filled_result_bold_styles_match_reference(self):
        result_columns = {"A.1": 7, "A.2": 7, "A.3": 2, "A.5": 5, "A.6": 5}
        starts = {"A.1": 2, "A.2": 2, "A.3": 1, "A.5": 2, "A.6": 2}
        for name, column in result_columns.items():
            actual_rows = section(self.root, name).findall("w:tr", NS)[starts[name]:]
            reference_rows = section(self.reference, name).findall("w:tr", NS)[starts[name]:]
            actual = [visible_bold_signature(row.findall("w:tc", NS)[column]) for row in actual_rows]
            expected = [visible_bold_signature(row.findall("w:tc", NS)[column]) for row in reference_rows]
            with self.subTest(section=name):
                self.assertEqual(actual, expected)

        actual_formulas = formula_paragraphs(self.root)
        reference_formulas = formula_paragraphs(self.reference)
        for key in ("A.1", "A.2", "A.6", "R"):
            with self.subTest(formula=key):
                self.assertEqual(
                    any(is_bold(run) for run in actual_formulas[key].findall("w:r", NS)),
                    any(is_bold(run) for run in reference_formulas[key].findall("w:r", NS)),
                )

        s_result_run = [
            run for run in actual_formulas["A.5"].findall("w:r", NS)
            if text(run) == "3"
        ][-1]
        self.assertTrue(is_bold(s_result_run))
        self.assertIsNotNone(s_result_run.find("w:rPr/w:bCs", NS))
        s_suffix_run = next(
            run for run in actual_formulas["A.5"].findall("w:r", NS)
            if "…" in text(run)
        )
        self.assertFalse(is_bold(s_suffix_run))

        for name in ("A.1", "A.2", "A.3", "A.5", "A.6", "A.7"):
            actual_symbols = [
                is_bold(run) for run in section(self.root, name).findall(".//w:r", NS)
                if run.find("w:sym", NS) is not None
                and run.find("w:sym", NS).get(qn("char")) in {"00FE", "0052"}
            ]
            reference_symbols = [
                is_bold(run) for run in section(self.reference, name).findall(".//w:r", NS)
                if run.find("w:sym", NS) is not None
                and run.find("w:sym", NS).get(qn("char")) in {"00FE", "0052"}
            ]
            with self.subTest(checkbox_section=name):
                self.assertEqual(actual_symbols, reference_symbols)


if __name__ == "__main__":
    unittest.main()
