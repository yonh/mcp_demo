import asyncio
import sys
import json
from typing import List, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolRequest, TextContent, ImageContent

# Paths (Hardcoded for this demo, but in real life would be config or user input)
SERVER_SCRIPT = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/server.py"
DB1_PATH = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/test_db_1.sqlite"
DB2_PATH = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/test_db_2.sqlite"

# --- Mock LLM "Brain" ---

def mock_llm_router(messages: List[Dict[str, Any]], tools: List[Any]) -> Dict[str, Any]:
    """
    Simulates an LLM (like GPT-4) making a decision based on conversation history and available tools.
    
    Returns a dict representing either a "tool_use" or a "text_response".
    """
    print("\n[Brain] Thinking...")
    
    # 1. Extract the latest user message
    user_messages = [m for m in messages if m["role"] == "user"]
    last_user_msg = user_messages[-1]["content"] if user_messages else ""
    
    # 2. Extract tool outputs from history to know what we already know
    tool_outputs = [m for m in messages if m["role"] == "tool"]
    known_dbs = []
    for output in tool_outputs:
        # We cheat a bit here for the mock: we look at the tool call ID or content to guess which DB was checked
        # In a real LLM, it reads the context window.
        content_str = str(output["content"])
        if "users" in content_str and "products" in content_str:
            # Simple heuristic: if we see table names, we assume we got data.
            # We need to know WHICH db it was. 
            # Let's look at the corresponding 'assistant' message that triggered this tool.
            # But for this simple mock, let's just count how many tool outputs we have.
            pass

    # 3. Simple State Machine Logic to simulate "Reasoning"
    
    # State 0: User asks to compare. We haven't checked anything.
    if "compare" in last_user_msg.lower() and len(tool_outputs) == 0:
        print("[Brain] Reason: User wants to compare. I have a 'list_tables' tool. I should check the first database.")
        return {
            "type": "tool_use",
            "name": "list_tables",
            "arguments": {"database_path": DB1_PATH},
            "thought": "I need to get the table list for the first database."
        }
    
    # State 1: We checked one DB. Now check the other.
    if len(tool_outputs) == 1:
        print("[Brain] Reason: I have data for one database. Now I need to check the second one to compare.")
        return {
            "type": "tool_use",
            "name": "list_tables",
            "arguments": {"database_path": DB2_PATH},
            "thought": "I need to get the table list for the second database."
        }
    
    # State 2: We have both. Time to answer.
    if len(tool_outputs) >= 2:
        print("[Brain] Reason: I have data for both databases. I can now perform the comparison logic.")
        
        # Parse the tool outputs to actually generate the answer
        # Output 1 (DB1)
        tables1_raw = tool_outputs[0]["content"] # List of TextContent
        tables1 = set([item.text for item in tables1_raw])
        
        # Output 2 (DB2)
        tables2_raw = tool_outputs[1]["content"]
        tables2 = set([item.text for item in tables2_raw])
        
        only_in_1 = tables1 - tables2
        only_in_2 = tables2 - tables1
        
        response_text = f"Comparison Complete:\n- Tables only in DB1: {only_in_1}\n- Tables only in DB2: {only_in_2}"
        
        return {
            "type": "text_response",
            "content": response_text
        }

    return {"type": "text_response", "content": "I'm not sure what to do."}

# --- Agent Core ---

async def run_agent_loop():
    # 1. Start MCP Server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 2. Dynamic Tool Discovery
            print("--- Agent Startup ---")
            print("Discovering tools...")
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"Found {len(tools)} tools: {[t.name for t in tools]}")
            
            # 3. Conversation Loop
            messages = []
            
            # Simulate User Input (in a real app, this comes from input())
            user_input = "Please compare the tables in test_db_1.sqlite and test_db_2.sqlite"
            print(f"\nUser: {user_input}")
            messages.append({"role": "user", "content": user_input})
            
            while True:
                # A. Ask "Brain" (LLM) what to do
                decision = mock_llm_router(messages, tools)
                
                if decision["type"] == "text_response":
                    print(f"\nAssistant: {decision['content']}")
                    messages.append({"role": "assistant", "content": decision['content']})
                    break # End conversation for this demo
                
                elif decision["type"] == "tool_use":
                    tool_name = decision["name"]
                    tool_args = decision["arguments"]
                    thought = decision.get("thought", "")
                    
                    print(f"\nAssistant (Thought): {thought}")
                    print(f"Assistant (Action): Call tool '{tool_name}' with {tool_args}")
                    
                    # Record assistant's intent to call tool
                    messages.append({
                        "role": "assistant", 
                        "content": None, 
                        "tool_calls": [{"name": tool_name, "args": tool_args}]
                    })
                    
                    # B. Execute Tool via MCP
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    
                    # C. Add Tool Output to History
                    # Note: result.content is a list of TextContent/ImageContent
                    print(f"Tool Output: Received {len(result.content)} items")
                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result.content
                    })
                    
                    # Loop continues... LLM will see the tool output in the next iteration

if __name__ == "__main__":
    asyncio.run(run_agent_loop())
