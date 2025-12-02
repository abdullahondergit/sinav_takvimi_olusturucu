from src.db.sqlite import get_connection

def list_courses_with_counts(department_id: int | None = None):
    """
    Kursları, kayıtlı öğrenci sayısı ile birlikte döndürür.
    Dönen kolonlar: id, code, name, department_id, student_count
    """
    con = get_connection(); cur = con.cursor()

    base = """
        SELECT
            c.id,
            c.code,
            c.name,
            c.department_id,
            COUNT(e.student_id) AS student_count
        FROM courses c
        LEFT JOIN enrollments e ON e.course_id = c.id
    """

    conds = []
    params = []

    if department_id is not None:
        conds.append("c.department_id = ?")
        params.append(department_id)

    where = (" WHERE " + " AND ".join(conds)) if conds else ""
    sql = base + where + " GROUP BY c.id ORDER BY c.code"

    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows
