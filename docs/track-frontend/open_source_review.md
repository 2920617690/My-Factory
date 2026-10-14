# Frontend Track Open Source Review

本文件记录 MVP 0.1 前端 Track 当前使用的开源依赖，以及它们在二次会议架构中的位置。前端只面向 Platform REST/MSW 接口，不直接调用 Runtime、Plugin、数据库或 Harness。

## 核心依赖

| 依赖 | 用途 | 当前使用位置 | 备注 |
| --- | --- | --- | --- |
| React | 前端 UI 组件与状态渲染 | `web/src/App.tsx`、`web/src/components/*` | 用于 Digital Factory Workspace 主界面 |
| Vite | 本地开发服务器与构建 | `web/vite.config.ts` | `npm run dev` / `npm run build` |
| Three.js | 3D 场景底层渲染 | 由 R3F/Drei 间接使用 | 用于双层工厂空间表达 |
| @react-three/fiber | React 方式组织 Three.js 场景 | `web/src/components/FactoryScene.tsx` | 不直接承载业务调用 |
| @react-three/drei | 3D 辅助控件与文本 | `web/src/components/*` | 用于 OrbitControls/Text 等 |
| lucide-react | 前端图标 | `web/src/App.tsx`、面板组件 | 保持控制区按钮可识别 |
| MSW | Platform Mock API | `web/src/mocks/*` | 用于独立开发和第一轮联调闭环 |
| Playwright | 最小 E2E 验证 | `web/tests/workspace.spec.ts` | 验证 inventory.analyze 前端流程 |
| oxlint | 静态检查 | `npm run lint` | 保持前端代码基本质量 |

## 架构边界

- 前端组件通过 `web/src/client/factoryClient.ts` 访问 `/api/v1/...`。
- MSW handlers 位于 `web/src/mocks/handlers.ts`，模拟 Platform 层的 factory/entities/actions/tasks/events。
- 旧 SimPy POC 直连接口已隔离到 `web/src/legacy/simpyApi.ts`，不属于 MVP 0.1 主前端链路。
- 当前尚未引入 Zustand、TanStack Query 或 WebSocket；这些属于后续真实 Platform 接入后的增强项。

## 风险记录

- `npm install` 当前报告 1 个 high severity vulnerability，尚未执行 `npm audit fix`，避免未经评估的依赖升级。
- 当前 MSW 只覆盖第一轮联调所需的 `WH-001 -> inventory.analyze -> Task -> Event -> Trace`，不是完整 Platform 实现。
