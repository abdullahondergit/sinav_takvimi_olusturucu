from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QGraphicsView, QGraphicsScene, QMessageBox
)
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter
from src.db.sqlite import get_connection
from src.services.room_repo_sqlite import get_room  

MM = 3.7795275591

BASE_CELL_W = 60 * MM
BASE_CELL_H = 18 * MM
GAP     = 3 * MM
SUB_GAP = 0.1 * MM

MARGIN = 18 * MM

WHITE_TXT = QColor(255, 255, 255)
BLACK     = QColor(0, 0, 0)

def rget(row, key, default=""):
    return row[key] if key in row.keys() and row[key] is not None else default


class SearchRoomTab(QWidget):
    def __init__(self, department_id: int | None = None):
        super().__init__()
        self.department_id = department_id
        self._rows = []  
        self._build_ui()

    # ---------------- UI kurulumu ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Arama alanı
        box = QGroupBox("Sınıf Arama")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("Sınıf ID / Kod:"))
        self.ed_query = QLineEdit()
        self.ed_query.setPlaceholderText("Örn: BM-101 veya 1")
        self.btn_search = QPushButton("Ara")
        self.btn_search.clicked.connect(self.search_room)
        row.addWidget(self.ed_query, 1)
        row.addWidget(self.btn_search)
        root.addWidget(box)

        # Tablo
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(["ID", "BölümID", "Kod", "Ad", "Kapasite", "Rows", "Cols"])
        self.tbl.itemSelectionChanged.connect(self._on_row_select)
        root.addWidget(self.tbl)

        # Görselleştirme alanı
        self.view = QGraphicsView()
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        # Yatayda merkezde dursun
        self.view.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        root.addWidget(self.view, 1)

    # ---------------- DB sorguları ----------------
    def _query_by_code(self, code: str):
        """Code ile (büyük/küçük harf duyarsız) arama. Tam eşleşme yoksa LIKE ile kısmi arama dener."""
        code = (code or "").strip()
        if not code:
            return []

        con = get_connection()
        cur = con.cursor()

        # 1) tam eşleşme
        cur.execute("SELECT * FROM rooms WHERE LOWER(code)=LOWER(?)", (code,))
        rows = cur.fetchall()

        # 2) yoksa kısmi
        if not rows:
            like = f"%{code}%"
            cur.execute("SELECT * FROM rooms WHERE LOWER(code) LIKE LOWER(?) ORDER BY code", (like,))
            rows = cur.fetchall()

        con.close()
        return rows

    # ---------------- Arama işlemi ----------------
    def search_room(self):
        q = (self.ed_query.text() or "").strip()
        if not q:
            QMessageBox.warning(self, "Uyarı", "Lütfen sınıf ID veya kod girin.")
            return

        # Öncelik: kod ile arama
        rows = self._query_by_code(q)

        # Bulunamadıysa, sayısal ID olarak dene
        if not rows and q.isdigit():
            r = get_room(int(q))
            rows = [r] if r else []

        # Hâlâ yoksa temizle
        if not rows:
            QMessageBox.information(self, "Bulunamadı", "Bu kod/ID için sınıf yok.")
            self.tbl.setRowCount(0)
            self.scene.clear()
            return

        self._rows = list(rows)

        # Tabloyu doldur
        self.tbl.setRowCount(0)
        for r in rows:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)
            self.tbl.setItem(i, 0, QTableWidgetItem(str(rget(r, "id"))))
            self.tbl.setItem(i, 1, QTableWidgetItem(str(rget(r, "department_id"))))
            self.tbl.setItem(i, 2, QTableWidgetItem(str(rget(r, "code"))))
            self.tbl.setItem(i, 3, QTableWidgetItem(str(rget(r, "name"))))
            self.tbl.setItem(i, 4, QTableWidgetItem(str(rget(r, "capacity"))))
            self.tbl.setItem(i, 5, QTableWidgetItem(str(rget(r, "rows"))))
            self.tbl.setItem(i, 6, QTableWidgetItem(str(rget(r, "cols"))))

        # İlk satırı seçip görselleştir
        self.tbl.selectRow(0)
        self._on_row_select()

    # ---------------- Görselleştirme ----------------
    def _on_row_select(self):
        items = self.tbl.selectedItems()
        if not items:
            self.scene.clear()
            return

        row_ix = items[0].row()
        r = self._rows[row_ix] if 0 <= row_ix < len(self._rows) else None
        if not r:
            self.scene.clear()
            return

        code = str(rget(r, "code"))
        name = str(rget(r, "name"))
        try:
            rows = int(rget(r, "rows", 0))
            cols = int(rget(r, "cols", 0))
        except (TypeError, ValueError):
            self.scene.clear()
            return

        # group_size yoksa 2 varsayıyoruz
        gsize = int(rget(r, "group_size", 2) or 2)

        if rows <= 0 or cols <= 0:
            self.scene.clear()
            return

        self._draw_room_layout(code=code, name=name, rows=rows, cols=cols, group_size=gsize)

    def _draw_room_layout(self, code: str, name: str, rows: int, cols: int, group_size: int):
        """
        'Sınıf Arama' önizlemesi:
        - 2/3/4 parçalı alt hücreler VAR ama hepsi EŞİT GENİŞLİKTE
        - SADECE ÇERÇEVE (NoBrush), beyaz çizgiler
        - Gerçek yatay merkezleme (dinamik sahne genişliği)
        """
        self.scene.clear()

        font_title = QFont(); font_title.setPointSize(18)
        font_axis  = QFont(); font_axis.setPointSize(9)

        pen_outer = QPen(WHITE_TXT); pen_outer.setWidthF(1.4)
        pen_inner = QPen(WHITE_TXT); pen_inner.setWidthF(0.9)

        y = MARGIN

        title = f"Sınıf: {code}"
        if name:
            title += f" - {name}"
        title += f" ({rows}x{cols})"

        titem = self.scene.addText(title, font_title)
        titem.setDefaultTextColor(WHITE_TXT)
        titem.setPos(MARGIN, y)
        title_h = titem.boundingRect().height()

        grid_w = cols * BASE_CELL_W + (cols - 1) * GAP
        grid_h = rows * BASE_CELL_H + (rows - 1) * GAP

        gx = MARGIN
        gy_top = y + title_h + 8 * MM

        for ccx in range(1, cols + 1):
            cx = gx + (ccx - 1) * (BASE_CELL_W + GAP) + BASE_CELL_W / 2
            lab = self.scene.addText(str(ccx), font_axis)
            lab.setDefaultTextColor(WHITE_TXT)
            br = lab.boundingRect()
            lab.setPos(cx - br.width() / 2, gy_top - 4 * MM - br.height())

        for rrx in range(1, rows + 1):
            cy = gy_top + (rrx - 1) * (BASE_CELL_H + GAP) + BASE_CELL_H / 2
            lab = self.scene.addText(str(rrx), font_axis)
            lab.setDefaultTextColor(WHITE_TXT)
            br = lab.boundingRect()
            lab.setPos(gx - 6 * MM - br.width(), cy - br.height() / 2)

        gsize = max(1, int(group_size or 2))

        sub_w = (BASE_CELL_W - max(0, gsize - 1) * SUB_GAP) / gsize

        for rr in range(1, rows + 1):
            for cc in range(1, cols + 1):
                x = gx + (cc - 1) * (BASE_CELL_W + GAP)
                yy = gy_top + (rr - 1) * (BASE_CELL_H + GAP)

                self.scene.addRect(QRectF(x, yy, BASE_CELL_W, BASE_CELL_H),
                                   pen_outer, QBrush(Qt.NoBrush))

                sx = x
                for pos in range(gsize):
                    self.scene.addRect(QRectF(sx, yy, sub_w, BASE_CELL_H),
                                       pen_inner, QBrush(Qt.NoBrush))
                    sx += sub_w + SUB_GAP

        total_w = grid_w + 2 * MARGIN
        total_h = gy_top + grid_h + MARGIN
        bounds = QRectF(0, 0, total_w, total_h).adjusted(-10, -10, 10, 10)
        self.scene.setSceneRect(bounds)

        title_br = titem.boundingRect()
        titem.setPos((total_w - title_br.width()) / 2.0, y)

        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        self.view.centerOn(self.scene.itemsBoundingRect().center())
