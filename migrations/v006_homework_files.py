import sqlite3
from config import DATABASE_NAME


def add_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall()]

    if column not in cols:
        cursor.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )


def migrate():

    conn = sqlite3.connect(DATABASE_NAME)
    cur = conn.cursor()

    add_column(cur, "homework", "assignment_file", "TEXT")
    add_column(cur, "homework", "student_file", "TEXT")

    add_column(cur, "homework", "deleted_assignment_file", "INTEGER DEFAULT 0")
    add_column(cur, "homework", "deleted_student_file", "INTEGER DEFAULT 0")

    conn.commit()
    conn.close()

    print("Homework files upgrade completed.")