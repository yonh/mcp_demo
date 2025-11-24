from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import List

# Initialize FastMCP server
mcp = FastMCP("sqlite-explorer")

@mcp.tool()
def list_tables(database_path: str) -> list[str]:
    """List all tables in the specified SQLite database."""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        return [f"Error: {str(e)}"]

@mcp.tool()
def run_sql(database_path: str, query: str) -> str:
    """
    Run a SQL query on the specified SQLite database.
    Use this for SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE, etc.
    Returns the result of the query as a string representation.
    """
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(query)
        
        # If the query returns rows (like SELECT), fetch them
        if cursor.description:
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            result = f"Columns: {columns}\nRows:\n"
            for row in rows:
                result += f"{row}\n"
        else:
            # For DDL/DML (INSERT, UPDATE, DELETE, CREATE, DROP), commit and return success message
            conn.commit()
            result = "Query executed successfully."
            
        conn.close()
        return result
    except Exception as e:
        return f"Error executing query: {str(e)}"

if __name__ == "__main__":
    # Run the server
    mcp.run()
