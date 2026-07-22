# Report Analysis Review Guide

Use this guide only when completing `报告章节/AI生成` in an assessment JSON.

## Protected values

Do not change anything under `报告章节/人工填写`. The assessment unit, lightning likelihood (L), consequence severity (S), and risk level (R) are manually entered facts.

Do not change the unit name, order, risk level, or color already prepared for Attachment 6. The generation script validates them against the source DOCX.

## Writing rules

- Use only facts present in `报告章节/资料上下文`, Attachment 1, and the manual L/S/R values.
- Do not invent measurements, defects, equipment status, completed corrective actions, qualifications, or inspection findings.
- If a specific site condition is unsupported, use cautious wording or state that it requires on-site confirmation.
- Keep every analysis consistent with the manual L/S/R values; never raise or lower a risk rating.

Complete these fields:

- Chapter 4: concise enterprise overview and one site-inspection analysis per assessment unit.
- Chapter 5: one main-risk analysis per unit, explaining the lightning path, affected object, and plausible consequence; then provide a conclusion consistent with the highest manual risk.
- Attachment 6: risk description, possible accident types, and practical control measures for every unit.

Control measures should be specific actions, such as inspection and maintenance, grounding and equipotential bonding, SPD checks, static-control measures, lightning-warning response, training, and emergency drills. Do not claim that a measure has already been completed.

Before generation, confirm that all required text is non-empty and that unit names, count, and order match the manual rows exactly.
