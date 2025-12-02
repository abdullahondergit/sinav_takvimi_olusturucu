from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel
from src.services.student_repo_sqlite import list_students

def rget(row, key, default=""):
    return row[key] if key in row.keys() and row[key] is not None else default

class StudentsViewTab(QWidget):
    def __init__(self, department_id: int | None = None):
        super().__init__()
        self.department_id = department_id
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        self.lbl = QLabel("Öğrenci Listesi")
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["ID", "Öğrenci No", "Ad Soyad", "BölümID"])
        lay.addWidget(self.lbl)
        lay.addWidget(self.tbl, 1)

    def refresh(self):
        rows = list_students(self.department_id)
        self.tbl.setRowCount(0)
        for r in rows:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)

            self.tbl.setItem(i, 0, QTableWidgetItem(str(rget(r, "id"))))
            self.tbl.setItem(i, 1, QTableWidgetItem(str(rget(r, "student_no") or rget(r, "number"))))

            full = (rget(r, "full_name") or "").strip()
            if not full:
                ad  = rget(r, "name") or rget(r, "first_name")
                soy = rget(r, "surname") or rget(r, "last_name")
                full = f"{(ad or '').strip()} {(soy or '').strip()}".strip()
            self.tbl.setItem(i, 2, QTableWidgetItem(full))

            self.tbl.setItem(i, 3, QTableWidgetItem(str(rget(r, "department_id"))))
