from db import get_connection

try:
    conn = get_connection()
    print("SUCCESS: Connected to Azure SQL")
    conn.close()
except Exception as e:
    print("ERROR:", e)