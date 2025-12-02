from PySide6.QtCore import Qt, QRectF, Signal 
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QFormLayout, QLineEdit, QSpinBox, QComboBox, QPushButton, QMessageBox,
    QGraphicsView, QGraphicsScene, QLabel, QAbstractItemView
)
from PySide6.QtCore import Qt, QRectF

from src.services.room_repo_sqlite import (
    list_departments, list_rooms, get_room, create_room, update_room, delete_room
)

CELL_W, CELL_H = 26, 18
CELL_GAP = 6

class RoomsTab(QWidget):
    dataChanged = Signal()
    def __init__(self, force_department_id=None):
        super().__init__()
        self.force_dep_id = force_department_id
        self.selected_room_id = None

        root = QHBoxLayout(self)

        left = QVBoxLayout()

        self.cmb_dep_filter = QComboBox()
        if self.force_dep_id is not None:
            self._load_only_forced_department(self.cmb_dep_filter)  
        else:
            self._load_departments_into(self.cmb_dep_filter, add_all=True)  
        self.cmb_dep_filter.currentIndexChanged.connect(self.load_rooms)
        left.addWidget(QLabel("Bölüm:"))
        left.addWidget(self.cmb_dep_filter)

        # Tablo
        self.tbl = QTableWidget(0, 8)
        self.tbl.setHorizontalHeaderLabels(
            ["ID", "Bölüm", "Kod", "Ad", "Kapasite", "Rows", "Cols", "Grup"]
        )
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl.itemSelectionChanged.connect(self.on_table_select)
        left.addWidget(self.tbl)

        # Form
        form = QFormLayout()

        self.cmb_dep = QComboBox()
        if self.force_dep_id is not None:
            self._load_only_forced_department(self.cmb_dep)      # tek bölüm + kilit
        else:
            self._load_departments_into(self.cmb_dep)            # admin: hepsi

        self.txt_code = QLineEdit()
        self.txt_name = QLineEdit()
        self.sp_capacity = QSpinBox(); self.sp_capacity.setRange(1, 100000); self.sp_capacity.setValue(60)
        self.sp_rows = QSpinBox(); self.sp_rows.setRange(1, 1000); self.sp_rows.setValue(10)
        self.sp_cols = QSpinBox(); self.sp_cols.setRange(1, 1000); self.sp_cols.setValue(6)
        self.cmb_group = QComboBox(); self.cmb_group.addItems(["2", "3", "4"])

        form.addRow("Bölüm:", self.cmb_dep)
        form.addRow("Kod:", self.txt_code)
        form.addRow("Ad:", self.txt_name)
        form.addRow("Kapasite:", self.sp_capacity)
        form.addRow("Satır (rows):", self.sp_rows)
        form.addRow("Sütun (cols):", self.sp_cols)
        form.addRow("Sıra grubu:", self.cmb_group)

        left.addLayout(form)

        # Butonlar
        btns = QHBoxLayout()
        self.btn_add = QPushButton("Ekle");      self.btn_add.clicked.connect(self.add_room)
        self.btn_upd = QPushButton("Güncelle");  self.btn_upd.clicked.connect(self.update_room)
        self.btn_del = QPushButton("Sil");       self.btn_del.clicked.connect(self.delete_room)
        self.btn_clear = QPushButton("Temizle"); self.btn_clear.clicked.connect(self.clear_form)
        btns.addWidget(self.btn_add); btns.addWidget(self.btn_upd)
        btns.addWidget(self.btn_del); btns.addWidget(self.btn_clear)
        left.addLayout(btns)

        right = QVBoxLayout()
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        right.addWidget(self.view)

        root.addLayout(left, 3)
        root.addLayout(right, 2)

        self.load_rooms()

        self.sp_rows.valueChanged.connect(self._redraw_from_form)
        self.sp_cols.valueChanged.connect(self._redraw_from_form)

        if self.force_dep_id is not None:
            dept_col_index = 1  
            self.tbl.setColumnHidden(dept_col_index, True)

    def _load_departments_into(self, combo: QComboBox, add_all: bool = False):
        combo.clear()
        if add_all:
            combo.addItem("Tümü", None)
        for d in list_departments():
            combo.addItem(d["name"], d["id"])

    def _load_only_forced_department(self, combo: QComboBox):
        combo.clear()
        for d in list_departments():
            if d["id"] == self.force_dep_id:
                combo.addItem(d["name"], d["id"])
                break
        combo.setEnabled(False)  

    def _current_dep_filter_id(self):
        if self.force_dep_id is not None:
            return self.force_dep_id
        i = self.cmb_dep_filter.currentIndex()
        return self.cmb_dep_filter.itemData(i)

    def _current_dep_form_id(self):
        if self.force_dep_id is not None:
            return self.force_dep_id
        i = self.cmb_dep.currentIndex()
        return self.cmb_dep.itemData(i)

    def load_rooms(self):
        self.tbl.setRowCount(0)
        dep_id = self._current_dep_filter_id()
        rooms = list_rooms(dep_id)  

        dep_names = {d["id"]: d["name"] for d in list_departments()}

        for r in rooms:
            rd = dict(r)  

            row = self.tbl.rowCount()
            self.tbl.insertRow(row)

            dept_name = rd.get("department_name")
            if dept_name is None:
                dept_name = dep_names.get(rd.get("department_id"), "")

            self.tbl.setItem(row, 0, QTableWidgetItem(str(rd.get("id", ""))))
            self.tbl.setItem(row, 1, QTableWidgetItem(dept_name))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(rd.get("code", ""))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(rd.get("name", ""))))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(rd.get("capacity", ""))))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(rd.get("rows", ""))))
            self.tbl.setItem(row, 6, QTableWidgetItem(str(rd.get("cols", ""))))
            self.tbl.setItem(row, 7, QTableWidgetItem(str(rd.get("group_size", ""))))

        self.selected_room_id = None
        self.scene.clear()


    def on_table_select(self):
        items = self.tbl.selectedItems()
        if not items:
            return
        row = items[0].row()
        room_id = int(self.tbl.item(row, 0).text())
        self.selected_room_id = room_id

        r = get_room(room_id)
        if not r:
            return
        rd = dict(r) 

        for i in range(self.cmb_dep.count()):
            if self.cmb_dep.itemData(i) == rd.get("department_id"):
                self.cmb_dep.setCurrentIndex(i)
                break
        self.txt_code.setText(str(rd.get("code", "")))
        self.txt_name.setText(str(rd.get("name", "")))
        self.sp_capacity.setValue(int(rd.get("capacity", 60)))
        self.sp_rows.setValue(int(rd.get("rows", 10)))
        self.sp_cols.setValue(int(rd.get("cols", 6)))
        self.cmb_group.setCurrentText(str(rd.get("group_size", 2)))

        self.draw_grid(self.sp_rows.value(), self.sp_cols.value())


    def _collect_form(self):
        return dict(
            department_id=self._current_dep_form_id(),
            code=self.txt_code.text().strip(),
            name=self.txt_name.text().strip(),
            capacity=int(self.sp_capacity.value()),
            rows=int(self.sp_rows.value()),
            cols=int(self.sp_cols.value()),
            group_size=int(self.cmb_group.currentText()),
        )

    def add_room(self):
        data = self._collect_form()
        if not data["department_id"] or not data["code"] or not data["name"]:
            QMessageBox.warning(self, "Eksik", "Bölüm, kod ve ad zorunludur.")
            return
        try:
            create_room(**data)
            self.load_rooms()
            self.dataChanged.emit()
            QMessageBox.information(self, "OK", "Derslik eklendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Ekleme başarısız:\n{e}")

    def update_room(self):
        if not self.selected_room_id:
            QMessageBox.warning(self, "Seçim", "Tablodan bir derslik seçin.")
            return
        data = self._collect_form()
        try:
            ok = update_room(self.selected_room_id, **data)
            if not ok:
                QMessageBox.warning(self, "Bulunamadı", "Kayıt yok.")
                return
            self.load_rooms()
            self.dataChanged.emit()
            QMessageBox.information(self, "OK", "Derslik güncellendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız:\n{e}")

    def delete_room(self):
        if not self.selected_room_id:
            QMessageBox.warning(self, "Seçim", "Tablodan bir derslik seçin.")
            return
        try:
            if delete_room(self.selected_room_id):
                self.load_rooms()
                self.dataChanged.emit()
                QMessageBox.information(self, "OK", "Derslik silindi.")
            else:
                QMessageBox.warning(self, "Bulunamadı", "Kayıt yok.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Silme başarısız:\n{e}")

    def clear_form(self):
        self.selected_room_id = None
        self.txt_code.clear()
        self.txt_name.clear()
        self.sp_capacity.setValue(60)
        self.sp_rows.setValue(10)
        self.sp_cols.setValue(6)
        self.cmb_group.setCurrentText("2")
        self.scene.clear()

    def draw_grid(self, rows: int, cols: int):
        self.scene.clear()
        y = 0
        for _ in range(rows):
            x = 0
            for _ in range(cols):
                rect = QRectF(x, y, CELL_W, CELL_H)
                self.scene.addRect(rect)
                x += CELL_W + CELL_GAP
            y += CELL_H + CELL_GAP
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def _redraw_from_form(self):
        if self.sp_rows.value() > 0 and self.sp_cols.value() > 0:
            self.draw_grid(self.sp_rows.value(), self.sp_cols.value())
