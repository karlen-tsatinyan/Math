from migrations.migration_utils import execute


SQL = """

CREATE TABLE IF NOT EXISTS schema_version(

    version INTEGER PRIMARY KEY,

    description TEXT,

    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

"""


def migrate():

    execute(SQL)


if __name__ == "__main__":

    migrate()