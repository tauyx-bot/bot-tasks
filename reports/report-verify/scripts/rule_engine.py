from __future__ import annotations

import json
import hashlib
import math
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from .utils import compact, decimal_value, normalize, rows_contain, unique


STATUS_LABELS = {
    "pass": "通过",
    "fail": "不通过",
    "manual_review": "待人工核验",
    "source_error": "来源数据错误",
    "no_rule": "无核验要求",
    "skip": "不核验",
}
OVERALL_LABELS = {
    "passed": "核验通过",
    "failed": "核验未通过",
    "needs_manual_review": "需要人工核验",
}


def get_path(value: Any, path: str) -> Any:
    current = value
    if not path:
        return current
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(strings(item))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(strings(item))
        return result
    return [] if value is None else [str(value)]


def _rows_between(document: dict[str, Any], spec: dict[str, Any]) -> list[list[str]]:
    rows = [row for table in document.get("tables", []) for row in (table.get("rows", []) if isinstance(table, dict) else table)]
    active = False
    result: list[list[str]] = []
    for row in rows:
        joined = "".join(str(cell) for cell in row)
        if all(term in joined for term in spec.get("start_all", [])):
            active = True
            if spec.get("include_start"):
                result.append(row)
            continue
        if active and any(term in joined for term in spec.get("stop_any", [])):
            break
        if active and len(row) >= spec.get("min_columns", 1):
            result.append(row)
    return result


def select(spec: Any, documents: dict[str, Any]) -> Any:
    if not isinstance(spec, dict) or "type" not in spec:
        return spec
    kind = spec["type"]
    if kind == "ref":
        return select(documents["__selectors__"][spec["name"]], documents)
    if kind == "literal":
        return spec.get("value")
    if kind == "combine":
        result: list[Any] = []
        for item in spec.get("items", []):
            value = select(item, documents)
            result.extend(value if isinstance(value, list) else [value])
        return result
    document = documents.get(spec.get("document", ""), {})
    if kind == "path":
        return get_path(document, spec.get("path", ""))
    if kind == "document_text":
        return "|".join(strings(document))
    if kind == "table_rows":
        rows = document["tables"][int(spec["index"])]["rows"]
        return rows[int(spec.get("start", 0)) : spec.get("end")]
    if kind == "table_text":
        rows = select({**spec, "type": "table_rows"}, documents)
        return "|".join(str(cell) for row in rows for cell in row)
    if kind == "section_rows":
        return _rows_between(document, spec)
    if kind == "pdf_field":
        labels = spec["labels"] if isinstance(spec["labels"], list) else [spec["labels"]]
        found: list[str] = []
        for table in document.get("tables", []):
            rows = table.get("rows", []) if isinstance(table, dict) else table
            for row in rows:
                for index, cell in enumerate(row[:-1]):
                    if str(cell) in labels:
                        found.append(str(row[index + 1]))
        occurrence = int(spec.get("occurrence", 0))
        return found[occurrence] if len(found) > occurrence else ""
    if kind == "regex":
        source = str(select(spec["source"], documents))
        flags = re.I if spec.get("ignore_case") else 0
        matches = re.findall(spec["pattern"], source, flags)
        values = [item[spec.get("group", 0)] if isinstance(item, tuple) else item for item in matches]
        values = unique([str(item) for item in values]) if spec.get("unique", True) else [str(item) for item in values]
        return values[0] if spec.get("first") and values else values
    if kind == "records":
        rows = select(spec["source"], documents)
        result: list[list[str]] = []
        for row in rows:
            if spec.get("skip_if_contains") and any(term in "".join(map(str, row)) for term in spec["skip_if_contains"]):
                continue
            columns = spec.get("columns", [])
            variants = spec.get("columns_by_length", {})
            if str(len(row)) in variants:
                columns = variants[str(len(row))]
            if not columns or max(columns) >= len(row):
                continue
            result.append([str(row[index]) for index in columns])
        return result
    if kind == "values":
        value = select(spec["source"], documents)
        result = strings(value)
        if spec.get("numeric"):
            return [number for item in result if (number := decimal_value(item)) is not None]
        return unique(result) if spec.get("unique", True) else result
    if kind == "workbook_cells":
        matrix = document["sheets"][spec["sheet"]]["matrix"]
        result = []
        for row, column in spec["cells"]:
            result.append(matrix[int(row)][int(column)] if len(matrix) > int(row) and len(matrix[int(row)]) > int(column) else None)
        return result
    if kind == "distinct_column":
        rows = select(spec["source"], documents)
        column = int(spec["column"])
        excluded = {compact(item) for item in spec.get("exclude", [])}
        return unique([str(row[column]) for row in rows if len(row) > column and compact(row[column]) not in excluded])
    if kind == "column_values":
        rows = select(spec["source"], documents)
        column = int(spec["column"])
        return [row[column] for row in rows if len(row) > column]
    if kind == "filter_rows":
        rows = select(spec["source"], documents)
        result = []
        for row in rows:
            matched = True
            for condition in spec.get("conditions", []):
                column = int(condition["column"])
                value = str(row[column]) if len(row) > column else ""
                if "equals" in condition and compact(value) != compact(condition["equals"]):
                    matched = False
                if "contains" in condition and compact(condition["contains"]) not in compact(value):
                    matched = False
                if "not_in" in condition and compact(value) in {compact(item) for item in condition["not_in"]}:
                    matched = False
            if matched:
                result.append(row)
        return result
    if kind == "filter_values":
        values = select(spec["source"], documents)
        values = values if isinstance(values, list) else [values]
        include = re.compile(spec["include_regex"]) if spec.get("include_regex") else None
        exclude = re.compile(spec["exclude_regex"]) if spec.get("exclude_regex") else None
        return [value for value in values if (include is None or include.search(str(value))) and (exclude is None or not exclude.search(str(value)))]
    if kind == "replace_values":
        values = select(spec["source"], documents)
        values = values if isinstance(values, list) else [values]
        result = []
        for value in values:
            text = str(value)
            for replacement in spec.get("replacements", []):
                text = re.sub(replacement["pattern"], replacement.get("value", ""), text)
            result.append(text)
        return result
    if kind == "group_max":
        rows = select(spec["source"], documents)
        groups: dict[tuple[str, ...], Decimal] = {}
        for row in rows:
            try:
                key = tuple(str(row[int(index)]) for index in spec["key_columns"])
            except IndexError:
                continue
            numbers = [decimal_value(row[int(index)]) for index in spec["value_columns"] if len(row) > int(index)]
            numbers = [number for number in numbers if number is not None]
            if numbers:
                groups[key] = max(groups.get(key, numbers[0]), *numbers)
        return [list(key) + [str(value)] for key, value in groups.items()]
    if kind == "average":
        values = select(spec["source"], documents)
        numbers = [decimal_value(value) for value in strings(values)]
        numbers = [number for number in numbers if number is not None]
        if not numbers:
            return ""
        average = sum(numbers) / Decimal(len(numbers))
        places = int(spec.get("decimal_places", 1))
        quantum = Decimal(1).scaleb(-places)
        return str(average.quantize(quantum))
    raise ValueError(f"unknown selector type: {kind}")


def _verification_basis(rule: dict[str, Any], documents: dict[str, Any]) -> list[dict[str, str]]:
    resolved = []
    for item in rule.get("basis", []):
        basis = dict(item)
        document_name = basis.pop("document", None)
        if document_name:
            source = documents.get(document_name, {}).get("source", "")
            basis["file"] = Path(source).name if source else str(document_name)
        resolved.append({key: str(value) for key, value in basis.items() if value not in (None, "")})
    return resolved


def _outcome(
    comment: dict[str, Any],
    rule: dict[str, Any],
    status: str,
    evidence: Any,
    message: str,
    documents: dict[str, Any],
) -> dict[str, Any]:
    return {
        "comment_id": comment["id"],
        "comment_number": comment.get("number"),
        "comment": comment.get("text", ""),
        "anchor": comment.get("anchor", ""),
        "context": comment.get("context", ""),
        "status": STATUS_LABELS.get(status, status),
        "rule_key": rule.get("name", "missing_rule"),
        "rule": rule.get("description") or comment.get("text") or message,
        "evidence": _compact_evidence(evidence),
        "message": message,
        "report_location": rule.get("report_location") or comment.get("context") or comment.get("anchor") or "批注未定位到具体小节",
        "basis": _verification_basis(rule, documents),
        "problem_origin": rule.get("problem_origin", "规则未提供问题来源说明"),
    }


def _compact_evidence(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 1000:
        return {
            "length": len(value),
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "preview": value[:500],
        }
    if isinstance(value, list):
        if len(value) > 50:
            return {"count": len(value), "first_items": [_compact_evidence(item) for item in value[:10]]}
        return [_compact_evidence(item) for item in value]
    if isinstance(value, dict):
        return {key: _compact_evidence(item) for key, item in value.items()}
    return value


def evaluate(comment: dict[str, Any], rule: dict[str, Any], documents: dict[str, Any]) -> dict[str, Any]:
    kind = rule["type"]
    if kind in {"manual_review", "no_rule", "skip"}:
        return _outcome(comment, rule, kind, rule.get("evidence", {}), rule["message"], documents)
    actual = select(rule.get("actual"), documents)
    expected = select(rule.get("expected"), documents)
    evidence: dict[str, Any] = {
        "actual": actual,
        "expected": expected,
        "actual_label": rule.get("actual_label", "来源文件中的内容"),
        "expected_label": rule.get("expected_label", "报告中的内容"),
    }

    if kind == "equals":
        ok = compact(actual) == compact(expected) if rule.get("normalize", True) else actual == expected
    elif kind == "unique_equals":
        actual_values = [compact(item) for item in actual]
        expected_values = [compact(item) for item in expected] if isinstance(expected, list) else [compact(expected)]
        ok = actual_values == expected_values
    elif kind == "contains_all":
        haystack = compact(actual)
        values = expected if isinstance(expected, list) else [expected]
        missing = [value for value in values if compact(value) and compact(value) not in haystack]
        evidence["missing"] = missing
        ok = not missing
    elif kind == "records_contained":
        aliases = {compact(key): compact(value) for key, value in rule.get("aliases", {}).items()}
        target_text = compact("|".join(str(cell) for row in expected for cell in row))
        missing = []
        split_pattern = rule.get("split_pattern")
        for row in actual:
            absent = []
            for cell in row:
                value = aliases.get(compact(cell), compact(cell))
                if value in {"", "/"} or value in target_text:
                    continue
                if split_pattern:
                    parts = [aliases.get(compact(part), compact(part)) for part in re.split(split_pattern, str(cell))]
                    if parts and all(not part or part in target_text for part in parts):
                        continue
                absent.append(value)
            if absent:
                missing.append(" / ".join(absent[:4]))
        ok = not missing
        evidence["missing"] = missing[: rule.get("max_evidence", 30)]
    elif kind == "set_equals":
        actual_set = {compact(item) for item in actual if compact(item)}
        expected_set = {compact(item) for item in expected if compact(item)}
        evidence.update({"actual_set": sorted(actual_set), "expected_set": sorted(expected_set)})
        ok = actual_set == expected_set
    elif kind == "allowed_in_text":
        found = [item for item in expected if compact(item) in compact(actual)]
        evidence["found"] = found
        ok = len(found) == int(rule.get("expected_count", 1))
    elif kind == "conditional_contains":
        condition = select(rule["condition"], documents)
        condition_met = bool(condition)
        ok = not condition_met or compact(expected) in compact(actual)
        evidence["condition"] = condition
    elif kind == "sum_equals":
        total = sum((decimal_value(item) or Decimal(0)) for item in actual)
        expected_number = decimal_value(expected)
        evidence["sum"] = total
        ok = expected_number is not None and total == expected_number
    elif kind == "numeric_values_present":
        haystack = compact(actual)
        values = [normalize(item) for item in strings(expected) if decimal_value(item) is not None]
        missing = [item for item in values if item not in haystack]
        evidence["missing"] = missing[: rule.get("max_evidence", 30)]
        ok = not missing
    elif kind == "threshold_table":
        errors = []
        for row in actual:
            value = decimal_value(row[int(rule["value_column"])]) if len(row) > int(rule["value_column"]) else None
            if value is None:
                continue
            threshold = Decimal(str(rule["threshold"]))
            positive = value > threshold if rule.get("strict", True) else value >= threshold
            expected_text = rule["positive"] if positive else rule["negative"]
            cell = row[int(rule["result_column"])] if len(row) > int(rule["result_column"]) else ""
            if compact(cell) != compact(expected_text):
                errors.append({"row": row, "expected": expected_text})
        evidence = {"errors": errors}
        ok = not errors
    elif kind == "scaled_sqrt_formula":
        errors = []
        checked = 0
        for row in actual:
            try:
                base = decimal_value(row[int(rule["base_column"])])
                duration = decimal_value(row[int(rule["duration_column"])])
                reported = decimal_value(row[int(rule["result_column"])])
            except IndexError:
                continue
            if None in {base, duration, reported}:
                continue
            calculated = base * Decimal(str(math.sqrt(float(duration / Decimal(str(rule["scale"]))))))
            checked += 1
            if abs(calculated - reported) > Decimal(str(rule.get("tolerance", "0.011"))):
                errors.append({"row": row, "calculated": f"{calculated:.4f}"})
        evidence = {"checked": checked, "errors": errors}
        ok = checked > 0 and not errors
    elif kind == "count_equals":
        actual_count = len(actual)
        expected_number = int(decimal_value(expected) or -1)
        evidence = {"values": actual, "actual_count": actual_count, "expected_count": expected_number}
        ok = actual_count == expected_number
    else:
        raise ValueError(f"unknown rule type: {kind}")

    return _outcome(
        comment,
        rule,
        "pass" if ok else rule.get("failure_status", "fail"),
        evidence,
        rule.get("pass_message", "核验通过") if ok else rule.get("fail_message", "核验不通过"),
        documents,
    )


def verify(documents: dict[str, Any], rules: list[dict[str, Any]], comment_document: str, selectors: dict[str, Any] | None = None) -> dict[str, Any]:
    documents = {**documents, "__selectors__": selectors or {}}
    comments = documents[comment_document].get("comments", [])
    by_id = {int(rule["comment_id"]): rule for rule in rules}
    results = []
    for comment_number, original_comment in enumerate(comments, start=1):
        comment = {**original_comment, "number": comment_number}
        rule = by_id.get(int(comment["id"]))
        if rule is None:
            results.append(_outcome(comment, {"type": "missing_rule", "name": "missing_rule"}, "source_error", {}, "配置中缺少该批注规则", documents))
            continue
        try:
            results.append(evaluate(comment, rule, documents))
        except Exception as exc:
            results.append(_outcome(comment, rule, "source_error", {"error": str(exc)}, "规则执行失败", documents))
    issue_number = 0
    for result in results:
        if result["status"] not in {"通过", "不核验"}:
            issue_number += 1
            result["issue_number"] = issue_number

    counts = Counter(result["status"] for result in results)
    if counts["不通过"] or counts["来源数据错误"]:
        overall = "failed"
    elif counts["待人工核验"]:
        overall = "needs_manual_review"
    else:
        overall = "passed"
    summary = {
        "批注总数": len(comments),
        "通过": counts["通过"],
        "不通过": counts["不通过"],
        "待人工核验": counts["待人工核验"],
        "来源数据错误": counts["来源数据错误"],
        "无核验要求": counts["无核验要求"],
        "不核验": counts["不核验"],
    }
    return {"overall_status": OVERALL_LABELS[overall], "summary": summary, "results": results}


def render_markdown(payload: dict[str, Any], title: str) -> str:
    summary = payload["summary"]
    summary_text = "，".join(
        f"{key} {summary.get(key, 0)}"
        for key in ("通过", "不通过", "待人工核验", "来源数据错误", "无核验要求", "不核验")
    )
    lines = [
        f"# {title}",
        "",
        f"**结论：{payload['overall_status']}**（{summary_text}）",
    ]
    formula_errors = payload.get("source_formula_errors", [])
    error_names = {"#REF!": "公式引用无效", "#NUM!": "数值计算错误"}
    errors_by_sheet: dict[tuple[str, str], Counter[str]] = {}
    for error in formula_errors:
        source_file = str(error.get("source_file", "未注明来源文件"))
        sheet = str(error.get("sheet", "未知工作表"))
        label = error_names.get(str(error.get("value", "")), "其他公式错误")
        errors_by_sheet.setdefault((source_file, sheet), Counter())[label] += 1
    formula_details_by_file: dict[str, list[str]] = {}
    for (source_file, sheet), counts in sorted(errors_by_sheet.items()):
        details = "，".join(f"{name} {count} 个" for name, count in sorted(counts.items()))
        formula_details_by_file.setdefault(source_file, []).append(f"{sheet}：{details}")
    if formula_errors:
        formula_details = "；".join(
            f"{source_file}（{'，'.join(details)}）"
            for source_file, details in formula_details_by_file.items()
        )
        lines.extend(["", f"**来源公式异常：{len(formula_errors)} 个**：{formula_details}"])
    lines.extend(["", "## 待处理项", ""])
    for item in payload["results"]:
        if item["status"] in {"通过", "不核验"}:
            continue
        comment_number = item.get("comment_number") or item["comment_id"] + 1
        basis = item.get("basis", [])
        basis_text = "；".join(
            f"{value.get('file', '未注明文件')} / {value.get('location', '未注明位置')}"
            for value in basis
        ) or "未提供核验依据"
        check_method = item["message"] if item["status"] == "无核验要求" else item["rule"]
        lines.extend(
            [
                f"### {item.get('issue_number', item['comment_id'] + 1)}. [{item['status']}] 第 {comment_number} 条批注 · 内部规则：`{item.get('rule_key', 'missing_rule')}`",
                "",
                f"- **位置**：{item['report_location']}",
                f"- **原因**：{item['problem_origin']}",
                f"- **依据**：{basis_text}",
                f"- **核对方法**：{check_method}",
            ]
        )
        evidence = item.get("evidence", {})
        missing = evidence.get("missing") if isinstance(evidence, dict) else None
        if missing:
            lines.append(f"- **具体差异**：{'；'.join(str(value) for value in missing)}")
        errors = evidence.get("errors") if isinstance(evidence, dict) else None
        if errors:
            lines.append(f"- **计算错误**：{'；'.join(str(value) for value in errors)}")
        lines.append("")
    return "\n".join(lines)
