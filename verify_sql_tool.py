import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Path to the server script
SERVER_SCRIPT = "./server.py"

async def run():
    # Start the server as a subprocess
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # 1. Create a table
            print("--- Creating Table 'test_users' ---")
            result = await session.call_tool(
                "run_sql",
                arguments={
                    "database_path": "test_db_1.sqlite",
                    "query": "CREATE TABLE IF NOT EXISTS test_users (id INTEGER PRIMARY KEY, name TEXT);"
                }
            )
            print(f"Result: {result.content[0].text}\n")

            # 2. Insert data
            print("--- Inserting Data ---")
            result = await session.call_tool(
                "run_sql",
                arguments={
                    "database_path": "test_db_1.sqlite",
                    "query": "INSERT INTO test_users (name) VALUES ('Alice'), ('Bob');"
                }
            )
            print(f"Result: {result.content[0].text}\n")

            # 3. Select data
            print("--- Selecting Data ---")
            result = await session.call_tool(
                "run_sql",
                arguments={
                    "database_path": "test_db_1.sqlite",
                    "query": "SELECT * FROM test_users;"
                }
            )
            print(f"Result: {result.content[0].text}\n")

            # 4. Drop table
            print("--- Dropping Table ---")
            result = await session.call_tool(
                "run_sql",
                arguments={
                    "database_path": "test_db_1.sqlite",
                    "query": "DROP TABLE test_users;"
                }
            )
            print(f"Result: {result.content[0].text}\n")

if __name__ == "__main__":
    asyncio.run(run())
