# src/services/seating_sqlite.py
from __future__ import annotations
from typing import List, Dict, Tuple
from dataclasses import dataclass
from src.db.sqlite import get_conn
from types import SimpleNamespace
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import sqlite3
@dataclass
class RoomInfo:
    id: int
    code: str
    rows: int
    cols: int
    group_size: int
    
def _allowed_positions(group_size: int, row: int, col: int) -> list[int]:
    """
    Bir sıradaki grup içinde hangi alt-pozisyonlara öğrenci oturabilir?
    2'li: 1 öğrenci, yan boş (satranç gibi sağ/solu sıraya göre alternatife bağlayalım)
    3'lü: 2 öğrenci, ortası boş  -> [0, 2]
    4'lü: 2 öğrenci, orta iki boş -> [0, 3]
    """
    if group_size <= 2:
        return [ (row + col) % 2 ]  
    if group_size == 3:
        return [0, 2]
    return [0, 3]

def _effective_capacity(rows: int, cols: int, group_size: int) -> int:
    """Görsel kurala göre gerçek oturabilecek kişi sayısı."""
    per_group = 1 if group_size <= 2 else 2
    return rows * cols * per_group



def list_exams_with_rooms(department_id: int | None = None, exam_type: str | None = None) -> List[dict]:
    """
    Sınavları 'tarih saat - CODE (ODA1,+ODA2...)' şeklinde listeler.
    """
    con = get_conn(); cur = con.cursor()
    where = []
    params: List = []
    if exam_type:
        where.append("ex.exam_type = ?"); params.append(exam_type)
    if department_id:
        where.append("c.department_id = ?"); params.append(department_id)
    wh = ("WHERE " + " AND ".join(where)) if where else ""

    cur.execute(f"""
        SELECT ex.id   AS exam_id,
               ex.date AS date,
               ex.start_time AS start_time,
               c.code AS course_code,
               c.name AS course_name,
               GROUP_CONCAT(r.code, '+') AS rooms
        FROM exams ex
        JOIN courses c ON c.id = ex.course_id
        JOIN exam_rooms er ON er.exam_id = ex.id
        JOIN rooms r ON r.id = er.room_id
        {wh}
        GROUP BY ex.id, ex.date, ex.start_time, c.code, c.name
        ORDER BY ex.date, ex.start_time, c.code
    """, params)
    rows = cur.fetchall()
    con.close()
    return rows

def get_exam_rooms(exam_id: int):
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        SELECT r.code, r.name, r.rows, r.cols, r.group_size, r.capacity
        FROM exam_rooms er
        JOIN rooms r ON r.id = er.room_id
        WHERE er.exam_id = ?
        ORDER BY r.capacity DESC, r.code
    """, (exam_id,))
    rows = cur.fetchall()
    con.close()

    return [
        SimpleNamespace(
            code = r["code"],
            name = r["name"],                 
            rows = int(r["rows"] or 0),
            cols = int(r["cols"] or 0),
            group_size = int(r["group_size"] or 2),
            capacity = int(r["capacity"] or 0),
        )
        for r in rows
    ]

def get_exam_students(exam_id: int) -> List[dict]:
    """
    Sınava girecek öğrenciler (ders alan tüm öğrenciler).
    """
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        SELECT s.id   AS student_id,
               s.student_no,
               s.full_name
        FROM exams ex
        JOIN courses c ON c.id = ex.course_id
        JOIN enrollments e ON e.course_id = c.id
        JOIN students s ON s.id = e.student_id
        WHERE ex.id = ?
        ORDER BY s.student_no
    """, (exam_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def build_seating(exam_id: int) -> Tuple[List[dict], List[str]]:
    rooms = get_exam_rooms(exam_id)
    students = get_exam_students(exam_id)
    warnings: List[str] = []

    if not rooms:
        return [], ["Bu sınav için atanmış derslik yok."]
    if not students:
        return [], ["Bu sınav için öğrenci bulunamadı."]

    placements: List[dict] = []
    idx = 0

    for room in rooms:
        if room.rows <= 0 or room.cols <= 0:
            warnings.append(f"{room.code} için rows/cols tanımlı değil; atlanıyor.")
            continue

        cap = _effective_capacity(room.rows, room.cols, room.group_size)
        take = min(cap, len(students) - idx)

        placed_in_room = 0 

        for r in range(1, room.rows + 1):
            if placed_in_room >= take:
                break
            for c in range(1, room.cols + 1):
                if placed_in_room >= take:
                    break
                for pos in _allowed_positions(room.group_size, r, c):
                    if placed_in_room >= take or idx >= len(students):
                        break
                    st = students[idx]; idx += 1
                    placements.append({
                        "room_code": room.code,
                        "row": r,
                        "col": c,
                        "pos": pos,
                        "student_no": st["student_no"],
                        "full_name": st["full_name"],
                    })
                    placed_in_room += 1  


    if idx < len(students):
        warnings.append(f"{len(students)-idx} öğrenci yerleştirilemedi (kapasite yetersiz).")
    return placements, warnings



def export_seating_csv(placements: List[dict], path: str) -> str:
    """
    Yerleşimi CSV olarak dışa aktarır. path'i döner.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["room_code","row","col","student_no","full_name"])
        for p in placements:
            w.writerow([p["room_code"], p["row"], p["col"], p["student_no"], p["full_name"]])
    return path

def _try_register_turkish_font():
    candidates = [
        os.path.join("assets", "fonts", "DejaVuSans.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("TR_FONT", p))
                return "TR_FONT"
            except Exception:
                pass
    return "Helvetica" 

def export_seating_pdf(exam_id: int, placements: List[dict], path: str) -> str:
    """Yerleşimi PDF'e yazar. Oda başına 1 sayfa; sadece büyük grid ve numaralar."""
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        SELECT ex.date, ex.start_time, c.code AS course_code, c.name AS course_name, ex.duration_min
        FROM exams ex JOIN courses c ON c.id = ex.course_id
        WHERE ex.id=?
    """, (exam_id,))
    ex = cur.fetchone()
    con.close()
    if not ex:
        raise RuntimeError("Sınav bulunamadı.")

    con = get_conn(); cur = con.cursor()
    cur.execute("""
        SELECT r.code, r.name, r.rows, r.cols, r.group_size
        FROM exam_rooms er
        JOIN rooms r ON r.id = er.room_id
        WHERE er.exam_id = ?
        ORDER BY r.capacity DESC, r.code
    """, (exam_id,))
    room_layout = {
        r["code"]: {
            "name": r["name"],
            "rows": int(r["rows"] or 0),
            "cols": int(r["cols"] or 0),
            "group_size": int(r["group_size"] or 2),
        }
        for r in cur.fetchall()
    }
    con.close()

    rooms: Dict[str, List[dict]] = {}
    for p in placements:
        rooms.setdefault(p["room_code"], []).append(p)
    for k in rooms:
        rooms[k].sort(key=lambda x: (x["row"], x["col"], int(x.get("pos", 0))))

    font_name = _try_register_turkish_font()

    c = canvas.Canvas(path, pagesize=A4)
    W, H = A4
    left = 18*mm; right = 18*mm; top = 18*mm; bottom = 18*mm
    usable_w = W - left - right

    for room_code, plist in rooms.items():
        info = room_layout.get(room_code, {"name":"", "rows":0, "cols":0, "group_size":2})
        room_name = info["name"] or ""
        room_rows = info["rows"]
        room_cols = info["cols"]
        gsize     = info["group_size"]

        if room_rows <= 0 or room_cols <= 0:
            c.showPage()
            continue

        y = H - top
        c.setFont(font_name, 18)
        if room_name:
            c.drawString(left, y, f"Oda: {room_code} - {room_name}")
        else:
            c.drawString(left, y, f"Oda: {room_code}")
        y -= 22
        c.setFont(font_name, 13)
        c.drawString(left, y, f"Ders: {ex['course_code']} - {ex['course_name']}")
        y -= 14

        base_cell_w = 60*mm
        base_cell_h = 18*mm
        gap = 3*mm
        sub_gap = 0.1*mm

        grid_w = room_cols*base_cell_w + (room_cols-1)*gap
        grid_h = room_rows*base_cell_h + (room_rows-1)*gap

        gx = left + (usable_w - grid_w) / 2.0
        gy = y - grid_h - 8*mm

        by_cell: Dict[Tuple[int,int], Dict[int,str]] = {}
        for p in plist:
            rr, cc, pos = int(p["row"]), int(p["col"]), int(p.get("pos", 0))
            by_cell.setdefault((rr, cc), {})[pos] = str(p["student_no"])

        c.setFont(font_name, 9)
        for ccx in range(1, room_cols+1):
            cx = gx + (ccx-1)*(base_cell_w+gap) + base_cell_w/2
            c.drawCentredString(cx, gy + grid_h + 4*mm, str(ccx))
        for rrx in range(1, room_rows+1):
            cy = gy + grid_h - (rrx-1)*(base_cell_h+gap) - base_cell_h/2
            c.drawString(gx - 6*mm, cy-3, str(rrx))

        c.setLineWidth(1.2)
        weight_allow = 2.0   
        weight_empty = 1.0   

        for rr in range(1, room_rows+1):
            for cc in range(1, room_cols+1):
                x = gx + (cc-1)*(base_cell_w+gap)
                yy = gy + grid_h - rr*(base_cell_h+gap) + gap

                c.rect(x, yy, base_cell_w, base_cell_h)

                allowed = _allowed_positions(gsize, rr, cc)
                weights = [(weight_allow if pos in allowed else weight_empty) for pos in range(gsize)]
                total_gaps = (gsize - 1) * sub_gap
                unit_w = (base_cell_w - total_gaps) / sum(weights)
                widths = [unit_w * w for w in weights]

                sx = x
                for pos, w in enumerate(widths):
                    c.setFillGray(0.92 if pos in allowed else 1.0)
                    c.rect(sx, yy, w, base_cell_h, fill=1)

                    num = by_cell.get((rr, cc), {}).get(pos)
                    if num:
                        c.setFillGray(0)
                        c.setFont(font_name, 8)
                        c.drawCentredString(sx + w/2, yy + base_cell_h/2 - 3, num)

                    sx += w + sub_gap

        c.showPage()

    c.save()
    return path



