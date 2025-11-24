# 05. 进阶篇 (二)：Agent 的认知架构

本章深入探讨 Agent 的“元认知”——思考机制。我们将从学术理论出发，解析 ReAct 模式的必要性，并展望 OpenAI o1 等推理模型带来的范式转移。

## 1. 为什么 LLM 需要“思考”？(The Why)

### 1.1 概率预测的本质缺陷
LLM (Large Language Model) 本质上是一个**自回归 (Autoregressive) 的概率预测机**。它永远在做一件事：`P(Next Token | Context)`。
*   **直觉反应 (System 1)**: 如果你直接问 LLM 一个复杂逻辑题，它会倾向于输出训练数据中最常见的答案，这往往是肤浅的“直觉”。
*   **逻辑推理 (System 2)**: 人类在解决复杂问题时，会慢下来思考（丹尼尔·卡尼曼《思考，快与慢》）。LLM 也需要这个过程。

### 1.2 思考即计算 (Thought as Computation)
在 Transformer 架构中，**计算量是恒定的**（每生成一个 Token，消耗的 FLOPs 是一样的）。
*   如果你让模型直接输出答案，它只有生成那几个 Token 的计算时间。
*   如果你让模型先输出一段“思考过程” (Chain of Thought)，你实际上是**通过增加生成的 Token 数量，强行增加了模型的总计算量**。
*   **结论**: `Thought` 字段不仅仅是给人看的日志，它是模型进行逻辑推演的**计算缓冲区**。

## 2. ReAct 模式：学术界的事实标准

### 2.1 起源
ReAct (Reason + Act) 模式源于 2023 年普林斯顿和 Google 的论文《ReAct: Synergizing Reasoning and Acting in Language Models》。
它解决了两个极端问题：
1.  **只推理不行动 (CoT)**: 模型在那空想，产生幻觉，不与现实交互。
2.  **只行动不推理 (Direct Action)**: 模型像个无头苍蝇，疯狂乱调 API，没有规划。

### 2.2 循环机制
ReAct 强制模型遵循以下循环：
1.  **Thought**: 描述当前状态，规划下一步。
    *   *例子*: "用户想对比表。我已经查了 DB1，现在需要查 DB2。"
2.  **Action**: 生成具体的工具调用指令。
    *   *例子*: `list_tables(db2)`
3.  **Observation**: 接收工具的返回结果（这是由环境/代码反馈的，不是模型生成的）。
    *   *例子*: `['invoices', 'products']`
4.  **Repeat**: 带着新的 Observation，回到第 1 步。

## 3. 显式思考 vs. 隐式思考

### 3.1 Explicit CoT (当前主流)
在 GPT-4 和 Claude 3.5 中，我们需要通过 **Prompt Engineering** 强迫模型思考。
*   **System Prompt**: "Before calling any tool, please analyze the user's request and output your thought process enclosed in `<thought>` tags."
*   **优点**: 可解释性强，开发者能看到模型为什么出错。
*   **缺点**: 占用 Context Window，消耗 Token（贵）。

### 3.2 Hidden CoT (未来趋势 - OpenAI o1 / DeepSeek R1)
新一代“推理模型”将思考过程内化了。
*   **机制**: 模型在输出最终答案前，会在内部生成大量的“思维链 Token”，这些 Token 对用户不可见，但参与了概率计算。
*   **API 变化**:
    *   未来的 Agent API 可能不再需要我们手动维护 ReAct 循环的 Prompt。
    *   我们只需要给工具，模型会自动在内部进行多轮推演，然后直接给出最终的 Action 或 Answer。
*   **影响**: 这将极大简化 Agent 的开发（`client_v2.py` 里的 `mock_llm_router` 逻辑将变得更简单，甚至不需要），但可能会降低可解释性（我们不知道它在黑盒里想了什么）。

## 4. 总结
我们在文档中探讨的 ReAct 模式，是当前构建可靠 Agent 的**必修课**。即使未来推理模型普及，理解“思考即计算”的原理，对于优化 Agent 的性能依然至关重要。
