from src.db.sqlite import get_connection

def list_students(department_id: int | None = None):
    con = get_connection(); cur = con.cursor()
    if department_id is None:
        cur.execute("SELECT * FROM students ORDER BY student_no")
    else:
        cur.execute("""
            SELECT * FROM students
            WHERE (? IS NULL) OR department_id=?
            ORDER BY student_no
        """, (department_id, department_id))
    rows = cur.fetchall(); con.close()
    return rows
