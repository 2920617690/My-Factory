# 官方 Harness 来宾源码

这里原样保存已验证 B 演示的 SDK runner、Cordis 原生 Tool 插件和 8 场景 fixture，使共享仓库包含真实模型路径所需的自研源码。没有复制来宾私有配置、SDK 二进制、VM 磁盘或旧 TaskStore。文件摘要见 provenance.json。

| 文件 | 部署位置与职责 |
|---|---|
| guest_run.py | 来宾 /opt/mf-demo/guest_run.py；使用官方 Python SDK / sdk-minimal，关闭 shell，返回脱敏事件与工具审计 |
| factory-tools/ | 来宾 /opt/mf-demo/factory-tools；版本 0.3.0，两项只读 Cordis Tool，MIT |
| fixtures/factory.json | 来宾 /opt/mf-demo/fixtures/factory.json；必须与 Runtime 主 fixture 摘要一致 |

## 环境约定

现有验证使用专用 Lima/Apple VZ Debian arm64 VM，名为 mf-b，2 CPU / 3 GiB 内存，无宿主目录挂载；执行身份 mf-agent，SDK venv 为 /home/mf-agent/.venv。Python SDK/匹配运行时固定为 deepseek-harness-sdk 0.1.5rc1，源码 commit 183f08e9c6dde7e36cd2318eaee70b0da08fb35e。它是当前开发复用版本，生产稳定性与完整许可仍待评审。

其他成员只有确定性开发需求时，无需准备 VM 或 API；按 runtime/README.md 运行即可。真实模型环境由 Runtime 负责人按受控部署条件单独准备，不能把普通宿主执行替代为代码沙箱验收。

## 原生插件打包与 profile 安装

在本目录 factory-tools 中使用 Node/npm 打包源码：

```sh
cd factory-tools
npm pack --ignore-scripts
```

把 guest_run.py、factory-tools/、fixtures/ 和生成的 factory-demo-tools-0.3.0.tgz 部署至专用 VM 的 /opt/mf-demo，root 所有、mf-agent 只读。在来宾由控制身份执行官方 profile 命令：

```sh
sudo -u mf-agent /usr/bin/env -C /home/mf-agent DSH_HOME=/home/mf-agent/mf-demo/dsh \
  /home/mf-agent/.venv/bin/dsh --profile sdk-minimal --dump-default-config
sudo -u mf-agent /usr/bin/env -C /home/mf-agent DSH_HOME=/home/mf-agent/mf-demo/dsh \
  /home/mf-agent/.venv/bin/dsh plugin --profile sdk-minimal add file:/opt/mf-demo/factory-demo-tools-0.3.0.tgz --ignore-scripts --offline
```

来宾模型凭据由操作者在本机私有配置中提供，文件 /home/mf-agent/.env.mf-demo 归 mf-agent 所有且 0600。宿主在被 Git 忽略的 runtime/config/runtime.local.json 配置已准备好的 Lima 连接，不放密钥。

runner 会在调用前核对已安装插件与 /opt/mf-demo 的源码摘要；新 Runtime 还会核对完整传入上下文与宿主/来宾 fixture。修改插件或数据要升版、部署、重新核对并实测，不能沿用旧成功记录。完整的环境隔离、受控网络、资源和许可评审仍按原 B 与 MVP 技术边界实施；本目录是部署源码，不是自动认证的生产环境。
