# MVP 0.1 开发决策记录

日期：2026-10-12。依据为同目录归档的四份新设计文档与既有 Foundation 技术约束。

## 工作编号与已有成果

新 Track A/B/C 分别指 Frontend/Platform/Runtime；原 POC A/B/C 分别指数据中台/Harness/孪生仿真。使用功能目录和 `MVP-RUNTIME` 标识避免字母混淆，原任务书和状态证据原样保留。用户确认其他成果在学弟电脑上，本机以“待接收、待核验”记录，不根据新文档的起点描述替他们判定 PASS。

## Runtime 与平台任务分离

原 B 的 SQLite TaskStore 是独立验证和演示已有实现，继续保留。本次不把该状态机带进新 Runtime；新 Adapter 只关联外部 task_id 与 execution_id，保留当前进程的执行事实及去重。Task 排队、持久化、审批、重启恢复、Event 与 WebSocket 由 Platform 负责。

## 能力目录与底层插件机制

Runtime 应用层仅提供 capability_id/version → Provider 的薄映射，负责冲突拒绝、发现与统一调用错误。它不实现 Agent Loop、动态插件加载器、热更新或另一个调度框架。官方脑路径继续复用已验证的 Harness/Cordis 工具注册、guard 和审计；确定性路径通过进程 Adapter 调用完全相同的 B 纯业务库。Inventory/Equipment/Data Contract 的具体实现仅在 composition root 导入，调用方依赖能力语义。

## 版本与许可证

继续固定 Harness commit `183f08e9c6dde7e36cd2318eaee70b0da08fb35e` / SDK `0.1.5rc1` / sdk-minimal。该版本是已有 POC 的预发布开发基线，不作为生产稳定性批准。此次不自动追随新 alpha/rc 版本，升级须单独核对 Adapter、插件 API、Profile、依赖与许可。数据校验采用固定版本 Pydantic/JSON Schema；依赖与许可证记录见 `../track-runtime/open_source_review.md`。

## 当前源数据与目标 ID

原 8 场景 fixture 原样复制，摘要仍为 `f86cf24391997655c70f4405a1335ea0d6cf346422f2b3f2749e7428a30f0290`。WH-001 是首个联合演示的仓库对象引用；源数据内的 L1/L2 位置 ID 保留，不据此改写原业务数据。当前计算沿用工厂级 Mock 截面和跨层备料检查，尚未建立完整的仓库归属领域模型。仓库/批次映射由两方实际数据契约对齐时细化。

## 接口字段细化

当前 `shared/contracts` 是四份规范概念的 Runtime 实施版，供另外两方接入确认。CapabilityRef 采用 capability_id/version；执行状态采用 COMPLETED/FAILED；ErrorEnvelope 带 refs。EventEnvelope 提供 timestamp_utc、refs、schema_version，不同时维护冲突的顶层 task_id 副本。此版本不等于三方已完成联合冻结，不覆盖旧 foundation.*.v1 契约。

Data Contract 的两份样例仅验证旧 `state` → 新 `factory_state` 的机制；不冻结企业全量 Schema。Live/Simulation 域标识分别返回，所有当前 ExecutionResult 的 state_effects 为空。Node 工具执行的是审计过的固定源码，不运行模型生成代码；生成代码隔离要求保留在原 B5 和未来 Sandbox Provider 边界。

## Runtime 可视化交付入口

2026-10-12：新增临时 Runtime 验证面板，复用既有 Foundation 工作台的 React/FastAPI 环境，不新增产品框架或 Agent Loop。浏览器只调用工作台后台；后台通过标准 HttpRuntimeClient 调用 18342 的独立 Runtime。执行输入从不可变 Mock fixture 构造，工作台不实现新的业务 Task 状态机、不改变 Factory State。

可共享的工作台源码保存在 `demos/foundation-workbench`，原本机 `Foundation/app` 继续为运行入口。该目录是临时交付展示与接入参考，Frontend/Platform 正式源码仍待两位学弟提供。只保留本页会话历史、Runtime 进程内查询，以及工作台最近 32 次实际返回的临时导出快照；没有跨进程恢复或平台 Task 持久化承诺。无响应明确显示结果未确认；无效契约保留实际 FAILED 与错误 Trace。共享协议和正式 Integration Gate 不因此改写。
