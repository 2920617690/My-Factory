# Platform Track 接收位置

新阶段 Track B；复用原数据中台 POC。用户确认源码在学弟电脑上，本机尚未接收。这里没有已完成的 PostgreSQL/Task/Event/WebSocket 服务。

接收时附：实际源码与模板目录、数据库迁移/认证、锁文件和许可、Factory State 与 Entity Query、Task 生命周期、Event/WebSocket、MockRuntimeClient、独立测试和运行方式。

Runtime 对接见 `../docs/track-runtime/handoff_platform.md`。本机 transport 在 18342；平台 worker 调用 `HttpRuntimeClient.execute()`，校验 `ExecutionResult` 后保存结果并推进自己的 Task。Runtime 的执行记录只保留本进程生命周期，不代替平台任务持久化。
