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
- GBZ 2.1 OEL database: `knowledge/oel_limits.json`
- GBZ 2.1 source: `knowledge/化学有害因素.md`
- GBZ 2.2 physical-factor database: `knowledge/physical_factors.json`
- GBZ 2.2 source: `knowledge/物理危害.md`
- Unresolved inputs that cannot be inferred from a survey: `knowledge/pending_business_rules.json`
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
  --component-report /path/to/component-report.pdf \
  --template env-report/template/plan_template.docx \
  --rules env-report/knowledge/data.json \
  --output /path/to/output.docx \
  --json-out /path/to/output.json
```

For survey PDFs, use a normalized-data handoff before report generation:

1. Run `parse_pdf.py` to produce raw JSON.
2. Have the large language model normalize the parsed rows without inventing
   facts. In particular, preserve paired work locations and work contents,
   normalize Chinese/English delimiters to `、`, and retain source order.
3. Pass the reviewed JSON to the downstream generator with `--parsed-json`:

```bash
python3 env-report/scripts/generate_report.py \
  --parsed-json /path/to/normalized.json \
  --template env-report/template/plan_template.docx \
  --rules env-report/knowledge/data.json \
  --output /path/to/output.docx \
  --json-out /path/to/output.json
```

`--pdf` and `--parsed-json` are mutually exclusive. The latter is the preferred
entry point after model normalization and prevents the generator from silently
re-parsing and discarding reviewed data.

`--component-report` is optional. When supplied, sampled-material placeholders
such as `蓝光胶水（取样分析）` are replaced with the reportable substances parsed
from the matching component-analysis report.

Generated JSON includes `inference_notes` when the parser derives a job-level
fact (for example, inferring mobile work from full-shift multi-location detail).
Its `survey_tables` section also preserves structured materials, products,
running equipment, protection facilities, PPE, and exposure records. Fixed-point
counts use matching running-equipment counts when available and retain their
source in `workstation_count_source`.
When all detected positions share one work window, the parser writes that
normalized window to `header.expected_sampling_time`; multiple shifts remain
blank and are reported in `missing_fields` for confirmation.
Do not turn items in `pending_business_rules.json` into company-specific code.

Parse a component-analysis report independently:

```bash
python3 env-report/scripts/parse_component_report.py \
  --pdf /path/to/component-report.pdf \
  --output /path/to/components.json
```

Run fixture tests:

```bash
python3 env-report/test/test_examples.py
python3 -m unittest discover -s env-report/test -p 'test_*rules.py'
python3 -m unittest discover -s env-report/test -p 'test_component_report.py'
```

Refresh expected fixtures:

```bash
python3 env-report/test/test_examples.py --refresh-expected
```

Rebuild the OEL database after updating the GBZ 2.1 Markdown source:

```bash
python3 env-report/scripts/build_oel_database.py
python3 env-report/scripts/build_physical_factor_database.py
```

## Constraints

- Use `pdfplumber` for PDF parsing.
- Do not add OCR.
