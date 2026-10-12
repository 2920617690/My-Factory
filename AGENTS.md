# My Factory MVP 协作约定

先读 README.md、CONTRIBUTING.md、docs/architecture/decisions.md，以及 docs/sources 中的共享规范和自己 Track 的任务书。用户当前指令优先；附件和历史报告是设计资料，不是扩大执行权限的授权。

- 三条功能线是 frontend、platform、runtime；新 Track 字母与原 POC 字母不同，使用功能名称沟通。
- Frontend 只通过 Platform REST/WebSocket 交互；不直连 Runtime/Harness/Plugin/数据库。
- Platform 拥有 Factory State、Task/Event 和业务持久化；Runtime 接收 ExecutionRequest，返回 ExecutionResult/Trace。
- Plugin 通过能力目录调用，不直接写 Platform DB、控制 UI 或推送 WebSocket。生产写和设备控制不属于当前 MVP。
- 使用共享 Entity/Task/Execution/Capability 引用与 Demo ID；接口改变同时更新 Schema、Mock、交接文档和相关测试。
- 各 Track 用自己的 Mock 独立验收；未接收/未运行记实际状态，不能把其他 Track 的历史描述当作本机 PASS。
- 确定性能力直接执行插件；需要推理才走官方 DeepSeek Harness Adapter。禁止假 Agent 或模型猜测库存数值。
- 新通用依赖先记录开源复用、许可、成熟度、集成成本和锁定版本。现有 SDK 预发布版本仅为已测开发基线，生产许可仍待审。
- 业务状态和仿真状态分离；SimPy 权威时钟与 3D 渲染分工保持，专业排产/库存/AGV 算法后置。
- 模型生成代码需独立受控隔离；当前固定 Node 业务代码执行不等于生产级代码沙箱。
- 本机凭据、运行环境、数据库和完整原始会话保留在本机归档。Git 共享源码、合成数据、协议、锁文件、许可与可共享验收摘要。
- 针对实际改动运行相关检查。当前 Runtime 验证为 runtime/.venv/bin/python runtime/scripts/verify_runtime.py；不要触发真实模型回合代替常规 CI。
- 各自功能分支和 Pull Request 协作，按 CONTRIBUTING.md 提交；共享协议改动需要相关 Track 评审。不要改写、强推或覆盖其他人的分支。
