# MCP Database Comparator Demo

这是一个基于 **Model Context Protocol (MCP)** 的数据库对比工具演示项目。它展示了如何从零构建一个 Agent 系统，从最简单的脚本到接入真实 LLM 的完整进化过程。

## 📂 项目结构

| 文件 | 说明 | 进化阶段 |
| :--- | :--- | :--- |
| `server.py` | **MCP Server**。基于 `FastMCP`，暴露了 `list_tables` 工具。 | 核心组件 |
| `client.py` | **Client V1 (MVP)**。硬编码调用逻辑，验证通路。 | Phase 1 |
| `client_v2.py` | **Client V2 (Mock Agent)**。实现了 ReAct 循环和动态工具发现，使用模拟大脑。 | Phase 2 |
| `client_v3.py` | **Client V3 (Real Agent)**。接入 OpenAI API，真正的智能体。 | Phase 4 |
| `create_dummy_dbs.py` | 测试数据生成脚本。 | 辅助工具 |
| `docs/` | **[学习文档](./docs/README.md)**。详细的技术原理和复盘。 | 文档 |

## 🚀 快速开始

### 1. 环境准备

本项目使用 Python 3。建议创建虚拟环境：

```bash
# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install mcp openai
```

### 2. 生成测试数据

首先运行此脚本，生成 `test_db_1.sqlite` 和 `test_db_2.sqlite`：

```bash
python3 create_dummy_dbs.py
```

### 3. 运行演示

#### 🟢 阶段一：MVP (验证连通性)
不依赖 LLM，直接测试 Client 能否通过 MCP 协议调用 Server。
```bash
python3 client.py
```

#### 🟡 阶段二：Mock Agent (理解原理)
不依赖 API Key，使用模拟逻辑演示 ReAct 思考循环。
```bash
python3 client_v2.py
```

#### 🔴 阶段三：Real Agent (实战)
接入真实 LLM。需要设置 API Key。

**使用 OpenAI:**
```bash
export OPENAI_API_KEY="sk-..."
python3 client_v3.py
```

**使用本地 Ollama / DeepSeek:**
```bash
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="ollama" # 任意非空值
python3 client_v3.py
```

## 📚 深入学习

如果你想了解代码背后的设计思想（如“胶水代码地狱”、Google A2A 协议、Token 爆炸问题），请阅读 **[docs/README.md](./docs/README.md)** 中的系列文档。
