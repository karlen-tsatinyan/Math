import sqlite3

from config import DATABASE_NAME



conn = sqlite3.connect(
    DATABASE_NAME
)

cursor = conn.cursor()



cursor.execute("""

CREATE TABLE IF NOT EXISTS progress_notes

(

id INTEGER PRIMARY KEY AUTOINCREMENT,

student_id INTEGER NOT NULL,

lesson_date TEXT,

topic TEXT,

strengths TEXT,

improvements TEXT,

homework TEXT,

next_steps TEXT,

created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


FOREIGN KEY(student_id)

REFERENCES students(id)

)

""")



conn.commit()

conn.close()



print(
    "Progress notes table created."
)