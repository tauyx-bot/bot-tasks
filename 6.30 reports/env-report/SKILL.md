---
name: env-report
description: Review workplace survey PDFs and generate occupational-health sampling-plan DOCX files. Use when a survey contains manually entered workplace, job, hazard, exposure-time, equipment, or shift data that must be normalized by the language model before report generation, including optional component-analysis reports.
---

# Env Report

Turn one workplace survey PDF into a reviewed sampling-plan DOCX. Always keep the model review between parsing and generation.

## 1. Parse

```bash
python3 scripts/skill_workflow.py parse \
  --pdf /path/to/survey.pdf \
  --output /path/to/survey.raw.json
```

Keep `survey.raw.json` unchanged as the audit source.

## 2. Review

Read `references/review-guide.md` completely. Compare the PDF with the raw JSON, correct supported formatting or extraction problems, and save a separate `/path/to/survey.reviewed.json`.

Do not invent missing facts. If a conflict cannot be resolved from the PDF, preserve the source value and report it to the user. Do not manually update derived fields such as `projects`, `table3`, or `missing_fields`.

## 3. Generate

```bash
python3 scripts/skill_workflow.py generate \
  --reviewed-json /path/to/survey.reviewed.json \
  --output /path/to/sampling-plan.docx
```

For a matching component-analysis report, add:

```bash
--component-report /path/to/component-report.pdf
```

The command validates the reviewed data before generating anything. If validation fails, return to the review step and fix the reported field; never bypass the gate. On success it writes the DOCX, normalized JSON, and final report JSON together.

## Completion rules

- Confirm that the DOCX exists and is non-empty.
- Check `missing_fields` in the final report JSON and summarize unresolved items.
- Preserve the source order of workplaces, jobs, activities, and hazards.
- Never overwrite the raw JSON or source PDF.
