# My Factory Runtime 独立开发交付

2026-10-12：已完成独立 Runtime 最小工程化闭环。它接收标准 ExecutionRequest，通过能力目录调用插件，返回 ExecutionResult、结构化错误和执行轨迹；业务任务与工厂状态由 Platform 持有。

已验证：30 项自动检查、库存/设备/旧上下文三个独立 Fixture、12 项真实 HTTP 交接检查，以及新 Adapter 的 1 次真实官方模型回合和 2 次工具调用。库存基线为可用 6、需求 10、缺口 4。证据在 `evidence/`，逐项结论见 `../docs/track-runtime/report.md`。

## 当前本机运行

无需 Frontend、Platform 或原 B 演示服务启动。

```sh
cd '/Users/fwk/Downloads/svs/My Factory/Foundation/mvp-0.1/runtime'
PYTHONPATH=src .venv/bin/python -m myfactory_runtime capabilities
PYTHONPATH=src .venv/bin/python -m myfactory_runtime execute fixtures/execution-inventory.json
PYTHONPATH=src .venv/bin/python -m myfactory_runtime execute fixtures/execution-equipment.json
.venv/bin/python scripts/verify_runtime.py
```

前三条 CLI 的 stdout 是标准 JSON；验证脚本不调用模型，更新实际证据。所有示例上下文均为合成 Mock，原 8 个场景和 6/10/4 基线保留。

启动平台可调用的本机服务：

```sh
.venv/bin/python start.py
```

地址 http://127.0.0.1:18342/；健康状态 `/api/v1/health`，接口说明 `/api/docs`。服务进程在终端用 Control+C 关闭。也可双击 Foundation 顶层的“启动MVP Runtime.command”。API 拒绝浏览器 Origin，产品前端仍通过 Platform 调用。

服务启动后进行真实 HTTP 交接检查：

```sh
.venv/bin/python ../tests/integration/check_runtime_transport.py
```

## 真实模型路径与查看结果

查看 `evidence/official-adapter-smoke.json` 可读取已保存实际回合，不新建模型调用。新建官方回合使用：

```sh
PYTHONPATH=src .venv/bin/python -m myfactory_runtime execute fixtures/execution-brain.json
```

该命令实际调用用户已配置的官方 API，并经原 Lima/VZ VM 内的官方 SDK/Profile 执行。它不连接原 B HTTP 服务，不迁移其 Task 状态机。SDK/Cordis/只读工具与业务 fixture 使用既有已验证版本，执行前核对宿主/来宾数据摘要与完整传入上下文，执行后核对真实工具返回。密钥继续只存在原来宾私有配置中。

当前受控脑路径仅支持原 fixture 的订单/订单组分析。传入不同来源事实会明确失败；未来 Platform Context Provider 接入后，再扩展该路径。确定性执行可使用符合 Mock Contract 的传入截面。

同一服务进程内，同 execution_id、同输入返回已有结果；改变输入拒绝。每次独立 CLI 启动都是新进程，真实模型 CLI 会建立新回合。跨进程任务幂等、恢复、审批、取消和业务副作用由平台及后续执行协调共同处理。

## 干净环境与共享包

使用 Python 3.12 与 Node.js 24，本次 Node 实测 24.19.0。新机器不需要官方 API 即可做确定性独立验收：

```sh
cd runtime
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python scripts/verify_runtime.py
.venv/bin/python start.py
```

Node 需要在 PATH，或在 `config/runtime.local.json` 指定 `node_binary`。没有本机配置时明确使用 `runtime.example.json`，官方模型路径默认关闭。源码包不含 `.venv`、Lima 磁盘、API 密钥或宿主机器配置。恢复真实模型执行按原 B 复现说明准备匹配 SDK、VM、身份和只读插件，再填写已授权的本机连接配置。

## 代码入口

共享仓库包含 [官方 SDK runner 与原生插件源码](harness-assets/README.md)。它们来自原 POC 的已验证实现；各成员可审查和按受控 VM 约定部署，常规开发与 CI 使用无模型的确定性路径。

| 部分 | 文件 |
|---|---|
| 标准输入、结果、错误、引用 | `src/myfactory_runtime/protocol.py` |
| Execute/Query/Cancel/GetCapabilities | `adapter.py` |
| 能力到 Provider 的薄目录 | `registry.py` |
| 数据契约注册/校验/转换/版本 | `data_contract.py` |
| 库存和设备 Mock Provider | `plugins.py` |
| 官方 SDK VM Adapter | `harness.py` |
| 唯一具体 Provider 装配位置 | `bootstrap.py` |
| 平台传输与客户端 | `service.py` / `client.py` |
| B 原业务代码原样复用 | `plugins/poc-inventory/vendor/business.mjs` |
| 独立样例与版本化场景 | `fixtures/` |

取消接口返回明确的 `CANCELLATION_NOT_SUPPORTED`，不报告已经停止。生成代码执行仍只沿用原 B5 的受控 POC；本服务没有执行用户/模型代码的入口。专业算法、State Effects、Simulation、企业接入和生产级沙箱属于后续阶段。
