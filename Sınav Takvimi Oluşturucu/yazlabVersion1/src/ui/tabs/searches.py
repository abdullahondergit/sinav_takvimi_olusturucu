from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem,QFrame, QHeaderView
)
from PySide6.QtCore import Qt
from src.services.room_repo_sqlite import list_departments
from src.services.search_repo_sqlite import get_student_courses, get_course_students
from src.db.sqlite import get_connection


class SearchesTab(QWidget):
    def __init__(self, current_user, force_department_id=None):
        super().__init__()
        self.current_user = current_user
        self.force_dep_id = force_department_id
        self._build_ui()

    def _build_ui(self):
            root = QVBoxLayout(self)
            root.setContentsMargins(10, 10, 10, 10) 
            root.setSpacing(15)

            top_frame = QFrame()
            top_frame.setObjectName("card")
            top_frame_vbox = QVBoxLayout(top_frame)
            top_frame_vbox.setContentsMargins(15, 15, 15, 15)

            search_hl = QHBoxLayout()
            
            self.cmb_dep_l = QComboBox()
            self._load_departments(self.cmb_dep_l, add_all=False)

            self.ed_sno = QLineEdit()
            self.ed_sno.setPlaceholderText("Öğrenci No")
            self.ed_sno.setFixedWidth(200) 

            self.btn_left = QPushButton("Dersleri Listele") 
            self.btn_left.clicked.connect(self._query_left)
            self.btn_left.setFixedWidth(140)

            search_hl.addWidget(QLabel("Bölüm:"))
            search_hl.addWidget(self.cmb_dep_l, 1)
            search_hl.addWidget(QLabel("Öğrenci No:"))
            search_hl.addWidget(self.ed_sno)
            search_hl.addWidget(self.btn_left)
            search_hl.addStretch(1) 

            self.lbl_student_info = QLabel("— Öğrenci bilgisi ve dersleri burada listelenecek. —")
            self.lbl_student_info.setStyleSheet("font-weight: 600; margin: 4px 4px; color: #a0a0a0;")

            self.tbl_left = QTableWidget(0, 2)
            self.tbl_left.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı"])
            self.tbl_left.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.tbl_left.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.tbl_left.setMinimumHeight(120) 

            top_frame_vbox.addLayout(search_hl)
            top_frame_vbox.addWidget(self.lbl_student_info)
            top_frame_vbox.addWidget(self.tbl_left)
            
            root.addWidget(top_frame)
            


            main_content_hl = QHBoxLayout()
            
            course_list_frame = QFrame()
            course_list_frame.setObjectName("card")
            course_list_vbox = QVBoxLayout(course_list_frame)
            course_list_vbox.setContentsMargins(15, 15, 15, 15)
            
            course_list_vbox.addWidget(QLabel("📚 Tüm Dersler"), alignment=Qt.AlignTop)
            
            top_row = QHBoxLayout()
            self.cmb_dep_r = QComboBox()
            self._load_departments(self.cmb_dep_r, add_all=False)
            self.cmb_dep_r.currentIndexChanged.connect(self._load_courses)
            top_row.addWidget(QLabel("Bölüm:"))
            top_row.addWidget(self.cmb_dep_r, 1)
            course_list_vbox.addLayout(top_row)

            self.tbl_courses = QTableWidget(0, 2)
            self.tbl_courses.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı"])
            self.tbl_courses.setSelectionBehavior(QTableWidget.SelectRows)
            self.tbl_courses.setSelectionMode(QTableWidget.SingleSelection)
            self.tbl_courses.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.tbl_courses.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            self.tbl_courses.itemSelectionChanged.connect(self._on_course_select)
            course_list_vbox.addWidget(self.tbl_courses)
            
            main_content_hl.addWidget(course_list_frame, 40) # %40 genişlik

            student_list_frame = QFrame()
            student_list_frame.setObjectName("card")
            student_list_vbox = QVBoxLayout(student_list_frame)
            student_list_vbox.setContentsMargins(15, 15, 15, 15)
            
            student_list_vbox.addWidget(QLabel("🧑‍🎓 Bu dersi alan öğrenciler"), alignment=Qt.AlignTop)

            self.tbl_right = QTableWidget(0, 2)
            self.tbl_right.setHorizontalHeaderLabels(["Öğrenci No", "Ad Soyad"])
            self.tbl_right.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.tbl_right.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            student_list_vbox.addWidget(self.tbl_right)
            

            main_content_hl.addWidget(student_list_frame, 60) 

            root.addLayout(main_content_hl, 1)            
            self._load_courses()

    # -------- Departman yükleme  --------
    def _load_departments(self, combo: QComboBox, add_all=False):
        combo.clear()
        if self.force_dep_id is not None:
            for d in list_departments():
                if d["id"] == self.force_dep_id:
                    combo.addItem(d["name"], d["id"])
                    break
            combo.setEnabled(False)
        else:
            if add_all:
                combo.addItem("Tümü", None)
            for d in list_departments():
                combo.addItem(d["name"], d["id"])
            combo.setEnabled(True)

    def _dep_id_of(self, combo: QComboBox):
        if self.force_dep_id is not None:
            return self.force_dep_id
        i = combo.currentIndex()
        return combo.itemData(i)

    # ================= SOL TARAF İŞLEMLERİ =================
    def _resolve_student_name_cols(self):
        con = get_connection()
        cur = con.cursor()
        cur.execute("PRAGMA table_info(students)")
        cols = {r["name"] for r in cur.fetchall()}
        con.close()

        if {"name", "surname"} <= cols:
            return "name", "surname", None
        if {"first_name", "last_name"} <= cols:
            return "first_name", "last_name", None
        if {"ad", "soyad"} <= cols:
            return "ad", "soyad", None
        if "full_name" in cols:
            return None, None, "full_name"
        return None, None, None

    def _has_students_department_col(self):
        con = get_connection()
        cur = con.cursor()
        cur.execute("PRAGMA table_info(students)")
        cols = {r["name"] for r in cur.fetchall()}
        con.close()
        return "department_id" in cols

    def _fetch_student_name(self, sno: str, dep_id: int | None):
        fname_col, lname_col, full_col = self._resolve_student_name_cols()
        has_dep = self._has_students_department_col()

        if not any([full_col, fname_col]):
            return None

        con = get_connection()
        cur = con.cursor()
        dep_filter = ""
        params = [sno]
        if has_dep and dep_id is not None:
            dep_filter = " AND department_id=?"
            params.append(dep_id)

        if full_col:
            q = f"SELECT {full_col} AS full_name FROM students WHERE student_no=?{dep_filter}"
            cur.execute(q, params)
            row = cur.fetchone()
            con.close()
            return row["full_name"] if row else None

        q = f"SELECT {fname_col} AS fname, {lname_col} AS lname FROM students WHERE student_no=?{dep_filter}"
        cur.execute(q, params)
        row = cur.fetchone()
        con.close()
        return f"{row['fname']} {row['lname']}" if row else None

    def _query_left(self):
        dep_id = self._dep_id_of(self.cmb_dep_l)
        sno = (self.ed_sno.text() or "").strip()

        self.tbl_left.setRowCount(0)
        self.lbl_student_info.setText("")
        if not sno:
            return

        fullname = self._fetch_student_name(sno, dep_id)
        if fullname:
            self.lbl_student_info.setText(f"👤 {fullname} — {sno}")
        else:
            self.lbl_student_info.setText("Öğrenci bulunamadı veya ad-soyad kolonları tanınmadı.")

        rows = get_student_courses(sno, department_id=dep_id)
        for r in rows:
            i = self.tbl_left.rowCount()
            self.tbl_left.insertRow(i)
            item_code = QTableWidgetItem(r["code"])
            item_name = QTableWidgetItem(r["name"])
            item_name.setToolTip(r["name"])
            self.tbl_left.setItem(i, 0, item_code)
            self.tbl_left.setItem(i, 1, item_name)

        self.tbl_left.resizeColumnToContents(0)
        self.tbl_left.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    # ================= SAĞ TARAF İŞLEMLERİ =================
    def _load_courses(self):
        """Bölüme göre tüm dersleri listele (kod + ad)."""
        dep_id = self._dep_id_of(self.cmb_dep_r)

        con = get_connection()
        cur = con.cursor()
        if dep_id is not None:
            cur.execute("SELECT id, code, name FROM courses WHERE department_id=? ORDER BY code", (dep_id,))
        else:
            cur.execute("SELECT id, code, name FROM courses ORDER BY code")
        rows = cur.fetchall()
        con.close()

        self.tbl_courses.setRowCount(0)
        for r in rows:
            i = self.tbl_courses.rowCount()
            self.tbl_courses.insertRow(i)

            code = str(r["code"])
            name = str(r["name"])

            it_code = QTableWidgetItem(code)
            it_name = QTableWidgetItem(name)
            it_name.setToolTip(name)

            it_code.setData(Qt.UserRole, code)          
            it_code.setData(Qt.UserRole + 1, int(r["id"]))  
            it_name.setData(Qt.UserRole, code)           

            self.tbl_courses.setItem(i, 0, it_code)
            self.tbl_courses.setItem(i, 1, it_name)

        if self.tbl_courses.rowCount() > 0:
            self.tbl_courses.selectRow(0)
            self._on_course_select()
        else:
            self.tbl_right.setRowCount(0)

    def _on_course_select(self):
        items = self.tbl_courses.selectedItems()
        if not items:
            self.tbl_right.setRowCount(0)
            return

        row = items[0].row()

        code_item = self.tbl_courses.item(row, 0)  
        code = code_item.data(Qt.UserRole) if code_item and code_item.data(Qt.UserRole) else code_item.text()

        dep_id = self._dep_id_of(self.cmb_dep_r)
        students = get_course_students(code, department_id=dep_id)

        self.tbl_right.setRowCount(0)
        for s in students:
            i = self.tbl_right.rowCount()
            self.tbl_right.insertRow(i)
            self.tbl_right.setItem(i, 0, QTableWidgetItem(s["student_no"]))
            self.tbl_right.setItem(i, 1, QTableWidgetItem(s["full_name"]))

        self.tbl_right.resizeColumnToContents(0)
        self.tbl_right.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

