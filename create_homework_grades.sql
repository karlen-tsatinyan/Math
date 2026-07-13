CREATE TABLE homework_grades(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_id INTEGER NOT NULL,

    assignment TEXT NOT NULL,

    grade REAL,

    max_grade REAL DEFAULT 100,

    percentage REAL,

    teacher_comment TEXT,

    grade_date DATE DEFAULT CURRENT_DATE,

    FOREIGN KEY(student_id)
    REFERENCES students(id)

);

