from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox, QDateEdit,
    QSpinBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QListWidget, QListWidgetItem, QFileDialog, QTimeEdit, QCheckBox, QDialog,
    QDialogButtonBox
)
from PySide6.QtCore import Qt, QDate, QTime, QTimer
from datetime import date
from src.services.room_repo_sqlite import list_departments, list_rooms
from src.services.scheduler_sqlite import (
    schedule_exams, list_scheduled, fetch_courses_with_counts
)
from src.services.scheduler_sqlite import export_schedule as export_schedule_to_file


class DurationOverrideDialog(QDialog):
    """Bir derse özel süre girmek için küçük pencere."""
    def __init__(self, courses: list[tuple[int, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Süre İstisnası Ekle")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)

        self.cmb_course = QComboBox()
        for cid, cname in courses:
            self.cmb_course.addItem(cname, cid)
        layout.addWidget(QLabel("Ders Seç:"))
        layout.addWidget(self.cmb_course)

        self.sp_dur = QSpinBox()
        self.sp_dur.setRange(0, 300)
        self.sp_dur.setValue(75)
        layout.addWidget(QLabel("Süre (dk):"))
        layout.addWidget(self.sp_dur)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_values(self):
        """(course_id, süre) döner."""
        return int(self.cmb_course.currentData()), int(self.sp_dur.value())


class RemoveOverrideDialog(QDialog):
    """Mevcut istisnalar arasından birini silmek için diyalog."""
    def __init__(self, items: list[tuple[int, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("İstisna Sil")
        self.setMinimumWidth(300)
        v = QVBoxLayout(self)
        self.cmb = QComboBox()
        for cid, text in items:
            self.cmb.addItem(text, cid)
        v.addWidget(QLabel("Silinecek ders:"))
        v.addWidget(self.cmb)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(bb)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)

    def get_course_id(self) -> int:
        return int(self.cmb.currentData())


# ------------------- Ana Sekme -------------------
class SchedulerTab(QWidget):
    def __init__(self, current_user, force_department_id=None):
        super().__init__()
        self.current_user = current_user
        self.force_dep_id = force_department_id
        self._course_duration_overrides: dict[int, int] = {}
        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # ---- Takvim Parametreleri ----
        gb = QGroupBox("Takvim Parametreleri")
        gl = QHBoxLayout(gb)

        self.cmb_dep = QComboBox()
        if self.force_dep_id is not None:
            for d in list_departments():
                if d["id"] == self.force_dep_id:
                    self.cmb_dep.addItem(d["name"], d["id"])
                    break
            self.cmb_dep.setEnabled(False)
        else:
            for d in list_departments():
                self.cmb_dep.addItem(d["name"], d["id"])

        self.cmb_type = QComboBox(); self.cmb_type.addItems(["vize","final","butunleme"])
        self.date_start = QDateEdit(QDate.currentDate()); self.date_start.setCalendarPopup(True)
        self.date_end   = QDateEdit(QDate.currentDate().addDays(4)); self.date_end.setCalendarPopup(True)

        self.time_start = QTimeEdit(QTime(9, 0));  self.time_start.setDisplayFormat("HH:mm")
        self.time_end   = QTimeEdit(QTime(17, 0)); self.time_end.setDisplayFormat("HH:mm")

        self.sp_dur = QSpinBox(); self.sp_dur.setRange(0, 300); self.sp_dur.setValue(75)

        gl.addWidget(QLabel("Bölüm:")); gl.addWidget(self.cmb_dep)
        gl.addWidget(QLabel("Tür:")); gl.addWidget(self.cmb_type)
        gl.addWidget(QLabel("Tarih Aralığı:")); gl.addWidget(self.date_start); gl.addWidget(self.date_end)
        gl.addWidget(QLabel("Saat Aralığı:")); gl.addWidget(self.time_start); gl.addWidget(self.time_end)
        gl.addWidget(QLabel("Vars. Süre (dk):")); gl.addWidget(self.sp_dur)

        # ---- Kısıtlar ----
        gb_rules = QGroupBox("Kısıtlar")
        hr = QHBoxLayout(gb_rules)

        labels = ["Pzt", "Salı", "Çar", "Per", "Cum", "Cmt", "Paz"]
        self.chk_days: list[QCheckBox] = []
        hr.addWidget(QLabel("Günleri dışla:"))
        for i, lab in enumerate(labels):
            chk = QCheckBox(lab)
            if i in (5, 6): chk.setChecked(True)
            self.chk_days.append(chk)
            hr.addWidget(chk)

        self.sp_gap = QSpinBox(); self.sp_gap.setRange(0, 240); self.sp_gap.setValue(15)
        self.chk_single = QCheckBox("Aynı anda tek sınav (global)")
        hr.addSpacing(12)
        hr.addWidget(QLabel("Bekleme (dk):")); hr.addWidget(self.sp_gap)
        hr.addSpacing(12)
        hr.addWidget(self.chk_single)
        hr.addStretch(1)

        # ---- Ders Seçimi ----
        gb_courses = QGroupBox("Ders Seçimi")
        v_courses = QVBoxLayout(gb_courses)
        self.lst_courses = QListWidget(); self.lst_courses.setSelectionMode(QListWidget.NoSelection)
        v_courses.addWidget(self.lst_courses)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_all = QPushButton("Tümünü Seç")
        self.btn_none = QPushButton("Tümünü Kaldır")
        btn_row.addWidget(self.btn_all)
        btn_row.addWidget(self.btn_none)

        # İstisna butonları + sayaç (Ders Seçimi satırında)
        self.lbl_ov = QLabel("İstisna: 0")
        self.btn_add_ov = QPushButton("İstisna Ekle")
        self.btn_del_ov = QPushButton("İstisna Sil")
        btn_row.addSpacing(12)
        btn_row.addWidget(self.lbl_ov)
        btn_row.addSpacing(12)
        btn_row.addWidget(self.btn_add_ov)
        btn_row.addWidget(self.btn_del_ov)

        v_courses.addLayout(btn_row)

        # ---- Derslikler ----
        rooms_box = QGroupBox("Kullanılacak Derslikler (bilgi)")
        rl = QHBoxLayout(rooms_box)
        self.lst_rooms = QListWidget(); rl.addWidget(self.lst_rooms)

        # ---- Çalıştır ve Sonuç ----
        self.btn_run = QPushButton("Takvimi Oluştur (Otomatik)")
        self.btn_run.clicked.connect(self.run_scheduler)
        self.btn_export = QPushButton("Dışa Aktar")
        self.btn_export.clicked.connect(self.export_schedule)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btn_run)
        btns.addWidget(self.btn_export)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["Ders Kodu","Ders Adı","Tarih","Başlangıç","Süre","Derslik"])

        # ---- Layout ----
        root.addWidget(gb)
        root.addWidget(gb_rules)
        root.addWidget(gb_courses, 3)
        root.addWidget(rooms_box, 2)
        root.addLayout(btns)
        root.addWidget(self.tbl, 4)

        # ---- Sinyaller ----
        self.cmb_dep.currentIndexChanged.connect(self._reload_all)
        self.btn_all.clicked.connect(lambda: self._check_all(True))
        self.btn_none.clicked.connect(lambda: self._check_all(False))
        self.btn_add_ov.clicked.connect(self._add_override)
        self.btn_del_ov.clicked.connect(self._remove_override_via_dialog)
        QTimer.singleShot(250, self._reload_all)

    # ---------------- Yardımcılar ----------------
    def _dep_id(self):
        if self.force_dep_id is not None: return self.force_dep_id
        i = self.cmb_dep.currentIndex()
        return self.cmb_dep.itemData(i) if i >= 0 else None

    def _reload_all(self):
        self._reload_courses()
        self._reload_rooms()
        self._reload_result(self.cmb_type.currentText(), self._dep_id())

    def _reload_courses(self):
        self.lst_courses.clear()
        dep_id = self._dep_id()
        selected_ids = set()
        for r in fetch_courses_with_counts(dep_id):
            it = QListWidgetItem(f"{r['code']} — {r['name']} (öğr: {r['student_count']})")
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            it.setData(Qt.UserRole, int(r["id"]))
            self.lst_courses.addItem(it)
            selected_ids.add(int(r["id"]))

        to_remove = [cid for cid in list(self._course_duration_overrides.keys()) if cid not in selected_ids]
        for cid in to_remove:
            self._course_duration_overrides.pop(cid, None)
        self._update_override_badge()

    def _reload_rooms(self):
        self.lst_rooms.clear()
        for r in list_rooms(self._dep_id()):
            it = QListWidgetItem(f"{r['code']} (kap: {r['capacity']})")
            self.lst_rooms.addItem(it)

    def _check_all(self, state: bool):
        for i in range(self.lst_courses.count()):
            self.lst_courses.item(i).setCheckState(Qt.Checked if state else Qt.Unchecked)

    def _included_courses(self):
        ids = []
        for i in range(self.lst_courses.count()):
            it = self.lst_courses.item(i)
            if it.checkState() == Qt.Checked:
                ids.append(int(it.data(Qt.UserRole)))
        return ids

    # ---------------- Süre İstisna Fonksiyonları ----------------
    def _update_override_badge(self):
        self.lbl_ov.setText(f"İstisna: {len(self._course_duration_overrides)}")

    def _add_override(self):
        """Seçili dersler arasından bir ders için özel süre ekler."""
        available = []
        for i in range(self.lst_courses.count()):
            it = self.lst_courses.item(i)
            if it.checkState() != Qt.Checked:
                continue
            cid = int(it.data(Qt.UserRole))
            text = it.text().split(" (öğr")[0].strip()
            available.append((cid, text))
        if not available:
            return QMessageBox.warning(self, "Uyarı", "Önce en az bir ders seçin.")

        dlg = DurationOverrideDialog(available, self)
        if dlg.exec() == QDialog.Accepted:
            cid, dur = dlg.get_values()
            self._course_duration_overrides[cid] = dur
            self._update_override_badge()
            QMessageBox.information(self, "Eklendi", f"Süre istisnası atandı: {dur} dk")

    def _remove_override_via_dialog(self):
        if not self._course_duration_overrides:
            return QMessageBox.information(self, "Bilgi", "Silinecek istisna yok.")

        dep_id = self._dep_id()
        all_courses = {int(r["id"]): r for r in fetch_courses_with_counts(dep_id)}
        items = []
        for cid in list(self._course_duration_overrides.keys()):
            r = all_courses.get(cid)
            if not r:
                continue
            items.append((cid, f"{r['code']} — {r['name']}"))

        dlg = RemoveOverrideDialog(items, self)
        if dlg.exec() == QDialog.Accepted:
            cid = dlg.get_course_id()
            self._course_duration_overrides.pop(cid, None)
            self._update_override_badge()
            QMessageBox.information(self, "Silindi", "İstisna kaldırıldı.")

    # ---------------- Ana işlem ----------------
    def run_scheduler(self):
        dep_id = self._dep_id()
        if not dep_id:
            return QMessageBox.warning(self, "Uyarı", "Bölüm seçilmedi.")

        start_dt = self.date_start.date().toPython()
        end_dt   = self.date_end.date().toPython()
        start_time = self.time_start.time().toString("HH:mm")
        end_time   = self.time_end.time().toString("HH:mm")
        default_dur = int(self.sp_dur.value())
        gap = int(self.sp_gap.value())
        single = self.chk_single.isChecked()
        include_ids = self._included_courses()
        excluded = {i for i, chk in enumerate(self.chk_days) if chk.isChecked()}

        if not include_ids:
            return QMessageBox.warning(self, "Uyarı", "En az bir ders seçin.")
        if end_dt < start_dt:
            return QMessageBox.warning(self, "Uyarı", "Bitiş tarihi başlangıçtan önce olamaz.")
        if start_time >= end_time:
            return QMessageBox.warning(self, "Uyarı", "Saat aralığı geçersiz (başlangıç < bitiş olmalı).")

        placed, warns = schedule_exams(
            department_id=dep_id,
            exam_type=self.cmb_type.currentText(),
            start_date=start_dt,
            end_date=end_dt,
            start_time=start_time,
            end_time=end_time,
            default_duration_min=default_dur,
            excluded_weekdays=excluded,
            min_gap_min=gap,
            single_at_a_time=single,
            include_course_ids=include_ids,
            duration_overrides=self._course_duration_overrides
        )

        self._reload_result(self.cmb_type.currentText(), dep_id)
        msg = f"{placed} ders yerleştirildi."
        if warns:
            msg += "\n" + "\n".join(f"- {w}" for w in warns[:12])
            if len(warns) > 12:
                msg += f"\n(+{len(warns)-12} uyarı daha)"
        QMessageBox.information(self, "Sonuç", msg)

    def _reload_result(self, exam_type, dep_id):
        rows = list_scheduled(exam_type, dep_id)
        self.tbl.setRowCount(0)
        for r in rows:
            i = self.tbl.rowCount(); self.tbl.insertRow(i)
            self.tbl.setItem(i, 0, QTableWidgetItem(r["code"]))
            self.tbl.setItem(i, 1, QTableWidgetItem(r["name"]))
            self.tbl.setItem(i, 2, QTableWidgetItem(r["date"]))
            self.tbl.setItem(i, 3, QTableWidgetItem(r["start_time"]))
            self.tbl.setItem(i, 4, QTableWidgetItem(str(r["duration_min"])))
            self.tbl.setItem(i, 5, QTableWidgetItem(r["room_code"]))

    def export_schedule(self):
        dep_id = self._dep_id()
        exam_type = self.cmb_type.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, "Sınav Programını Dışa Aktar",
            "sinav_programi.xlsx",
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not path: return
        try:
            out = export_schedule_to_file(exam_type, dep_id, path)
            QMessageBox.information(self, "Dışa Aktarım", f"Kaydedildi:\n{out}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarılamadı:\n{e}")
