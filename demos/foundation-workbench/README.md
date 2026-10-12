# Runtime 现场验证工作台

本目录共享既有 Foundation 工作台及本轮新增的 Runtime 操作面板。打开 `http://127.0.0.1:18341/#runtime`，可以直接点击执行和查看实际返回。它是临时开发演示，正式 Frontend/Platform 由另外两位开发者交付。

## 本轮新增的操作

| 用例 | 展示结果 |
|---|---|
| 单订单库存分析 | ORD-001：可用 6、需求 10、缺口 4 |
| 订单组共同备料 | 五个场景分别执行，控制板缺口 60、40、30、0、0；最后跨层通道受阻 |
| 设备状态检查 | EQ-001 可选空闲、运行、检修或离线，返回实际检查结果 |
| 旧数据格式转换 | 输入契约 0.1.0 的 state 转换为 1.0.0 的 factory_state，再执行库存分析 |
| 无效输入拒绝 | 未注册版本 99.0.0 返回实际 FAILED、结构化错误与失败轨迹 |

每次点击产生新的 task_id/execution_id。页面显示实际结果、插件版本、起止时间、标准输入和原始返回，可以查询同一执行并导出完整记录。切换用例、模式、设备状态或截面会清空旧结果，直到当前输入执行完成。默认直接计算，不调用模型；只有主动选择官方大脑路径才调用已配置的模型服务。

调用链是浏览器 → 临时工作台后台 → HttpRuntimeClient → 独立 Runtime → 插件。浏览器没有直连 Runtime/Harness，也没有持有模型密钥。

## 干净机器启动

需要 Python 3.12、Node.js 24.19.0、pnpm 11.25.0。先按仓库 `runtime/README.md` 准备并启动 Runtime 18342，保持运行。新机器无需模型配置就能完成全部确定性用例。

在另一个终端，从仓库根目录执行：

```sh
cd demos/foundation-workbench
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cd ui
pnpm install --frozen-lockfile
pnpm run build
cd ..
.venv/bin/python start.py
```

随后打开 `http://127.0.0.1:18341/#runtime`。当前用户本机已完成配置，继续使用原 Foundation 的启动入口，不需要重复安装。

本机原 B 服务 18340 是旧“工厂大脑”页面的可选服务。本轮 Runtime 验证页使用 18342，不依赖 B HTTP 服务。新克隆的工作台没有 Foundation 外部台账时，使用明确标注来源日期的 `fixtures/workflow-status.json` 历史状态快照；该快照不表示其他两方已经交付或联调完成。

## 验证

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/check_runtime_demo_http.py
```

第二条要求两个服务都已启动，只走确定性路径，不调用模型。GitHub Actions 同时构建页面并运行单元与实际 HTTP 交接检查。

## 范围与许可

复用原 React/TypeScript、FastAPI 与锁文件，无新增运行依赖。pnpm 11.25.0 为 MIT 开发工具，其官方 npm 元数据已经核对；Node 要求 >=22.13，本项目固定 24.19.0。已有许可证保存在 `licenses/`，自研代码沿用 MIT。官方 Harness 来源与版本见仓库 `runtime/harness-assets/README.md`；生产许可仍 REVIEW_REQUIRED。

工作台不写库存、不控制设备、不执行 SimPy；完整三方 Gate 仍 NOT_RUN。Runtime 查询只保留当前进程的记录，页面历史只保留当前页面会话。HTTP 导出使用工作台最近 32 次实际响应的临时快照，工作台重启后失效；及时下载可用于汇报。它不是平台 TaskStore 或业务持久化。
