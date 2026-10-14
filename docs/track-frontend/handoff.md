# Frontend Track Handoff

## 当前完成内容

- 建立 Digital Factory Workspace 主界面，包含双层 3D 工厂、实体上下文、动作区、任务中心、事件区和执行轨迹。
- 前端主链路通过 `factoryClient` 调用 `/api/v1/...` Platform 风格接口。
- 使用 MSW 提供独立开发 Mock，覆盖实体列表、实体状态、动作提交、任务查询和事件查询。
- 第一轮闭环已落到前端：选择/默认聚焦 `WH-001`，点击“库存分析”，创建 `inventory.analyze` 任务，轮询任务状态，并展示执行轨迹与结果。
- 旧 SimPy 直连接口已移动到 `web/src/legacy/simpyApi.ts`，保留为后续 `simulation.run` 参考，不再作为主界面数据来源。

## 运行方式

```powershell
cd D:\BIT_Course\研一上\my_factory\my-factory-twin-poc\web
npm install
npm run dev -- --host 127.0.0.1
```

默认启用 MSW Platform Mock。接入真实 Platform 时可关闭 MSW：

```powershell
$env:VITE_USE_MSW="false"
$env:VITE_PLATFORM_API_URL="http://127.0.0.1:8000"
npm run dev -- --host 127.0.0.1
```

## 验证方式

```powershell
npm run lint
npm run build
npm run test:e2e
```

`test:e2e` 会启动 Vite，并验证库存分析任务能从前端发起、完成并展示结果。

## 对 Platform Track 的接口期望

前端当前期望 Platform 提供以下 REST 接口：

- `GET /api/v1/factory/entities`
- `GET /api/v1/factory/entities/{entityId}/state`
- `POST /api/v1/actions`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{taskId}`
- `GET /api/v1/events`

首个动作请求示例：

```json
{
  "capability": "inventory.analyze",
  "target": {
    "entity_id": "WH-001",
    "entity_type": "warehouse"
  },
  "parameters": {
    "material_id": "MAT-001",
    "order_id": "ORD-001"
  }
}
```

## 后续建议

- 当 Platform 提供稳定接口后，把 MSW 返回结构与正式 OpenAPI/Schema 对齐。
- 引入 WebSocket 或 SSE 后，将事件区从轮询切换为实时订阅。
- 如状态增长明显，再引入 Zustand 或 TanStack Query 管理实体、任务和事件缓存。
