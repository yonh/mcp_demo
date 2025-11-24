from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import List

# Initialize FastMCP server
mcp = FastMCP("sqlite-explorer")

@mcp.tool()
def list_tables(database_path: str) -> List[str]:
    """
    List all table names in a SQLite database.
    
    Args:
        database_path: Absolute path to the SQLite database file.
    """
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Query to get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return tables
    except Exception as e:
        return [f"Error: {str(e)}"]

if __name__ == "__main__":
    # Run the server
    mcp.run()
