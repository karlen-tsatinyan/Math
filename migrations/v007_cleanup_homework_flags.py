from database import get_connection


def migrate():

    conn = get_connection()

    conn.autocommit = True

    cursor = conn.cursor()


    cursor.execute(
        """
        ALTER TABLE homework
        DROP COLUMN IF EXISTS deleted_assignment_file
        """
    )


    cursor.execute(
        """
        ALTER TABLE homework
        DROP COLUMN IF EXISTS deleted_student_file
        """
    )


    cursor.close()

    conn.close()


    print(
        "Homework flag cleanup completed."
    )


if __name__ == "__main__":

    migrate()
