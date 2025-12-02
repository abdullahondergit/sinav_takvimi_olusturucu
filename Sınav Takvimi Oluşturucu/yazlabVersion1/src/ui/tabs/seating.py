from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QPushButton,
    QGraphicsView, QGraphicsScene, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPen, QBrush, QFont, QPainter, QColor
from src.services.seating_sqlite import (
    list_exams_with_rooms, build_seating, export_seating_csv, get_exam_rooms
)

MM = 3.7795275591

PAGE_W = 210 * MM
PAGE_H = 297 * MM
MARGIN = 18 * MM
USABLE_W = PAGE_W - 2 * MARGIN

BASE_CELL_W = 60 * MM
BASE_CELL_H = 18 * MM
GAP = 3 * MM
SUB_GAP = 0.1 * MM

# Renkler
GRAY_ALLOWED = QColor(235, 235, 235)  # ~0.92
WHITE = QColor(255, 255, 255)
BLACK = QColor(0, 0, 0)
WHITE_TXT = QColor(255, 255, 255)

def _allowed_positions(group_size: int, row: int, col: int) -> list[int]:
    if group_size <= 2:
        return [(row + col) % 2]
    if group_size == 3:
        return [0, 2]
    return [0, group_size - 1]

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setRenderHints(
            QPainter.Antialiasing
            | QPainter.TextAntialiasing
            | QPainter.SmoothPixmapTransform
        )
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            zoom_in = 1.15
            zoom_out = 1 / zoom_in
            factor = zoom_in if event.angleDelta().y() > 0 else zoom_out
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def reset_zoom(self):
        self.setTransform(self.transform().reset())

    def step_zoom(self, inout: int):
        zoom_in = 1.15
        zoom_out = 1 / zoom_in
        factor = zoom_in if inout > 0 else zoom_out
        self.scale(factor, factor)

    def fit_to_scene(self):
        rect = self.scene().itemsBoundingRect()
        if rect.isValid():
            self.fitInView(rect, Qt.KeepAspectRatio)


class SeatingTab(QWidget):
    def __init__(self, current_user, force_department_id=None):
        super().__init__()
        self.current_user = current_user
        self.force_dep_id = force_department_id
        self._placements = []
        self._rooms_meta = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        # Üst: sınav seçimi
        gb = QGroupBox("Sınav Seç")
        hl = QHBoxLayout(gb)
        self.cmb_exam_type = QComboBox(); self.cmb_exam_type.addItems(["vize", "final", "butunleme"])
        self.cmb_exam = QComboBox()
        self.btn_reload = QPushButton("Listele"); self.btn_reload.clicked.connect(lambda: self.reload_exams(silent=False))
        self.btn_make = QPushButton("Oturma Planı Oluştur"); self.btn_make.clicked.connect(self.make_seating)
        self.btn_export = QPushButton("CSV Dışa Aktar"); self.btn_export.clicked.connect(self.export_csv)
        self.btn_export_pdf = QPushButton("PDF'ye Aktar"); self.btn_export_pdf.clicked.connect(self.export_pdf)

        hl.addWidget(QLabel("Tür:")); hl.addWidget(self.cmb_exam_type)
        hl.addWidget(QLabel("Sınav:")); hl.addWidget(self.cmb_exam, 1)
        hl.addWidget(self.btn_reload); hl.addWidget(self.btn_make); hl.addWidget(self.btn_export); hl.addWidget(self.btn_export_pdf)

        self.cmb_exam_type.currentIndexChanged.connect(lambda: self.reload_exams(silent=True))

        # Zoom araçları
        tools = QHBoxLayout()
        self.btn_fit = QPushButton("Sığdır")
        self.btn_100 = QPushButton("%100")
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out = QPushButton("–")
        tools.addWidget(self.btn_fit); tools.addWidget(self.btn_100); tools.addWidget(self.btn_zoom_in); tools.addWidget(self.btn_zoom_out); tools.addStretch()

        self.view = ZoomableGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        self.btn_fit.clicked.connect(lambda: self.view.fit_to_scene())
        self.btn_100.clicked.connect(lambda: self.view.reset_zoom())
        self.btn_zoom_in.clicked.connect(lambda: self.view.step_zoom(+1))
        self.btn_zoom_out.clicked.connect(lambda: self.view.step_zoom(-1))

        root.addWidget(gb)
        root.addLayout(tools)
        root.addWidget(self.view, 1)

        self.reload_exams(silent=True)

    def _dep_id(self):
        return self.force_dep_id

    def reload_exams(self, silent: bool = False):
        self.cmb_exam.clear()
        et = self.cmb_exam_type.currentText()
        rows = list_exams_with_rooms(self._dep_id(), et)
        for r in rows:
            label = f"{r['date']} {r['start_time']} - {r['course_code']} ({r['rooms']})"
            self.cmb_exam.addItem(label, int(r["exam_id"]))
        if not rows:
            self.cmb_exam.addItem("Kayıt yok", None)
            if not silent:
                QMessageBox.information(self, "Bilgi", "Seçilen türde sınav bulunamadı.")

    def make_seating(self):
        exam_id = self.cmb_exam.itemData(self.cmb_exam.currentIndex())
        if not exam_id:
            QMessageBox.warning(self, "Seçim", "Lütfen bir sınav seçin."); return
        placements, warnings = build_seating(int(exam_id))
        self._placements = placements
        self._rooms_meta = get_exam_rooms(int(exam_id))
        self._draw()
        msg = f"{len(placements)} yerleşim oluşturuldu."
        if warnings:
            msg += "\n" + "\n".join(f"- {w}" for w in warnings)
        QMessageBox.information(self, "Oturma Planı", msg)

    # ---------------- PDF ile birebir UI çizimi ----------------
    def _draw(self):
        self.scene.clear()

        # PDF font ölçekleri
        font_title = QFont(); font_title.setPointSize(18)
        font_axis  = QFont(); font_axis.setPointSize(9)
        font_num   = QFont(); font_num.setPointSize(8)

        pen_outer = QPen(BLACK); pen_outer.setWidthF(1.2)
        pen_inner = QPen(BLACK); pen_inner.setWidthF(0.8)

        y_page_top = 0.0   
        max_right  = 0.0

        for room in self._rooms_meta:
            page_top = y_page_top

            # --- Başlık: sayfanın ÜSTÜNDEN başla ---
            y = page_top + MARGIN

            # Odaya ait yerleşimler
            room_pl = [p for p in self._placements if p["room_code"] == room.code]
            room_pl.sort(key=lambda x: (int(x["row"]), int(x["col"]), int(x.get("pos", 0))))

            title_text = f"Oda: {room.code}"
            room_name = getattr(room, "name", None)
            if room_name:
                title_text += f" - {room_name}"
            title_text += f"  ({room.rows}x{room.cols}, grup={room.group_size})"

            title_item = self.scene.addText(title_text, font_title)
            title_item.setDefaultTextColor(WHITE_TXT)
            title_item.setPos(MARGIN, y)
            title_h = title_item.boundingRect().height()

            # --- GRID ölçüleri ---
            room_rows = int(room.rows or 0)
            room_cols = int(room.cols or 0)
            gsize     = max(1, int(room.group_size or 2))
            if room_rows <= 0 or room_cols <= 0:
                y_page_top += PAGE_H
                continue

            grid_w = room_cols * BASE_CELL_W + (room_cols - 1) * GAP
            grid_h = room_rows * BASE_CELL_H + (room_rows - 1) * GAP

            gx = MARGIN + (USABLE_W - grid_w) / 2.0
            gy_top = y + title_h + 8 * MM 

            # --- Sütun Numaraları 
            for ccx in range(1, room_cols + 1):
                cx = gx + (ccx - 1) * (BASE_CELL_W + GAP) + BASE_CELL_W / 2
                t = self.scene.addText(str(ccx), font_axis)
                t.setDefaultTextColor(WHITE_TXT)
                br = t.boundingRect()
                t.setPos(cx - br.width() / 2, gy_top - 4 * MM - br.height())

            # --- Satır Numaraları 
            for rrx in range(1, room_rows + 1):
                cy = gy_top + (rrx - 1) * (BASE_CELL_H + GAP) + BASE_CELL_H / 2
                t = self.scene.addText(str(rrx), font_axis)
                t.setDefaultTextColor(WHITE_TXT)
                br = t.boundingRect()
                t.setPos(gx - 6 * MM - br.width(), cy - br.height() / 2)

            by_cell = {}
            for p in room_pl:
                rr, cc, pos = int(p["row"]), int(p["col"]), int(p.get("pos", 0))
                by_cell.setdefault((rr, cc), {})[pos] = str(p["student_no"])

            # --- Grid çizimi (TOP-DOWN) ---
            for rr in range(1, room_rows + 1):
                for cc in range(1, room_cols + 1):
                    x = gx + (cc - 1) * (BASE_CELL_W + GAP)
                    yy = gy_top + (rr - 1) * (BASE_CELL_H + GAP)

                    # Dış çerçeve
                    self.scene.addRect(QRectF(x, yy, BASE_CELL_W, BASE_CELL_H),
                                       pen_outer, QBrush(Qt.NoBrush))

                    allowed = _allowed_positions(gsize, rr, cc)
                    weight_allow = 2.0
                    weight_empty = 1.0
                    weights = [(weight_allow if pos in allowed else weight_empty)
                               for pos in range(gsize)]
                    total_gaps = (gsize - 1) * SUB_GAP
                    unit_w = (BASE_CELL_W - total_gaps) / sum(weights)
                    widths = [unit_w * w for w in weights]

                    sx = x
                    for pos, w in enumerate(widths):
                        fill = QBrush(GRAY_ALLOWED if pos in allowed else WHITE)
                        self.scene.addRect(QRectF(sx, yy, w, BASE_CELL_H),
                                           pen_inner, fill)

                        num = by_cell.get((rr, cc), {}).get(pos)
                        if num:
                            ti = self.scene.addText(num, font_num)
                            ti.setDefaultTextColor(BLACK)  # hücre içindeki numaralar siyah
                            br = ti.boundingRect()
                            ti.setPos(sx + (w - br.width()) / 2,
                                      yy + (BASE_CELL_H - br.height()) / 2)
                        sx += w + SUB_GAP

            right_edge = gx + grid_w + MARGIN
            max_right = max(max_right, right_edge)
            y_page_top += PAGE_H

        total_h = y_page_top
        total_w = max(PAGE_W, max_right + MARGIN)
        bounds = QRectF(0, 0, total_w, total_h).adjusted(-10, -10, 10, 10)
        self.scene.setSceneRect(bounds)

    def export_csv(self):
        if not self._placements:
            QMessageBox.warning(self, "Boş", "Önce oturma planını oluşturun."); return
        path, _ = QFileDialog.getSaveFileName(self, "CSV Dışa Aktar", "oturma_plani.csv", "CSV (*.csv)")
        if not path: return
        try:
            export_seating_csv(self._placements, path)
            QMessageBox.information(self, "Dışa Aktarım", f"Kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydedilemedi:\n{e}")

    def export_pdf(self):
        if not self._placements:
            QMessageBox.warning(self, "Boş", "Önce oturma planını oluşturun."); return
        exam_id = self.cmb_exam.itemData(self.cmb_exam.currentIndex())
        if not exam_id:
            QMessageBox.warning(self, "Seçim", "Lütfen bir sınav seçin."); return
        path, _ = QFileDialog.getSaveFileName(self, "PDF Dışa Aktar", "oturma_plani.pdf", "PDF (*.pdf)")
        if not path: return
        try:
            from src.services.seating_sqlite import export_seating_pdf
            out = export_seating_pdf(int(exam_id), self._placements, path)
            QMessageBox.information(self, "Dışa Aktarım", f"Kaydedildi:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulamadı:\n{e}")
