# 03. 实战篇 (一)：构建 MCP 工具 (MVP)

本章深度复盘我们构建数据库对比 MVP 的过程。我们将不仅展示代码，更要解释**为什么这么写**，以及在开发过程中遇到的真实陷阱。

## 1. 架构设计决策

### 1.1 为什么选择 FastMCP？
在 `server.py` 中，我们使用了 `mcp.server.fastmcp`。
*   **背景**: 标准的 MCP Server 实现需要处理复杂的 JSON-RPC 消息循环、生命周期管理和错误处理。
*   **FastMCP**: 这是一个高层封装（类似 FastAPI 之于 Starlette）。它通过装饰器 `@mcp.tool()` 自动处理了：
    1.  函数签名解析（自动生成 JSON Schema）。
    2.  类型检查。
    3.  RPC 消息路由。
*   **价值**: 它让我们专注于业务逻辑（查数据库），而不是协议细节。

### 1.2 为什么选择 stdio 通信？
在 `client.py` 中，我们通过 `StdioServerParameters` 连接 Server。
*   **原理**: Client 启动 Server 作为一个子进程，通过**标准输入 (stdin)** 发送请求，通过**标准输出 (stdout)** 接收响应。
*   **优势**:
    1.  **安全**: 不占用网络端口，不暴露给公网。
    2.  **简单**: 不需要配置 IP 和防火墙。
    3.  **兼容性**: 任何能运行命令行的环境都能用。
*   **注意**: 这也意味着 Server 的日志不能直接打印到 stdout，否则会破坏协议格式。FastMCP 会自动将日志重定向到 stderr。

## 2. 代码深度解析

### 2.1 Server 端 (`server.py`)
```python
@mcp.tool()
def list_tables(database_path: str) -> list[str]:
    """
    List all table names in a SQLite database.
    Args:
        database_path: Absolute path to the SQLite database file.
    """
    # ... 实现代码 ...
```
*   **Docstring 的重要性**: 注意这里的文档字符串。FastMCP 会自动将其提取为工具的 `description`。LLM **完全依赖**这段文字来理解这个工具是干嘛的。如果写得含糊，LLM 就不会调用。
*   **类型提示**: `database_path: str` 告诉 FastMCP 参数类型，它会在生成的 Schema 中标记为 `string`。

### 2.2 Client 端 (`client.py`)
```python
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # ...
```
*   **Session 管理**: `ClientSession` 负责维护 MCP 的连接状态。`initialize()` 这一步至关重要，它完成了“握手”，Client 此时会收到 Server 的能力清单。

## 3. 踩坑实录：FastMCP 的返回格式

在开发过程中，我们遇到了一个典型的解析错误。

### 错误现场
```python
# 原始代码
import json
tables = json.loads(result.content[0].text)
# 报错: JSONDecodeError
```

### 根本原因
我们误以为 `list_tables` 返回的 Python `list` 会被自动序列化成一个 JSON 字符串。
但实际上，MCP 协议规定 `CallToolResult` 的 `content` 是一个 `Content` 对象列表（通常是 `TextContent` 或 `ImageContent`）。
FastMCP 的默认行为是：将 Python 函数的返回值，转换成**一系列**的 `TextContent`，或者将复杂对象转成文本。

### 修正逻辑
```python
# 修正后
# result.content 是一个 TextContent 对象的列表
# 每个 TextContent 代表列表中的一个元素（如果是简单列表）
# 或者整个返回值被序列化在 text 属性中
tables = [item.text for item in result.content]
```
*经验教训*: 在对接 MCP 时，必须严格检查 `CallToolResult` 的结构，不要想当然地认为它就是 JSON。

## 4. 总结
MVP 阶段虽然简单，但它打通了 **Client -> Protocol -> Server -> DB** 的全链路。这为后续引入 LLM 决策奠定了物理基础。
