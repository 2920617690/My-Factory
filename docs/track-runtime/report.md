# Runtime 阶段交付报告

日期：2026-10-12。范围为 My Factory MVP 0.1 Phase 1 Runtime 独立开发与平台交接入口。结论：**Runtime 独立 Done Definition PASS；真实 Harness Adapter 路径 PASS；完整三方系统 Integration Gate NOT_RUN。** 本次开发不依赖 Frontend/Platform，不重跑原 SDK 可行性验证，不替其他 Track 判定完成。

## 实际完成与证据

| 要求 | 当前结论 | 实际证据 |
|---|---|---|
| R0 原 POC 审计/复用 | PASS | 固定上游 commit；原纯业务工具和 8 场景 fixture 原样复制，provenance.json 与 verification.json 校验摘要 |
| R1 MyFactory Harness Adapter | PASS | official-adapter-smoke.json：经原 VM / SDK，实际完成 1 次模型回合、2 次工具调用；宿主/来宾事实核对一致 |
| R2 Plugin/Capability Registry | PASS | Inventory、Equipment、Data Contract 注册/发现/调用；重复注册和未知能力/版本拒绝；unit-tests.log |
| R3 执行协议与 Trace | PASS | 11 份引用/错误/执行/Event Schema；成功和失败均保留 task/execution/entity/plugin/capability、UTC 起止、result/error |
| R4 Data Contract | PASS | 两个版本的 Mock Contract；旧 state → 新 factory_state；入参/出参/精确版本校验，缺版本/转换/无效结果拒绝 |
| R5 Factory Mock Plugins | PASS | first-inventory.json 可用 6、需求 10、缺口 4；first-equipment.json 检查 EQ-001；五个复杂场景缺口 60→40→30→0→0，最后跨层受阻 |
| R6 两种执行路径 | PASS，库存能力范围 | deterministic 直接调用同一工具库，brain 通过官方 SDK/Cordis；两者同 ExecutionResult、实际工具数值一致；通用跨能力脑编排仍待扩展 |
| R7 Platform 交接入口 | PASS，Runtime 传输范围 | HttpRuntimeClient 与 12 项真实 HTTP 检查、JSON Schema、Query/去重/错误/Origin 拒绝；完整真实 Platform 接入未执行 |
| 状态与职责边界 | PASS，本次静态/运行范围 | Runtime 无 PostgreSQL/React/WebSocket，实现只读 Mock；state_effects 为空；TaskStore 继续留在原 POC，未迁入新 Runtime |

核心文件位于 `runtime/src/myfactory_runtime`、`runtime/plugins/poc-inventory`、`runtime/fixtures`、`runtime/tests` 与 `shared/contracts`。当前源码/文件摘要清单见 `runtime/evidence/source-manifest.json`；交付调用方式见 handoff_platform.md。

2026-10-12 Github 协作准备：origin 已指向用户新建仓库。共享源码新增 harness-assets，原样包含 SDK runner/原生插件/fixture；没有改变当前执行路径。Git 共享标准执行记录、工具 Trace 和校验摘要，完整原始 SDK 会话、本机来源清单与打包记录继续保留本机并被 Git 忽略。新增 Runtime checks 配置使用已有无模型检查；远端上传/CI 的实际状态单独记录，不改写本报告独立验收范围。

## 实际执行结果

```text
.venv/bin/python scripts/verify_runtime.py
30 tests / 0 failures / 0 errors
inventory / legacy-context / equipment: COMPLETED
public schemas: 11
tool source copy / fixture copy hash: PASS

.venv/bin/python ../tests/integration/check_runtime_transport.py
12 Runtime HTTP handoff checks: PASS

.venv/bin/python -m pip check
No broken requirements found
```

官方回合由新 Adapter 执行，task_id=TASK-001、execution_id=EXEC-BRAIN-001，原生 session_id=MF-DEMO-03c83279e81e45f7897ef2a5776f33d7；provider=DeepSeek 官方 API，model=deepseek-flash。返回实际 available=6、demand=10、shortage=4，结构化结果核对 verified=true。原始脱敏 SDK 事件/工具审计位于 `runtime/evidence/raw/official-MF-DEMO-03c83279e81e45f7897ef2a5776f33d7.json`，标准结果在 official-adapter-smoke.json。

工具 Trace 的 host interval 表示接收记录时间，guest_result_at 对应来宾审计返回时间；保留原始事件供核对，不将接收时间等同 SDK 调用开始时间。原 B 演示数据库的历史计数不包含本次直接 Adapter 回合；原验收记录保留历史范围。

## 未完成范围

BLOCKER：无阻止本机 Runtime 独立运行的技术阻塞。

NEXT GATE：两位学弟的源码/独立验收还在各自电脑，本机待接收核验；共同确认实施版字段；接入真实 Platform Task/Event、PostgreSQL/WebSocket 与 Frontend，进行第一次三方成功/失败闭环。

NEXT PHASE：可取消 Provider、持久执行协调、平台 Context Provider、业务授权、State Effects 和第二次状态变化 Gate。当前取消接口诚实返回未支持，执行记录只保留进程生命周期，不能宣称生产 exactly-once 或完整中断恢复。

LATER：SimPy/3D 联合仿真、专业排产/库存/AGV 算法、企业 ERP/WMS、模型自主部署与替换、生产级生成代码沙箱、跨主机认证和完整许可评审。

原平台方向、ERP/WMS/WAC/WCS/RCS 职责与原 6/10/4、C 3/7 约定继续保留。当前仅证明合成数据和受控真实模型接口的技术执行，不证明企业交期或生产收益。生产可用性未验收，许可门禁 REVIEW_REQUIRED。
