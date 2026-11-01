# -*- coding: utf-8 -*-
"""
ui/tabs/settings_tab.py
=======================
تب «تنظیمات» برنامه حسابداری شخصی — کلاس مستقل (SettingsTab).

ظاهر جدید (هماهنگ با تم سایر تب‌ها):

    ┌──────────────────────────────────────────────────────────────┐
    │  ⚙️ تنظیمات  |  مدیریت امنیت، پشتیبان‌گیری و اطلاعات برنامه  │
    │                                        [ نسخه ۲.۱ ]          │
    ├──────────────────────────────┬───────────────────────────────┤
    │  🔐 امنیت و حساب کاربری       │  💾 پشتیبان‌گیری               │
    │  نام کاربری: admin            │  [💾 ایجاد نسخه پشتیبان]      │
    │  [🔑 تغییر رمز عبور]          │  [📂 باز کردن پوشه پشتیبان‌ها] │
    │  نکته امنیتی...               │  فهرست نسخه‌های پشتیبان اخیر   │
    ├──────────────────────────────┴───────────────────────────────┤
    │  🗄️ وضعیت پایگاه داده (اندازه، تراکنش‌ها، حساب‌ها، ...)         │
    ├──────────────────────────────────────────────────────────────┤
    │  ℹ️ درباره برنامه                                            │
    └──────────────────────────────────────────────────────────────┘

امکانات:
  - تغییر رمز عبور (پنجره مستقل ChangePasswordDialog)
  - پشتیبان‌گیری آفلاین با VACUUM INTO (بکاپ امن و فشرده)
  - مشاهده فهرست نسخه‌های پشتیبان + باز کردن پوشه بکاپ‌ها
  - نمایش آمار پایگاه داده به صورت چیپ‌های رنگی
  - اطلاعات برنامه و نسخه

نکته: قابلیت بکاپ آنلاین Dropbox طبق درخواست کاربر حذف شده است.
"""

import os
import sqlite3
from datetime import datetime

import jdatetime
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect,
)

from core.paths import (
    APP_NAME, APP_RELEASE_NAME, APP_VERSION, backup_dir,
)
from core.utils import format_amount
from ui.dialogs.change_password_dialog import ChangePasswordDialog

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با سایر تب‌ها)
# ----------------------------------------------------------------------------
PAGE_BG = "#eef1f6"
CARD_BORDER = "#e5eaf1"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
GREEN = "#16a34a"
DARK_GREEN = "#15803d"
RED = "#dc2626"
SLATE = "#475569"
SOFT_GREEN = "#dcfce7"
SOFT_RED = "#fee2e2"
SOFT_SLATE = "#f1f5f9"
SOFT_BLUE = "#e0f2fe"
SOFT_AMBER = "#fef3c7"
SOFT_VIOLET = "#ede9fe"


class SettingsTab(QWidget):
    """تب تنظیمات: امنیت حساب، پشتیبان‌گیری آفلاین و اطلاعات برنامه."""

    STYLESHEET = f"""
    SettingsTab {{
        background-color: {PAGE_BG};
        font-family: 'Vazir', 'Arial';
    }}

    /* ---------- هدر ---------- */
    QFrame#headerCard {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #0f3d2e, stop:0.55 #166534, stop:1 #15803d);
        border-radius: 16px;
    }}
    QLabel#headerIcon {{
        background-color: rgba(255, 255, 255, 0.16);
        border-radius: 14px;
        font-size: 24px;
    }}
    QLabel#headerTitle {{
        color: #ffffff;
        font-size: 21px;
        font-weight: bold;
    }}
    QLabel#headerSubtitle {{
        color: rgba(255, 255, 255, 215);
        font-size: 12px;
    }}
    QFrame#versionPill {{
        background-color: rgba(255, 255, 255, 0.14);
        border-radius: 12px;
    }}
    QLabel#versionTitle {{
        color: rgba(255, 255, 255, 200);
        font-size: 11px;
    }}
    QLabel#versionValue {{
        color: #ffffff;
        font-size: 18px;
        font-weight: bold;
    }}

    /* ---------- کارت‌ها ---------- */
    QFrame#panelCard {{
        background-color: #ffffff;
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
    }}
    QLabel#panelIcon {{
        border-radius: 10px;
        font-size: 15px;
    }}
    QLabel#panelTitle {{
        color: {TEXT_DARK};
        font-size: 15px;
        font-weight: bold;
    }}
    QLabel#panelHint {{
        color: {TEXT_MUTED};
        font-size: 11px;
    }}

    /* ---------- ردیف اطلاعات (لیبل/مقدار) ---------- */
    QLabel#infoKey {{
        color: {TEXT_MUTED};
        font-size: 12px;
        font-weight: bold;
    }}
    QLabel#infoValue {{
        color: {TEXT_DARK};
        font-size: 13px;
        font-weight: bold;
        background-color: {SOFT_SLATE};
        border-radius: 9px;
        padding: 6px 12px;
    }}
    QLabel#hintLabel {{
        color: {TEXT_MUTED};
        font-size: 11px;
        background-color: {SOFT_AMBER};
        border-radius: 9px;
        padding: 8px 12px;
    }}

    /* ---------- دکمه‌ها ---------- */
    QPushButton#primaryBtn {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #16a34a, stop:1 #15803d);
        color: white;
        border: none;
        border-radius: 9px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#primaryBtn:hover {{
        background-color: {DARK_GREEN};
    }}
    QPushButton#primaryBtn:pressed {{
        background-color: #166534;
    }}
    QPushButton#secondaryBtn {{
        background-color: {SOFT_SLATE};
        color: {SLATE};
        border: 1px solid #d8e0ea;
        border-radius: 9px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#secondaryBtn:hover {{
        background-color: #e6ecf3;
        border-color: {SLATE};
    }}

    /* ---------- جدول بکاپ‌ها ---------- */
    QTableWidget#backupsTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
        gridline-color: #eef2f7;
        selection-background-color: {SOFT_GREEN};
        selection-color: #14532d;
        font-size: 12px;
    }}
    QTableWidget#backupsTable QHeaderView::section {{
        background-color: #f1f5f9;
        color: #334155;
        font-weight: bold;
        font-size: 11px;
        padding: 6px;
        border: none;
        border-bottom: 2px solid #e2e8f0;
    }}
    QLabel#emptyLabel {{
        background-color: #f8fafc;
        color: {TEXT_MUTED};
        border: 1px dashed #cbd5e1;
        border-radius: 10px;
        padding: 18px;
        font-size: 12px;
    }}

    /* ---------- چیپ‌های آمار ---------- */
    QFrame#statChip {{
        background-color: #ffffff;
        border: 1px solid {CARD_BORDER};
        border-radius: 12px;
    }}
    QLabel#statIcon {{
        border-radius: 9px;
        font-size: 14px;
    }}
    QLabel#statKey {{
        color: {TEXT_MUTED};
        font-size: 11px;
    }}
    QLabel#statValue {{
        color: {TEXT_DARK};
        font-size: 15px;
        font-weight: bold;
    }}

    /* ---------- درباره ---------- */
    QLabel#aboutTitle {{
        color: {TEXT_DARK};
        font-size: 14px;
        font-weight: bold;
    }}
    QLabel#aboutText {{
        color: {TEXT_MUTED};
        font-size: 11px;
    }}
    QLabel#aboutBadge {{
        background-color: {SOFT_GREEN};
        color: #166534;
        border-radius: 9px;
        padding: 5px 12px;
        font-size: 11px;
        font-weight: bold;
    }}
    """

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent  # ارجاع به پنجره اصلی (مثل سایر تب‌ها)

        # کاربر جاری برنامه (سازگار با نسخه قبل: admin پیش‌فرض)
        self.current_username = self._detect_username()

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.STYLESHEET)

        self.setup_ui()

    # ================================================================== #
    # ساخت رابط کاربری
    # ================================================================== #
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        # ۱. هدر
        layout.addWidget(self._build_header())

        # ۲. دو ستون: امنیت + پشتیبان‌گیری
        columns = QHBoxLayout()
        columns.setSpacing(14)
        columns.addWidget(self._build_security_card(), 1)
        columns.addWidget(self._build_backup_card(), 1)
        layout.addLayout(columns)

        # ۳. وضعیت پایگاه داده
        layout.addWidget(self._build_db_stats_card())

        # ۴. درباره برنامه
        layout.addWidget(self._build_about_card())

        layout.addStretch(1)

    # ------------------------------------------------------------------ #
    def _build_header(self):
        card = QFrame()
        card.setObjectName("headerCard")

        lay = QHBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        icon = QLabel("⚙️")
        icon.setObjectName("headerIcon")
        icon.setFixedSize(52, 52)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("تنظیمات")
        title.setObjectName("headerTitle")
        subtitle = QLabel("مدیریت امنیت، پشتیبان‌گیری و اطلاعات برنامه")
        subtitle.setObjectName("headerSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addStretch()

        lay.addWidget(icon)
        lay.addLayout(title_box)
        lay.addStretch(1)

        pill = QFrame()
        pill.setObjectName("versionPill")
        pill_lay = QVBoxLayout(pill)
        pill_lay.setContentsMargins(18, 10, 18, 10)
        pill_lay.setSpacing(2)
        pill_title = QLabel("نسخه برنامه")
        pill_title.setObjectName("versionTitle")
        pill_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill_value = QLabel(APP_VERSION)
        pill_value.setObjectName("versionValue")
        pill_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill_lay.addWidget(pill_title)
        pill_lay.addWidget(pill_value)

        lay.addWidget(pill)

        self._apply_shadow(card, blur=22, alpha=45, dy=4)
        return card

    # ------------------------------------------------------------------ #
    def _build_security_card(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(12)

        # سربرگ کارت
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🔐")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("امنیت و حساب کاربری")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        # ردیف نام کاربری
        user_row = QHBoxLayout()
        user_row.setSpacing(10)
        user_key = QLabel("نام کاربری:")
        user_key.setObjectName("infoKey")
        user_value = QLabel(self.current_username)
        user_value.setObjectName("infoValue")
        user_row.addWidget(user_key)
        user_row.addWidget(user_value)
        user_row.addStretch(1)
        lay.addLayout(user_row)

        # نکته امنیتی
        hint = QLabel("💡 برای امنیت بیشتر، رمز عبور را هر چند ماه یک‌بار تغییر دهید "
                      "(حداقل ۶ کاراکتر).")
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        # دکمه تغییر رمز
        change_btn = QPushButton("🔑 تغییر رمز عبور")
        change_btn.setObjectName("primaryBtn")
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.clicked.connect(self._change_password)
        lay.addWidget(change_btn)

        lay.addStretch(1)
        return card

    # ------------------------------------------------------------------ #
    def _build_backup_card(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(12)

        # سربرگ کارت
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("💾")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_BLUE}; font-size: 15px;")
        title = QLabel("پشتیبان‌گیری آفلاین")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.backup_count_label = QLabel("")
        self.backup_count_label.setObjectName("panelHint")
        header_row.addWidget(self.backup_count_label)
        lay.addLayout(header_row)

        # توضیح
        desc = QLabel("نسخه پشتیبان کامل و فشرده از پایگاه داده در پوشه "
                      "«database-backup» کنار برنامه ذخیره می‌شود.")
        desc.setObjectName("panelHint")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # دکمه‌ها
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        backup_btn = QPushButton("💾 ایجاد نسخه پشتیبان")
        backup_btn.setObjectName("primaryBtn")
        backup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        backup_btn.clicked.connect(self._create_backup)
        btn_row.addWidget(backup_btn, 1)

        open_btn = QPushButton("📂 پوشه پشتیبان‌ها")
        open_btn.setObjectName("secondaryBtn")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(self._open_backup_folder)
        btn_row.addWidget(open_btn, 1)

        lay.addLayout(btn_row)

        # جدول بکاپ‌های اخیر
        self.backups_table = QTableWidget()
        self.backups_table.setObjectName("backupsTable")
        self.backups_table.setColumnCount(3)
        self.backups_table.setHorizontalHeaderLabels(["نام فایل", "تاریخ ایجاد", "حجم"])
        self.backups_table.verticalHeader().setVisible(False)
        self.backups_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.backups_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.backups_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.backups_table.setAlternatingRowColors(True)
        self.backups_table.setMaximumHeight(170)
        header = self.backups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        lay.addWidget(self.backups_table)

        self.empty_backups_label = QLabel("هنوز نسخه پشتیبانی ساخته نشده است.")
        self.empty_backups_label.setObjectName("emptyLabel")
        self.empty_backups_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.empty_backups_label)

        return card

    # ------------------------------------------------------------------ #
    def _build_db_stats_card(self):
        card = QFrame()
        card.setObjectName("panelCard")
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(12)

        # سربرگ کارت
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🗄️")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_VIOLET}; font-size: 15px;")
        title = QLabel("وضعیت پایگاه داده")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        outer.addLayout(header_row)

        # شبکه چیپ‌های آمار
        grid = QHBoxLayout()
        grid.setSpacing(10)

        self.stat_labels = {}
        stats = [
            ("size", "📄", "اندازه فایل", SOFT_SLATE),
            ("transactions", "🧾", "تراکنش‌ها", SOFT_GREEN),
            ("accounts", "🏦", "حساب‌ها", SOFT_BLUE),
            ("persons", "👥", "اشخاص", SOFT_AMBER),
            ("debts", "⚖️", "بدهی/طلب", SOFT_RED),
            ("loans", "🏁", "وام‌ها", SOFT_VIOLET),
        ]
        for key, emoji, label, soft_color in stats:
            chip = QFrame()
            chip.setObjectName("statChip")
            chip_lay = QVBoxLayout(chip)
            chip_lay.setContentsMargins(10, 10, 10, 10)
            chip_lay.setSpacing(4)

            chip_icon = QLabel(emoji)
            chip_icon.setObjectName("statIcon")
            chip_icon.setFixedSize(30, 30)
            chip_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip_icon.setStyleSheet(f"background-color: {soft_color}; font-size: 14px;")

            chip_key = QLabel(label)
            chip_key.setObjectName("statKey")
            chip_key.setAlignment(Qt.AlignmentFlag.AlignCenter)

            chip_value = QLabel("—")
            chip_value.setObjectName("statValue")
            chip_value.setAlignment(Qt.AlignmentFlag.AlignCenter)

            chip_lay.addWidget(chip_icon, 0, Qt.AlignmentFlag.AlignCenter)
            chip_lay.addWidget(chip_key)
            chip_lay.addWidget(chip_value)

            self.stat_labels[key] = chip_value
            grid.addWidget(chip, 1)

        outer.addLayout(grid)
        return card

    # ------------------------------------------------------------------ #
    def _build_about_card(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        title = QLabel(APP_NAME)
        title.setObjectName("aboutTitle")
        text = QLabel("مدیریت حساب‌ها، تراکنش‌ها، بدهی/طلب، وام‌ها و گزارش‌های مالی "
                      "با تقویم شمسی — ساخته‌شده با Python و PyQt6 و SQLite.")
        text.setObjectName("aboutText")
        text.setWordWrap(True)
        text_box.addWidget(title)
        text_box.addWidget(text)

        lay.addLayout(text_box, 1)

        badge = QLabel(f"نسخه {APP_VERSION} — {APP_RELEASE_NAME}")
        badge.setObjectName("aboutBadge")
        lay.addWidget(badge)

        return card

    # ================================================================== #
    # رفتارها
    # ================================================================== #
    def showEvent(self, event):
        """هر بار که تب تنظیمات نمایش داده می‌شود، آمار تازه شود."""
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        """به‌روزرسانی فهرست بکاپ‌ها و آمار پایگاه داده."""
        self._load_backups()
        self._load_db_stats()

    # ------------------------------------------------------------------ #
    # امنیت
    # ------------------------------------------------------------------ #
    def _detect_username(self):
        """تشخیص نام کاربر جاری (admin پیش‌فرض، مثل نسخه قبل)."""
        try:
            self.db_manager.execute("SELECT username FROM users ORDER BY id LIMIT 1")
            row = self.db_manager.fetchone()
            if row and row[0]:
                return row[0]
        except sqlite3.Error:
            pass
        return "admin"

    def _change_password(self):
        dialog = ChangePasswordDialog(self.db_manager, self.current_username, self)
        dialog.exec()

    # ------------------------------------------------------------------ #
    # پشتیبان‌گیری
    # ------------------------------------------------------------------ #
    def _create_backup(self):
        """ایجاد نسخه پشتیبان امن با VACUUM INTO (در پوشه database-backup)."""
        db_path = self.db_manager.db_path
        backup_dir_path = backup_dir()

        try:
            os.makedirs(backup_dir_path, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"finance_backup_offline_{timestamp}.db"
            backup_filepath = os.path.join(backup_dir_path, backup_filename)

            # اتصال مجزا برای بکاپ (عدم تداخل با اتصال اصلی برنامه)
            source_conn = sqlite3.connect(db_path)
            source_conn.execute("VACUUM INTO ?", (backup_filepath,))
            source_conn.close()

            QMessageBox.information(
                self, "موفقیت",
                f"نسخه پشتیبان با موفقیت در مسیر زیر ذخیره شد:\n{backup_filepath}"
            )
            self._load_backups()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا در پشتیبان‌گیری",
                                 f"خطای پایگاه داده هنگام ایجاد نسخه پشتیبان: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطا در پشتیبان‌گیری",
                                 f"یک خطای غیرمنتظره رخ داد: {e}")

    def _open_backup_folder(self):
        """باز کردن پوشه نسخه‌های پشتیبان در فایل‌مدیر سیستم."""
        folder = backup_dir()
        try:
            os.makedirs(folder, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"باز کردن پوشه ممکن نشد: {e}")

    def _load_backups(self):
        """پر کردن جدول فهرست نسخه‌های پشتیبان (جدیدترین در بالا)."""
        folder = backup_dir()
        files = []
        if os.path.isdir(folder):
            files = [f for f in os.listdir(folder)
                     if f.startswith("finance_backup_offline_") and f.endswith(".db")]
        # جدیدترین اول
        files.sort(reverse=True)

        visible_count = 8  # فقط ۸ مورد اخیر نمایش داده می‌شود
        shown = files[:visible_count]

        self.backups_table.setRowCount(0)
        has_backups = bool(files)
        self.backups_table.setVisible(has_backups)
        self.empty_backups_label.setVisible(not has_backups)

        total_size = 0
        for f in files:
            try:
                total_size += os.path.getsize(os.path.join(folder, f))
            except OSError:
                pass

        if has_backups:
            self.backup_count_label.setText(
                f"{len(files)} نسخه — {_human_size(total_size)}")
        else:
            self.backup_count_label.setText("بدون نسخه پشتیبان")

        for row_idx, filename in enumerate(shown):
            filepath = os.path.join(folder, filename)
            self.backups_table.insertRow(row_idx)

            # نام فایل
            self.backups_table.setItem(row_idx, 0, QTableWidgetItem(filename))

            # تاریخ ایجاد (تبدیل به شمسی)
            date_text = "—"
            try:
                stamp = filename.replace("finance_backup_offline_", "").replace(".db", "")
                dt = datetime.strptime(stamp, "%Y%m%d_%H%M%S")
                jalali = jdatetime.datetime.fromgregorian(
                    year=dt.year, month=dt.month, day=dt.day,
                    hour=dt.hour, minute=dt.minute)
                date_text = jalali.strftime("%Y/%m/%d — %H:%M")
            except ValueError:
                try:
                    stamp = os.path.getmtime(filepath)
                    dt = datetime.fromtimestamp(stamp)
                    jalali = jdatetime.datetime.fromgregorian(
                        year=dt.year, month=dt.month, day=dt.day,
                        hour=dt.hour, minute=dt.minute)
                    date_text = jalali.strftime("%Y/%m/%d — %H:%M")
                except Exception:
                    pass
            date_item = QTableWidgetItem(date_text)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.backups_table.setItem(row_idx, 1, date_item)

            # حجم
            size_text = "—"
            try:
                size_text = _human_size(os.path.getsize(filepath))
            except OSError:
                pass
            size_item = QTableWidgetItem(size_text)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.backups_table.setItem(row_idx, 2, size_item)

    # ------------------------------------------------------------------ #
    # آمار پایگاه داده
    # ------------------------------------------------------------------ #
    def _load_db_stats(self):
        """به‌روزرسانی چیپ‌های آمار پایگاه داده."""
        # اندازه فایل
        try:
            size = os.path.getsize(self.db_manager.db_path)
            self.stat_labels["size"].setText(_human_size(size))
        except OSError:
            self.stat_labels["size"].setText("—")

        # تعداد ردیف‌ها
        counts = {
            "transactions": "SELECT COUNT(*) FROM transactions",
            "accounts": "SELECT COUNT(*) FROM accounts",
            "persons": "SELECT COUNT(*) FROM persons",
            "debts": "SELECT COUNT(*) FROM debts",
            "loans": "SELECT COUNT(*) FROM loans",
        }
        for key, query in counts.items():
            try:
                self.db_manager.execute(query)
                row = self.db_manager.fetchone()
                self.stat_labels[key].setText(format_amount(row[0] if row else 0))
            except sqlite3.Error:
                self.stat_labels[key].setText("—")

    # ================================================================== #
    # ابزار
    # ================================================================== #
    @staticmethod
    def _apply_shadow(widget, blur=18, alpha=38, dy=3):
        """سایه نرم زیر کارت‌ها (همان الگوی سایر تب‌ها)."""
        from PyQt6.QtGui import QColor

        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, dy)
        effect.setColor(QColor(15, 61, 46, alpha))
        widget.setGraphicsEffect(effect)


# ------------------------------------------------------------------ #
# ابزارهای ماژول
# ------------------------------------------------------------------ #
def _human_size(num_bytes):
    """تبدیل بایت به متن خوانا (کیلوبایت/مگابایت)."""
    try:
        num_bytes = float(num_bytes)
    except (TypeError, ValueError):
        return "—"
    if num_bytes < 1024:
        return f"{int(num_bytes)} بایت"
    if num_bytes < 1024 ** 2:
        return f"{num_bytes / 1024:.1f} کیلوبایت"
    return f"{num_bytes / 1024 ** 2:.1f} مگابایت"
