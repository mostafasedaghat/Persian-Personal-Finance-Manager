# -*- coding: utf-8 -*-
"""
ui/dialogs/login_dialog.py
==========================
پنجره ورود به برنامه.

ظاهر جدید — هماهنگ با طراحی سایر بخش‌های برنامه:
    ┌──────────────────────────────────┐
    │   🏦  (گرادیان سبز + آیکون)      │
    │   نرم‌افزار حسابداری شخصی         │
    │   ورود به حساب کاربری             │
    ├──────────────────────────────────┤
    │   نام کاربری:  [____________]    │
    │   رمز عبور:    [____________]    │
    │   [        ورود به برنامه      ] │
    │   نسخه ۲.۱ — مرکز گزارش‌ها        │
    └──────────────────────────────────┘

منطق check_login دقیقاً مانند قبل است (bcrypt + جدول users).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame,
)

from core.paths import APP_VERSION, APP_RELEASE_NAME

GREEN = "#16a34a"
DARK_GREEN = "#15803d"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
CARD_BORDER = "#d3dce6"


class LoginDialog(QDialog):
    """پنجره ورود با نام کاربری و رمز عبور."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("ورود به نرم‌افزار")
        self.setFixedSize(400, 430)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.setStyleSheet(f"""
            LoginDialog {{
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
                border-radius: 22px;
                font-size: 30px;
            }}
            QLabel#bannerTitle {{
                color: #ffffff;
                font-size: 17px;
                font-weight: bold;
            }}
            QLabel#bannerSubtitle {{
                color: rgba(255, 255, 255, 210);
                font-size: 12px;
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
                font-size: 14px;
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
            QPushButton#loginBtn {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton#loginBtn:hover {{
                background-color: {DARK_GREEN};
            }}
            QPushButton#loginBtn:pressed {{
                background-color: #166534;
            }}
            QLabel#footerLabel {{
                color: {TEXT_MUTED};
                font-size: 11px;
            }}
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(16)

        # ---------- بنر بالای پنجره ----------
        banner = QFrame()
        banner.setObjectName("banner")
        banner_lay = QVBoxLayout(banner)
        banner_lay.setContentsMargins(20, 18, 20, 18)
        banner_lay.setSpacing(8)

        icon = QLabel("🏦")
        icon.setObjectName("bannerIcon")
        icon.setFixedSize(64, 64)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("نرم‌افزار حسابداری شخصی")
        title.setObjectName("bannerTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("برای ادامه، وارد حساب کاربری خود شوید")
        subtitle.setObjectName("bannerSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        banner_lay.addWidget(icon, 0, Qt.AlignmentFlag.AlignCenter)
        banner_lay.addWidget(title)
        banner_lay.addWidget(subtitle)

        layout.addWidget(banner)

        # ---------- کارت فرم ورود ----------
        card = QFrame()
        card.setObjectName("formCard")
        card_lay = QFormLayout(card)
        card_lay.setContentsMargins(20, 20, 20, 20)
        card_lay.setSpacing(12)
        card_lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        user_label = QLabel("نام کاربری:")
        user_label.setObjectName("formLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("مثلاً admin")
        self.username_input.setMinimumWidth(240)

        pass_label = QLabel("رمز عبور:")
        pass_label.setObjectName("formLabel")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("********")
        self.password_input.returnPressed.connect(self.check_login)

        card_lay.addRow(user_label, self.username_input)
        card_lay.addRow(pass_label, self.password_input)

        login_button = QPushButton("ورود به برنامه")
        login_button.setObjectName("loginBtn")
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        login_button.clicked.connect(self.check_login)
        card_lay.addRow(login_button)

        layout.addWidget(card)
        layout.addStretch(1)

        # ---------- پانوشت ----------
        footer = QLabel(f"نسخه {APP_VERSION} — {APP_RELEASE_NAME}")
        footer.setObjectName("footerLabel")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    # ------------------------------------------------------------------ #
    # منطق ورود (بدون تغییر نسبت به نسخه قبل)
    # ------------------------------------------------------------------ #
    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().encode('utf-8')

        if not username or not self.password_input.text():
            QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور نمی‌توانند خالی باشند!")
            return

        try:
            self.db_manager.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            result = self.db_manager.fetchone()
            if result:
                import bcrypt
                stored_hash = result[0].encode('utf-8')
                if bcrypt.checkpw(password, stored_hash):
                    self.accept()
                else:
                    QMessageBox.warning(self, "خطا", "نام کاربری یا رمز عبور اشتباه است!")
            else:
                QMessageBox.warning(self, "خطا", "نام کاربری یا رمز عبور اشتباه است!")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
