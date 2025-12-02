import sqlite3
from src.db.sqlite import get_conn
from src.auth.security import hash_password

def init_db():
    con = get_conn(); cur = con.cursor()

    # --- tablolar ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','coordinator')),
        department_id INTEGER NULL,
        FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE SET NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT,
        capacity INTEGER NOT NULL DEFAULT 0,
        rows INTEGER DEFAULT 0,
        cols INTEGER DEFAULT 0,
        group_size INTEGER DEFAULT 2,
        UNIQUE(department_id, code),
        FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        instructor TEXT,
        class_level INTEGER,
        compulsory INTEGER DEFAULT 1,
        UNIQUE(department_id, code),
        FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_id INTEGER NOT NULL,
        student_no TEXT NOT NULL,
        full_name TEXT NOT NULL,
        class_level INTEGER,
        UNIQUE(department_id, student_no),
        FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS enrollments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id  INTEGER NOT NULL,
        UNIQUE(student_id, course_id),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY(course_id)  REFERENCES courses(id)  ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exams(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        exam_type TEXT NOT NULL,
        date TEXT NOT NULL,         -- YYYY-MM-DD
        start_time TEXT NOT NULL,   -- HH:MM
        duration_min INTEGER NOT NULL,
        FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_rooms(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
        FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE
    )""")

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_coord_per_dep
        ON users(department_id) WHERE role='coordinator'
        """)

    
    departments = [
        "Bilgisayar Mühendisliği",
        "Yazılım Mühendisliği",
        "Elektrik Mühendisliği",
        "Elektronik Mühendisliği",
        "İnşaat Mühendisliği",
    ]
    for name in departments:
        cur.execute("INSERT OR IGNORE INTO departments(name) VALUES(?)", (name,))

    
    cur.execute("SELECT id, name FROM departments")
    dep_map = {r["name"]: r["id"] for r in cur.fetchall()}

    
    cur.execute("SELECT 1 FROM users WHERE username=?", ("admin",))
    if not cur.fetchone():
        cur.execute("""INSERT INTO users(username, password_hash, role, department_id)
                       VALUES(?,?, 'admin', NULL)""",
                    ("admin", hash_password("123")))



    con.commit()
    con.close()
    print("✅ DB hazır (tablolar + 5 bölüm + admin & koordinatörler).")

if __name__ == "__main__":
    init_db()
