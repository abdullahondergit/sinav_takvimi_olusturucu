from __future__ import annotations
from src.services.guards import ensure_classrooms_ready, DomainError
from src.config import DB_PATH
from dataclasses import dataclass
from typing import List, Tuple, Optional
import re
import unicodedata
import pandas as pd
from src.db.sqlite import get_conn

REQUIRED_COURSE_COLS = ["code", "name", "instructor", "class_level", "compulsory"]
REQUIRED_STUDENT_COLS = ["student_no", "full_name", "class_level", "course_code"]

@dataclass
class ImportResult:
    inserted: int
    updated: int
    errors: List[str]

def _u(s) -> str:
    """Unicode normalize + NBSP temizliği + whitespace sadeleştirme."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _norm(x) -> str:
    return _u(x)

def _normalize_cols(cols) -> list[str]:
    return [_u(c) for c in cols]

_COURSE_HEADER_TOKENS = {"DERS KODU", "DERSİN ADI", "DERSİ VEREN ÖĞR. ELEMANI"}

def _find_course_header_row(df: pd.DataFrame) -> Optional[int]:
    """Ders listesi örnek şablonundaki tablo başlık satırını bulur."""
    for i, row in df.iterrows():
        tokens = {_u(v).upper() for v in row.values if _u(v)}
        if _COURSE_HEADER_TOKENS.issubset(tokens):
            return i
    return None

_CLASS_PAT = re.compile(r"^\s*(\d+)\s*[\.\-]?\s*Sınıf\s*$", re.I)

def _extract_class_from_colname(colname: str) -> Optional[int]:
    """Sütun başlığından (örn. '1. Sınıf') sınıf numarasını çıkarır."""
    m = _CLASS_PAT.match(_u(colname))
    return int(m.group(1)) if m else None

def _row_is_class_header(text: str) -> Optional[int]:
    s = _u(text)
    m = _CLASS_PAT.match(s)
    return int(m.group(1)) if m else None

_ELECTIVE_MARKERS = (
    "SEÇMELİ", "SEÇİMLİK",
    "SEÇMELİ DERS", "SEÇİMLİK DERS",
    "SEÇMELİ DERSLER", "SEÇİMLİK DERSLER"
)

def _row_is_elective_header(text: str) -> bool:
    s = _u(text).upper()
    return any(mark in s for mark in _ELECTIVE_MARKERS)

def _first_nonempty_cell(row: pd.Series) -> str:
    for v in row.values:
        s = _u(v)
        if s:
            return s
    return ""

def _looks_like_course_code(code: str) -> bool:
    """ABC101, BLM205, MUH403 gibi; TR karakterlerini destekler."""
    c = _u(code)
    if not c:
        return False
    return re.match(r"^[A-Za-zÇĞİÖŞÜçğıöşü]{2,}\d{2,}[A-Za-zÇĞİÖŞÜçğıöşü\-]*$", c) is not None


def _to_standard_courses_df(xlsx_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Çıkış:
      - Kolonlar: ['code','name','instructor','class_level','compulsory']
      - 'compulsory' sınıf/SEÇMELİ başlıklarına göre hesaplanır.
    """
    warnings: List[str] = []
    xls = pd.ExcelFile(xlsx_path)
    if not xls.sheet_names:
        return pd.DataFrame(columns=REQUIRED_COURSE_COLS), ["Sayfa bulunamadı."]

    sheet = xls.sheet_names[0]
    raw = xls.parse(sheet, header=None)  
    raw = raw.applymap(_u)

    out_rows: List[dict] = []
    current_class: int = 0
    current_compulsory: int = 1
    idx_code = idx_name = idx_instr = None

    for _, row in raw.iterrows():
        # 1) sınıf başlığı?
        first_text = _first_nonempty_cell(row)
        maybe_cls = _row_is_class_header(first_text)
        if maybe_cls is not None:
            current_class = int(maybe_cls)
            current_compulsory = 1
            continue

        # 2) seçmeli/seçimlik?
        if _row_is_elective_header(first_text):
            current_compulsory = 0
            continue

        tokens = { _u(v).upper() for v in row.values if _u(v) }
        if _COURSE_HEADER_TOKENS.issubset(tokens):
            idx_code = idx_name = idx_instr = None
            for j, v in enumerate(row.values):
                t = _u(v).upper()
                if t == "DERS KODU" and idx_code is None:
                    idx_code = j
                elif t == "DERSİN ADI" and idx_name is None:
                    idx_name = j
                elif t == "DERSİ VEREN ÖĞR. ELEMANI" and idx_instr is None:
                    idx_instr = j
            if idx_code is None or idx_name is None or idx_instr is None:
                warnings.append("Başlık satırı bulundu ama sütun indeksleri çıkarılamadı.")
                idx_code = idx_name = idx_instr = None
            continue

        if idx_code is None or idx_name is None or idx_instr is None:
            continue

        code = _u(row.iloc[idx_code]) if idx_code < len(row) else ""
        name = _u(row.iloc[idx_name]) if idx_name < len(row) else ""
        instr = _u(row.iloc[idx_instr]) if idx_instr < len(row) else ""

        if not _looks_like_course_code(code) or not name:
            continue

        out_rows.append({
            "code": code,
            "name": name,
            "instructor": instr,
            "class_level": int(current_class or 0),
            "compulsory": int(current_compulsory),
        })

    out = pd.DataFrame(out_rows).drop_duplicates(subset=["code"]).reset_index(drop=True)
    if out.empty:
        warnings.append("Geçerli ders kaydı bulunamadı.")

    return out[REQUIRED_COURSE_COLS], warnings


def _to_standard_students_df(xlsx_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Giriş:
      - Ya zaten REQUIRED_STUDENT_COLS kolonlarına sahip düz tablo
      - Ya da örnek şablon (Öğrenci No, Ad Soyad, Sınıf, Ders)
    Çıkış:
      - ['student_no','full_name','class_level','course_code']
    """
    warnings: List[str] = []
    xls = pd.ExcelFile(xlsx_path)
    if not xls.sheet_names:
        return pd.DataFrame(columns=REQUIRED_STUDENT_COLS), ["Sayfa bulunamadı."]

    sheet = xls.sheet_names[0]
    df = xls.parse(sheet)
    df.columns = _normalize_cols(df.columns)

    if set(REQUIRED_STUDENT_COLS).issubset(set(df.columns)):
        out = df.copy()
        return out[REQUIRED_STUDENT_COLS], warnings

    turkish_map = {
        "Öğrenci No": "student_no",
        "Ad Soyad": "full_name",
        "Sınıf": "class_level",
        "Ders": "course_code",
    }
    missing = [k for k in turkish_map.keys() if k not in df.columns]
    if missing:
        return pd.DataFrame(columns=REQUIRED_STUDENT_COLS), [f"Eksik sütun(lar): {missing}"]

    out = df[list(turkish_map.keys())].rename(columns=turkish_map).copy()

    out = out.dropna(how="all")
    def _to_int_class(v) -> int:
        s = _u(v)
        m = re.search(r"(\d+)", s)
        return int(m.group(1)) if m else 0

    out["student_no"] = out["student_no"].map(_u)
    out = out[out["student_no"] != ""]
    out["full_name"] = out["full_name"].map(_u)
    out["course_code"] = out["course_code"].map(_u)
    out["class_level"] = out["class_level"].apply(_to_int_class)

    before = len(out)
    out = out[(out["full_name"] != "") & (out["course_code"] != "")]
    removed = before - len(out)
    if removed > 0:
        warnings.append(f"{removed} satır boş/eksik veri nedeniyle atlandı.")

    out = out.drop_duplicates(subset=["student_no", "course_code"], keep="first").reset_index(drop=True)

    return out[REQUIRED_STUDENT_COLS], warnings


def import_courses(xlsx_path: str, department_id: int) -> ImportResult:
    ensure_classrooms_ready( department_id)
    df, prep_warnings = _to_standard_courses_df(xlsx_path)
    df.columns = _normalize_cols(df.columns)

    errors: List[str] = []
    errors.extend(prep_warnings)

    for col in REQUIRED_COURSE_COLS:
        if col not in df.columns:
            errors.append(f"Kolon eksik: {col}")
    if df.empty:
        return ImportResult(0, 0, errors)

    ins, upd = 0, 0
    con = get_conn(); cur = con.cursor()
    try:
        for i, row in df.iterrows():
            code = _norm(row.get("code"))
            name = _norm(row.get("name"))
            instructor = _norm(row.get("instructor"))

            try:
                class_level = int(row.get("class_level"))
            except Exception:
                errors.append(f"Satır {i+2}: class_level sayısal değil.")
                continue
            try:
                compulsory = int(row.get("compulsory"))
            except Exception:
                errors.append(f"Satır {i+2}: compulsory sayısal değil.")
                continue

            if not code or not name:
                errors.append(f"Satır {i+2}: code/name boş olamaz.")
                continue

            cur.execute("SELECT id FROM courses WHERE department_id=? AND code=?",
                        (department_id, code))
            ex = cur.fetchone()
            if ex:
                cur.execute("""UPDATE courses
                               SET name=?, instructor=?, class_level=?, compulsory=?
                               WHERE id=?""",
                            (name, instructor, class_level, 1 if compulsory else 0, ex["id"]))
                upd += 1
            else:
                cur.execute("""INSERT INTO courses(department_id, code, name, instructor, class_level, compulsory)
                               VALUES(?,?,?,?,?,?)""",
                            (department_id, code, name, instructor, class_level, 1 if compulsory else 0))
                ins += 1
        con.commit()
    finally:
        con.close()
    return ImportResult(ins, upd, errors)


def import_students(xlsx_path: str, department_id: int) -> ImportResult:
    ensure_classrooms_ready( department_id)
    df, prep_warnings = _to_standard_students_df(xlsx_path)
    df.columns = _normalize_cols(df.columns)

    errors: List[str] = []
    errors.extend(prep_warnings)

    for col in REQUIRED_STUDENT_COLS:
        if col not in df.columns:
            errors.append(f"Kolon eksik: {col}")
    if df.empty:
        return ImportResult(0, 0, errors)

    ins, upd = 0, 0
    con = get_conn(); cur = con.cursor()
    try:
        course_id_by_code: dict[str, int] = {}

        for i, row in df.iterrows():
            sno = _norm(row.get("student_no"))
            full_name = _norm(row.get("full_name"))
            ccode = _norm(row.get("course_code"))
            try:
                class_level = int(row.get("class_level"))
            except Exception:
                errors.append(f"Satır {i+2}: class_level sayısal değil.")
                continue

            if not sno or not full_name or not ccode:
                errors.append(f"Satır {i+2}: student_no/full_name/course_code boş olamaz.")
                continue

            cur.execute("SELECT id, department_id FROM students WHERE student_no=?", (sno,))
            st = cur.fetchone()
            if st:
                if st["department_id"] != department_id:
                    cur.execute("UPDATE students SET department_id=? WHERE id=?",
                                (department_id, st["id"]))
                cur.execute("""UPDATE students
                               SET full_name=?, class_level=?
                               WHERE id=?""",
                            (full_name, class_level, st["id"]))
                st_id = st["id"]
                upd += 1
            else:
                cur.execute("""INSERT INTO students(department_id, student_no, full_name, class_level)
                               VALUES(?,?,?,?)""",
                            (department_id, sno, full_name, class_level))
                st_id = cur.lastrowid
                ins += 1


            if ccode not in course_id_by_code:
                cur.execute("""SELECT id FROM courses
                               WHERE department_id=? AND code=?""",
                            (department_id, ccode))
                c = cur.fetchone()
                if not c:
                    errors.append(f"Satır {i+2}: course_code '{ccode}' bulunamadı (önce dersleri içe aktarın).")
                    continue
                course_id_by_code[ccode] = c["id"]
            cid = course_id_by_code[ccode]

            cur.execute("""SELECT 1 FROM enrollments
                           WHERE student_id=? AND course_id=?""",
                        (st_id, cid))
            if not cur.fetchone():
                cur.execute("""INSERT INTO enrollments(student_id, course_id)
                               VALUES(?,?)""", (st_id, cid))

        con.commit()
    finally:
        con.close()

    return ImportResult(ins, upd, errors)
