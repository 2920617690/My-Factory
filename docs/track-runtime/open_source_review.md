# Runtime 开源复用审查

审查日期：2026-10-12；范围为本地 MVP 开发与当前执行路径。先核对现有 B 源码、锁定 commit、官方发布/接口文档，再确定复用方式。许可审查的开发记录不替代整个平台生产门禁。

| 能力 | 项目与固定版本 | 许可 | 决策与成本 |
|---|---|---|---|
| Agent / Tool Runtime | DeepSeek Harness，commit 183f08e9c6dde7e36cd2318eaee70b0da08fb35e；SDK 0.1.5rc1，sdk-minimal | 主仓库 MIT；完整依赖沿用 B 待审记录 | ADOPT，复用原 VM SDK/Profile/只读工具；不重建 Agent Loop |
| 插件机制 | 上述版本内 Cordis / dsh-tools；原插件 0.3.0 | 上游源码通知与原 B 许可记录保留 | ADOPT/REFERENCE，脑路径沿用原生注册与 disposer；应用层仅做能力目录映射 |
| 业务执行 | B demo/factory-tools/src/business.mjs 0.3.0 | MIT | ADOPT，原样复制并摘要校验，以固定 Node 进程 Adapter 复用，保留 6/10/4 与五复杂场景规则 |
| 输入与协议 Schema | Pydantic 2.13.5 / pydantic_core 2.46.5 | MIT | ADOPT，沿用现有已安装稳定依赖；生成 JSON Schema、验证输入 |
| Data Contract 校验 | python-jsonschema 4.26.0 | MIT | ADOPT，成熟 JSON Schema Draft 2020-12 校验；不自写校验引擎；禁止远程引用和表达式执行 |
| 本机 HTTP 传输 | FastAPI 0.141.1、uvicorn 0.54.0 | MIT / BSD-3-Clause | ADOPT，沿用工作台固定版本；只提供平台调用入口 |
| 远程 Tool 协议 | MCP | 此次未引入软件包 | REFERENCE，当前无跨系统工具暴露需求，不新增核心依赖 |
| Durable Workflow / Event Bus | Temporal / NATS | 此次未引入软件包 | LATER EVALUATE，当前不需要第二套调度和消息框架 |
| 沙箱 | 原 Lima/VZ VM 与 B5 受控执行 | 原 B 版本与许可记录 | REFERENCE/REUSE，本轮只复用官方模型隔离路径，不声称生产级生成代码执行 |

官方检索与机制依据：

- [Harness 官方发布](https://github.com/deepseek-ai/deepseek-harness/releases) 与 [官方 SDK 指南](https://github.com/deepseek-ai/deepseek-harness/blob/183f08e9c6dde7e36cd2318eaee70b0da08fb35e/docs/user/guide/python-sdk.md)。当前发布页仍显示预发布条目；版本策略是复用已有已测基线，不把它作为生产基线。
- [Pydantic JSON Schema 文档](https://docs.pydantic.dev/latest/concepts/json_schema/)：从模型生成 Draft 2020-12 Schema。
- [python-jsonschema 校验文档](https://python-jsonschema.readthedocs.io/en/stable/validate/)：采用现有 Draft202012Validator，安装与实际执行版本固定为 4.26.0。

新增 JSON Schema 传递依赖已经安装后核对 metadata 和许可文本，并全部锁定：attrs 26.1.0、jsonschema-specifications 2025.9.1、referencing 0.37.0、rpds-py 2026.9.1，均记录为 MIT。已有底座的 typing_extensions 为 PSF-2.0；其余 MIT/BSD 通知保存在 runtime/licenses。完整 18 包清单为 `runtime/evidence/python-dependencies.json` / `runtime/requirements.lock`；`pip check` 实测通过。

Node.js 使用本机 24.19.0，只执行固定业务源文件；交付包不分发 Node 或 VM 二进制。新版 Harness API 升级、运行时完整传递依赖、企业模型部署与生产许可仍为 REVIEW_REQUIRED，沿用原 B LICENSE_REVIEW.md，不据此推断整个系统许可通过。

## GitHub 自动检查复用

2026-10-12：采用 GitHub 官方 checkout / setup-python / setup-node 来执行已有确定性检查，均为 MIT，固定官方 tag 对应 commit：checkout v4=`11d5960a326750d5838078e36cf38b85af677262`；setup-python v5=`a26af69be951a213d495a4c3e4e4022e16d87065`；setup-node v4=`49933ea5288caeca8642d1e84afbd3f7d6820020`。Tag 摘要通过各自官方 Git 仓库实际查询，三份官方 LICENSE 已核对；不自建 CI 执行框架。

依据为 [GitHub Python CI 官方指南](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) 及对应官方 Action 源码。运行环境采用 Python 3.12、Node 24.19.0；Node 官方发布校验文件 URL 已实际返回 HTTP 200。Workflow 只读仓库，不配置模型调用凭据。YAML 解析及本机从 Git index 导出的 30 项检查通过；远端 runner 尚未执行，CI 状态为 NOT_RUN。
