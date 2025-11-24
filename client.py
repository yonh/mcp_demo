import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Paths
SERVER_SCRIPT = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/server.py"
DB1_PATH = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/test_db_1.sqlite"
DB2_PATH = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp/test_db_2.sqlite"

async def run():
    # Define server parameters
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Tool 1: Get tables from DB 1
            print(f"Agent: Calling list_tables for {DB1_PATH}...")
            result1 = await session.call_tool("list_tables", arguments={"database_path": DB1_PATH})
            tables1 = set(result1.content[0].text) # Assuming the server returns a list, but FastMCP might wrap it. 
                                                   # Actually FastMCP returns the result directly in content as text usually JSON.
                                                   # Let's inspect the result structure in a real run, but for now assume standard MCP response.
            # FastMCP returns JSON string in text content usually. 
            # FastMCP returns a list of TextContent items, one for each element in the returned list.
            tables1_list = [item.text for item in result1.content]
            print(f"Result DB1: {tables1_list}")

            # Tool 2: Get tables from DB 2
            print(f"Agent: Calling list_tables for {DB2_PATH}...")
            result2 = await session.call_tool("list_tables", arguments={"database_path": DB2_PATH})
            tables2_list = [item.text for item in result2.content]
            print(f"Result DB2: {tables2_list}")

            # Agent Logic: Compare
            set1 = set(tables1_list)
            set2 = set(tables2_list)

            only_in_1 = set1 - set2
            only_in_2 = set2 - set1
            
            print("\n--- Comparison Result ---")
            if not only_in_1 and not only_in_2:
                print("Both databases have the same tables.")
            else:
                if only_in_1:
                    print(f"Tables only in DB1: {only_in_1}")
                if only_in_2:
                    print(f"Tables only in DB2: {only_in_2}")

if __name__ == "__main__":
    asyncio.run(run())
