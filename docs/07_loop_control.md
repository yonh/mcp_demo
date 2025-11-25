# 07. 进阶篇 (三)：Agent 循环控制 - 业界实践与设计哲学

本章深入探讨 Agent 系统最核心的问题之一：**如何决定何时继续执行，何时停止？** 我们将对比业界主流框架的策略，并解释我们的设计决策。

---

## 1. 循环控制的重要性

### 1.1 为什么这是核心问题？

Agent 的循环控制（Loop Control）直接影响三个关键指标：

| 指标 | 影响 |
|------|------|
| **任务完成度** | 能否处理复杂的多步骤任务 |
| **成本控制** | 避免无限循环导致的 API 滥用 |
| **用户体验** | 响应速度与任务透明度 |

**核心矛盾**：
- 太早停止 → 任务未完成
- 太晚停止 → 浪费成本、用户体验差

---

## 2. 业界主流方案

### 2.1 LangChain AgentExecutor

**循环策略**：
```python
class AgentExecutor:
    def run(self, user_input):
        max_iterations = 15  # 默认上限
        iterations = 0
        
        while iterations < max_iterations:
            action = self.agent.plan(...)
            
            if isinstance(action, AgentFinish):
                return action.output  # 退出1：Agent主动结束
            
            observation = self.execute_tool(action)
            iterations += 1
        
        raise MaxIterationsExceeded()  # 退出2：达到上限
```

**特点**：
- ✅ **双重保险**：Agent 主动结束 + 迭代上限
- ✅ **显式状态**：`AgentFinish` vs `AgentAction`
- ⚠️ **硬编码上限**：15 次可能不够也可能太多

**退出条件**：
1. Agent 返回 `AgentFinish`
2. 达到 15 次迭代

---

### 2.2 AutoGPT

**循环策略**：
```python
class AutoGPT:
    def run(self, user_goal):
        max_iterations = 100  # 更高的上限
        
        for iteration in range(1, max_iterations + 1):
            thoughts = self.agent.think(...)
            
            if thoughts.command.name == "finish":
                return thoughts.command.args["response"]
            
            result = self.execute_command(thoughts.command)
            
            # 自我批评机制
            critique = self.agent.criticize(result)
            if critique.confidence < 0.5:
                continue  # 不满意，继续迭代
            
            # 人类监督
            if iteration % 5 == 0:
                if not self.ask_user_permission():
                    return "User stopped"
```

**特点**：
- ✅ **自主性强**：允许 100 次迭代
- ✅ **自我批评**：Agent 可以质疑自己
- ✅ **人类监督**：周期性请求确认
- ⚠️ **成本高**：可能进行大量无效迭代

**退出条件**：
1. Agent 调用 `finish` 命令
2. 达到 100 次迭代
3. 用户手动停止

---

### 2.3 OpenAI Assistants API

**循环策略**（服务端实现）：
```python
# OpenAI 服务端逻辑（简化）
class AssistantRunner:
    def run(self, thread_id):
        max_iterations = 10
        
        for iteration in range(max_iterations):
            response = self.llm.call(thread_id)
            
            if response.status == "completed":
                return response.messages
            
            if response.status == "requires_action":
                # 等待客户端提交工具输出
                tool_outputs = self.wait_for_tool_outputs()
                self.submit_tool_outputs(tool_outputs)
                continue
        
        return "Run timed out"
```

**特点**：
- ✅ **状态机模式**：清晰的状态转换
- ✅ **服务端控制**：OpenAI 控制循环
- ✅ **安全**：10 次硬上限
- ⚠️ **不透明**：开发者看不到内部逻辑
- ⚠️ **延迟高**：网络往返开销

**退出条件**：
1. Run 状态 = `completed`
2. Run 状态 = `failed`
3. 超过 10 次迭代

---

### 2.4 Google Vertex AI Agent Builder

**循环策略**（动态调整）：
```python
class VertexAgent:
    def run(self, user_query):
        # 根据任务复杂度动态调整
        complexity = self.estimate_complexity(user_query)
        max_iterations = min(5 + complexity * 2, 20)
        
        timeout = 60  # 60秒超时
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.llm.generate(...)
            
            # 置信度检查
            if response.confidence > 0.9 and not response.tool_calls:
                return response.text
            
            if response.tool_calls:
                self.execute_tools(...)
            
            iterations += 1
            if iterations >= max_iterations:
                break
        
        return self.summarize_partial_result()
```

**特点**：
- ✅ **动态上限**：根据任务调整
- ✅ **置信度检查**：不仅看工具调用
- ✅ **时间限制**：防止长时间阻塞
- ✅ **优雅降级**：超时返回部分结果

**退出条件**：
1. 高置信度 + 无工具调用
2. 动态迭代上限
3. 60 秒超时

---

## 3. 我们的实现（client_v5.py）

### 3.1 极简方案

```python
# Agent Execution Loop
while True:  # 无上限的循环
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=openai_tools,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    messages.append(response_message)
    
    if response_message.content:
        print_colored(response_message.content, ...)
    
    if response_message.tool_calls:
        # 执行所有工具
        for tool_call in response_message.tool_calls:
            result = await session.call_tool(...)
            messages.append({
                "role": "tool",
                "content": str(result)
            })
        # 隐式 continue：回到 while True
    else:
        # 唯一的退出条件：LLM 认为完成
        break
```

### 3.2 设计特点

| 特性 | 我们的实现 |
|------|-----------|
| **循环类型** | `while True`（无上限） |
| **退出条件** | 仅依赖 LLM 判断 |
| **安全机制** | 无（完全信任 LLM） |
| **代码复杂度** | 极简（~20 行） |

**优势**：
- ✅ **极简主义**：代码清晰易懂
- ✅ **LLM 自主**：充分信任 GPT-4
- ✅ **灵活性高**：无硬编码限制
- ✅ **低延迟**：本地循环

**风险**：
- ⚠️ **无限循环**：理论上可能
- ⚠️ **成本失控**：LLM 判断错误时
- ⚠️ **缺乏监控**：无计数/超时

---

## 4. 业界对比总结

### 4.1 主流退出策略对比

| 框架 | 主要退出条件 | 保险机制 | 默认上限 | 适用场景 |
|------|-------------|----------|----------|----------|
| **LangChain** | Agent 主动结束 | 迭代计数 | 15 次 | 通用任务 |
| **AutoGPT** | `finish` 命令 | 计数 + 人类监督 | 100 次 | 自主任务 |
| **OpenAI Assistants** | Run `completed` | 计数 + 超时 | 10 次 | 服务端 |
| **Vertex AI** | 置信度 + 无工具 | 动态上限 + 超时 | 5-20 次 | 企业应用 |
| **我们（v5）** | 无工具调用 | **无** | **无** | 可信环境 |

### 4.2 三层防护模型（业界共识）

```
┌─────────────────────────────────────┐
│  Layer 1: Agent 主动判断            │
│  "我认为任务完成了"                  │
│  → 所有框架都实现                    │
└─────────────────────────────────────┘
              ↓ 失效时
┌─────────────────────────────────────┐
│  Layer 2: 客观限制                   │
│  最大迭代 / 超时 / 成本上限          │
│  → 业界主流实现，我们未实现          │
└─────────────────────────────────────┘
              ↓ 失效时
┌─────────────────────────────────────┐
│  Layer 3: 人类干预                   │
│  手动停止 / 紧急熔断                 │
│  → 部分框架实现（AutoGPT）          │
└─────────────────────────────────────┘
```

**我们只实现了 Layer 1**。

---

## 5. 为什么我们选择极简方案？

### 5.1 设计理由

1. **信任 GPT-4 的能力**
   - GPT-4 在判断任务完成度方面表现优秀
   - 实测中几乎没有遇到无限循环

2. **场景特定性**
   - 数据库操作：通常 1-3 次工具调用
   - 代码执行：很少超过 5 次迭代
   - **不是通用 Agent**：不处理开放任务

3. **开发效率**
   - 添加保险机制增加代码复杂度
   - 对学习项目，极简更利于理解

4. **用户体验**
   - 本地运行，随时可 Ctrl+C 终止
   - 非服务端，风险可控

### 5.2 适用边界

**适合**：
- ✅ 本地开发环境
- ✅ 可信用户（开发者自己）
- ✅ 明确的工具驱动任务
- ✅ 高质量 LLM（GPT-4, Claude 3.5）

**不适合**：
- ❌ 多租户 SaaS
- ❌ 付费 API 服务
- ❌ 不可信用户
- ❌ 开放式任务

---

## 6. 循环终止的技术细节

### 6.1 OpenAI Function Calling 的限制

当使用 `tools` 参数时，LLM 只能返回两种情况：

```python
# 情况 A：调用工具
{
  "content": "[Thought] 我需要查表\n\n",
  "tool_calls": [{"function": {"name": "list_tables", ...}}]
}
# → 循环继续

# 情况 B：给出答案
{
  "content": "[Thought] 已获取数据\n\n答案是...",
  "tool_calls": null
}
# → 循环结束
```

**没有第三种选择**："我先思考一轮，不调用工具，也不结束"

### 6.2 多轮纯思考的局限

**问题**：如果任务需要多轮纯思考（不调用工具），当前代码会在第一轮思考后就退出。

**原因**：OpenAI API 设计假设：
- 需要工具 → 调用工具
- 不需要工具 → 给出答案

**解决方案**（如果需要）：
```python
@mcp.tool()
def continue_thinking(reasoning: str) -> str:
    """虚拟工具：让 Agent 继续思考"""
    return "Thought recorded. Continue."
```

这样 LLM 可以通过调用 `continue_thinking` 来延续思考。

---

## 7. 生产环境升级建议

### 7.1 添加保险机制（推荐）

```python
async def safe_agent_loop(user_input, max_iterations=20, timeout=60):
    iterations = 0
    start_time = time.time()
    
    while True:
        # 保险1：迭代次数
        if iterations >= max_iterations:
            logger.warning(f"Reached max iterations")
            return summarize_partial_result()
        
        # 保险2：超时
        if time.time() - start_time > timeout:
            logger.warning("Timeout")
            return summarize_partial_result()
        
        # 正常流程
        response = await llm_call(...)
        
        if not response.tool_calls:
            return response.content  # 主退出条件
        
        execute_tools(...)
        iterations += 1
```

### 7.2 动态调整策略

```python
def estimate_max_iterations(user_input):
    """根据任务复杂度动态调整"""
    if "分析" in user_input or "清洗" in user_input:
        return 15
    elif "查询" in user_input:
        return 5
    else:
        return 10
```

### 7.3 成本控制

```python
class CostAwareAgent:
    def __init__(self, max_cost_usd=0.50):
        self.max_cost = max_cost_usd
        self.cost = 0
    
    async def run(self):
        while True:
            response = await self.llm_call(...)
            self.cost += calculate_cost(response)
            
            if self.cost > self.max_cost:
                raise CostLimitExceeded()
            
            # 正常流程...
```

---

## 8. 设计哲学对比

### 8.1 两种理念

| 维度 | 业界主流 | 我们的实现 |
|------|----------|-----------|
| **核心理念** | 防御性编程 | 极简 + 信任 |
| **安全策略** | 多层保护 | 单层（LLM） |
| **复杂度** | 中-高 | 极低 |
| **适用环境** | 生产 | 开发/学习 |

**业界主流**：
> **"永远不要完全信任 LLM"**
> 
> 通过工程手段（迭代上限、超时、成本控制）确保系统鲁棒性。

**我们的选择**：
> **"在可控环境下，充分信任 GPT-4"**
> 
> 依赖 LLM 的智能而非复杂的工程保护。

### 8.2 何时使用哪种方案？

**使用我们的极简方案**：
- ✅ 个人项目、学习
- ✅ 本地开发
- ✅ 工具驱动任务
- ✅ 高质量 LLM

**升级到业界方案**：
- ⚠️ 生产环境
- ⚠️ 多用户服务
- ⚠️ 按量付费
- ⚠️ 不可信输入

---

## 9. 实战案例分析

### 9.1 简单查询（3 轮循环）

```
User: 查看 test_db_1 的表

第1轮：
[Thought] 用户想查表
[Action] list_tables('sqlite', 'test_db_1.sqlite')
[Observation] ['users', 'orders']

第2轮：
[Thought] 已获取表列表
数据库有 2 个表：users, orders
→ tool_calls = null → 退出
```

### 9.2 复杂任务（5+ 轮循环）

```
User: 查看 test_db_1 的表，然后删除 users 表

第1轮：list_tables
第2轮：[Thought] 获取到表，现在删除 users
第3轮：run_sql("DROP TABLE users")
第4轮：[Thought] 删除成功，回复用户
→ 退出
```

**关键**：LLM 自己知道"什么时候任务完成了"。

---

## 10. 总结与建议

### 10.1 核心要点

1. **循环控制是 Agent 的生命线**
   - 决定任务完成度、成本、用户体验

2. **业界共识：多层防护**
   - Layer 1: LLM 主动判断
   - Layer 2: 客观限制
   - Layer 3: 人类干预

3. **我们的选择：极简 + 信任**
   - 适合学习、开发环境
   - 生产环境需升级

### 10.2 实践建议

**学习阶段**：
- ✅ 使用我们的极简方案
- ✅ 理解 ReAct 循环机制
- ✅ 观察 LLM 如何决策

**生产阶段**：
- ⚠️ 添加迭代上限（15-20 次）
- ⚠️ 添加超时机制（30-60 秒）
- ⚠️ 添加成本监控

**企业级**：
- ⚠️ 动态调整策略
- ⚠️ 人类监督机制
- ⚠️ 循环检测与熔断

---

## 参考资料

- **LangChain**: [Agent Executor 源码](https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/agents/agent.py)
- **AutoGPT**: [自主循环实现](https://github.com/Significant-Gravitas/AutoGPT)
- **OpenAI Assistants**: [官方文档](https://platform.openai.com/docs/assistants/how-it-works/runs-and-run-steps)
- **ReAct 论文**: [Yao et al., 2022](https://arxiv.org/abs/2210.03629)
