# 02. 进阶篇：2025 架构演进

本章深入探讨 Agent 技术的最新发展，重点解析 Google A2A 标准的技术细节，以及针对 MCP 痛点的具体优化方案。

## 1. Google A2A (Agent-to-Agent) 深度解析

我们在对话中提到，Google 的 A2A 协议与 MCP 是“横向与纵向”的关系。这里我们深入其技术细节。

### 1.1 核心理念：去中心化的 Agent 网络
与 MCP 关注“单体 Agent 如何变强”不同，A2A 关注“Agent 之间如何协作”。Google 的愿景是建立一个去中心化的 Agent 网络，就像互联网连接网站一样连接 Agent。

### 1.2 关键技术组件
*   **Agent Card (身份名片)**:
    *   每个支持 A2A 的 Agent 必须暴露一个 JSON 格式的“名片”。
    *   内容包括：Agent 的名字、描述、支持的输入模态（文本/语音）、输出模态、以及它能解决的任务类型。
    *   **作用**: 让其他 Agent (Client Agent) 能够通过搜索发现它。
*   **Task Lifecycle (任务生命周期)**:
    *   A2A 定义了一个标准的任务对象。
    *   状态流转：`Draft` -> `Pending` -> `In Progress` -> `Completed` / `Failed`。
    *   这解决了“长耗时任务”的问题。比如你呼叫一个“视频渲染 Agent”，它可能需要 1 小时。A2A 协议允许你通过 `Task ID` 轮询状态，而不是一直挂着 HTTP 连接。
*   **安全与隐私**:
    *   A2A 强调**不共享内部状态**。Agent A 呼叫 Agent B，只能看到 B 暴露的接口，看不到 B 的 Prompt 或内部数据。这对于企业级应用（跨部门协作）至关重要。

### 1.3 A2A 与 MCP 的协作图谱
```text
[用户] -> [主 Agent (Orchestrator)]
              |
              +--- (MCP 协议) ---> [本地工具: 文件读取]
              |
              +--- (MCP 协议) ---> [本地工具: 数据库查询]
              |
              +--- (A2A 协议) ---> [外部 Agent: 差旅预订服务]
                                        |
                                        +--- (MCP 协议) ---> [航司 API]
```

## 2. MCP 的痛点：Token 爆炸 (Token Bloat)

### 2.1 算一笔账
为什么说 MCP 会导致 Token 爆炸？
假设你有一个企业级 Agent，连接了 50 个 MCP Server，每个 Server 有 10 个工具。总共 500 个工具。
*   每个工具的 JSON Schema 定义平均需要 200 Tokens（包含描述、参数说明）。
*   **总消耗**: 500 * 200 = **100,000 Tokens**。
*   **后果**:
    1.  **贵**: 每次对话还没开始，光是 System Prompt 就消耗了 $1 (按 GPT-4 价格估算)。
    2.  **慢**: 首字延迟 (TTFT) 极高。
    3.  **笨**: LLM 的注意力机制在处理超长 Context 时会衰减，导致它“忘记”用户的原始问题。

## 3. 2025 年解决方案 (The Better Plan)

针对上述问题，2025 年的架构演进方向非常明确：**从“全量加载”转向“按需加载”**。

### 方案 A：动态工具检索 (Retrieval-based Tool Selection)
这是目前最成熟的方案。
1.  **Embedding**: 将 500 个工具的描述（Description）转换成向量，存入向量数据库 (Vector DB)。
2.  **Retrieval**: 用户问“帮我查下上个月的销售额”。
3.  **Search**: 系统将用户问题转向量，在数据库中搜索最相似的 Top-5 工具（例如 `query_sales_db`, `get_report` 等）。
4.  **Context Injection**: **只将这 5 个工具**的定义注入到 LLM 的 Context 中。
5.  **Result**: Token 消耗从 100k 降到了 1k。

### 方案 B：Code-as-Action (代码即行动)
这是更激进的方案，以 LangChain 和 OpenAI Code Interpreter 为代表。
*   **原理**: 不再让 LLM 学习几百个 JSON 格式。而是给它一个 Python 环境，并预装好 SDK。
*   **Prompt**: "你有一个 `sdk` 对象，可以用 `dir(sdk)` 查看可用方法。请写代码解决用户问题。"
*   **执行**:
    ```python
    # LLM 生成的代码
    methods = dir(sdk.sales)
    print(methods) # 动态探索
    data = sdk.sales.get_monthly_data(month="2023-10")
    print(data)
    ```
*   **优势**: LLM 利用 Python 的自省能力 (Introspection) 来动态发现和使用工具，完全绕过了 Context Window 的限制。

## 4. 总结
我们在实战中构建的 `client_v2.py` 采用了基础的 MCP 模式（全量加载）。如果我们要将其生产化，第一步就是引入 **方案 A (动态检索)**，这将是区分“玩具”和“产品”的关键一步。
