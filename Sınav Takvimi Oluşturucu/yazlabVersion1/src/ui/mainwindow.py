from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PySide6.QtCore import QObject

from src.services.guards import classrooms_ready, imports_ready

from src.ui.tabs.rooms import RoomsTab
from src.ui.tabs.imports import ImportsTab
from src.ui.tabs.searches import SearchesTab
from src.ui.tabs.scheduler import SchedulerTab
from src.ui.tabs.seating import SeatingTab
from src.ui.tabs.searchroom import SearchRoomTab
from src.ui.tabs.students_view import StudentsViewTab
from src.ui.tabs.courses_view import CoursesViewTab
from src.ui.tabs.users import UsersTab


MAIN_QSS = """
QMainWindow {
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #071029, stop:1 #0b1530);
    color: #e6eef8;
    font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial;
}

/* Central pane / card-like look for tab contents */
QTabWidget::pane {
    background: rgba(17,24,39,0.72);
    border-radius: 12px;
    padding: 20px;
    margin: 8px;
    border: 1px solid rgba(255,255,255,0.03);
}

/* Tab bar */
QTabBar::tab {
    background: transparent;
    color: #cbd5e1;
    padding: 8px 14px;
    border-radius: 8px;
    margin-right: 6px;
    min-height: 36px;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #2563eb, stop:1 #7c3aed);
    color: white;
    font-weight: 600;
    box-shadow: 0 6px 18px rgba(124,58,237,0.12);
}
QTabBar::tab:hover { background: rgba(255,255,255,0.02); }

/* Buttons (consistent with login) */
QPushButton {
    color: white;
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #3b82f6, stop:1 #7c3aed);
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 34px;
    font-weight: 600;
}
QPushButton:disabled {
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.4);
}

/* Inputs & tables */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background: rgba(11,17,28,0.6);
    color: #e6eef8;
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}

/* Table styling */
QTableView {
    background: transparent;
    alternate-background-color: rgba(255,255,255,0.015);
    gridline-color: rgba(255,255,255,0.08);
    color: #e6eef8;
    selection-background-color: rgba(59,130,246,0.22);
    font-size: 13px;
}
QHeaderView::section {
    background: rgba(11,17,28,0.75);
    color: #cbd5e1;
    padding: 10px 8px;
    border: none;
    font-weight: 700;
    min-height: 38px;
}

/* Small helpers and frames */
QFrame.card {
    background: rgba(17,24,39,0.72);
    border-radius: 10px;
    padding: 10px;
    border: 1px solid rgba(255,255,255,0.03);
}
QToolTip {
    background-color: #0b1530;
    color: #e6eef8;
    border: 1px solid rgba(255,255,255,0.04);
}
"""


class MainWindow(QMainWindow):
    def __init__(self, user_row):
        super().__init__()
        self.user = user_row
        self.setWindowTitle("Sınav Takvimi Oluşturucu")
        self.resize(1200, 700)

        self.setStyleSheet(MAIN_QSS)

        force_dep_id = None
        if self.user["role"] == "coordinator":
            force_dep_id = int(self.user["department_id"]) if self.user["department_id"] is not None else None
        self.force_dep_id = force_dep_id

        self.tabs = QTabWidget()
        self._classroom_info_shown = False

        self.rooms_tab = RoomsTab(self.force_dep_id)
        self.imports_tab = ImportsTab(self.force_dep_id)
        self.searches_tab = SearchesTab(self.user, self.force_dep_id)
        self.searchroom_tab = SearchRoomTab(self.force_dep_id)
        self.seating_tab = SeatingTab(self.user, self.force_dep_id)

        self.scheduler_tab = None     # Programlama (sınav programı)
        self.students_tab = None      # Öğrenci Listesi
        self.courses_tab = None       # Ders Listesi
        self.users_tab = None         # Kullanıcı Yönetimi (sadece admin)

        self.tabs.addTab(self.rooms_tab, "Derslikler")
        self.tabs.addTab(self.searchroom_tab, "Sınıf Arama")
        self.tabs.addTab(self.imports_tab, "İçe Aktarım")
        self.tabs.addTab(self.searches_tab, "Aramalar")
        self.tabs.addTab(self.seating_tab, "Oturma Planı")

        if self.user["role"] == "admin":
            self.users_tab = UsersTab(self.user)
            self.tabs.addTab(self.users_tab, "Kullanıcı Yönetimi")

        self.setCentralWidget(self.tabs)

        self.imports_tab.studentsImported.connect(self._open_students_tab)
        self.imports_tab.coursesImported.connect(self._open_courses_tab)
        self.imports_tab.studentsImported.connect(self._maybe_add_scheduler_tab)
        self.imports_tab.coursesImported.connect(self._maybe_add_scheduler_tab)
        self.imports_tab.studentsImported.connect(self._refresh_searches_tab)
        self.imports_tab.coursesImported.connect(self._refresh_searches_tab)

        if hasattr(self.rooms_tab, "dataChanged"):
            self.rooms_tab.dataChanged.connect(self.apply_feature_gating)
            self.rooms_tab.dataChanged.connect(self._on_rooms_changed)

        self.tabs.currentChanged.connect(self._on_tab_changed)


        self.apply_feature_gating()
        self._maybe_add_scheduler_tab()

    def _open_students_tab(self):
        if self.students_tab is None:
            self.students_tab = StudentsViewTab(self.force_dep_id)
            self.tabs.addTab(self.students_tab, "Öğrenci Listesi")
        try:
            self.students_tab.refresh()
        except Exception:
            pass
        self.tabs.setCurrentWidget(self.students_tab)

    def _open_courses_tab(self):
        if self.courses_tab is None:
            self.courses_tab = CoursesViewTab(self.force_dep_id)
            self.tabs.addTab(self.courses_tab, "Ders Listesi")
        try:
            self.courses_tab.refresh()
        except Exception:
            pass
        self.tabs.setCurrentWidget(self.courses_tab)

    def _maybe_add_scheduler_tab(self):
        if self.user["role"] != "coordinator":
            if self.scheduler_tab is None:
                self.scheduler_tab = SchedulerTab(self.user, self.force_dep_id)
                self.tabs.addTab(self.scheduler_tab, "Programlama")
            return

        if self.scheduler_tab is None and imports_ready(self.force_dep_id):
            self.scheduler_tab = SchedulerTab(self.user, self.force_dep_id)
            self.tabs.addTab(self.scheduler_tab, "Programlama")

    def _refresh_searches_tab(self):
        """
        Excel import tamamlandıktan sonra arama sekmesini yeniler.
        Böylece yeni dersler/öğrenciler hemen görünebilir.
        """
        if hasattr(self, "searches_tab") and self.searches_tab is not None:
            try:
                if hasattr(self.searches_tab, "reload_data"):
                    self.searches_tab.reload_data()
                else:
                    self.searches_tab.tbl_left.setRowCount(0)
                    self.searches_tab.tbl_right.setRowCount(0)
            except Exception:
                pass

    def _on_rooms_changed(self):
        """
        RoomsTab içinde derslik eklendi/güncellendi/silindi.
        - Kilitleri (enable/disable) tekrar değerlendir.
        - Programlama sekmesindeki oda listesini tazele.
        """
        self.apply_feature_gating()
        if self.scheduler_tab is not None:
            try:
                self.scheduler_tab.refresh_rooms()
            except Exception:
                pass

    def _on_tab_changed(self, idx: int):
        w = self.tabs.widget(idx)
        if self.scheduler_tab is not None and w is self.scheduler_tab:
            try:
                self.scheduler_tab.refresh_rooms()
            except Exception:
                pass
        if self.students_tab is not None and w is self.students_tab:
            try:
                self.students_tab.refresh()
            except Exception:
                pass
        if self.courses_tab is not None and w is self.courses_tab:
            try:
                self.courses_tab.refresh()
            except Exception:
                pass


    def apply_feature_gating(self):
        """
        Derslikler hazır olmadan (kapasite/rows/cols/group koşulları) diğer sekmeler kilitli.
        Admin’in “Kullanıcı Yönetimi” sekmesi daima açık kalmalı.
        """
        ready = classrooms_ready(self.force_dep_id)

        always_open = {"Derslikler", "Sınıf Arama", "İçe Aktarım", "Aramalar"}

        is_admin = (self.user["role"] == "admin")
        if is_admin:
            always_open.add("Kullanıcı Yönetimi")

        for i in range(self.tabs.count()):
            label = self.tabs.tabText(i)
            if label in always_open:
                self.tabs.setTabEnabled(i, True)
            else:
                self.tabs.setTabEnabled(i, bool(ready))

        if not ready and not self._classroom_info_shown:
            QMessageBox.information(
                self,
                "Önce Derslikleri Tamamlayın",
                "Derslik bilgileri (kapasite, satır, sütun ve sıra yapısı) eksiksiz girilene kadar diğer alanlar kapalı.\n"
                "Lütfen önce 'Derslikler' sekmesinden bölümünüzün dersliklerini ekleyin/düzenleyin."
            )
            self._classroom_info_shown = True