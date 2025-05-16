from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import QDate, Qt
import bcrypt

class LoginDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("ورود به نرم‌افزار")
        self.setFixedSize(300, 200)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        login_button = QPushButton("ورود")
        login_button.clicked.connect(self.check_login)

        layout.addRow("نام کاربری:", self.username_input)
        layout.addRow("رمز عبور:", self.password_input)
        layout.addRow(login_button)
        self.setLayout(layout)

        # استایل‌دهی
        self.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
                font-family: Vazir, Arial;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
        """)

    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().encode('utf-8')

        if not username or not password:
            QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور نمی‌توانند خالی باشند!")
            return

        try:
            self.db_manager.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = self.db_manager.fetchone()
            if result:
                stored_hash = result[0].encode('utf-8')
                if bcrypt.checkpw(password, stored_hash):
                    self.accept()
                else:
                    QMessageBox.warning(self, "خطا", "نام کاربری یا رمز عبور اشتباه است!")
            else:
                QMessageBox.warning(self, "خطا", "نام کاربری یا رمز عبور اشتباه است!")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")