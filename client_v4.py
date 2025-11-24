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
MODEL_NAME = "gpt-4o"

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
                f"Loaded {len(openai_tools)} tools: {[t['function']['name'] for t in openai_tools]}"
            )

            # 3. Conversation Loop
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized database administrator agent. "
                        "You ONLY answer questions related to database operations, SQL, and data analysis. "
                        "If a user asks about other topics (e.g., weather, general knowledge, jokes), "
                        "politely decline and remind them that you are a database tool. "
                        "You have access to tools to list tables and execute SQL queries. "
                        "Always use the provided tools to verify data before answering."
                    ),
                }
            ]

            print("\n" + "="*50)
            print("🤖 DB Agent V4 Online")
            print(f"Connected to DBs:\n1. {DB1_PATH}\n2. {DB2_PATH}")
            print("Type 'exit' or 'quit' to stop.")
            print("="*50 + "\n")

            while True:
                try:
                    user_input = input("\nUser: ").strip()
                except EOFError:
                    break

                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break

                messages.append({"role": "user", "content": user_input})

                # Agent Execution Loop (Handle Tool Calls)
                while True:
                    print(".", end="", flush=True) # Thinking indicator
                    try:
                        response = client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=messages,
                            tools=openai_tools,
                            tool_choice="auto",
                        )
                    except Exception as e:
                        print(f"\nError calling LLM: {e}")
                        return

                    response_message = response.choices[0].message
                    messages.append(response_message)

                    if response_message.tool_calls:
                        # print(f"\n[Tool Calls]: {len(response_message.tool_calls)}")
                        
                        for tool_call in response_message.tool_calls:
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            
                            print(f"\n[Action] {tool_name}({tool_args})")

                            try:
                                result = await session.call_tool(
                                    tool_name, arguments=tool_args
                                )
                                tool_output_text = str(
                                    [item.text for item in result.content]
                                )
                            except Exception as e:
                                tool_output_text = f"Error: {str(e)}"

                            # print(f"[Result] {tool_output_text[:100]}...")

                            messages.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": tool_name,
                                    "content": tool_output_text,
                                }
                            )
                        # Continue loop to send tool outputs back to LLM
                    else:
                        # Final response from LLM
                        print(f"\n\nAssistant: {response_message.content}")
                        break

if __name__ == "__main__":
    try:
        asyncio.run(run_agent_loop())
    except KeyboardInterrupt:
        print("\nGoodbye!")
