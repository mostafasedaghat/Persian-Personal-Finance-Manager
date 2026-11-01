# -*- coding: utf-8 -*-
"""
ui/dialogs/change_password_dialog.py
====================================
پنجره تغییر رمز عبور — هماهنگ با طراحی پنجره ورود.

منطق change_password دقیقاً مانند قبل است:
  - بررسی پر بودن همه فیلدها
  - یکسان بودن رمز جدید و تأیید آن
  - حداقل ۶ کاراکتر
  - بررسی رمز فعلی با bcrypt و به‌روزرسانی جدول users
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame,
)

import bcrypt

GREEN = "#16a34a"
DARK_GREEN = "#15803d"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
CARD_BORDER = "#d3dce6"


class ChangePasswordDialog(QDialog):
    """پنجره تغییر رمز عبور کاربر جاری."""

    def __init__(self, db_manager, username, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.username = username
        self.setWindowTitle("تغییر رمز عبور")
        self.setFixedSize(400, 440)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.setStyleSheet(f"""
            ChangePasswordDialog {{
                background-color: #eef1f6;
                font-family: 'Vazir', 'Arial';
            }}
            QFrame#banner {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f3d2e, stop:0.55 #166534, stop:1 #15803d);
                border-radius: 16px;
            }}
            QLabel#bannerIcon {{
                background-color: rgba(255, 255, 255, 0.16);
                border-radius: 20px;
                font-size: 22px;
            }}
            QLabel#bannerTitle {{
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }}
            QLabel#bannerSubtitle {{
                color: rgba(255, 255, 255, 210);
                font-size: 11px;
            }}
            QFrame#formCard {{
                background-color: #ffffff;
                border: 1px solid {CARD_BORDER};
                border-radius: 14px;
            }}
            QLineEdit {{
                background-color: #ffffff;
                border: 1px solid {CARD_BORDER};
                border-radius: 9px;
                padding: 10px 12px;
                font-size: 13px;
                color: {TEXT_DARK};
            }}
            QLineEdit:focus {{
                border: 2px solid {GREEN};
                background-color: #fcfffd;
            }}
            QLabel#formLabel {{
                color: {TEXT_MUTED};
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton#primaryBtn {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#primaryBtn:hover {{
                background-color: {DARK_GREEN};
            }}
            QPushButton#primaryBtn:pressed {{
                background-color: #166534;
            }}
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(14)

        # ---------- بنر ----------
        banner = QFrame()
        banner.setObjectName("banner")
        banner_lay = QVBoxLayout(banner)
        banner_lay.setContentsMargins(18, 14, 18, 14)
        banner_lay.setSpacing(4)

        icon = QLabel("🔐")
        icon.setObjectName("bannerIcon")
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("تغییر رمز عبور")
        title.setObjectName("bannerTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel(f"حساب کاربری: {self.username}")
        subtitle.setObjectName("bannerSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        banner_lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)
        banner_lay.addWidget(title)
        banner_lay.addWidget(subtitle)

        layout.addWidget(banner)

        # ---------- کارت فرم ----------
        card = QFrame()
        card.setObjectName("formCard")
        card_lay = QFormLayout(card)
        card_lay.setContentsMargins(20, 18, 20, 18)
        card_lay.setSpacing(11)
        card_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        current_label = QLabel("رمز عبور فعلی:")
        current_label.setObjectName("formLabel")
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        new_label = QLabel("رمز عبور جدید:")
        new_label.setObjectName("formLabel")
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        confirm_label = QLabel("تأیید رمز جدید:")
        confirm_label.setObjectName("formLabel")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)

        change_button = QPushButton("ثبت رمز عبور جدید")
        change_button.setObjectName("primaryBtn")
        change_button.setCursor(Qt.CursorShape.PointingHandCursor)
        change_button.clicked.connect(self.change_password)

        card_lay.addRow(current_label, self.current_password_input)
        card_lay.addRow(new_label, self.new_password_input)
        card_lay.addRow(confirm_label, self.confirm_password_input)
        card_lay.addRow(change_button)

        layout.addWidget(card)
        layout.addStretch(1)

    # ------------------------------------------------------------------ #
    # منطق تغییر رمز (بدون تغییر نسبت به نسخه قبل)
    # ------------------------------------------------------------------ #
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
            QMessageBox.warning(self, "خطا", "رمز عبور جدید باید حداقل ۶ کاراکتر باشد!")
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
