import sys, os
from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QHBoxLayout, QMessageBox, QFrame, QCheckBox
)
from PySide6.QtCore import Qt

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from src.db.init_db import init_db
from src.db.sqlite import get_conn
from src.auth.security import verify_password
from src.db.sqlite import DB_PATH, get_connection
print(f"⚙️ DB path -> {DB_PATH}")
print("⚙️ Tables ->", get_connection().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())

from src.ui.mainwindow import MainWindow   

def fetch_user_by_username(username: str):
    """Kullanıcıyı email ile getirir (sqlite3.Row döner veya None)."""
    con = get_conn()
    cur = con.cursor()
    cur.execute("SELECT id, username, password_hash, role, department_id FROM users WHERE username=?", (username,))

    row = cur.fetchone()
    con.close()
    return row


LOGIN_QSS = """
QDialog {
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #071029, stop:1 #09142a);
    color: #e6eef8;
    font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial;
}

/* Card */
QFrame#card {
    background: rgba(17,24,39,0.72);
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.04);
    padding: 20px;
}

/* Logo monogram */
QLabel#logo {
    color: white;
    font-weight: 700;
    font-size: 20px;
    min-width: 72px;
    min-height: 72px;
    max-width: 72px;
    max-height: 72px;
    qproperty-alignment: AlignCenter;
    border-radius: 36px;
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #2563eb, stop:1 #7c3aed);
}

/* Titles */
QLabel#title {
    color: #e6eef8;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.2px;
}
QLabel#subtitle, QLabel#hint {
    color: #9aa6b2;
    font-size: 12px;
}

/* Inputs */
QLineEdit {
    color: #e6eef8;
    background: rgba(11,17,28,0.6);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 10px 12px;
    selection-background-color: #3b82f6;
}
QLineEdit:focus {
    border: 1px solid #3b82f6;
    background: rgba(11,17,28,0.75);
}

/* Primary button */
QPushButton#primary {
    color: white;
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #3b82f6, stop:1 #7c3aed);
    border: none;
    border-radius: 10px;
    padding: 10px;
    min-height: 40px;
    font-weight: 600;
}
QPushButton#primary:hover { opacity: 0.95; }
QPushButton#primary:pressed { opacity: 0.9; }
QPushButton#primary:disabled {
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.4);
}

/* Checkbox */
QCheckBox { color: #9aa6b2; }

/* small helpers */
QLabel#hint { margin-top: 6px; }
"""

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kullanıcı Girişi")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(LOGIN_QSS)
        self.user_record = None  

        init_db()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        card = QFrame()
        card.setObjectName("card")
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(24, 20, 24, 20)
        card_l.setSpacing(12)

        logo = QLabel("")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignCenter)
        card_l.addWidget(logo, alignment=Qt.AlignHCenter)

        title = QLabel("Sınav Takvimi Oluşturucu")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignHCenter)
        subtitle = QLabel("Lütfen hesabınızla giriş yapın.")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignHCenter)
        card_l.addWidget(title); card_l.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        self.username = QLineEdit(); self.username.setPlaceholderText("admin")
        self.password = QLineEdit(); self.password.setPlaceholderText("Şifre"); self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Kullanıcı", self.username); form.addRow("Şifre", self.password)
        card_l.addLayout(form)

        toggle_row = QHBoxLayout()
        self.show_pass = QCheckBox("Şifreyi göster")
        self.show_pass.stateChanged.connect(lambda st: self.password.setEchoMode(QLineEdit.Normal if st else QLineEdit.Password))
        toggle_row.addWidget(self.show_pass); toggle_row.addStretch(1)
        card_l.addLayout(toggle_row)

        hint = QLabel("")
        hint.setObjectName("hint"); hint.setAlignment(Qt.AlignLeft)
        card_l.addWidget(hint)

        self.btn_login = QPushButton("Giriş Yap")
        self.btn_login.setObjectName("primary")
        self.btn_login.clicked.connect(self.try_login)
        self.btn_login.setDefault(True)       
        self.btn_login.setAutoDefault(True)
        card_l.addWidget(self.btn_login)

        self.username.setFocus()
        root.addStretch(1); root.addWidget(card, alignment=Qt.AlignCenter); root.addStretch(1)

    def try_login(self):
        username = (self.username.text() or "").strip().lower()
        pwd = self.password.text() or ""
        if not username or not pwd:
            QMessageBox.warning(self, "Eksik Bilgi", "E-posta ve şifre gerekli.")
            return

        try:
            row = fetch_user_by_username(username)
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"DB erişim hatası:\n{e}")
            return

        if not row or not verify_password(pwd, row["password_hash"]):
            QMessageBox.warning(self, "Hatalı Giriş", "E-posta veya şifre yanlış.")
            return

        self.user_record = row
        self.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = LoginDialog()
    if dlg.exec() == QDialog.Accepted and dlg.user_record:
        mw = MainWindow(dlg.user_record)   
        mw.show()
        sys.exit(app.exec())
