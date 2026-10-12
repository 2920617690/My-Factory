# Integration Gate

`check_runtime_transport.py` 验证实际 Runtime HTTP 服务、平台 SDK 的请求/结果替换入口及拒绝行为。它不启动 Platform Task/Event、PostgreSQL、WebSocket 或 Frontend，不能代替三方 Gate。

完整 `inventory_analysis_e2e` 尚未执行。接收 Frontend/Platform 源码和独立证据后，再按共享规范验证 WH-001 → inventory.analyze → Platform Task → Runtime → Plugin → Result → Platform Event → WebSocket → Frontend re-fetch；包含成功和失败路径。
