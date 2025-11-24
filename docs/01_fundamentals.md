# 01. 基础篇：Agent 的大脑与手脚

本章深入解析现代 AI Agent 系统的核心基石。我们将超越简单的定义，从软件工程的痛点出发，探讨为什么我们需要 MCP 和 Function Calling。

## 1. 演进史：从 Chat 到 Agent

### 1.1 阶段一：纯 LLM (Chat)
*   **状态**: 用户问“今天天气怎么样？”，LLM 只能回答“我不知道”或根据训练数据瞎编。
*   **本质**: 只有**世界知识 (World Knowledge)**，没有**实时信息 (Real-time Info)**，也没有**行动能力 (Action)**。

### 1.2 阶段二：Function Calling (原生手脚)
OpenAI 和 Anthropic 在模型训练阶段，教会了模型一种特殊的输出格式（通常是 JSON）。
*   **流程**:
    1.  **定义**: 开发者在 API 请求中附带一个 `tools` 参数，描述函数签名（如 `get_weather(city)`）。
    2.  **思考**: LLM 分析用户意图，返回结构化数据 `{"name": "get_weather", "args": {"city": "Beijing"}}`。
    3.  **执行**: 开发者捕获这个 JSON，运行本地代码，拿到结果。
    4.  **反馈**: 将结果再次喂给 LLM，LLM 生成最终自然语言回复。
*   **痛点：胶水代码地狱 (Glue Code Hell)**
    虽然 LLM 能“想”出调用什么，但**“连接”**这一步非常痛苦。
    - 接 Google Drive？你需要读 50 页 API 文档，写一套 OAuth 认证和 API 封装。
    - 接 Slack？又要写一套。
    - 接本地文件系统？还要写一套。
    - **后果**: 你的 Agent 项目里 80% 的代码都是在写各种 API 的适配器 (Adapter)，而不是业务逻辑。

### 1.3 阶段三：MCP (通用插座)
**Model Context Protocol (MCP)** 的出现，就是为了消灭“胶水代码”。
*   **核心隐喻**: MCP 之于 AI，就像 **USB 之于电脑**。
    - 在 USB 出现之前，鼠标有鼠标的口，键盘有键盘的口，打印机有并口。
    - USB 出现后，所有设备都遵循同一个标准。操作系统不需要为每个鼠标写驱动，只要支持 USB 协议即可。
*   **MCP 架构**:
    - **MCP Server**: 工具的提供方（如 `sqlite-mcp-server`）。它按照标准格式暴露 `list_tables`, `query_db` 等能力。
    - **MCP Client (Host)**: 你的 Agent 系统。它只需要实现一次 MCP 协议，就能连接所有支持 MCP 的工具。

## 2. 深度架构解析

我们在对话中画过一张架构图，这里进行详细拆解：

```mermaid
flowchart TD
    subgraph "MCP Server (工具层)"
        A[SQLite DB]
        B[Local Files]
        C[Web Search]
        MCP_Interface[MCP 协议接口 (JSON-RPC)]
        A --> MCP_Interface
        B --> MCP_Interface
        C --> MCP_Interface
    end

    subgraph "Agent Host (应用层)"
        Host_Logic[MCP Client / Host 逻辑]
        Converter[转换器: MCP工具 -> LLM Tool Schema]
        Router[路由器: LLM调用 -> MCP执行]
    end

    subgraph "LLM (认知层)"
        Model[GPT-4 / Claude 3.5]
    end

    MCP_Interface -- 1. 握手 & 暴露能力 (List Tools) --> Host_Logic
    Host_Logic --> Converter
    Converter -- 2. 翻译为 JSON Schema --> Model
    Model -- 3. 决策 (Function Call) --> Router
    Router -- 4. 路由请求 --> MCP_Interface
    MCP_Interface -- 5. 执行并返回结果 --> Router
    Router -- 6. 结果回传 --> Model
```

### 关键环节详解
1.  **握手 (Handshake)**: Agent 启动时，Client 和 Server 建立连接（通常是 stdio 管道）。Server 发送 `capabilities`，告诉 Client 它支持什么（工具、资源、Prompt 模板）。
2.  **转换 (Translation)**: MCP 定义的工具格式与 OpenAI/Claude 的 API 格式略有不同。Client 需要一个适配层，将 MCP 的 `Tool` 对象转换成 LLM API 需要的 `function` 定义。
3.  **路由 (Routing)**: 当 LLM 返回 `call_tool` 指令时，Client 需要根据工具名称，找到对应的 MCP Server 连接，并转发请求。

## 3. 总结
*   **Function Calling** 是 LLM 的**认知能力**（大脑），解决了“什么时候调用、调用什么”的问题。
*   **MCP** 是系统的**工程标准**（神经末梢），解决了“如何低成本连接万物”的问题。
*   **实现 MCP 必须依赖 Function Calling**：MCP 只是把工具送到了 LLM 嘴边，最后“吃不吃、怎么吃”，还是得靠 LLM 的 Function Calling 能力。
