from database import get_connection


def column_exists(cursor, table, column):

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = %s
            AND column_name = %s
        )
        """,
        (
            table,
            column
        )
    )

    return cursor.fetchone()[0]


def add_column(cursor, table, column, definition):

    if not column_exists(
        cursor,
        table,
        column
    ):

        cursor.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )
