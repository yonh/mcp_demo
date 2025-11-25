from mcp.server.fastmcp import FastMCP
import sqlite3
from typing import List
import io
import sys
from contextlib import redirect_stdout
from urllib.parse import urlparse

# Try to import pymysql, but don't fail if not available
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# Initialize FastMCP server
mcp = FastMCP("database-explorer")

def _get_connection(db_type: str, connection_string: str):
    """
    Factory function for database connections.
    
    Args:
        db_type: 'sqlite' or 'mysql'
        connection_string: 
            - SQLite: '/path/to/database.sqlite'
            - MySQL: 'mysql://user:password@host:port/database'
    
    Returns:
        Database connection object
    """
    if db_type == 'sqlite':
        return sqlite3.connect(connection_string)
    elif db_type == 'mysql':
        if not MYSQL_AVAILABLE:
            raise ImportError("pymysql is not installed. Run: pip install pymysql")
        
        # Parse MySQL connection string
        parsed = urlparse(connection_string)
        return pymysql.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 3306,
            user=parsed.username,
            password=parsed.password or '',
            database=parsed.path.lstrip('/') if parsed.path else ''
        )
    else:
        raise ValueError(f"Unsupported db_type: {db_type}. Use 'sqlite' or 'mysql'.")

@mcp.tool()
def list_tables(db_type: str, connection_string: str) -> list[str]:
    """
    List all tables in the specified database.
    
    Args:
        db_type: 'sqlite' or 'mysql'
        connection_string:
            - SQLite: '/path/to/database.sqlite'
            - MySQL: 'mysql://user:password@host:port/database'
    
    Returns:
        List of table names
    """
    try:
        conn = _get_connection(db_type, connection_string)
        cursor = conn.cursor()
        
        if db_type == 'sqlite':
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        elif db_type == 'mysql':
            cursor.execute("SHOW TABLES;")
        
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        return [f"Error: {str(e)}"]

@mcp.tool()
def run_sql(db_type: str, connection_string: str, query: str) -> str:
    """
    Run a SQL query on the specified database.
    Use this for SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE, etc.
    
    Args:
        db_type: 'sqlite' or 'mysql'
        connection_string:
            - SQLite: '/path/to/database.sqlite'
            - MySQL: 'mysql://user:password@host:port/database'
        query: SQL query to execute
    
    Returns:
        Query result as string
    """
    try:
        conn = _get_connection(db_type, connection_string)
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

@mcp.tool()
def run_python(code: str) -> str:
    """
    Execute Python code and return stdout.
    WARNING: No sandbox. For testing only.
    
    Args:
        code: Python code to execute
    
    Returns:
        stdout output or error message
    """
    # Capture stdout
    output_buffer = io.StringIO()
    
    try:
        with redirect_stdout(output_buffer):
            exec(code, {"__builtins__": __builtins__})
        output = output_buffer.getvalue()
        return output if output else "Code executed successfully (no output)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"

if __name__ == "__main__":
    # Run the server
    mcp.run()
