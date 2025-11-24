import sqlite3
import os

DB_DIR = "/Users/yonh/.gemini/antigravity/playground/crystal-quasar/db_compare_mcp"
DB1_PATH = os.path.join(DB_DIR, "test_db_1.sqlite")
DB2_PATH = os.path.join(DB_DIR, "test_db_2.sqlite")

def create_db(path, tables):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT)")
    conn.commit()
    conn.close()
    print(f"Created database at {path} with tables: {tables}")

if __name__ == "__main__":
    # DB 1 has 'users', 'products', 'orders'
    create_db(DB1_PATH, ["users", "products", "orders"])
    
    # DB 2 has 'users', 'products', 'invoices' (orders is missing, invoices is new)
    create_db(DB2_PATH, ["users", "products", "invoices"])
