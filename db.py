import os
import pyodbc

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{soccerregistry},1433;"
        f"DATABASE={SoccerRegistryDB};"
        f"UID={anleylafleur@hotmail.com};"
        f"PWD={#Champ195472};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )

    return pyodbc.connect(conn_str, timeout=60)
