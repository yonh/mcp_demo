# 第六章：Code-as-Action - 从工具调用者到程序员

## 1. 为什么需要代码执行能力？

### 1.1 固定工具的局限性

在前面的章节中，我们的 Agent 只能调用**预定义的工具**：
- `list_tables` - 列出表
- `run_sql` - 执行SQL

这种模式的问题：
1. **工具爆炸**：每个新需求都要写一个新工具
2. **灵活性差**：无法处理临时性、一次性的任务
3. **维护成本高**：工具越多，维护负担越重

**例子**：如果用户问"把用户表导出为 CSV"，我们需要：
- Option 1: 新增 `export_to_csv` 工具
- Option 2: 让 Agent 自己写代码实现

Option 2 显然更优雅。

### 1.2 Code-as-Action 的优势

让 Agent 能够**写代码并执行**，它就拥有了**无限的工具集**：
- 需要爬虫？写 `requests` + `BeautifulSoup`
- 需要数据分析？写 `pandas`
- 需要画图？写 `matplotlib`
- 需要调用 API？写 `httpx`

**这就是 Code-as-Action 的核心理念**：把"工具"变成"能力"。

---

## 2. 实现方案演进

### 2.1 方案对比

| 方案 | 安全性 | 复杂度 | 适用场景 |
|------|--------|--------|----------|
| **MVP: 裸 exec()** | ❌ 极低 | ⭐ 简单 | 本地测试、学习演示 |
| **RestrictedPython** | ⚠️ 中等 | ⭐⭐ 中等 | 受限环境、内部工具 |
| **Docker 容器** | ✅ 高 | ⭐⭐⭐ 复杂 | 生产环境、多租户 |
| **E2B 云沙箱** | ✅ 极高 | ⭐⭐ 中等 | SaaS 产品、企业应用 |

我们采用**渐进式演进**：先实现 MVP 验证可行性，再逐步升级安全性。

---

## 3. MVP 实现：裸 exec()

### 3.1 Server 端：run_python 工具

**文件**: [server.py](file:///Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/server.py)

```python
import io
import sys
from contextlib import redirect_stdout

@mcp.tool()
def run_python(code: str) -> str:
    """
    Execute Python code and return stdout.
    WARNING: No sandbox. For testing only.
    """
    output_buffer = io.StringIO()
    
    try:
        with redirect_stdout(output_buffer):
            exec(code, {"__builtins__": __builtins__})
        output = output_buffer.getvalue()
        return output if output else "Code executed successfully (no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"
```

**关键点**：
1. **捕获输出**: 使用 `redirect_stdout` 捕获 `print()` 输出
2. **直接执行**: 使用 `exec()` 直接执行代码
3. **错误处理**: 捕获异常并返回错误信息

**安全警告** ⚠️：
- 使用 `exec()` 可以执行任意代码，包括 `import os; os.system('rm -rf /')`
- **禁止在生产环境使用**
- 仅用于本地测试和学习

### 3.2 Client 端：System Prompt 更新

**文件**: [client_v5.py](file:///Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/client_v5.py)

在 System Prompt 中添加：

```python
# AVAILABLE TOOLS:
1. list_tables(database_path) - List all tables in a database
2. run_sql(database_path, query) - Execute SQL queries
3. run_python(code) - Execute Python code for calculations, data processing, web scraping, etc.

# CODE EXECUTION CAPABILITIES:
You have access to a Python interpreter via the `run_python` tool.
Use it when you need to:
- Perform calculations (e.g., '计算 123 * 456')
- Process data (e.g., '生成斐波那契数列')
- Web scraping (e.g., '抓取网页内容' - use requests library)
- Data analysis (e.g., '分析这些数据' - can use pandas if available)

Example:
User: 计算 123 的平方
[Thought] 用户想计算平方，我可以用 run_python 工具。
[Action] run_python(code="print(123 ** 2)")
[Observation] 15129
```

**告诉 LLM**：
1. 你有一个 Python 解释器
2. 这些场景下可以用它
3. 如何调用（通过 `run_python` 工具）

---

## 4. 使用示例

### 4.1 简单计算

**用户输入**：
```
计算 123 * 456
```

**Agent 执行流程**：
```
[Thought]
用户想计算乘法，我可以用 run_python 工具。

[Action] run_python(code="print(123 * 456)")
[Observation] 56088
