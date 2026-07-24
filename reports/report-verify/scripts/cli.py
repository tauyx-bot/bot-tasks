from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .docx_extract import extract_docx
from .pdf_extract import extract_pdf
from .rule_engine import render_markdown, verify
from .utils import sha256, write_json
from .xlsx_extract import extract_workbook


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _extract(path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    extractor = spec["extractor"]
    if extractor == "docx":
        return extract_docx(path, include_comments=bool(spec.get("comments")))
    if extractor == "pdf":
        return extract_pdf(path)
    if extractor == "xlsx":
        return extract_workbook(path)
    raise ValueError(f"unsupported extractor: {extractor}")


def verify_command(config_path: Path, output_override: Path | None) -> int:
    config_path = config_path.resolve()
    config = load_config(config_path)
    base_dir = config_path.parent
    input_root = (base_dir / config["input_root"]).resolve()
    output_dir = (output_override or (base_dir / config["output_dir"])).resolve()
    if _inside(output_dir, input_root):
        raise ValueError("output directory must not be the input directory or one of its children")

    input_paths: dict[str, Path] = {}
    for name, spec in config["documents"].items():
        path = (input_root / spec["path"]).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        input_paths[name] = path
    before = {name: sha256(path) for name, path in input_paths.items()}

    output_dir.mkdir(parents=True, exist_ok=True)
    json_paths: dict[str, Path] = {}
    for name, spec in config["documents"].items():
        payload = _extract(input_paths[name], spec)
        json_path = output_dir / spec.get("json", f"{name}.json")
        write_json(json_path, payload)
        json_paths[name] = json_path

    # Verification deliberately reads only the generated JSON artifacts.
    documents = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in json_paths.items()
    }
    result = verify(documents, config["rules"], config["comment_document"], config.get("selectors"))
    result["profile"] = config.get("name", config_path.stem)
    result["source_formula_errors"] = [
        {**error, "source_file": Path(document.get("source", name)).name}
        for name, document in documents.items()
        for error in document.get("formula_errors", [])
    ]

    after = {name: sha256(path) for name, path in input_paths.items()}
    unchanged = before == after
    result["input_integrity"] = {
        "unchanged": unchanged,
        "before": before,
        "after": after,
        "files": {name: str(path) for name, path in input_paths.items()},
    }
    if not unchanged:
        result["overall_status"] = "核验未通过"
    write_json(output_dir / config.get("result_json", "verification_result.json"), result)
    report_path = output_dir / config.get("result_markdown", "verification_report.md")
    report_path.write_text(render_markdown(result, config.get("report_title", "文档核验结果")), encoding="utf-8")
    write_json(output_dir / "source_manifest.json", result["input_integrity"])
    print(json.dumps({"overall_status": result["overall_status"], "summary": result["summary"], "output_dir": str(output_dir)}, ensure_ascii=False))
    if not unchanged or result["overall_status"] == "核验未通过":
        return 1
    if result["overall_status"] == "需要人工核验":
        return 3
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JSON 配置驱动的只读文档核验工具")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("verify", help="提取文档为 JSON，再按 JSON 规则核验")
    command.add_argument("--config", required=True, type=Path)
    command.add_argument("--output-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "verify":
            return verify_command(args.config, args.output_dir)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2
