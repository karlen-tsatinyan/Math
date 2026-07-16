import sqlite3

from config import DATABASE_NAME


def add_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [r[1] for r in cursor.fetchall()]

    if column not in columns:
        cursor.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )


def migrate():

    conn = sqlite3.connect(DATABASE_NAME)

    cur = conn.cursor()

    add_column(cur, "homework", "title", "TEXT")
    add_column(cur, "homework", "curriculum_topic", "TEXT")
    add_column(cur, "homework", "assigned_date", "DATE")
    add_column(cur, "homework", "due_date", "DATE")
    add_column(cur, "homework", "priority", "TEXT DEFAULT 'Normal'")
    add_column(cur, "homework", "grade", "TEXT")
    add_column(cur, "homework", "submitted_at", "TIMESTAMP")
    add_column(cur, "homework", "reviewed_at", "TIMESTAMP")
    add_column(cur, "homework", "archived", "INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

    print("Homework upgrade completed.")