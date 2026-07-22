---
name: fill-lightning-assessment-docx
description: Parse and complete lightning-protection risk-assessment DOCX files. Use when Attachment 2 must be scored or when the model must complete Chapter 4, Chapter 5, and Attachment 6 from manually entered assessment values.
---

# Fill Lightning Assessment DOCX

Turn one source assessment DOCX into a completed copy. Never overwrite the source document.

For Attachment 2 only, go directly to Generate. When report analysis is requested, start with Parse.

## 1. Parse

```bash
python3 scripts/extract_attachment1.py \
  --input-dir /path/to/docx-directory \
  --output-dir /path/to/json-directory
```

This produces the existing `*.assessment.json`. When report analysis is needed, the same JSON also contains `报告章节`; do not create a separate sections JSON.

## 2. Review

To complete Chapter 4, Chapter 5, and Attachment 6, read `references/report-review-guide.md` completely and fill only `报告章节/AI生成` in the assessment JSON.

Treat the parsed assessment units and their L, S, and R values as manual facts. Do not modify or recalculate them. Do not invent missing site conditions or inspection results.

## 3. Generate

Attachment 2 only:

```bash
python3 scripts/fill_docx.py source.docx \
  --output source.filled.docx \
  --report source.assessment.json
```

Attachment 2 plus report analysis:

```bash
python3 scripts/fill_docx.py source.docx \
  --assessment-json source.assessment.json \
  --output source.filled.docx
```

The command validates the assessment JSON against the source DOCX before writing anything. Fix the reported field when validation fails; never bypass the check.

## Completion rules

- Confirm that the output DOCX exists and is non-empty.
- Report every `validation_errors` item; never silently replace `待确认` with a score.
- Preserve the source order of assessment units.
- Link the completed DOCX in the final response.
- Never overwrite the source DOCX or broaden edits beyond the requested report areas.
