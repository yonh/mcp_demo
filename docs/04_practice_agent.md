# 04. 实战篇 (二)：构建智能 Agent

本章复盘 `client_v2.py` 的开发，这是从“脚本”向“智能体”进化的关键一步。我们将深入解析 ReAct 循环的代码实现。

## 1. 核心进化：从线性到循环

### 1.1 脚本思维 (Client V1)
```python
# 线性执行
get_db1()
get_db2()
compare()
```
这种代码是脆弱的。如果我想对比 3 个数据库怎么办？如果我想对比完之后删除表怎么办？必须重写代码。

### 1.2 Agent 思维 (Client V2)
```python
# 循环执行
while True:
    decision = brain.think(history)
    if decision == "stop": break
    execute(decision)
    history.append(result)
```
这种代码是**通用**的。无论任务多复杂，只要“大脑”足够聪明，这个循环就能一直跑下去直到解决问题。

## 2. 关键代码深度解析

### 2.1 动态工具发现 (Dynamic Discovery)
```python
tools_response = await session.list_tools()
tools = tools_response.tools
```
*   **意义**: Agent 启动时，对 Server 的能力一无所知。通过 `list_tools()`，它动态获取了工具的名称、描述和参数 Schema。
*   **System Prompt 构建**: 在真实的 Agent 中，我们会把这个 `tools` 列表转换成 JSON Schema 字符串，塞入 System Prompt，告诉 LLM：“你可以使用这些工具...”。

### 2.2 模拟大脑 (`mock_llm_router`)
为了演示原理，我们手写了一个简单的状态机来模拟 LLM。

```python
def mock_llm_router(messages, tools):
    # 1. 感知 (Perception)
    # 提取最新的用户消息和已有的工具执行结果
    last_user_msg = ...
    tool_outputs = ...

    # 2. 记忆 (Memory)
    # 检查 tool_outputs 的数量，判断当前处于什么阶段
    
    # 3. 推理 (Reasoning)
    if "compare" in last_user_msg and len(tool_outputs) == 0:
        # 状态 0: 刚开始，啥数据都没有 -> 查 DB1
        return {"type": "tool_use", "name": "list_tables", "args": {DB1}}
    
    if len(tool_outputs) == 1:
        # 状态 1: 有一份数据了 -> 查 DB2
        return {"type": "tool_use", "name": "list_tables", "args": {DB2}}
        
    # ...
```
*   **深度解读**: 这个函数虽然简单，但它完美展示了 LLM 在 Agent 中的角色——**基于上下文 (Context) 的状态路由器**。
*   **真实 LLM 的区别**: 真实的 GPT-4 不需要我们写 `if len(tool_outputs) == 1`。它通过语义理解，自己知道“我还缺一份数据”。

### 2.3 ReAct 循环实现
```python
while True:
    # 1. Thought (思考)
    decision = mock_llm_router(messages, tools)
    
    if decision["type"] == "tool_use":
        # 2. Action (行动)
        print(f"Assistant (Action): Call tool '{tool_name}'...")
        result = await session.call_tool(tool_name, arguments=tool_args)
        
        # 3. Observation (观察)
        messages.append({
            "role": "tool",
            "content": result.content
        })
        # 循环继续，LLM 将在下一轮看到这个 observation
```
*   **消息历史 (History)**: `messages` 列表是 Agent 的短期记忆。它必须包含完整的对话流：`User -> Assistant(Call) -> Tool(Result) -> Assistant(Think)...`。如果丢失了中间的 Tool Result，LLM 就会“失忆”。

## 3. 总结
`client_v2.py` 虽然使用 Mock LLM，但其**骨架**与最先进的 AutoGPT 或 LangChain Agent 完全一致。
它证明了：只要有一个能根据 Context 做决策的大脑，配合 MCP 提供的标准手脚，我们就能构建出解决复杂问题的智能体。
