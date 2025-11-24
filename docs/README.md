# Agent 系统开发实战指南

欢迎来到 Agent 系统开发学习文档。本文档记录了从零开始构建一个基于 MCP (Model Context Protocol) 的智能 Agent 系统的全过程。

## 目录

### [01. 基础篇：Agent 的大脑与手脚](./01_fundamentals.md)
- 什么是 Function Calling？
- 什么是 MCP？
- 为什么说 MCP 是“插座”，Function Calling 是“大脑”？

### [02. 进阶篇：2025 架构演进](./02_advanced_protocols.md)
- Google A2A (Agent-to-Agent) 协议解析
- MCP 的 Token 消耗痛点
- 2025 年的解决方案：动态检索与 Code-as-Action

### [03. 实战篇 (一)：构建 MCP 工具 (MVP)](./03_practice_mvp.md)
- 编写第一个 MCP Server (`server.py`)
- 编写基础 Client (`client.py`)
- 实现数据库表结构对比

### [04. 实战篇 (二)：构建智能 Agent](./04_practice_agent.md)
- 从脚本到 Agent 的进化
- 实现 ReAct (Reason-Act) 循环
- 动态工具发现与模拟 LLM 决策 (`client_v2.py`)

### [05. 进阶篇 (二)：Agent 的认知架构](./05_cognitive_architecture.md)
- 为什么 LLM 需要“思考”？(CoT 原理)
- ReAct 模式：学术界的事实标准
- OpenAI o1 与推理模型的未来

---
*本文档由 Antigravity 辅助生成，旨在帮助开发者理解现代 Agent 架构。*
