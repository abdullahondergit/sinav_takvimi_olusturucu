from __future__ import annotations
from typing import List, Optional, Dict
import bcrypt
from src.auth.security import hash_password
from src.db.sqlite import get_conn

ENFORCE_SINGLE_COORD_PER_DEPARTMENT = True

VALID_ROLES = {"admin", "coordinator"}


def _role_ok(role: str) -> bool:
    return role in VALID_ROLES


def list_users() -> List[dict]:
    """
    Kullanıcıları rol ve bölüm adıyla birlikte listeler.
    users(role TEXT, department_id INTEGER NULL) varsayımıyla çalışır.
    """
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.role, u.department_id,
               d.name AS department_name
        FROM users u
        LEFT JOIN departments d ON d.id = u.department_id
        ORDER BY
            CASE WHEN u.role='admin' THEN 0 ELSE 1 END,
            COALESCE(d.name, ''),
            u.username
    """)
    rows = cur.fetchall()
    con.close()

    return [dict(r) for r in rows]


def get_roles() -> List[str]:
    """
    Arayüz combosu için sabit rol listesi döndürür.
    (Projede roles tablosu olsa da UI için yeterli.)
    """
    return ["admin", "coordinator"]


def exists_username(username: str, exclude_user_id: Optional[int] = None) -> bool:
    con = get_conn(); cur = con.cursor()
    if exclude_user_id is not None:
        cur.execute("SELECT 1 FROM users WHERE username=? AND id <> ? LIMIT 1", (username, int(exclude_user_id)))
    else:
        cur.execute("SELECT 1 FROM users WHERE username=? LIMIT 1", (username,))
    hit = cur.fetchone() is not None
    con.close()
    return hit


def _department_has_coordinator(department_id: int) -> bool:
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        SELECT 1 FROM users
        WHERE role='coordinator' AND department_id=?
        LIMIT 1
    """, (int(department_id),))
    hit = cur.fetchone() is not None
    con.close()
    return hit


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_user(username: str,
                password: str,
                role: str,
                department_id: Optional[int]) -> int:
    """
    Yeni kullanıcı oluşturur.
    - username benzersiz olmalı
    - role ∈ {admin, coordinator}
    - coordinator için department_id zorunlu
    - admin için department_id NULL olmalı
    - (opsiyonel) Bölüm başına tek koordinatör kuralı
    """
    username = (username or "").strip()
    role = (role or "").strip()

    if not username:
        raise ValueError("Kullanıcı adı boş olamaz.")
    if not password:
        raise ValueError("Şifre boş olamaz.")
    if not _role_ok(role):
        raise ValueError("Geçersiz rol. Sadece 'admin' veya 'coordinator' olabilir.")
    if exists_username(username):
        raise ValueError("Bu kullanıcı adı zaten mevcut.")

    if role == "coordinator":
        if department_id is None:
            raise ValueError("Koordinatör için bölüm zorunludur.")
        if ENFORCE_SINGLE_COORD_PER_DEPARTMENT and _department_has_coordinator(int(department_id)):
            raise ValueError("Bu bölümde zaten bir koordinatör var.")
    else:
        department_id = None

    pwd_hash = _hash_password(password)

    con = get_conn(); cur = con.cursor()
    cur.execute("""
        INSERT INTO users(username, password_hash, role, department_id)
        VALUES(?,?,?,?)
    """, (username, pwd_hash, role, department_id))
    new_id = cur.lastrowid
    con.commit(); con.close()
    return int(new_id)


def update_user(user_id: int,
                username: str,
                role: str,
                department_id: Optional[int]) -> bool:
    """
    Kullanıcıyı şifresiz günceller (şifre için reset_password kullan).
    Benzersizlik ve rol/bölüm kuralları uygulanır.
    """
    user_id = int(user_id)
    username = (username or "").strip()
    role = (role or "").strip()

    if not username:
        raise ValueError("Kullanıcı adı boş olamaz.")
    if not _role_ok(role):
        raise ValueError("Geçersiz rol. Sadece 'admin' veya 'coordinator' olabilir.")
    if exists_username(username, exclude_user_id=user_id):
        raise ValueError("Bu kullanıcı adı başka bir kullanıcı tarafından kullanılıyor.")

    if role == "coordinator":
        if department_id is None:
            raise ValueError("Koordinatör için bölüm zorunludur.")
        if ENFORCE_SINGLE_COORD_PER_DEPARTMENT:
            con = get_conn(); cur = con.cursor()
            cur.execute("""
                SELECT 1 FROM users
                WHERE role='coordinator' AND department_id=? AND id<>?
                LIMIT 1
            """, (int(department_id), user_id))
            exists_other = cur.fetchone() is not None
            con.close()
            if exists_other:
                raise ValueError("Bu bölümde zaten başka bir koordinatör var.")
    else:
        department_id = None

    con = get_conn(); cur = con.cursor()
    cur.execute("""
        UPDATE users
        SET username=?, role=?, department_id=?
        WHERE id=?
    """, (username, role, department_id, user_id))
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed


def reset_password(user_id: int, new_password: str) -> bool:
    """
    Şifreyi bcrypt ile resetler.
    """
    if not new_password:
        raise ValueError("Yeni şifre boş olamaz.")
    user_id = int(user_id)
    pwd_hash = _hash_password(new_password)

    con = get_conn(); cur = con.cursor()
    cur.execute("UPDATE users SET password_hash=? WHERE id=?", (pwd_hash, user_id))
    con.commit()
    changed = cur.rowcount > 0
    con.close()
    return changed


def delete_user(user_id: int) -> bool:
    """
    Kullanıcıyı siler. (Admin'in kendini silmesini engellemek istersen
    UI/servis katmanında ayrıca kontrol ekleyebilirsin.)
    """
    user_id = int(user_id)
    con = get_conn(); cur = con.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    con.commit()
    deleted = cur.rowcount > 0
    con.close()
    return deleted


def department_has_coordinator(department_id: int, exclude_user_id: Optional[int] = None) -> bool:
    """
    Verilen bölümde (opsiyonel olarak belirli bir kullanıcı hariç) zaten bir koordinatör var mı?
    UI tarafında ön-kontrol için.
    """
    con = get_conn(); cur = con.cursor()
    if exclude_user_id is not None:
        cur.execute("""
            SELECT 1 FROM users
            WHERE role='coordinator' AND department_id=? AND id<>?
            LIMIT 1
        """, (int(department_id), int(exclude_user_id)))
    else:
        cur.execute("""
            SELECT 1 FROM users
            WHERE role='coordinator' AND department_id=?
            LIMIT 1
        """, (int(department_id),))
    hit = cur.fetchone() is not None
    con.close()
    return hit
