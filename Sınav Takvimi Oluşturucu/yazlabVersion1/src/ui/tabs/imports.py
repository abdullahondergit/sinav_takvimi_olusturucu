from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton, QLabel,
    QFileDialog, QTextEdit, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from src.services.room_repo_sqlite import list_departments
from src.services.importer_sqlite import import_courses, import_students
from src.services.guards import DomainError


class ImportsTab(QWidget):
    coursesImported = Signal()
    studentsImported = Signal()

    def __init__(self, force_department_id=None):
        super().__init__()
        self.force_dep_id = force_department_id

        self.course_path = None
        self.student_path = None

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("Bölüm:"))
        self.cmb_dep = QComboBox()
        self._load_departments()
        row.addWidget(self.cmb_dep, 1)
        root.addLayout(row)

        gb1 = QGroupBox("Ders Listesi Yükle (dersler.xlsx)")
        g1 = QHBoxLayout(gb1)
        self.lbl_course = QLabel("Dosya: (seçilmedi)")
        btn_course = QPushButton("Dosya Seç")
        btn_course.clicked.connect(self._pick_courses)
        btn_course_imp = QPushButton("İçe Aktar")
        btn_course_imp.clicked.connect(self._import_courses)
        g1.addWidget(self.lbl_course, 1)
        g1.addWidget(btn_course)
        g1.addWidget(btn_course_imp)

        gb2 = QGroupBox("Öğrenci Listesi Yükle (ogrenciler.xlsx)")
        g2 = QHBoxLayout(gb2)
        self.lbl_student = QLabel("Dosya: (seçilmedi)")
        btn_student = QPushButton("Dosya Seç")
        btn_student.clicked.connect(self._pick_students)
        btn_student_imp = QPushButton("İçe Aktar")
        btn_student_imp.clicked.connect(self._import_students)
        g2.addWidget(self.lbl_student, 1)
        g2.addWidget(btn_student)
        g2.addWidget(btn_student_imp)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("İçe aktarma sonuçları burada görünecek...")

        root.addWidget(gb1)
        root.addWidget(gb2)
        root.addWidget(self.out, 1)

    def _dep_id(self):
        if self.force_dep_id is not None:
            return self.force_dep_id
        i = self.cmb_dep.currentIndex()
        return self.cmb_dep.itemData(i) if i >= 0 else None

    def _load_departments(self):
        self.cmb_dep.clear()
        if self.force_dep_id is not None:
            for d in list_departments():
                if d["id"] == self.force_dep_id:
                    self.cmb_dep.addItem(d["name"], d["id"])
                    break
            self.cmb_dep.setEnabled(False)
        else:
            for d in list_departments():
                self.cmb_dep.addItem(d["name"], d["id"])
            self.cmb_dep.setEnabled(True)

    def _pick_courses(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ders Excel Seç", "", "Excel (*.xlsx)")
        if path:
            self.course_path = path
            self.lbl_course.setText(f"Dosya: {path}")

    def _pick_students(self):
        path, _ = QFileDialog.getOpenFileName(self, "Öğrenci Excel Seç", "", "Excel (*.xlsx)")
        if path:
            self.student_path = path
            self.lbl_student.setText(f"Dosya: {path}")

    def _import_courses(self):
        dep_id = self._dep_id()
        if not dep_id:
            self.out.append("⚠️ Bölüm seçilmedi.")
            return
        if not self.course_path:
            self.out.append("⚠️ Ders Excel seçilmedi.")
            return
        try:
            res = import_courses(self.course_path, dep_id)
            self.out.append(f"📘 Dersler → Eklendi: {res.inserted}, Güncellendi: {res.updated}")
            if res.errors:
                self.out.append("Hatalar:")
                for e in res.errors:
                    self.out.append(f" - {e}")
            self.coursesImported.emit()
        except DomainError as e:
            QMessageBox.warning(self, "Önce Derslikler", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yükleme başarısız:\n{e}")
        finally:
            self.out.append("—"*40)

    def _import_students(self):
        dep_id = self._dep_id()
        if not dep_id:
            self.out.append("⚠️ Bölüm seçilmedi.")
            return
        if not self.student_path:
            self.out.append("⚠️ Öğrenci Excel seçilmedi.")
            return
        try:
            res = import_students(self.student_path, dep_id)
            self.out.append(f"👥 Öğrenciler → Eklendi: {res.inserted}, Güncellendi: {res.updated}")
            if res.errors:
                self.out.append("Hatalar:")
                for e in res.errors:
                    self.out.append(f" - {e}")
            self.studentsImported.emit()
        except DomainError as e:
            QMessageBox.warning(self, "Önce Derslikler", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yükleme başarısız:\n{e}")
        finally:
            self.out.append("—"*40)
