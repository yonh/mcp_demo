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

# Initialize OpenAI Client (Expects OPENAI_API_KEY env var)
# You can also set base_url for Ollama/DeepSeek e.g. base_url="http://localhost:11434/v1"
client = OpenAI()
MODEL_NAME = "gpt-4o"  # Or "llama3", "deepseek-chat"

print(f"--- OpenAI Client Configuration ---")
print(f"Base URL: {client.base_url}")
print(f"API Key:  {client.api_key[:8]}..." if client.api_key else "API Key:  Not Set")
print(f"-----------------------------------")


def mcp_tool_to_openai_tool(mcp_tool: Any) -> Dict[str, Any]:
    """
    Converts an MCP Tool definition to an OpenAI Tool definition.
    """
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.inputSchema,
        },
    }


async def run_agent_loop():
    # 1. Start MCP Server
    server_params = StdioServerParameters(
        command=sys.executable, args=[SERVER_SCRIPT], env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 2. Dynamic Tool Discovery
            print("--- Agent Startup ---")
            print("Discovering tools via MCP...")
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools

            # Convert to OpenAI Format
            openai_tools = [mcp_tool_to_openai_tool(t) for t in mcp_tools]
            print(
                f"Loaded {len(openai_tools)} tools for LLM: {[t['function']['name'] for t in openai_tools]}"
            )

            # 3. Conversation Loop
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful database assistant. Use the supplied tools to answer user questions.",
                }
            ]

            # Initial User Input
            user_input = f"Please compare the tables in these two databases:\n1. {DB1_PATH}\n2. {DB2_PATH}"
            print(f"\nUser: {user_input}")
            messages.append({"role": "user", "content": user_input})

            while True:
                print("\n[LLM] Thinking...")
                try:
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        tools=openai_tools,
                        tool_choice="auto",
                    )
                except Exception as e:
                    print(f"Error calling LLM: {e}")
                    print("Make sure OPENAI_API_KEY is set.")
                    break

                response_message = response.choices[0].message

                # Check if LLM wants to call a tool
                if response_message.tool_calls:
                    print(
                        f"[LLM] Decided to call {len(response_message.tool_calls)} tools."
                    )

                    # Append the assistant's message (with tool calls) to history
                    messages.append(response_message)

                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        print(
                            f"Assistant (Action): Call '{tool_name}' with {tool_args}"
                        )

                        # Execute via MCP
                        try:
                            result = await session.call_tool(
                                tool_name, arguments=tool_args
                            )

                            # Parse result text
                            # FastMCP returns list of TextContent
                            tool_output_text = str(
                                [item.text for item in result.content]
                            )

                        except Exception as e:
                            tool_output_text = f"Error executing tool: {str(e)}"

                        print(f"Tool Output: {tool_output_text[:100]}")  # Truncate log

                        # Append Tool Output to history
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_name,
                                "content": tool_output_text,
                            }
                        )

                    # Loop continues to let LLM see the output
                else:
                    # No tool calls, just text response. We are done.
                    print(f"\nAssistant: {response_message.content}")
                    messages.append(response_message)

                    with open("messages.json", "w") as f:
                        json.dump(
                            messages, f, indent=2, default=lambda o: o.model_dump()
                        )

                    print("[END]")
                    break


if __name__ == "__main__":
    asyncio.run(run_agent_loop())
