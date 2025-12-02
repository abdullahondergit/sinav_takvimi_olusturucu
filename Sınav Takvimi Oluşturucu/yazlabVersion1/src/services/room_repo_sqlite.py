from src.db.sqlite import get_conn

def list_departments():
    con = get_conn(); cur = con.cursor()
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    rows = cur.fetchall()
    con.close()
    return rows

def list_rooms(department_id=None):
    con = get_conn(); cur = con.cursor()
    if department_id:
        cur.execute("""
            SELECT r.id, r.department_id, r.code, r.name, r.capacity, r.rows, r.cols, r.group_size,
                   d.name AS department_name
            FROM rooms r
            JOIN departments d ON d.id = r.department_id
            WHERE r.department_id=?
            ORDER BY r.code
        """, (department_id,))
    else:
        cur.execute("""
            SELECT r.id, r.department_id, r.code, r.name, r.capacity, r.rows, r.cols, r.group_size,
                   d.name AS department_name
            FROM rooms r
            JOIN departments d ON d.id = r.department_id
            ORDER BY r.code
        """)
    rows = cur.fetchall()
    con.close()
    return rows

def get_room(room_id: int):
    con = get_conn(); cur = con.cursor()
    cur.execute("""
       SELECT id, department_id, code, name, capacity, rows, cols, group_size
       FROM rooms WHERE id=?
    """, (room_id,))
    row = cur.fetchone()
    con.close()
    return row

def create_room(department_id: int, code: str, name: str, capacity: int, rows: int, cols: int, group_size: int):
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        INSERT INTO rooms(department_id, code, name, capacity, rows, cols, group_size)
        VALUES(?,?,?,?,?,?,?)
    """, (department_id, code, name, capacity, rows, cols, group_size))
    con.commit()
    new_id = cur.lastrowid
    con.close()
    return new_id

def update_room(room_id: int, **fields):
    if not fields:
        return False
    cols = ", ".join([f"{k}=?" for k in fields.keys()])
    vals = list(fields.values()) + [room_id]
    con = get_conn(); cur = con.cursor()
    cur.execute(f"UPDATE rooms SET {cols} WHERE id=?", vals)
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok

def delete_room(room_id: int):
    con = get_conn(); cur = con.cursor()
    cur.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    con.commit()
    ok = cur.rowcount > 0
    con.close()
    return ok
