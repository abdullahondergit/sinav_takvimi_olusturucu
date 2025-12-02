# src/ui/tabs/users.py
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from src.services.users_repo_sqlite import (
    list_users, get_roles, create_user, update_user, reset_password, delete_user, exists_username,
    department_has_coordinator
)
from src.services.room_repo_sqlite import list_departments


class UsersTab(QWidget):
    """
    Sadece ADMIN görecek.
    - Kullanıcıları listeler
    - Admin/Koordinatör ekle/güncelle/sil
    - Şifre sıfırlama
    """
    def __init__(self, current_user: dict | None = None):
        super().__init__()
        self.current_user = current_user  # admin bilgisi (kendi kendini silmeyi engellemek için)
        self._selected_user_id: int | None = None
        self._build_ui()
        self._load_roles()
        self._load_departments()
        self._reload_table()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)

        # Liste
        gb_list = QGroupBox("Kullanıcılar")
        vl_list = QVBoxLayout(gb_list)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["ID", "Kullanıcı Adı", "Rol", "Bölüm", "DeptID"])
        self.tbl.setColumnHidden(4, True)  
        self.tbl.setSelectionBehavior(self.tbl.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(self.tbl.SelectionMode.SingleSelection)
        self.tbl.itemSelectionChanged.connect(self._on_table_select)
        vl_list.addWidget(self.tbl)

        # Form
        gb_form = QGroupBox("Kullanıcı Formu")
        form = QFormLayout(gb_form)

        self.ed_username = QLineEdit()
        self.ed_password = QLineEdit(); self.ed_password.setPlaceholderText("Yeni kullanıcı için zorunlu / Güncellemede boş")
        self.ed_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.cmb_role = QComboBox()
        self.cmb_role.currentIndexChanged.connect(self._on_role_change)

        self.cmb_department = QComboBox()

        form.addRow("Kullanıcı Adı:", self.ed_username)
        form.addRow("Şifre:", self.ed_password)
        form.addRow("Rol:", self.cmb_role)
        form.addRow("Bölüm:", self.cmb_department)

        # Butonlar
        btns = QHBoxLayout()
        self.btn_new = QPushButton("Ekle");      self.btn_new.clicked.connect(self._on_add)
        self.btn_upd = QPushButton("Güncelle");  self.btn_upd.clicked.connect(self._on_update)
        self.btn_pwd = QPushButton("Şifre Sıfırla"); self.btn_pwd.clicked.connect(self._on_reset_password)
        self.btn_del = QPushButton("Sil");       self.btn_del.clicked.connect(self._on_delete)
        self.btn_clear = QPushButton("Temizle"); self.btn_clear.clicked.connect(self._clear_form)
        btns.addWidget(self.btn_new); btns.addWidget(self.btn_upd)
        btns.addWidget(self.btn_pwd); btns.addWidget(self.btn_del); btns.addWidget(self.btn_clear)

        root.addWidget(gb_list)
        root.addWidget(gb_form)
        root.addLayout(btns)

    def _reload_table(self):
        self.tbl.setRowCount(0)
        for r in list_users():
            rd = dict(r)
            row = self.tbl.rowCount()
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(rd.get("id", ""))))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(rd.get("username", ""))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(rd.get("role", ""))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(rd.get("department_name", ""))))
            self.tbl.setItem(row, 4, QTableWidgetItem("" if rd.get("department_id") is None else str(rd.get("department_id"))))

        self._selected_user_id = None

    def _load_roles(self):
            self.cmb_role.clear()
            self.cmb_role.addItem("coordinator", "coordinator")

    def _load_departments(self):
        self.cmb_department.clear()
        self.cmb_department.addItem("— Seçiniz —", None)
        for d in list_departments():
            self.cmb_department.addItem(d["name"], d["id"])

    def _selected_department_id(self):
        i = self.cmb_department.currentIndex()
        return self.cmb_department.itemData(i)

    def _selected_role(self):
        i = self.cmb_role.currentIndex()
        return self.cmb_role.itemData(i)

    def _on_role_change(self):
        role = self._selected_role()
        if role == "admin":
            self.cmb_department.setEnabled(False)
            self.cmb_department.setCurrentIndex(0)  
        else:
            self.cmb_department.setEnabled(True)

    def _select_department_in_combo(self, dep_id: int | None):
        """
        Combobox’ta itemData == dep_id olanı seçer. dep_id None ise —Seçiniz—.
        """
        if dep_id is None:
            self.cmb_department.setCurrentIndex(0)
            return
        for i in range(self.cmb_department.count()):
            if self.cmb_department.itemData(i) == dep_id:
                self.cmb_department.setCurrentIndex(i)
                return

        self.cmb_department.setCurrentIndex(0)

    def _on_table_select(self):
        items = self.tbl.selectedItems()
        if not items:
            self._selected_user_id = None
            return
        row = items[0].row()

        self._selected_user_id = int(self.tbl.item(row, 0).text())
        username = self.tbl.item(row, 1).text()
        role = self.tbl.item(row, 2).text()
        dept_id_text = self.tbl.item(row, 4).text().strip()
        dep_id = int(dept_id_text) if dept_id_text else None


        self.ed_username.setText(username)
        self.ed_password.clear()

        for i in range(self.cmb_role.count()):
            if self.cmb_role.itemData(i) == role:
                self.cmb_role.setCurrentIndex(i)
                break
        self._on_role_change()

        self._select_department_in_combo(dep_id)

    def _clear_form(self):
        self._selected_user_id = None
        self.ed_username.clear()
        self.ed_password.clear()

        for i in range(self.cmb_role.count()):
            if self.cmb_role.itemData(i) == "admin":
                self.cmb_role.setCurrentIndex(i)
                break
        self._on_role_change()
        self.cmb_department.setCurrentIndex(0)

    # ---------------- Actions ----------------
    def _on_add(self):
        username = (self.ed_username.text() or "").strip()
        password = (self.ed_password.text() or "").strip()
        role = self._selected_role()
        dep_id = self._selected_department_id()

        if not username:
            QMessageBox.warning(self, "Uyarı", "Kullanıcı adı zorunludur.")
            return
        if exists_username(username):
            QMessageBox.warning(self, "Uyarı", "Bu kullanıcı adı zaten mevcut.")
            return
        if not password:
            QMessageBox.warning(self, "Uyarı", "Yeni kullanıcı için şifre zorunludur.")
            return
        if role == "coordinator" and not dep_id:
            QMessageBox.warning(self, "Uyarı", "Koordinatör için bölüm seçmelisiniz.")
            return


        if role == "coordinator" and dep_id and department_has_coordinator(int(dep_id)):
            QMessageBox.warning(
                self,
                "Kural",
                "Bu bölümde zaten bir koordinatör var. Lütfen farklı bir bölüm seçin "
                "ya da mevcut koordinatörü güncelleyin."
            )
            return

        try:
            new_id = create_user(username, password, role, dep_id)
            self._reload_table()
            self._clear_form()
            QMessageBox.information(self, "Tamam", f"Kullanıcı eklendi (id={new_id}).")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kullanıcı eklenemedi:\n{e}")


    def _on_update(self):
        if not self._selected_user_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden bir kullanıcı seçin.")
            return

        username = (self.ed_username.text() or "").strip()
        role = self._selected_role()
        dep_id = self._selected_department_id()

        if not username:
            QMessageBox.warning(self, "Uyarı", "Kullanıcı adı zorunludur.")
            return
        if role == "coordinator" and not dep_id:
            QMessageBox.warning(self, "Uyarı", "Koordinatör için bölüm seçmelisiniz.")
            return

        if role == "coordinator" and dep_id and department_has_coordinator(int(dep_id), exclude_user_id=int(self._selected_user_id)):
            QMessageBox.warning(
                self,
                "Kural",
                "Bu bölümde zaten başka bir koordinatör var. Önce o kaydı güncelleyiniz "
                "ya da bölüm atamasını değiştiriniz."
            )
            return

        try:
            ok = update_user(self._selected_user_id, username, role, dep_id)
            if ok:
                self._reload_table()
                QMessageBox.information(self, "Tamam", "Kullanıcı güncellendi.")
            else:
                QMessageBox.warning(self, "Bilgi", "Değişen bir şey yok.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Güncelleme başarısız:\n{e}")


    def _on_reset_password(self):
        if not self._selected_user_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden bir kullanıcı seçin.")
            return
        new_pwd, ok = self._ask_text("Yeni şifre girin:")
        if not ok or not new_pwd:
            return
        try:
            if reset_password(self._selected_user_id, new_pwd):
                QMessageBox.information(self, "Tamam", "Şifre güncellendi.")
            else:
                QMessageBox.warning(self, "Bilgi", "Şifre değişmedi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Şifre sıfırlanamadı:\n{e}")

    def _on_delete(self):
        if not self._selected_user_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden bir kullanıcı seçin.")
            return
        if self.current_user and int(self.current_user.get("id", -1)) == int(self._selected_user_id):
            QMessageBox.warning(self, "Uyarı", "Kendi hesabınızı silemezsiniz.")
            return

        if QMessageBox.question(self, "Onay", "Seçili kullanıcı silinsin mi?") != QMessageBox.StandardButton.Yes:
            return

        try:
            if delete_user(self._selected_user_id):
                self._reload_table()
                self._clear_form()
                QMessageBox.information(self, "Tamam", "Kullanıcı silindi.")
            else:
                QMessageBox.warning(self, "Bilgi", "Silinecek kullanıcı bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kullanıcı silinemedi:\n{e}")

    def _ask_text(self, prompt: str):
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Girdi", prompt)
        return text, ok
