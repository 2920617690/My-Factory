# Runtime 交接给 Platform

平台以 `RuntimeClient` 调用能力，独立拥有 Task 和 Factory State。新 Runtime 不需要原 B 网页/FastAPI，也不要求任何前端运行。模块源代码位于 `runtime/`；可独立用 CLI 或本机 HTTP 服务运行。

## 一处替换 RuntimeClient

平台自己的 MockRuntimeClient 与真实 HttpRuntimeClient 均实现：

```text
execute(ExecutionRequest) → ExecutionResult
query_execution(execution_id) → execution facts
cancel_execution(execution_id) → structured unsupported error for this milestone
get_capabilities() → stable capability references
```

客户端在 `runtime/src/myfactory_runtime/client.py`，它不导入 DeepSeek SDK、Profile、Cordis 或具体 Factory Plugin。可复制这一小段 client 模块到平台 Adapter 层，也可把 runtime/src 加入 Python 包路径后使用。传入/返回都是 JSON 字典，平台的 Task Service 不依赖具体插件实现。

```python
from myfactory_runtime.client import HttpRuntimeClient
client = HttpRuntimeClient('http://127.0.0.1:18342')
result = client.execute(execution_request)
```

## ExecutionRequest 实施版

稳定字段为 schema_version=`mf.execution.v1`、task_id、execution_id、capability={capability_id,version}、target={entity_id,entity_type}、context、parameters、policy。完整样例为 `runtime/fixtures/execution-inventory.json`，JSON Schema 为 `shared/contracts/ExecutionRequest.schema.json`。

首个能力 `inventory.analyze@1.0.0`，目标 WH-001/warehouse。上下文中声明 ContractRef 与 data，样例 data 包含 warehouse_id、material_id、order_id、state_domain 和 factory_state Mock 截面。`parameters` 可以为空而使用 context.order_id，也可传单订单、2–5 订单组或单物料/需求；相互冲突的参数会拒绝。完整业务字段是样例 Contract，不代表企业全量 Schema 已冻结。

`policy.mode=deterministic` 直接调用已验证工具库；`mode=brain` 才调用官方模型。两者数值均由同一业务工具决定，返回同一个 ExecutionResult。当前真实脑路径只接受原受控模拟来源，事实不一致先失败，不带着另一份数据调用模型。

## ExecutionResult 与平台处理

返回 task_id、execution_id、target、status、output、state_effects、trace、error。状态为 COMPLETED 或 FAILED；`output.analysis` 是业务事实，`output.narrative` 仅在模型路径存在。当前库存规则是工厂级 Mock 截面核对，仓库归属模型由双方后续对齐。模型自然语言的数量和单位以工具事实为准。

每条 trace 包含 trace_id、task_id、execution_id、entity_id、capability、plugin_id/version、start/end、status 和 result/error。时间统一 UTC ISO 8601；工具原始事件另保留于实际证据 JSON。脑路径工具 trace 的 host interval 是收到已完成审计后的记录时间，guest_result_at 标明真实来宾审计返回时间，不把它宣称为 SDK 开始时间。

业务失败的 HTTP 状态仍为 200，消费方必须检查 ExecutionResult.status；传输、JSON 语法、大小或来源错误使用 HTTP 4xx 和 ErrorEnvelope。能力不存在、版本不匹配、输入校验、插件异常、官方运行错误均结构化，客户端不解析 traceback。

客户端连接失败、超时或非 JSON 响应返回 `RUNTIME_TRANSPORT_UNAVAILABLE`，details.completion_known=false；这不是一个已确认 FAILED 的 ExecutionResult。平台据此查询或对账，不把传输中断直接当作插件执行失败。

当前 state_effects 始终为空。Platform 保存 ExecutionResult、推进自己的 Task、产生 Event；本轮不会改业务库存。第二次 Gate 才接入平台验证的状态变更。Runtime 不连接 PostgreSQL、不发 WebSocket、不控制 React。

## HTTP 与生命周期

| 方法 | 路径 | 行为 |
|---|---|---|
| GET | /api/v1/health | 服务与职责状态 |
| GET | /api/v1/capabilities | 能力发现与执行模式 |
| POST | /api/v1/executions | 同步执行；平台 worker 使用，浏览器不能直接提交 |
| GET | /api/v1/executions/{execution_id} | 当前进程执行事实查询 |
| POST | /api/v1/executions/{execution_id}/cancel | 明确返回 CANCELLATION_NOT_SUPPORTED，不伪报停止 |

输入最大 1 MiB，工具执行和真实 SDK 受时限限制。HTTP 只监听 loopback，拒绝 Origin，不是正式认证/远程生产接口。当前 execution 去重与查询只在进程内有效；重启后平台持久化 Task/ExecutionResult 仍应提供权威历史。平台请求超时不能直接推断失败，需按 execution_id 对账，不盲目重发真实模型调用。

## 两版本 Data Contract 与独立验证

注册、校验、转换、精确版本解析均通过 Data Contract Provider 暴露；远程引用和任意代码表达式禁用。旧样例 `mf.mock.factory-context@0.1.0` 的 state 字段转换到 `@1.0.0` 的 factory_state，入参和出参都校验。两个版本和 Fixture 见 runtime/fixtures/mock-contracts.json。

独立运行、真实 HTTP SDK 替换和 JSON Schema 校验已通过，见 runtime/evidence/verification.json 与 http-handoff-checks.json。这个范围不代表真实 Platform Task/Event、WebSocket、Frontend 已参与。接收两方实现后，通过共享规范的 inventory_analysis_e2e 再判三方 Gate。

## 交付后的顺序

NEXT GATE：接收前端和平台源码/报告；共同确认实施版字段；Platform 仅替换 RuntimeClient，进行成功/失败任务与事件联调。后续加入上下文提供者、业务授权、持久执行协调和可取消 Provider。

LATER：State Effects、SimPy 的 Simulation State、专业算法、真实 ERP/WMS、生产沙箱、模型自主部署/替换与完整许可评审。当前没有技术 BLOCKER 阻止 Runtime 独立运行。
