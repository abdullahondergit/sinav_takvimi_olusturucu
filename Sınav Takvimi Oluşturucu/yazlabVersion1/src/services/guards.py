from __future__ import annotations
from dataclasses import dataclass
from src.db.sqlite import get_connection

@dataclass
class DomainError(Exception):
    message: str
    def __str__(self):
        return self.message

def classrooms_ready(department_id: int | None = None) -> bool:
    """
    Derslik bilgilerinin tam olduğunu kontrol eder.
    'seat_group' sütunu varsa dahil eder, yoksa kapasite / satır / sütun kriteri yeterlidir.
    """
    con = get_connection()
    cur = con.cursor()

    cur.execute("PRAGMA table_info(rooms)")
    cols = {r["name"] for r in cur.fetchall()}

    if "seat_group" in cols:
        extra_cond = "AND seat_group IN (2,3)"
    else:
        extra_cond = ""

    if department_id is not None:
        cur.execute(f"""
            SELECT COUNT(*) AS c
            FROM rooms
            WHERE department_id=? AND capacity>0 AND rows>0 AND cols>0 {extra_cond}
        """, (department_id,))
    else:
        cur.execute(f"""
            SELECT COUNT(*) AS c
            FROM rooms
            WHERE capacity>0 AND rows>0 AND cols>0 {extra_cond}
        """)

    ok = cur.fetchone()["c"] > 0
    con.close()
    return ok


def ensure_classrooms_ready(department_id: int | None):
    if not classrooms_ready(department_id):
        raise DomainError("Derslik bilgileri tamamlanmadan bu işlem yapılamaz.")

def imports_ready(department_id: int | None) -> bool:
    """
    'Programlama' sekmesini göstermek için asgari koşul:
      - İlgili bölümde en az 1 ders (courses)
      - En az 1 öğrenci (students)
      - Bu bölüm dersleriyle ilişkilendirilmiş en az 1 kayıt (enrollments)
    """
    con = get_connection(); cur = con.cursor()


    if department_id is not None:
        cur.execute("SELECT COUNT(*) AS c FROM courses WHERE department_id=?", (department_id,))
    else:
        cur.execute("SELECT COUNT(*) AS c FROM courses")
    has_courses = cur.fetchone()["c"] > 0

    cur.execute("PRAGMA table_info(students)")
    cols = {r["name"] for r in cur.fetchall()}
    if "department_id" in cols and department_id is not None:
        cur.execute("SELECT COUNT(*) AS c FROM students WHERE department_id=?", (department_id,))
    else:
        cur.execute("SELECT COUNT(*) AS c FROM students")
    has_students = cur.fetchone()["c"] > 0

    if department_id is not None:
        cur.execute("""
            SELECT COUNT(*) AS c
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE c.department_id=?
        """, (department_id,))
    else:
        cur.execute("SELECT COUNT(*) AS c FROM enrollments")
    has_enrollments = cur.fetchone()["c"] > 0

    con.close()
    return has_courses and has_students and has_enrollments
