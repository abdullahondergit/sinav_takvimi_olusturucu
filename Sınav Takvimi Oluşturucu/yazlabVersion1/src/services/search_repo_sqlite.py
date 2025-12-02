from src.db.sqlite import get_conn

def get_student_courses(student_no: str, department_id: int | None = None):
    con = get_conn(); cur = con.cursor()
    if department_id:
        cur.execute("""
            SELECT c.code, c.name, c.class_level, c.compulsory
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            JOIN courses c ON c.id = e.course_id
            WHERE s.student_no = ? AND s.department_id = ?
            ORDER BY c.code
        """, (student_no, department_id))
    else:
        cur.execute("""
            SELECT c.code, c.name, c.class_level, c.compulsory
            FROM students s
            JOIN enrollments e ON e.student_id = s.id
            JOIN courses c ON c.id = e.course_id
            WHERE s.student_no = ?
            ORDER BY c.code
        """, (student_no,))
    rows = cur.fetchall()
    con.close()
    return rows

def get_course_students(course_code: str, department_id: int | None = None):
    con = get_conn(); cur = con.cursor()
    if department_id:
        cur.execute("""
            SELECT s.student_no, s.full_name, s.class_level
            FROM courses c
            JOIN enrollments e ON e.course_id = c.id
            JOIN students s ON s.id = e.student_id
            WHERE c.code = ? AND c.department_id = ?
            ORDER BY s.student_no
        """, (course_code, department_id))
    else:
        cur.execute("""
            SELECT s.student_no, s.full_name, s.class_level
            FROM courses c
            JOIN enrollments e ON e.course_id = c.id
            JOIN students s ON s.id = e.student_id
            WHERE c.code = ?
            ORDER BY s.student_no
        """, (course_code,))
    rows = cur.fetchall()
    con.close()
    return rows
