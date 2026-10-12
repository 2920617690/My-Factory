# My Factory MVP 0.1

统一代码仓库：[2920617690/My-Factory](https://github.com/2920617690/My-Factory)。三人分支、PR、接口变更和自动检查见 [协作说明](CONTRIBUTING.md)。云端检查的实际结果在仓库 Actions 页面查看，独立验收范围见下文。

2026-10-12：已收到总体设计、共享集成规范、验收总指导及 Runtime 独立任务书，进入 Phase 1 工程化开发。源码在统一目录组织，现有 Foundation 工作台和原 POC 保留。Runtime 独立闭环已实际通过；Frontend/Platform 成果按用户说明在两位学弟电脑上，本机尚未接收与核验，三方 Integration Gate 尚未执行。

新阶段按功能分为 **Frontend / Platform / Runtime**，对应新文档的 Track A/B/C。这与原验证任务 A/B/C 编号不同：旧 B 的 Harness 成果由新 Runtime Track C 复用；旧 A 对应新 Platform Track B；旧 C 的展示能力对应新 Frontend Track A，SimPy 后续独立接入。人员安排继续按实际分工，不根据字母自动调换。

```text
frontend/          接收数字孪生前端，当前只有交付说明
platform/          接收平台核心，当前只有交付说明
runtime/           已实现的独立能力执行层与实际证据
shared/contracts/  跨边界引用和执行协议 JSON Schema，Runtime 实施版
shared/fixtures/   统一 Demo ID
docs/architecture/ 边界、接口细化与决策记录
docs/track-runtime/开源审查、平台交接、实际验收
docs/sources/      四份新文档原件及摘要校验
tests/integration/ Runtime 传输检查；完整三方测试待接入
demos/             临时交付工作台，可直接操作 Runtime 验证
```

先看 [Runtime 运行说明](runtime/README.md)、[平台交接说明](docs/track-runtime/handoff_platform.md) 和 [阶段报告](docs/track-runtime/report.md)。本机 Runtime 服务为 http://127.0.0.1:18342/；它是平台调用入口，没有新的产品页面。原演示 18340 和 Foundation 先导工作台 18341 保持各自职责。

2026-10-12 新增 [Runtime 现场验证工作台](demos/foundation-workbench/README.md)：本机打开 http://127.0.0.1:18341/#runtime，可点击执行单订单/订单组库存分析、设备检查、旧契约转换和无效输入拒绝，查看新生成的执行编号、实际结果与插件轨迹。浏览器通过临时工作台后台的 HttpRuntimeClient 调用独立 Runtime，不直连 Runtime。该演示源自既有 Foundation 工作台，单独放在 demos 中；不替代两位学弟的 Frontend/Platform 交付，不把临时网关验证记为完整三方 Gate。

## 整个系统如何继续构建

1. 三方使用四份共同设计资料，分别提交源码、启动步骤、锁版本、许可证、自动测试与实际证据。两个待接收 Track 保留成熟模板原目录，不为目录图机械重构。
2. Frontend 用 Mock Platform/MSW 独立跑通对象选择与 Task UI；Platform 用 MockRuntimeClient 独立跑通 Factory State、Task/Event、PostgreSQL 与 WebSocket。
3. Runtime 已提供 `inventory.analyze` 的确定性和真实 Harness 路径，以及标准输入/结果、失败轨迹、HTTP RuntimeClient 和 Schema。平台只替换 RuntimeClient，前端只替换 Mock API。
4. 接收并核验两方独立成果后，执行 WH-001 的第一次三方 Gate，包含成功、失败、跨层追踪和可重复运行。
5. 再验证结果经平台业务校验改变 Factory State，并通知前端重新查询。随后接入 Simulation；业务状态与仿真状态保持分离。

企业 ERP/WMS 权威记录、原厂设备控制职责、后置专业算法、版本/许可和独立隔离要求继续沿用 Foundation 约束。生产可用性仍未验收，许可门禁仍为 REVIEW_REQUIRED。
