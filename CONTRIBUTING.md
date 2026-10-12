# 三人代码协作

统一仓库：https://github.com/2920617690/My-Factory 。本地当前源码位于 Foundation/mvp-0.1，仓库根目录直接包含 frontend、platform、runtime、shared 和 docs。原独立 POC 与现场演示继续留在 Foundation 中。

## 各自在哪里开发

| 功能线 | 主目录 | 分支示例 | 交付接口 |
|---|---|---|---|
| Frontend / Digital Twin | frontend/ | feature/frontend-context-panel | FactoryClient → Platform REST/WebSocket |
| Platform Core | platform/ | feature/platform-task-runtime | Application API / Task / Event / RuntimeClient |
| Harness Runtime / Plugin | runtime/ | feature/runtime-inventory-plugin | ExecutionRequest / ExecutionResult / Capabilities |
| 共同约定 | shared/、docs/architecture/ | feature/contract-execution-v1 | Schema、版本、Demo ID、Mock |

main 保存经过评审的共同版本。空仓库首次初始化为本次准备的 MVP 基线；此后每项功能在自己的分支开发，提交 Pull Request 后合入 main。前端和平台负责人接入已有成果时，保留成熟模板的实际目录和历史证据。

## 一次正常开发

首次拿代码：

```sh
git clone https://github.com/2920617690/My-Factory.git
cd My-Factory
```

开始一个功能前同步共同版本，再建分支：

```sh
git switch main
git pull --ff-only
git switch -c feature/runtime-your-change
```

完成相关检查、提交并上传自己分支，然后在 GitHub 的 Pull requests 页面创建 PR。PR 写清问题和结果、接口变化、实际验证、仍需其他 Track 接入的事项。不要把整套源码通过压缩包反复覆盖到 main。

共享协议改动在 PR 中说明影响，并同步更新对应 Mock 和版本；涉及两条线时请双方一起评审。GitHub 评论用于讨论具体差异，docs/architecture/decisions.md 保存长期决定。发现冲突先对齐接口，不各自创建不兼容的私有协议。

## Runtime 本机准备与检查

需要 Python 3.12 和 Node.js 24：

```sh
cd runtime
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python scripts/verify_runtime.py
```

Runtime 的 GitHub Actions 已配置为固定版本 Action、Python/Node 环境和确定性检查，常规 CI 不调用模型。上传后才能验证 GitHub runner 的实际结果；本机通过不自动等同远端 CI 通过。

真实模型配置由各自负责的受控环境持有，版本与隔离说明见 runtime/harness-assets。GitHub 中保留 portable 配置样例与脱敏标准执行记录。完整 SDK 会话、本机来源路径和打包记录继续在原本机 evidence 中保存；对应文件被 .gitignore 排除，未删除。

## 各自电脑的提交身份与登录

每位开发者在自己的电脑完成 `gh auth login`，使用自己的 GitHub 账号登录。密码、设备登录和 token 均在本机交互，不进入聊天或仓库。提交作者名/邮箱只设置在此仓库，可使用 GitHub 隐私邮箱；推送前确认作者身份和当前功能分支。

仓库成员由仓库所有者在 GitHub Settings → Collaborators 添加两位学弟的真实 GitHub 账号。此处未假定他们的账号或替所有者邀请成员。Runtime 现有源码作为第一批共享基线，两条待交付功能线通过各自分支和 PR 接入。
