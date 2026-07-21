import sqlite3
import psycopg2
from config import DATABASE_NAME

# 🔑 REPLACE WITH YOUR SUPABASE CONNECTION STRING FROM STREAMLIT SECRETS
SUPABASE_URI = "postgresql://postgres:YOUR_PASSWORD@db.xxxxxx.supabase.co:5432/postgres"

def push_sqlite_to_supabase():
    print("Connecting to local SQLite database...")
    sqlite_conn = sqlite3.connect(DATABASE_NAME)
    sqlite_cur = sqlite_conn.cursor()

    # Get all table names in local database.db
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in sqlite_cur.fetchall()]

    print(f"Found tables in local DB: {tables}")

    print("Connecting to Supabase PostgreSQL...")
    pg_conn = psycopg2.connect(SUPABASE_URI)
    pg_cur = pg_conn.cursor()

    for table in tables:
        print(f"\nProcessing table: {table}...")

        # 1. Get column names and types from SQLite
        sqlite_cur.execute(f"PRAGMA table_info('{table}');")
        columns_info = sqlite_cur.fetchall()
        
        # Build CREATE TABLE statement for PostgreSQL
        col_defs = []
        col_names = []
        for col in columns_info:
            col_name = col[1]
            col_type = col[2].upper()
            is_pk = col[5]

            # Map SQLite types to Postgres types
            if "INT" in col_type:
                pg_type = "SERIAL PRIMARY KEY" if is_pk else "INTEGER"
            elif "TEXT" in col_type or "VARCHAR" in col_type:
                pg_type = "TEXT"
            elif "REAL" in col_type or "FLOAT" in col_type:
                pg_type = "DOUBLE PRECISION"
            else:
                pg_type = "TEXT"

            col_defs.append(f'"{col_name}" {pg_type}')
            col_names.append(f'"{col_name}"')

        create_sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)});'
        pg_cur.execute(create_sql)

        # 2. Fetch all data rows from SQLite
        sqlite_cur.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cur.fetchall()

        if rows:
            placeholders = ", ".join(["%s"] * len(col_names))
            insert_sql = f'INSERT INTO "{table}" ({", ".join(col_names)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;'
            pg_cur.executemany(insert_sql, rows)
            print(f"  --> Copied {len(rows)} rows into '{table}'.")
        else:
            print(f"  --> Table '{table}' created (0 rows to copy).")

    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
    print("\n✅ Migration to Supabase complete! All tables and data are live.")

if __name__ == "__main__":
    push_sqlite_to_supabase()
