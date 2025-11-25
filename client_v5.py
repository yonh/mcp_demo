import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

# Configuration
SERVER_SCRIPT = (
    "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/server.py"
)
DB1_PATH = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/test_db_1.sqlite"
DB2_PATH = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/test_db_2.sqlite"

# Initialize OpenAI Client
client = OpenAI()
MODEL_NAME = "gpt-5.1"

print(f"--- OpenAI Client Configuration ---")
print(f"Base URL: {client.base_url}")
print(f"API Key:  {client.api_key[:8]}..." if client.api_key else "API Key:  Not Set")
print(f"-----------------------------------")


def mcp_tool_to_openai_tool(mcp_tool: Any) -> Dict[str, Any]:
    """Converts an MCP Tool definition to an OpenAI Tool definition."""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.inputSchema,
        },
    }


# ANSI Color Codes
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_colored(text: str, color: str, end: str = "\n"):
    print(f"{color}{text}{Colors.ENDC}", end=end)


async def run_agent_loop():
    # 1. Start MCP Server
    server_params = StdioServerParameters(
        command=sys.executable, args=[SERVER_SCRIPT], env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. Dynamic Tool Discovery
            print_colored("--- Agent Startup ---", Colors.HEADER)
            print("Discovering tools via MCP...")
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools

            # Convert to OpenAI Format
            openai_tools = [mcp_tool_to_openai_tool(t) for t in mcp_tools]
            print(
                f"Loaded {len(openai_tools)} tools: {[t['function']['name'] for t in openai_tools]}"
            )

            # 3. Conversation Loop
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized database administrator and programming agent. "
                        "Any response must translate to Chinese. "
                        "You can handle database operations, SQL, data analysis, and general programming tasks. "
                        "If a user asks about other topics, politely decline. "
                        "\n\n"
                        "# AVAILABLE TOOLS:\n"
                        "1. list_tables(database_path) - List all tables in a database\n"
                        "2. run_sql(database_path, query) - Execute SQL queries\n"
                        "3. run_python(code) - Execute Python code for calculations, data processing, web scraping, etc.\n"
                        "\n"
                        "# CODE EXECUTION CAPABILITIES:\n"
                        "You have access to a Python interpreter via the `run_python` tool.\n"
                        "Use it when you need to:\n"
                        "- Perform calculations (e.g., '计算 123 * 456')\n"
                        "- Process data (e.g., '生成斐波那契数列')\n"
                        "- Web scraping (e.g., '抓取网页内容' - use requests library)\n"
                        "- Data analysis (e.g., '分析这些数据' - can use pandas if available)\n"
                        "\n"
                        "Example:\n"
                        "User: 计算 123 的平方\n"
                        "[Thought] 用户想计算平方，我可以用 run_python 工具。\n"
                        "[Action] run_python(code=\"print(123 ** 2)\")\n"
                        "[Observation] 15129\n"
                        "\n"
                        "# CRITICAL RULES FOR TOOL USAGE:\n"
                        "1. When you need to call a tool, you MUST use the tool_calls mechanism provided by the API.\n"
                        "2. NEVER write JSON manually in your response to simulate a tool call.\n"
                        "3. NEVER say 'I will call X tool' without actually calling it.\n"
                        "4. **MANDATORY**: You MUST output a [Thought] in your text response BEFORE calling any tool.\n"
                        "   - The API allows you to return both 'content' (text) and 'tool_calls' (function calls) in the same response.\n"
                        "   - Always use this feature: output your thought first, then call the tool.\n"
                        "\n"
                        "# REASONING FORMAT (ReAct):\n"
                        "Before taking any action, output your thought process in this format:\n"
                        "\n"
                        "[Thought]\n"
                        "Your reasoning here (what you understand, what you plan to do).\n"
                        "\n"
                        "Then:\n"
                        "- If you need data from tools: Output the thought, then call the tool in the same response.\n"
                        "- If you already have enough information: Provide your answer after the blank line.\n"
                    ),
                }
            ]

            print("\n" + "=" * 50)
            print_colored("🤖 DB Agent V5 Online (Code Execution Mode)", Colors.CYAN)
            print(f"Connected to DBs:\n1. {DB1_PATH}\n2. {DB2_PATH}")
            print("Type 'exit', 'quit', or 'bye' to stop.")
            print("=" * 50 + "\n")

            while True:
                try:
                    # User Input (Green)
                    user_input = input(f"{Colors.GREEN}User: {Colors.ENDC}").strip()
                except EOFError:
                    break

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("Goodbye!")
                    break

                messages.append({"role": "user", "content": user_input})

                # Agent Execution Loop (Handle Tool Calls)
                while True:
                    # print(".", end="", flush=True) # Thinking indicator removed in favor of explicit thoughts
                    try:
                        response = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=messages,
                            tools=openai_tools,
                            tool_choice="auto",
                        )
                    except Exception as e:
                        print_colored(f"\nError calling LLM: {e}", Colors.RED)
                        return

                    response_message = response.choices[0].message
                    messages.append(response_message)

                    content = response_message.content
                    if content:
                        # Check if it contains a thought
                        if "[Thought]" in content:
                            # Split by double newline or look for pattern
                            # Expected format: "[Thought]\nReasoning here...\n\nActual response"
                            lines = content.split("\n")
                            thought_lines = []
                            response_lines = []
                            in_thought = False
                            thought_ended = False

                            for line in lines:
                                if line.strip() == "[Thought]":
                                    in_thought = True
                                    thought_lines.append(line)
                                elif in_thought and not thought_ended:
                                    if line.strip() == "":
                                        # Empty line marks end of thought
                                        thought_ended = True
                                    else:
                                        thought_lines.append(line)
                                else:
                                    response_lines.append(line)

                            # Print Thought in Yellow
                            if thought_lines:
                                print_colored(
                                    f"\n{chr(10).join(thought_lines)}", Colors.YELLOW
                                )

                            # Print the rest (if any) in Cyan
                            if response_lines and any(
                                line.strip() for line in response_lines
                            ):
                                print_colored(
                                    f"\n{chr(10).join(response_lines).strip()}",
                                    Colors.CYAN,
                                )
                        else:
                            print_colored(f"\nAssistant: {content}", Colors.CYAN)

                    if response_message.tool_calls:
                        for tool_call in response_message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)

                            # Tool Call (Magenta)
                            print_colored(
                                f"\n[Action] {tool_name}({tool_args})", Colors.HEADER
                            )

                            try:
                                result = await session.call_tool(
                                    tool_name, arguments=tool_args
                                )
                                tool_output_text = str(
                                    [item.text for item in result.content]
                                )
                            except Exception as e:
                                tool_output_text = f"Error: {str(e)}"

                            # Tool Result (Green - Observation in ReAct)
                            # Truncate if too long
                            display_output = (
                                tool_output_text[:300] + "..."
                                if len(tool_output_text) > 300
                                else tool_output_text
                            )
                            print_colored(
                                f"[Observation] {display_output}", Colors.GREEN
                            )

                            messages.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": tool_output_text,
                                }
                            )
                        # Continue loop to let LLM see the tool output and decide next step
                    else:
                        # No tool calls, and we already printed the content above.
                        # Save conversation history for debugging
                        with open("messages.json", "w") as f:
                            json.dump(
                                messages,
                                f,
                                indent=2,
                                default=lambda o: o.model_dump()
                                if hasattr(o, "model_dump")
                                else str(o),
                            )
                        break


if __name__ == "__main__":
    try:
        asyncio.run(run_agent_loop())
    except KeyboardInterrupt:
        print("\nGoodbye!")
