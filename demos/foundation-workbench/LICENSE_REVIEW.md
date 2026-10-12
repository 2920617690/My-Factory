# Foundation 工作台许可与来源记录

更新：2026-10-10。范围是新增 `Foundation/app` 首版开发工作台。**生产许可门禁 REVIEW_REQUIRED，production_ready=false。** 沿用 Foundation 的自主部署维护要求；没有引入新的收费必要组件。

| 组件 | 实际锁定 | 源码/来源 | 许可与通知位置 | 本轮使用 |
|---|---|---|---|---|
| 自研工作台 | 0.1.0 | 本目录 `backend/`、`ui/src/` | MIT，`LICENSE` | 可修改的本地网关和页面 |
| FastAPI | 0.141.1 | https://github.com/fastapi/fastapi | MIT，`licenses/python/fastapi@0.141.1/LICENSE` | API；保留通知 |
| Uvicorn | 0.54.0 | https://github.com/encode/uvicorn | BSD-3-Clause，`licenses/python/uvicorn@0.54.0/LICENSE.md` | 本机 HTTP 服务 |
| Pydantic / Core | 2.13.5 / 2.46.5 | https://github.com/pydantic/pydantic | 各自 MIT 通知，`licenses/python/` | 契约与输入校验 |
| React / React DOM | 19.3.0 | https://github.com/facebook/react | MIT，`licenses/npm/react@19.3.0/` 与 `react-dom@19.3.0/` | 自研工作台 UI |
| TypeScript | 7.0.2 | https://github.com/microsoft/TypeScript | Apache-2.0，包本体与 darwin-arm64 的 LICENSE/NOTICE 位于 `licenses/npm/` | 构建工具，不改变原任务的语言路线 |
| Vite | 8.3.1 | https://github.com/vitejs/vite | MIT 及包内第三方通知，`licenses/npm/vite@8.3.1/LICENSE.md` | 静态页面构建 |
| 其他直接/传递依赖 | Python 13 个锁项；前端按 pnpm lock | 锁文件与实际包元数据 | 从现有 B demo 按同版本复制到 `licenses/` | 未升级或添加新依赖；保留原通知 |
| 模拟 fixture | 本轮摘要登记 | B `demo/fixtures/factory.json` 的一致副本 | 合成数据，无企业正式记录 | 只读投影，来源追踪保留 |
| 官方 Harness/SDK/插件/VM | 沿用 B：0.1.5rc1、固定 tag/commit、插件 0.3.0 | B 独立工作区与专用 VM | 见 `../pocs/my-factory-harness-poc/LICENSE_REVIEW.md` 与 demo 许可记录 | 通过本机服务桥接，未复制进工作台依赖或源码包 |

`requirements.lock`、`ui/package.json`、`ui/pnpm-lock.yaml` 与原 B demo 对应依赖一致；本轮离线安装并核对了版本。详细包来源、声明文件摘要和源文件摘要在 `evidence/source-manifest.json`。MIT/Apache/BSD 的分发声明应随包保留；复制通知不是对整个系统商业分发的最终批准。

仍需审查官方 Runtime 完整二进制闭包、外部 API 条款、自主部署模型、A 的 PostgreSQL/容器及 C 的 Three/R3F/SimPy/3D 资产。当前页面无外部字体、图片或 3D 资产，C 服务尚未接入；仿真工具未向 Agent 注册。遵循 [Foundation 许可登记](../docs/06_许可登记.md)，不以自研 MIT 或已复制的依赖通知推定全栈获批。

## 2026-10-12 Runtime 现场验证补充

复用现有 React/FastAPI 环境和锁文件，没有新增运行依赖。新增面板通过标准 HttpRuntimeClient 调用独立 Runtime；自研源码沿用 MIT。共享副本位于仓库 demos/foundation-workbench，原记录中的 Foundation/POC 相对路径属于历史本机来源；共享官方 SDK runner/插件与许可范围以仓库 runtime/harness-assets、runtime/licenses 和 docs/track-runtime 为准。CI 构建固定 pnpm 11.25.0，官方 npm 元数据为 MIT、Node >=22.13；生产许可门禁保持 REVIEW_REQUIRED。
