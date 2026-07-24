# 报告核验工具

这是一个 JSON 配置驱动的通用报告核验工具。当前示例只读提取 `data/hongmei` 中的四份来源文件，并按目标职业卫生报告内的 60 条批注逐条核验。程序不会修改输入文件，执行前后会比较 SHA-256。

```bash
python3 -m venv .venv
.venv/bin/pip install -r report-verify/requirements.txt
.venv/bin/python report-verify/scripts/verify.py verify \
  --config report-verify/configs/hongmei.json
```

退出码：`0` 全部通过，`1` 存在失败，`2` 提取错误，`3` 自动检查无失败但仍需人工核验。

工具本身不包含企业名、文件名、表序号、人员、阈值或项目数据。每个项目通过一个 JSON 配置声明输入文档、提取方式、JSON 选择器和批注规则；核验阶段只读取已经生成的 JSON 文件。

Markdown 报告仅展开失败、待人工核验、来源错误和无规则项；通过项只计入汇总，不逐条展示。完整逐项结果保留在 JSON 中。

配置由三部分组成：

- `documents`：输入文件、通用提取器类型和 JSON 输出名。
- `selectors`：从提取 JSON 中选择表格、区段、字段、正则结果或工作簿单元格。
- `rules`：按批注 ID 声明比较器、公式参数、允许值及结果消息。问题定位信息也在规则中配置：`report_location` 指明检测报告小节，`basis` 指明来源文档及原始表/字段，`problem_origin` 说明哪项原始资料未被正确处理或缺少何种依据。

`basis` 中使用 `document` 引用 `documents` 的文档键。执行时会从提取 JSON 的 `source` 字段解析真实文件名，报告不会显示输入文件的绝对路径。对于尚未提供的资料，可用 `file` 直接写明资料名称并标注“未提供”。

新增企业时只新增配置文件，不修改 `report-verify/scripts` 中的通用代码。
