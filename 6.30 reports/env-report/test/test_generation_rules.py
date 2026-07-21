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
import build_oel_database  # noqa: E402
import build_physical_factor_database  # noqa: E402


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
        cls.oel_index = generate_report.load_oel_index(
            ROOT / "knowledge" / "oel_limits.json"
        )
        cls.physical_factor_index = generate_report.load_physical_factor_index(
            ROOT / "knowledge" / "physical_factors.json"
        )
        parse_pdf.PARSING_RULES = cls.rules["parsing"]

    def test_limit_type_is_derived_from_gbz_oels_and_sampling_mode(self) -> None:
        cases = [
            ("甲苯", "定点", "PC-STEL"),
            ("甲苯", "个体", "PC-TWA"),
            ("甲醛", "定点", "MAC"),
            ("二异丁基甲酮", "定点", "PE"),
            ("二异丁基甲酮", "个体", "PC-TWA"),
            ("其他粉尘", "定点", "PE"),
            ("其他粉尘", "个体", "PC-TWA"),
        ]
        for project, sampling_mode, expected in cases:
            with self.subTest(project=project, sampling_mode=sampling_mode):
                rule = self.rule_index[generate_report.normalize_lookup(project)]
                self.assertEqual(
                    expected,
                    generate_report.limit_type_for(
                        project,
                        sampling_mode,
                        rule["collector"],
                        True,
                        self.rules,
                        rule,
                        self.oel_index,
                    ),
                )

    def test_physical_factor_limit_type_uses_slash_without_missing_oel(self) -> None:
        source = {
            "job_group_id": "overall:0",
            "job_workplace": "生产车间",
            "job_representative_time": "8h",
            "workplace": "生产车间",
            "position": "操作工",
            "people_per_shift": "1",
            "workstation_count": "1",
            "job_type": "固定",
            "target": "设备工位",
            "project": "噪声",
            "exposure_type": "②",
            "representative_time": "8h",
        }
        rows, missing = generate_report.build_table3(
            [source],
            self.collector_index,
            self.rule_index,
            "定期检测",
            self.rules,
            self.oel_index,
        )
        self.assertEqual([], missing)
        self.assertEqual(1, len(rows))
        self.assertEqual("/", rows[0]["limit_type"])

    def test_all_gbz_22_factor_names_and_aliases_use_slash_limit_type(self) -> None:
        factor_names = json.loads(
            (ROOT / "knowledge" / "physical_factors.json").read_text(encoding="utf-8")
        )
        chemical_rule = {"category": "chemical", "collector": "活性炭管"}
        for project in factor_names:
            with self.subTest(project=project):
                self.assertTrue(
                    generate_report.is_physical_factor(
                        project,
                        chemical_rule,
                        self.physical_factor_index,
                    )
                )
                self.assertEqual(
                    "/",
                    generate_report.limit_type_for(
                        project,
                        "定点",
                        "活性炭管",
                        True,
                        self.rules,
                        chemical_rule,
                        self.oel_index,
                    ),
                )

    def test_physical_factor_format_variants_match_without_false_chemical_hit(self) -> None:
        for project in (
            "1HZ～100KHZ电场",
            "噪声（稳态）",
            "WBGT（湿球黑球温度）",
            "紫外线(人工紫外辐射)",
        ):
            with self.subTest(project=project):
                self.assertTrue(generate_report.is_physical_factor(project))
        self.assertFalse(generate_report.is_physical_factor("甲苯"))

    def test_gbz_22_alias_without_rule_is_not_reported_as_missing_oel(self) -> None:
        source = {
            "job_group_id": "overall:0",
            "job_workplace": "焊接车间",
            "job_representative_time": "8h",
            "workplace": "焊接车间",
            "position": "焊工",
            "people_per_shift": "1",
            "workstation_count": "1",
            "job_type": "固定",
            "target": "焊接工位",
            "project": "电焊弧光",
            "exposure_type": "②",
            "representative_time": "8h",
        }
        rows, missing = generate_report.build_table3(
            [source],
            self.collector_index,
            self.rule_index,
            "定期检测",
            self.rules,
            self.oel_index,
        )
        self.assertEqual([], missing)
        self.assertEqual("/", rows[0]["limit_type"])
        self.assertEqual("定点", rows[0]["sampling_mode"])

    def test_committed_physical_factor_database_matches_gbz_22_source(self) -> None:
        committed = json.loads(
            (ROOT / "knowledge" / "physical_factors.json").read_text(encoding="utf-8")
        )
        rebuilt = build_physical_factor_database.build_database(
            ROOT / "knowledge" / "物理危害.md"
        )
        self.assertEqual(committed, rebuilt)

    def test_oel_lookup_ignores_chinese_english_and_mixed_parentheses(self) -> None:
        base = generate_report.normalize_lookup("碳酰氯")
        for variant in (
            "碳酰氯(光气)",
            "碳酰氯（光气）",
            "碳酰氯（光气)",
            "碳酰氯(光气）",
            "碳酰氯((光气))",
        ):
            with self.subTest(variant=variant):
                self.assertEqual(base, generate_report.normalize_lookup(variant))
                self.assertEqual(
                    {"MAC"},
                    generate_report.oel_limit_types(variant, self.oel_index),
                )
        self.assertEqual(
            {"MAC"},
            generate_report.oel_limit_types("碳酰氯", self.oel_index),
        )

    def test_oel_lookup_handles_unbalanced_nested_source_parentheses(self) -> None:
        source_name = "二氯二苯基三氯乙烷((滴滴涕,DDT)"
        bare_name = "二氯二苯基三氯乙烷"
        self.assertEqual(
            generate_report.normalize_lookup(bare_name),
            generate_report.normalize_lookup(source_name),
        )
        self.assertEqual(
            generate_report.oel_limit_types(source_name, self.oel_index),
            generate_report.oel_limit_types(bare_name, self.oel_index),
        )

    def test_gbz_database_never_defines_mac_and_pc_stel_together(self) -> None:
        unique_entries = {id(entry): entry for entry in self.oel_index.values()}.values()
        for entry in unique_entries:
            limit_types = set(entry["limit_types"])
            self.assertFalse(
                {"MAC", "PC-STEL"} <= limit_types,
                entry["project"],
            )

    def test_committed_oel_database_matches_markdown_source(self) -> None:
        committed = json.loads(
            (ROOT / "knowledge" / "oel_limits.json").read_text(encoding="utf-8")
        )
        rebuilt = build_oel_database.build_database(
            ROOT / "knowledge" / "化学有害因素.md"
        )
        self.assertEqual(committed, rebuilt)

    def test_dust_enumeration_expands_but_condition_does_not(self) -> None:
        database = json.loads(
            (ROOT / "knowledge" / "oel_limits.json").read_text(encoding="utf-8")
        )
        for project in (
            "人造矿物纤维绝热棉粉尘",
            "玻璃棉粉尘",
            "矿渣棉粉尘",
            "岩棉粉尘",
        ):
            self.assertEqual(["PC-TWA"], database[project])
        self.assertEqual(["PC-TWA"], database["滑石粉尘"])
        self.assertNotIn("滑石粉尘(游离 SiO2含量<10%)", database)
        self.assertNotIn("游离 SiO2含量<10%", database)

    def test_semantic_parenthetical_aliases_are_expanded(self) -> None:
        database = json.loads(
            (ROOT / "knowledge" / "oel_limits.json").read_text(encoding="utf-8")
        )
        alias_groups = (
            ("碳酰氯", "光气"),
            ("甲乙酮", "2-丁酮", "丁酮"),
            ("二氯二苯基三氯乙烷", "滴滴涕", "DDT"),
            ("沉淀SiO2", "白炭黑", "白炭黑粉尘"),
            ("大理石粉尘", "碳酸钙", "碳酸钙粉尘"),
            ("三氧化铬、铬酸盐、重铬酸盐", "三氧化铬", "铬酸盐", "重铬酸盐"),
            ("铝金属、铝合金粉尘", "铝金属粉尘", "铝合金粉尘"),
        )
        for aliases in alias_groups:
            expected = database[aliases[0]]
            for alias in aliases[1:]:
                self.assertEqual(expected, database[alias], alias)

    def test_structural_parentheses_are_preserved(self) -> None:
        database = json.loads(
            (ROOT / "knowledge" / "oel_limits.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            ["PC-TWA", "PC-STEL"],
            database["双(巯基乙酸)二辛基锡"],
        )
        self.assertNotIn("双二辛基锡", database)

    def test_mac_only_factor_does_not_create_an_individual_twa_row(self) -> None:
        source = {
            "job_group_id": "overall:0",
            "job_workplace": "甲醛车间",
            "job_representative_time": "8h",
            "workplace": "甲醛车间",
            "position": "操作工",
            "people_per_shift": "1",
            "workstation_count": "1",
            "job_type": "固定",
            "target": "甲醛工位",
            "project": "甲醛",
            "exposure_type": "①",
            "representative_time": "8h",
        }
        rows, missing = generate_report.build_table3(
            [source],
            self.collector_index,
            self.rule_index,
            "定期检测",
            self.rules,
            self.oel_index,
        )
        self.assertEqual([], missing)
        self.assertEqual(1, len(rows))
        self.assertEqual("定点", rows[0]["sampling_mode"])
        self.assertEqual("MAC", rows[0]["limit_type"])

    def test_twa_only_factor_uses_pe_for_point_and_twa_for_individual(self) -> None:
        source = {
            "job_group_id": "overall:0",
            "job_workplace": "涂布车间",
            "job_representative_time": "8h",
            "workplace": "涂布车间",
            "position": "操作工",
            "people_per_shift": "1",
            "workstation_count": "1",
            "job_type": "固定",
            "target": "涂布工位",
            "project": "二异丁基甲酮",
            "exposure_type": "②",
            "representative_time": "8h",
        }
        rows, missing = generate_report.build_table3(
            [source],
            self.collector_index,
            self.rule_index,
            "定期检测",
            self.rules,
            self.oel_index,
        )
        self.assertEqual([], missing)
        self.assertEqual(
            {("定点", "PE"), ("个体", "PC-TWA")},
            {(row["sampling_mode"], row["limit_type"]) for row in rows},
        )

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
        self.assertEqual(
            "1F开料车间开料工位、2F生产车间粘膜工位、2F生产车间过膜工位",
            individual[0]["workplace"],
        )
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
            "GBZ/T300.60—2017",
            self.rule_index[normalized]["basis"].replace(" ", ""),
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
            "解吸液:二硫化碳",
            self.rule_index[normalized]["analysis_group"],
        )
        self.assertEqual(
            "戊烷（全部异构体）",
            generate_report.display_project_name(
                "戊烷（全部异构体）",
                self.rule_index,
            ),
        )

    def test_project_flow_rate_uses_time_type_from_rule_data(self) -> None:
        rule = self.rule_index[generate_report.normalize_lookup("环己酮")]
        for mode, time_type, expected in (
            ("定点", "短时间", "0.3"),
            ("个体", "长时间", "0.05"),
        ):
            with self.subTest(mode=mode):
                self.assertEqual(
                    expected,
                    generate_report.flow_rate_for_project(
                        "环己酮", mode, time_type, self.rule_index, "wrong"
                    ),
                )
        self.assertEqual(
            "15~40",
            generate_report.flow_rate_for_project(
                "其他粉尘", "定点", "短时间", self.rule_index, "wrong"
            ),
        )

    def test_different_analysis_treatments_do_not_merge(self) -> None:
        rule_index = {
            "苯": {
                **self.rule_index["苯"],
                "analysis_group": "解吸液:二硫化碳",
            },
            "戊烷": {
                **self.rule_index["戊烷"],
                "analysis_group": "解吸液:含甲醇的溶液",
            },
        }
        sources = [
            {
                "job_group_id": "overall:0",
                "job_workplace": "车间",
                "job_representative_time": "8h",
                "workplace": "车间",
                "position": "操作工",
                "people_per_shift": "1",
                "workstation_count": "1",
                "job_type": "固定",
                "target": "操作工位",
                "project": project,
                "exposure_type": "②",
                "representative_time": "8h",
            }
            for project in ("苯", "戊烷")
        ]
        rows, _missing = generate_report.build_table3(
            sources,
            self.collector_index,
            rule_index,
            "定期检测",
            self.rules,
            self.oel_index,
        )
        self.assertFalse(any("、" in row["project"] for row in rows))

    def test_mobile_work_content_keeps_activity_and_short_final_detail_row(self) -> None:
        self.assertEqual(
            "加油工位加油、卸油工位卸油、营业厅收银",
            parse_pdf.detail_work_content(
                "加油工位/卸油工位；营业厅",
                "加油、卸油\n收银",
            ),
        )
        self.assertEqual(
            ["加油工位", "卸油工位", "营业厅收银"],
            parse_pdf.sampling_targets(
                "加油工位加油，卸油工位卸油;营业厅收银"
            ),
        )
        self.assertEqual(
            ["加油工位", "卸油工位", "营业厅"],
            parse_pdf.sampling_targets("加油工位/卸油工位；营业厅"),
        )
        self.assertEqual(
            ["CNC工位"],
            parse_pdf.sampling_targets("CNC工位/操作CNC"),
        )
        raw_details = [
            [
                "刘燕霞",
                "加油区、卸油区、营业厅",
                "加油工",
                "加油时",
                "加油工位",
                "加油",
                "苯",
                "6h",
                "间断加油",
            ],
            ["续页干扰文字", "收银时", "营业厅", "收银", "/", "1.5h", "间断收银"],
            ["卸油时", "卸油工位", "卸油", "苯、高温", "0.5h"],
        ]
        details = parse_pdf.parse_detail_rows(raw_details)
        self.assertEqual(3, len(details))
        overall = {
            "workplace": "加油区、卸油区、营业厅",
            "position": "加油工",
            "people_per_shift": "2",
            "work_time": "8:00-16:00",
            "job_type": "流动作业",
            "target": "加油工位加油卸油工位卸油营业厅收银",
            "project_raw": "苯、高温",
            "exposure_type": "②",
            "daily_exposure": "8.00",
        }
        rows = parse_pdf.build_table3([overall], details)
        self.assertEqual(
            {("加油区", "加油工位"), ("卸油区", "卸油工位")},
            {(row["workplace"], row["target"]) for row in rows},
        )
        self.assertEqual(
            {"加油工位加油、卸油工位卸油、营业厅收银"},
            {row["job_work_content"] for row in rows},
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
