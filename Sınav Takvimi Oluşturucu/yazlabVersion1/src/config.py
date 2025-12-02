# src/config.py
from pathlib import Path

# Proje kökü (src'nin bir üstü)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Varsayılan SQLite dosya yolu (senin dosya adın farklıysa değiştir)
DB_PATH = PROJECT_ROOT / "yazlab_exam.db"

# Gerekirse başka sabitler:
# EXPORT_DIR = PROJECT_ROOT / "exports"
# EXPORT_DIR.mkdir(exist_ok=True)
