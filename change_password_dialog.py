from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import QDate, Qt
import bcrypt

class ChangePasswordDialog(QDialog):
    def __init__(self, db_manager, username, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.username = username
        self.setWindowTitle("تغییر رمز عبور")
        self.setFixedSize(300, 250)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout()
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        change_button = QPushButton("تغییر رمز عبور")
        change_button.clicked.connect(self.change_password)

        layout.addRow("رمز عبور فعلی:", self.current_password_input)
        layout.addRow("رمز عبور جدید:", self.new_password_input)
        layout.addRow("تأیید رمز جدید:", self.confirm_password_input)
        layout.addRow(change_button)
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

    def change_password(self):
        current_password = self.current_password_input.text().encode('utf-8')
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # اعتبارسنجی ورودی‌ها
        if not current_password or not new_password or not confirm_password:
            QMessageBox.warning(self, "خطا", "همه فیلدها باید پر شوند!")
            return
        if new_password != confirm_password:
            QMessageBox.warning(self, "خطا", "رمز عبور جدید و تأیید آن یکسان نیستند!")
            return
        if len(new_password) < 6:
            QMessageBox.warning(self, "خطا", "رمز عبور جدید باید حداقل 6 کاراکتر باشد!")
            return

        try:
            # بررسی رمز عبور فعلی
            self.db_manager.execute("SELECT password_hash FROM users WHERE username = ?", (self.username,))
            result = self.db_manager.fetchone()
            if result:
                stored_hash = result[0].encode('utf-8')
                if bcrypt.checkpw(current_password, stored_hash):
                    # هش کردن رمز عبور جدید
                    new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    # به‌روزرسانی رمز عبور در دیتابیس
                    self.db_manager.execute("UPDATE users SET password_hash = ? WHERE username = ?",
                                          (new_password_hash, self.username))
                    self.db_manager.commit()
                    QMessageBox.information(self, "موفق", "رمز عبور با موفقیت تغییر کرد!")
                    self.accept()
                else:
                    QMessageBox.warning(self, "خطا", "رمز عبور فعلی اشتباه است!")
            else:
                QMessageBox.warning(self, "خطا", "کاربر یافت نشد!")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")