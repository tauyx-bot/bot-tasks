#!/usr/bin/env python3
"""Focused regression tests for sampling-plan business rules."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import generate_report  # noqa: E402
import parse_pdf  # noqa: E402


class MobileJobRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = json.loads(
            (ROOT / "knowledge" / "report_rules.json").read_text(encoding="utf-8")
        )
        cls.rule_index = generate_report.load_rule_index(ROOT / "knowledge" / "data.json")
        cls.collector_index = generate_report.load_collector_index(
            ROOT / "knowledge" / "collector.json"
        )
        parse_pdf.PARSING_RULES = cls.rules["parsing"]

    def build_rows(self, projects_by_detail: list[tuple[str, str, str]]) -> list[dict[str, str]]:
        overall = [
            {
                "workplace": "1F开料车间、2F生产车间",
                "position": "操作工",
                "people_per_shift": "1",
                "work_time": "8:00-12:00,13:30-17:30",
                "job_type": "流动作业",
                "project_raw": "噪声、其他粉尘、环己酮",
                "exposure_type": "②",
                "daily_exposure": "8.00",
            }
        ]
        details = [
            {
                "worker_name": "刘建军",
                "workplace": overall[0]["workplace"],
                "position": "操作工",
                "target": target,
                "project_raw": projects,
                "duration": duration,
            }
            for target, projects, duration in projects_by_detail
        ]
        parsed_rows = parse_pdf.build_table3(overall, details)
        rows, missing = generate_report.build_table3(
            parsed_rows,
            self.collector_index,
            self.rule_index,
            "定期检测",
            self.rules,
        )
        self.assertEqual([], missing)
        return rows

    def test_cross_workplace_mobile_job_uses_overall_context_for_individual_sample(self) -> None:
        rows = self.build_rows(
            [
                ("1F开料车间开料工位", "噪声、其他粉尘", "1h"),
                ("2F生产车间粘膜工位", "噪声", "5h"),
                ("2F生产车间过膜工位", "噪声", "2h"),
            ]
        )
        individual = [row for row in rows if row["sampling_mode"] == "个体"]
        self.assertEqual(1, len(individual))
        self.assertEqual("1F开料车间、2F生产车间", individual[0]["workplace"])
        self.assertEqual("劳动者", individual[0]["target"])
        self.assertEqual("8h", individual[0]["representative_time"])
        self.assertEqual("4h", individual[0]["sampling_time"])
        self.assertEqual({"overall:0"}, {row["job_group_id"] for row in rows})
        self.assertEqual({"1F开料车间", "2F生产车间"}, {
            row["workplace"] for row in rows if row["sampling_mode"] == "定点"
        })

    def test_short_segment_only_factor_does_not_gain_individual_sample(self) -> None:
        rows = self.build_rows(
            [
                ("2F生产车间丝印工位", "甲苯、噪声", "7h"),
                ("2F生产车间洗网工位", "甲苯、环己酮", "0.5h"),
            ]
        )
        individual_projects = {
            project
            for row in rows
            if row["sampling_mode"] == "个体"
            for project in row["project"].split("、")
        }
        self.assertIn("甲苯", individual_projects)
        self.assertIn("噪声", individual_projects)
        self.assertNotIn("环己酮", individual_projects)

    def test_daily_times_are_one_for_all_projects(self) -> None:
        for project in ("噪声", "高温", "手传振动", "其他粉尘", "甲苯"):
            result = generate_report.sampling_parameters(
                project,
                "定点",
                "直读",
                True,
                "/",
                "1",
                "固定",
                "8h",
                "定期检测",
                self.rules,
            )
            self.assertEqual("1", result["times_per_day"], project)
            self.assertEqual("短时间", result["time_type"], project)

    def test_mobile_individual_noise_is_long_time(self) -> None:
        rule = self.rule_index[generate_report.normalize_lookup("噪声")]
        result = generate_report.sampling_parameters(
            "噪声",
            "个体",
            "直读",
            True,
            "/",
            "1",
            "流动",
            "8h",
            "定期检测",
            self.rules,
            rule,
        )
        self.assertEqual("长时间", result["time_type"])
        self.assertEqual("4h", result["sampling_time"])

    def test_fixed_stable_sample_bag_keeps_global_once_and_is_instantaneous(self) -> None:
        collector = generate_report.collector_for_project(
            "二氯甲烷", "定点", self.collector_index, self.rule_index, self.rules
        )
        parameters = generate_report.sampling_parameters(
            "二氯甲烷",
            "定点",
            collector["collector"],
            bool(collector["supports_individual"]),
            collector["flow_rate"],
            "3",
            "固定",
            "8h",
            "定期检测",
            self.rules,
            self.rule_index[generate_report.normalize_lookup("二氯甲烷")],
            workstation_count="1",
        )
        result = generate_report.apply_collector_sampling_capabilities(
            parameters, collector, "固定", "①", self.rules
        )
        self.assertEqual("1", result["times_per_day"])
        self.assertEqual("/", result["sampling_time"])

    def test_overall_time_falls_back_to_shift_schedule(self) -> None:
        self.assertEqual(
            "8h",
            parse_pdf.overall_representative_time(
                {"daily_exposure": "", "work_time": "8:00-12:00,13:30-17:30"}
            ),
        )

    def test_expected_sampling_time_uses_one_common_normalized_shift(self) -> None:
        rows = [
            {"project_raw": "噪声", "work_time": "8：00-12：0013:30-17:30"},
            {"project_raw": "甲苯", "work_time": "8:00-12:00,13:30-17:30（8,6,48）"},
            {"project_raw": "/", "work_time": "9:00-12:00,13:00-18:00"},
        ]
        self.assertEqual(
            "8:00-12:00，13:30-17:30",
            parse_pdf.expected_sampling_time(rows),
        )

    def test_expected_sampling_time_rejects_multiple_detected_shifts(self) -> None:
        rows = [
            {"project_raw": "噪声", "work_time": "8:00-12:00,13:30-17:30"},
            {"project_raw": "甲苯", "work_time": "7:30-11:30,13:30-17:30"},
        ]
        self.assertEqual("", parse_pdf.expected_sampling_time(rows))
        missing = parse_pdf.build_missing_fields(
            {
                "detection_task_no": "任务1",
                "unit_name": "测试公司",
                "contact": "张三13800000000",
                "address": "测试地址",
                "detection_type": "定期检测",
                "expected_sampling_time": "",
            },
            rows,
            ["噪声", "甲苯"],
        )
        self.assertIn("header.expected_sampling_time", missing)

    def test_equipment_rows_drive_fixed_point_count(self) -> None:
        equipment = [
            {
                "name": "裁断机",
                "running_count": "4",
                "workplace": "车间",
                "position": "裁断工",
            }
        ]
        count, source = parse_pdf.workstation_context(
            "车间", "裁断工", "裁断工位", equipment
        )
        self.assertEqual("4", count)
        self.assertIn("裁断机", source)
        self.assertEqual(
            "2",
            generate_report.points_per_day(
                "1", "定点", self.rules["sampling"], count
            ),
        )

    def test_target_selects_matching_equipment_within_mobile_position(self) -> None:
        equipment = [
            {"name": "磨床", "running_count": "1", "workplace": "车间", "position": "维修工"},
            {"name": "车床", "running_count": "1", "workplace": "车间", "position": "维修工"},
        ]
        count, source = parse_pdf.workstation_context(
            "车间", "维修工", "车床工位", equipment
        )
        self.assertEqual("1", count)
        self.assertIn("车床", source)
        self.assertNotIn("磨床", source)

    def test_supporting_survey_table_parser_keeps_page_continuations(self) -> None:
        tables = [
            [
                ["原辅材料名称", "年用量", "物理状态", "主要成分", "使用的工作场所", "使用岗位"],
                ["胶水", "1t", "液态", "甲苯", "车间", "刷胶工"],
            ],
            [
                ["清洗水", "2t", "液态", "正己烷", "车间", "清洁工"],
                ["注：以下为说明"],
            ],
        ]
        supporting = parse_pdf.parse_supporting_survey_tables(tables)
        self.assertEqual(["胶水", "清洗水"], [row["name"] for row in supporting["materials"]])

    def test_manual_multiworker_point_requests_workstation_count(self) -> None:
        source = {
            "job_group_id": "overall:0",
            "job_workplace": "车间",
            "job_representative_time": "8h",
            "workplace": "车间",
            "position": "装配工",
            "people_per_shift": "5",
            "workstation_count": "1",
            "workstation_count_source": "岗位接触表列出1个明确工位",
            "job_type": "固定",
            "target": "装配工位",
            "project": "噪声",
            "exposure_type": "①",
            "representative_time": "8h",
        }
        _, missing = generate_report.build_table3(
            [source], self.collector_index, self.rule_index, "定期检测", self.rules
        )
        self.assertIn("Table3 车间 装配工 相同工位数量", missing)

    def test_component_report_replaces_sample_placeholder(self) -> None:
        parsed = {
            "projects": ["噪声", "蓝光胶水（取样分析）"],
            "table3": [
                {"position": "成型工", "project": "蓝光胶水（取样分析）"}
            ],
        }
        component_payload = {
            "samples": [
                {
                    "sample_name": "蓝光胶水",
                    "components": [
                        {"name": "乙酸甲酯"},
                        {"name": "正丁醛"},
                        {"name": "甲苯"},
                        {"name": "其他烃类化合物"},
                    ],
                }
            ]
        }
        missing = generate_report.replace_component_placeholders(
            parsed,
            component_payload,
            self.rules,
        )
        self.assertEqual([], missing)
        self.assertEqual(["噪声", "乙酸甲酯", "正丁醛", "甲苯"], parsed["projects"])
        self.assertEqual(
            ["乙酸甲酯", "正丁醛", "甲苯"],
            [row["project"] for row in parsed["table3"]],
        )

    def test_parenthetical_isomer_name_uses_rule_data_without_alias(self) -> None:
        normalized = generate_report.normalize_lookup("戊烷（全部异构体）")
        self.assertEqual("戊烷", normalized)
        self.assertEqual(
            "GBZ/T 300.60—2017",
            self.rule_index[normalized]["basis"],
        )
        collector = generate_report.collector_for_project(
            "戊烷（全部异构体）",
            "定点",
            self.collector_index,
            self.rule_index,
            self.rules,
        )
        self.assertEqual("活性炭管，溶剂解吸型", collector["collector"])
        self.assertEqual("防爆大气采样器QC-4S", collector["device"])
        self.assertEqual(
            "正戊烷、异戊烷",
            generate_report.display_project_name(
                "戊烷（全部异构体）",
                self.rule_index,
            ),
        )

    def test_fixed_stable_chemical_uses_individual_sample_only(self) -> None:
        source = {
            "job_group_id": "overall:0",
            "job_workplace": "车间",
            "job_representative_time": "8h",
            "source_job_type": "固定作业",
            "job_type_inference_reason": "",
            "workplace": "车间",
            "position": "操作工",
            "people_per_shift": "3",
            "job_type": "固定",
            "target": "操作工位",
            "project": "甲苯",
            "exposure_type": "①",
            "representative_time": "8h",
        }
        rows, missing = generate_report.build_table3(
            [source],
            self.collector_index,
            self.rule_index,
            "定期检测",
            self.rules,
        )
        self.assertEqual([], missing)
        self.assertEqual(1, len(rows))
        self.assertEqual("个体", rows[0]["sampling_mode"])
        self.assertEqual("劳动者", rows[0]["target"])
        self.assertEqual("2", rows[0]["points_per_day"])

    def test_full_shift_multi_target_details_infer_mobile_job(self) -> None:
        overall = {
            "workplace": "生产车间",
            "position": "维修工",
            "job_type": "固定作业",
            "daily_exposure": "8.00",
            "work_time": "7:30-11:30,13:30-17:30",
        }
        details = [
            {"workplace": "生产车间", "position": "维修工", "target": target, "duration": duration}
            for target, duration in (
                ("磨床工位", "1h"),
                ("车床工位", "2h"),
                ("钻床工位", "2h"),
                ("铣床工位", "3h"),
            )
        ]
        context = parse_pdf.inferred_job_context(0, overall, details, [overall])
        self.assertEqual("固定作业", context["source_job_type"])
        self.assertEqual("流动作业", context["job_type"])
        self.assertIn("工位时长合计8h", context["job_type_inference_reason"])


if __name__ == "__main__":
    unittest.main()
