from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel,
    QFrame, QHBoxLayout, QLineEdit, QPushButton, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt

from src.services.course_repo_sqlite import list_courses_with_counts

def rget(row, key, default=""):
    return row[key] if key in row.keys() and row[key] is not None else default

class CoursesViewTab(QWidget):
    def __init__(self, department_id: int | None = None):
        super().__init__()
        self.department_id = department_id
        self._rows: list = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("Ders Listesi")
        title.setStyleSheet("font-weight:700; font-size:14px; color: #e6eef8;")
        header_row.addWidget(title)
        header_row.addStretch(1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Ara: kod veya ad ile filtrele")
        self.search.setMinimumWidth(220)
        self.search.textChanged.connect(self._apply_filter)
        header_row.addWidget(self.search)

        self.btn_refresh = QPushButton("Yenile")
        self.btn_refresh.clicked.connect(self.refresh)
        header_row.addWidget(self.btn_refresh)

        root.addLayout(header_row)

        frame = QFrame()
        frame.setProperty("class", "card")  
        frame_l = QVBoxLayout(frame)
        frame_l.setContentsMargins(8, 8, 8, 8)
        frame_l.setSpacing(6)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["ID", "Kod", "Ad", "BölümID", "Öğrenci Sayısı"])
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl.verticalHeader().setVisible(False)

        header = self.tbl.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Kod
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Ad
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # BölümID
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Öğrenci Sayısı

        frame_l.addWidget(self.tbl)
        root.addWidget(frame, 1)

    def _apply_filter(self):
        q = (self.search.text() or "").strip().lower()
        if not q:
            rows = self._rows
        else:
            rows = [
                r for r in self._rows
                if q in str(rget(r, "code", "")).lower() or q in str(rget(r, "name", "")).lower()
            ]
        self._populate_table(rows)

    def _populate_table(self, rows):
        self.tbl.setRowCount(0)
        for r in rows:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)

            id_item = QTableWidgetItem(str(rget(r, "id")))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 0, id_item)

            code_item = QTableWidgetItem(str(rget(r, "code")))
            code_item.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 1, code_item)

            name_item = QTableWidgetItem(str(rget(r, "name")))
            name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.tbl.setItem(i, 2, name_item)

            dep_item = QTableWidgetItem(str(rget(r, "department_id", "")))
            dep_item.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 3, dep_item)

            count_item = QTableWidgetItem(str(rget(r, "student_count", 0)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.tbl.setItem(i, 4, count_item)

    def refresh(self):
        try:
            rows = list_courses_with_counts(self.department_id)
            self._rows = rows or []
            self._apply_filter()
        except Exception:
            self._rows = []
            self._populate_table([])
