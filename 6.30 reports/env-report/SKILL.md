---
name: env-report
description: Parse a survey PDF with pdfplumber, fill Table 2 and Table 3 in the plan DOCX, and verify output against fixed JSON fixtures.
---

# Env Report

Use this skill to turn a workplace survey PDF into a filled `现场采样/测量计划表` DOCX.

## Resources

- Survey PDF
- Template DOCX (`现场采样/测量计划表`): `template/plan_template.docx`
- Rule data: `knowledge/data.json`
- Example fixtures:
  - `test/expected/*.expected.json`

## Scripts

- `scripts/parse_pdf.py`
- `scripts/generate_report.py`
- `scripts/fill_docx.py`
- `test/test_examples.py`

## Commands

Generate a report:

```bash
python3 env-report/scripts/generate_report.py \
  --pdf /path/to/input.pdf \
  --template env-report/template/plan_template.docx \
  --rules env-report/knowledge/data.json \
  --output /path/to/output.docx \
  --json-out /path/to/output.json
```

Run fixture tests:

```bash
python3 env-report/test/test_examples.py
```

Refresh expected fixtures:

```bash
python3 env-report/test/test_examples.py --refresh-expected
```

## Constraints

- Use `pdfplumber` for PDF parsing.
- Do not add OCR.
