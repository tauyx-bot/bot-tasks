from scripts.rule_engine import evaluate, render_markdown, select, verify


def test_selectors_resolve_references_and_paths():
    documents = {"source": {"tables": [{"rows": [["a", "1"], ["b", "2"]]}]}, "__selectors__": {"rows": {"type": "table_rows", "document": "source", "index": 0}}}
    assert select({"type": "ref", "name": "rows"}, documents) == [["a", "1"], ["b", "2"]]


def test_threshold_rule_is_config_driven():
    comment = {"id": 1, "text": "check", "anchor": "", "context": ""}
    documents = {"data": {"tables": [{"rows": [["sample", "10", "normal"], ["sample", "11", "high"]]}]}, "__selectors__": {}}
    rule = {
        "comment_id": 1,
        "type": "threshold_table",
        "actual": {"type": "table_rows", "document": "data", "index": 0},
        "value_column": 1,
        "result_column": 2,
        "threshold": 10,
        "strict": True,
        "positive": "high",
        "negative": "normal"
    }
    assert evaluate(comment, rule, documents)["status"] == "通过"


def test_issue_metadata_resolves_document_source_to_filename():
    comment = {"id": 2, "text": "核对内容", "anchor": "选中文字", "context": "某章节"}
    documents = {"source": {"source": "/private/input/source.pdf"}, "__selectors__": {}}
    rule = {
        "comment_id": 2,
        "type": "manual_review",
        "name": "source_date_check",
        "message": "需要人工确认",
        "report_location": "第二节表2-1",
        "problem_origin": "来源字段缺失",
        "basis": [{"document": "source", "location": "第一部分原始表", "explanation": "核对字段"}],
    }

    result = evaluate(comment, rule, documents)

    assert result["report_location"] == "第二节表2-1"
    assert result["rule_key"] == "source_date_check"
    assert result["problem_origin"] == "来源字段缺失"
    assert result["basis"] == [{"file": "source.pdf", "location": "第一部分原始表", "explanation": "核对字段"}]


def test_markdown_issue_is_self_contained():
    payload = {
        "overall_status": "需要人工核验",
        "summary": {"通过": 0, "不通过": 0, "待人工核验": 1, "来源数据错误": 0, "无核验要求": 0},
        "results": [{
            "comment_id": 0,
            "comment_number": 4,
            "issue_number": 1,
            "comment": "核对",
            "anchor": "字段值",
            "context": "",
            "status": "待人工核验",
            "rule_key": "date_check",
            "rule": "核验说明",
            "message": "核验结论",
            "evidence": {},
            "report_location": "封面日期",
            "problem_origin": "来源未提供日期",
            "basis": [{"file": "原始表.pdf", "location": "首页日期栏", "explanation": "仅有调查日期"}],
        }],
    }

    markdown = render_markdown(payload, "核验结果")

    assert "问题 1：待人工核验" in markdown
    assert "对应报告批注序号：第 4 条" in markdown
    assert "内部规则标识：`date_check`" in markdown
    assert "检测报告位置：封面日期" in markdown
    assert "原始表.pdf，首页日期栏；仅有调查日期" in markdown
    assert "问题来源：来源未提供日期" in markdown


def test_issue_numbers_are_contiguous_when_passing_results_are_hidden():
    documents = {
        "target": {"comments": [
            {"id": 10, "text": "通过项", "anchor": "", "context": ""},
            {"id": 20, "text": "问题项一", "anchor": "", "context": ""},
            {"id": 30, "text": "问题项二", "anchor": "", "context": ""},
        ]},
    }
    rules = [
        {"comment_id": 10, "type": "equals", "actual": 1, "expected": 1},
        {"comment_id": 20, "type": "manual_review", "message": "人工核验"},
        {"comment_id": 30, "type": "no_rule", "message": "没有规则"},
    ]

    payload = verify(documents, rules, "target")

    assert payload["results"][0]["comment_number"] == 1
    assert "issue_number" not in payload["results"][0]
    assert payload["results"][1]["comment_number"] == 2
    assert payload["results"][1]["issue_number"] == 1
    assert payload["results"][2]["comment_number"] == 3
    assert payload["results"][2]["issue_number"] == 2
