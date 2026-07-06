#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$ROOT_DIR/env-report"
OUTPUT_ZIP="${1:-$ROOT_DIR/env-report-core.zip}"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "env-report directory not found: $PROJECT_DIR" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

STAGE_DIR="$TMP_DIR/env-report"
mkdir -p \
  "$STAGE_DIR/knowledge" \
  "$STAGE_DIR/scripts" \
  "$STAGE_DIR/template"

cp "$PROJECT_DIR/SKILL.md" "$STAGE_DIR/"
cp "$PROJECT_DIR/knowledge/data.json" "$STAGE_DIR/knowledge/"
cp "$PROJECT_DIR/scripts/fill_docx.py" "$STAGE_DIR/scripts/"
cp "$PROJECT_DIR/scripts/generate_report.py" "$STAGE_DIR/scripts/"
cp "$PROJECT_DIR/scripts/parse_pdf.py" "$STAGE_DIR/scripts/"
cp "$PROJECT_DIR/template/plan_template.docx" "$STAGE_DIR/template/"

rm -f "$OUTPUT_ZIP"

(
  cd "$TMP_DIR"
  python3 - <<'PY' "$OUTPUT_ZIP"
import sys
import zipfile
from pathlib import Path

output = Path(sys.argv[1])
root = Path("env-report")
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            zf.write(path, path.as_posix())
PY
)

echo "saved $OUTPUT_ZIP"
