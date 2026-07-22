# 调查表审核指南

在编辑 JSON 前完整阅读本指南。可参考 `reviewed-json-template.json` 的完整可运行示例。

## 目标格式

reviewed JSON 使用 UTF-8，不写注释。所有单元格值都是字符串，包括人数、设备数和小时数。未知值写 `""`；PDF明确表示无此项时才写 `"/"`。

顶层保留：

```json
{
  "header": {},
  "survey_tables": {
    "basic_info": [],
    "materials": [],
    "products": [],
    "equipment": [],
    "protection_facilities": [],
    "ppe": [],
    "overall_exposure": [],
    "detail_exposure": [],
    "attachments": []
  }
}
```

9个 `survey_tables` 数组必须全部存在。不要维护 `projects`、`table3`、`missing_fields` 和 `review_status`；生成命令会重新计算。

## header

必须保留以下6个字符串字段：

- `detection_task_no`：检测任务编号
- `unit_name`：用人单位名称
- `contact`：联系人及电话
- `address`：单位地址
- `detection_type`：检测类型
- `expected_sampling_time`：预计采样时间

时间使用半角冒号和连字符，多个时段用中文逗号，例如 `8:00-12:00，13:30-17:30`。

## 普通表格

下列数组中的每一项都是对象；字段必须全部保留，未知值写空字符串。

- `materials`：`name`、`annual_use`、`physical_state`、`components`、`workplace`、`position`
- `products`：`name`、`annual_output`、`physical_state`、`packaging`
- `equipment`：`name`、`model`、`total_count`、`running_count`、`workplace`、`position`、`layout`
- `protection_facilities`：`workplace`、`target`、`name`、`type`、`total_count`、`running_count`、`notes`
- `ppe`：`classification`、`category`、`manufacturer`、`model`、`workplace`、`position`、`replacement_cycle`、`wearing_status`、`notes`

`basic_info` 和 `attachments` 只保留解析结果，不要补充推断内容。

## 岗位接触表

`overall_exposure` 是二维字符串数组。每行严格保留15列或16列，不能改成对象或调整顺序：

```text
0 工作场所          8 危害因素
1 岗位/工种         9 危害来源
2 班制             10 接触类型
3 总人数           11 日接触时间
4 每班人数         12 周工作天数
5 工作时间         13 周接触时间
6 作业类型         14 代表性劳动者（15列）
7 工位与工作内容    14 劳动强度、15 代表性劳动者（16列）
```

规范示例：

```json
[
  "加油区、卸油区、营业厅",
  "加油工",
  "三班制",
  "5",
  "2",
  "8:00-16:00，16:00-0:00，0:00-8:00",
  "流动作业",
  "加油工位加油、卸油工位卸油、营业厅收银",
  "苯、甲苯、溶剂汽油、高温",
  "原料、环境",
  "②",
  "8.00",
  "6.00",
  "48.00",
  "Ⅰ级",
  "刘燕霞"
]
```

## 详细接触表

`detail_exposure` 也是二维字符串数组。续行依靠列数继承首行的劳动者、场所和岗位，不要统一补成9列。

- 9列首行：劳动者、工作场所、岗位、触发条件、工位、动作、危害因素、时长、频次。
- 7列续行：空占位格、触发条件、工位、动作、危害因素、时长、频次；第0列必须为 `""`。
- 6列续行：触发条件、工位、动作、危害因素、时长、频次。
- 5列续行：触发条件、工位、动作、危害因素、时长。

```json
[
  ["刘燕霞", "加油区、卸油区、营业厅", "加油工", "加油时", "加油工位", "加油", "苯、甲苯、溶剂汽油", "6h", "不定时、间断加油"],
  ["", "卸油时", "卸油工位", "卸油", "苯、甲苯、溶剂汽油、高温", "0.5h", "不定时、间断卸油"]
]
```

## 必须检查的问题

1. 将全角冒号、粘连时段和混用分隔符规范为统一时间格式。
2. 将粘连的场所—工位—动作拆成完整语义对，例如把`加油工位加油卸油工位卸油营业厅收银`改成`加油工位加油、卸油工位卸油、营业厅收银`。
3. 多值统一用`、`，但不能拆开`二甲苯（全部异构体）`等括号内容。
4. 清空7列详细续行的第0列，删除窜入其中的上一行文字。
5. 删除`七、其他附件`、`搜索复制翻译`等PDF页脚或界面噪声，保留同格真实数据。
6. 核对固定/流动作业、总体行与详细行、总人数与每班人数、设备总数与运行数；没有PDF证据时不要改值。
7. `某材料（取样分析）`在没有组分报告时必须保留，不能猜测化学组分。

## 提交审核

保存为新的 reviewed JSON 后运行生成命令。若门禁报错，按错误路径定位字段并继续修正，直到通过。成功后程序会自动重建检测项目、采样行、工位数量来源和缺失字段。
