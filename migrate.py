import sqlite3
import importlib

from config import DATABASE_NAME



MIGRATIONS = [

    (
        1,
        "Initial schema version table",
        "migrations.v001_schema_version"
    ),

    (
        2,
        "Calendar upgrade",
        "migrations.v002_calendar_upgrade"
    ),

    (
        3,
        "Homework Grades",
        "migrations.v003_homework_grades"
    ),

]



def ensure_version_table():

    conn = sqlite3.connect(DATABASE_NAME)

    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version(

            version INTEGER PRIMARY KEY,

            description TEXT,

            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    conn.commit()

    conn.close()



def applied_versions():

    conn = sqlite3.connect(DATABASE_NAME)

    cur = conn.cursor()

    cur.execute(
        "SELECT version FROM schema_version"
    )

    versions = {

        row[0]

        for row in cur.fetchall()

    }

    conn.close()

    return versions



def record(version, description):

    conn = sqlite3.connect(DATABASE_NAME)

    cur = conn.cursor()

    cur.execute(

        """

        INSERT INTO schema_version

        (

        version,

        description

        )

        VALUES

        (?,?)

        """,

        (

            version,

            description

        )

    )

    conn.commit()

    conn.close()



def migrate():

    ensure_version_table()

    completed = applied_versions()

    for version, description, module_name in MIGRATIONS:

        if version not in completed:

            print(f"Applying migration {version}: {description}")

            module = importlib.import_module(module_name)

            module.migrate()

            record(version, description)

            print("Done.")



if __name__ == "__main__":

    migrate()