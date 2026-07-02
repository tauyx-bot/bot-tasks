# 定时任务 OpenAPI 暴露计划（基于 claw websocket 现有能力）

## Summary

- 目标：把 claw 中现有的任务/定时任务 websocket 能力通过 `apps/server` 的 `/openapi/v1` 暴露出来，采用 TDD 顺序：先补 e2e 契约测试，再补 OpenAPI spec/unit 断言，最后实现 server 侧代理与 DTO 映射。
- 数据源：不在 server 建任务主表；定时任务定义与运行记录都以 claw websocket RPC 为准。
- 能力边界：
  - 生命周期管理主走 `tego.cron.*`
  - 运行态任务注册表是 `tasks.*`
  - 本期不新造任务域，只做现有内部能力外露与字段投影
- 认证：继续使用 OpenAPI API key + impersonated user。
- 资源归属：任务归属于目标 `avatarId` 对应的 claw；“归属 Agent”优先取 `agentId`，无值时按 avatar 维度投影。

## 现状校准

- `tasks.*` 已存在于 claw websocket 协议：
  - `tasks.list`
  - `tasks.get`
  - `tasks.cancel`
  - 作用是任务运行注册表 / workboard 生命周期，不是定时任务维护面。
- `tego.cron.*` 已存在于 claw websocket 协议：
  - `tego.cron.status`
  - `tego.cron.list`
  - `tego.cron.add`
  - `tego.cron.update`
  - `tego.cron.run`
  - `tego.cron.remove`
  - `tego.cron.runs`
- 协议字段已覆盖需求主体：
  - `ConsoleCronJob` 提供任务定义、`enabled`、`schedule`、`agentId`、最近运行状态摘要
  - `CronRunLogEntry` 提供运行记录、成功/失败、失败原因、summary

## 文档方案

- OpenAPI 自描述文档：
  - 在 `src/openapi/app.ts` 中新增 `Tasks` tag 的中英文说明。
  - 明确这是“server 代理 claw websocket RPC”的外部 HTTP 契约，不是 server 本地持久化资源。
  - 对每个端点标注其内部映射：
    - 创建 -> `tego.cron.add`
    - 编辑/停用/启用 -> `tego.cron.update`
    - 删除 -> `tego.cron.remove`
    - 单次触发 -> `tego.cron.run`
    - 查询 -> `tego.cron.list` + `tego.cron.runs`
- 契约稳定性文档：
  - 通过 `src/tests/unit/openapi-spec.test.ts` 固化任务路径、operationId、tag、Problem 错误模型引用、双语文案关键字。
- 工程说明：
  - 在计划文件中记录内部能力映射。
  - 实现完成后补一份短文档，说明 claw 协议、字段投影规则、错误映射、权限约束。

## Public API / Contract

- 新增 Tag：`任务` / `Tasks`
- 新增 scope：
  - `tasks:read`：允许查询当前用户可见 avatar 上的定时任务及最近运行结果
  - `tasks:write`：允许创建、编辑、停用/启用、删除、单次触发
- 新增端点：
  - `POST /openapi/v1/avatars/{avatarId}/tasks`
    - 内部映射 `tego.cron.add`
  - `GET /openapi/v1/avatars/{avatarId}/tasks`
    - 内部映射 `tego.cron.list`
    - 必要时按 job id 批量补 `tego.cron.runs`
  - `GET /openapi/v1/avatars/{avatarId}/tasks/{taskId}`
    - 内部映射 `tego.cron.list` 过滤单项，或 `tego.cron.runs` 补最近执行记录
  - `PATCH /openapi/v1/avatars/{avatarId}/tasks/{taskId}`
    - 内部映射 `tego.cron.update`
  - `DELETE /openapi/v1/avatars/{avatarId}/tasks/{taskId}`
    - 内部映射 `tego.cron.remove`
  - `POST /openapi/v1/avatars/{avatarId}/tasks/{taskId}/pause`
    - 内部映射 `tego.cron.update({ enabled: false })`
  - `POST /openapi/v1/avatars/{avatarId}/tasks/{taskId}/resume`
    - 内部映射 `tego.cron.update({ enabled: true })`
  - `POST /openapi/v1/avatars/{avatarId}/tasks/{taskId}/trigger`
    - 内部映射 `tego.cron.run`
- 外部 DTO 投影规则：
  - `taskId` -> `ConsoleCronJob.id`
  - `taskName` -> `ConsoleCronJob.name`
  - `taskContent` -> 从 `payload` 提取：
    - `agentTurn.message`
    - 或 `systemEvent.text`
  - `frequency` -> `schedule` 格式化字符串或结构化字段
  - `agent` -> `agentId`，无值时返回 `null`
  - `status`：
    - `enabled=true` -> `active`
    - `enabled=false` -> `paused`
  - `lastRunAt` -> `state.lastRunAtMs`
  - `lastRunResult`：
    - `ok` -> `success`
    - `error` -> `failed`
    - `skipped` -> `skipped`
  - `lastRunFailureReason` -> `state.lastError` 或最近一条 run 的 `error`
  - `executionStatus`：
    - `state.runningAtMs` 存在 -> `running`
    - 有最近 run 且当前未运行 -> `completed`
    - 否则 -> `pending`
- 查询筛选：
  - 需求里的“生效、暂停、全部”映射到 `enabled=true/false/all`
  - OpenAPI 层负责把外部枚举转换为对 claw 返回结果的过滤，不改 claw 协议

## Implementation Changes

- 测试优先：
  - 新增独立 e2e 文件，专测任务 OpenAPI 契约。
  - e2e 红测覆盖：
    - 创建 / 编辑 / 删除
    - pause / resume
    - trigger
    - 列表过滤
    - claw RPC 错误映射
    - 无权限 / 无可见性 / 无可路由 gateway
  - 更新 `src/tests/unit/openapi-spec.test.ts` 固定任务路由、operationId、tag、Problem schema、双语说明。
- OpenAPI 层：
  - 在 `src/openapi/routes/` 新增任务路由模块。
  - 新增任务 DTO schema，但仅作为外部稳定契约，不复刻内部 claw 类型。
  - 在 `src/openapi/app.ts` 中补文档文案、tag、本地化 operation 映射。
- server 侧代理层：
  - 新增一个面向 OpenAPI 的 task/cron service，职责只有：
    - 校验 API key 与 avatar 可见性
    - 解析目标 avatar 的 gateway / claw 连接
    - 调用 websocket RPC
    - 把 claw 响应投影为 OpenAPI DTO
  - 不在 server 增加任务定义持久化表，也不新增执行记录表。
- claw RPC 适配：
  - 优先复用 `@tego/channel` 的 `GatewayClient` / 协议类型，而不是手写 websocket 协议。
  - 如果 server 侧没有现成可直接复用的连接管理器，则新增最小适配层，仅封装：
    - 连接目标 claw
    - 发送 `tego.cron.*`
    - 接收 RPC 响应
  - 对 `tego.cron.list` + `tego.cron.runs` 做组合查询，用于满足“上次执行结果 / 失败原因 / 当前执行状态”。
- 错误映射：
  - claw RPC 未连接 / gateway 不可达 -> `503 problem+json`
  - claw 返回业务错误 -> `400` 或 `409`，按现有 OpenAPI problem 语义映射
  - avatar 不可见 / 无 impersonation / scope 不足 -> `403`
  - 任务不存在 -> `404`

## Test Plan

- e2e 契约：
  - `POST /avatars/{avatarId}/tasks` 调用 `tego.cron.add` 成功并返回投影后的任务对象。
  - `GET /avatars/{avatarId}/tasks?status=active|paused|all` 正确映射 `enabled` 过滤。
  - `PATCH` 正确映射到 `tego.cron.update`。
  - `POST /pause` / `POST /resume` 正确切换 `enabled`。
  - `POST /trigger` 正确调用 `tego.cron.run` 并返回 run 投影。
  - `DELETE` 正确调用 `tego.cron.remove`。
  - 查询接口能返回最近执行时间、结果、失败原因、当前执行状态。
  - claw websocket 不可达时返回稳定的 Problem 响应。
- OpenAPI spec/unit：
  - `openapi.json` 新增任务路径、operationId、Tag、本地化说明。
  - 所有新错误响应引用 `Problem` schema。
  - 新 scope 出现在 API key schema/文档中。
- 集成验证：
  - 验证 DTO 投影规则：
    - payload -> taskContent
    - schedule -> frequency
    - `state` + `runs` -> 最近执行结果与当前执行状态

## Assumptions

- “任务全生命周期管理”在当前系统中以 `tego.cron.*` 作为唯一真实内部维护面。
- `tasks.*` 不用于定时任务 CRUD，只作为运行态任务注册表参考，不纳入本期对外主接口。
- server 不新增任务主存储，claw 是唯一事实源。
- 如果单个查询接口需要最近运行记录，本期接受 server 侧额外调用 `tego.cron.runs` 做组合投影。
