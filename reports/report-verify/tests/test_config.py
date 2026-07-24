import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_example_config():
    path = PROJECT_ROOT / "configs/hongmei.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_profile_paths_stay_inside_report_verify():
    path, config = load_example_config()
    for key in ("input_root", "output_dir"):
        resolved = (path.parent / config[key]).resolve()
        assert PROJECT_ROOT in resolved.parents


def test_example_profile_covers_every_comment_once():
    _, config = load_example_config()
    ids = [rule["comment_id"] for rule in config["rules"]]
    assert len(ids) == len(set(ids))
    assert sorted(ids) == list(range(60))
    names = [rule["name"] for rule in config["rules"]]
    assert len(names) == len(set(names))


def test_generic_package_does_not_embed_profile_data():
    forbidden = ("鸿美", "粤鑫", "中山市", "彭爱华", "电焊烟尘")
    source = "\n".join(path.read_text(encoding="utf-8") for path in (PROJECT_ROOT / "scripts").glob("*.py"))
    assert not any(value in source for value in forbidden)


def test_every_current_nonpassing_rule_has_self_contained_provenance():
    _, config = load_example_config()
    displayed_ids = {7, 12, 43, 46, 47, 58, 59}
    rules = {rule["comment_id"]: rule for rule in config["rules"]}

    for comment_id in displayed_ids:
        rule = rules[comment_id]
        assert rule.get("report_location")
        assert rule.get("problem_origin")
        assert rule.get("basis")
        assert all(item.get("location") for item in rule["basis"])


def test_configured_rules_are_excluded_from_verification():
    _, config = load_example_config()
    rules = {rule["comment_id"]: rule for rule in config["rules"]}

    assert {comment_id for comment_id, rule in rules.items() if rule["type"] == "skip"} == {2, 4, 15, 57}
