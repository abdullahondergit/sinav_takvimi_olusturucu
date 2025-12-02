from __future__ import annotations
from pathlib import Path
import os
import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CANDIDATES = [
    PROJECT_ROOT / "yazlab_exam.db",                
    PROJECT_ROOT / "data" / "exam_scheduler.db",     
]

env_db = os.environ.get("YAZLAB_DB_PATH")
if env_db:
    DB_PATH = Path(env_db)
else:
    existing = next((p for p in CANDIDATES if p.exists()), None)
    DB_PATH = existing if existing else CANDIDATES[0]

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row      
    con.execute("PRAGMA foreign_keys=ON")
    return con

def get_conn() -> sqlite3.Connection:
    return get_connection()
