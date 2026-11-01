# -*- coding: utf-8 -*-
"""
ui/tabs/accounts_tab.py
=======================
تب «حساب‌ها» برنامه حسابداری شخصی

ظاهر جدید (هماهنگ با تم داشبورد):

    ┌──────────────────────────────────────────────────────┐
    │  🏦 حساب‌های من   |   [ موجودی کل: ... ریال ]         │
    ├──────────────────────────────────────────────────────┤
    │  ➕ افزودن حساب جدید:  [نام] [موجودی اولیه] [افزودن]  │
    ├──────────────────────────────────────────────────────┤
    │  💳 فهرست حساب‌ها (n حساب)                            │
    │  جدول: شناسه | نام حساب | موجودی | اقدامات            │
    └──────────────────────────────────────────────────────┘

عملکرد کاملاً حفظ شده:
  - افزودن حساب جدید (با اعتبارسنجی نام خالی)
  - ویرایش نام حساب (با بررسی تکراری‌بودن نام)
  - load_accounts_table() همچنان توسط main.py فراخوانی می‌شود
"""

import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QHeaderView, QAbstractItemView,
    QGraphicsDropShadowEffect,
)

from ui.components.custom_widgets import NumberInput
from core.utils import format_amount

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با داشبورد)
# ----------------------------------------------------------------------------
PAGE_BG = "#eef1f6"
CARD_BORDER = "#e5eaf1"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
GREEN = "#16a34a"
RED = "#dc2626"
SLATE = "#475569"
SOFT_GREEN = "#dcfce7"
SOFT_RED = "#fee2e2"
SOFT_SLATE = "#f1f5f9"


class AccountsTab(QWidget):
    """تب مدیریت حساب‌ها: افزودن، ویرایش و مشاهده موجودی."""

    STYLESHEET = f"""
    AccountsTab {{
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
    QFrame#balancePill {{
        background-color: rgba(255, 255, 255, 0.14);
        border-radius: 12px;
    }}
    QLabel#balanceTitle {{
        color: rgba(255, 255, 255, 200);
        font-size: 11px;
    }}
    QLabel#balanceValue {{
        color: #ffffff;
        font-size: 20px;
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
    QLabel#chip {{
        border-radius: 9px;
        padding: 4px 10px;
        font-size: 11px;
        font-weight: bold;
        background: transparent;
    }}

    /* ---------- فرم ---------- */
    QLineEdit {{
        background-color: #ffffff;
        border: 1px solid #d3dce6;
        border-radius: 9px;
        padding: 8px 10px;
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

    /* ---------- دکمه‌ها ---------- */
    QPushButton#primaryBtn {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #16a34a, stop:1 #15803d);
        color: white;
        border: none;
        border-radius: 9px;
        padding: 9px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#primaryBtn:hover {{
        background-color: #15803d;
    }}
    QPushButton#primaryBtn:pressed {{
        background-color: #166534;
    }}
    QPushButton#editBtn {{
        background-color: {SOFT_GREEN};
        color: #166534;
        border: 1px solid #bbe7c9;
        border-radius: 8px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#editBtn:hover {{
        background-color: #d1f0da;
        border-color: {GREEN};
    }}

    /* ---------- جدول ---------- */
    QTableWidget#accountsTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#accountsTable QHeaderView::section {{
        background-color: #f1f5f9;
        color: #334155;
        font-weight: bold;
        font-size: 12px;
        padding: 7px 6px;
        border: none;
        border-bottom: 2px solid #e2e8f0;
    }}

    QLabel#emptyLabel {{
        background-color: #f8fafc;
        color: {TEXT_MUTED};
        border: 1px dashed #cbd5e1;
        border-radius: 10px;
        padding: 26px;
        font-size: 13px;
    }}
    """

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent  # ارجاع به کلاس اصلی برای ارتباط با سایر تب‌ها

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

        # ۱. هدر (موجودی کل)
        layout.addWidget(self._build_header())

        # ۲. کارت افزودن حساب
        layout.addWidget(self._build_add_form())

        # ۳. کارت فهرست حساب‌ها
        layout.addWidget(self._build_accounts_list(), 1)

    def _build_header(self):
        card = QFrame()
        card.setObjectName("headerCard")

        lay = QHBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        icon = QLabel("🏦")
        icon.setObjectName("headerIcon")
        icon.setFixedSize(52, 52)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("حساب‌های من")
        title.setObjectName("headerTitle")
        subtitle = QLabel("مدیریت حساب‌ها و مشاهده موجودی هر حساب")
        subtitle.setObjectName("headerSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addStretch()

        lay.addWidget(icon)
        lay.addLayout(title_box)
        lay.addStretch(1)

        pill = QFrame()
        pill.setObjectName("balancePill")
        pill_lay = QVBoxLayout(pill)
        pill_lay.setContentsMargins(18, 10, 18, 10)
        pill_lay.setSpacing(2)
        balance_title = QLabel("موجودی کل")
        balance_title.setObjectName("balanceTitle")
        balance_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_balance_label = QLabel("0 ریال")
        self.total_balance_label.setObjectName("balanceValue")
        self.total_balance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill_lay.addWidget(balance_title)
        pill_lay.addWidget(self.total_balance_label)

        lay.addWidget(pill)

        self._apply_shadow(card, blur=22, alpha=45, dy=4)
        return card

    def _build_add_form(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        # سربرگ کارت
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("➕")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("افزودن حساب جدید")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        # فرم افقی: نام + موجودی اولیه + دکمه
        form_row = QHBoxLayout()
        form_row.setSpacing(10)

        name_box = QVBoxLayout()
        name_label = QLabel("نام حساب:")
        name_label.setObjectName("formLabel")
        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText("مثلاً: بانک ملت - جاری")
        self.account_name_input.setMinimumWidth(220)
        name_box.addWidget(name_label)
        name_box.addWidget(self.account_name_input)

        balance_box = QVBoxLayout()
        balance_label = QLabel("موجودی اولیه (ریال):")
        balance_label.setObjectName("formLabel")
        self.account_balance_input = NumberInput()
        self.account_balance_input.setPlaceholderText("0")
        balance_box.addWidget(balance_label)
        balance_box.addWidget(self.account_balance_input)

        add_account_btn = QPushButton("افزودن حساب")
        add_account_btn.setObjectName("primaryBtn")
        add_account_btn.setMinimumHeight(40)
        add_account_btn.clicked.connect(self.add_account)
        btn_box = QVBoxLayout()
        btn_box.addStretch(1)
        btn_box.addWidget(add_account_btn)

        form_row.addLayout(name_box, 2)
        form_row.addLayout(balance_box, 1)
        form_row.addLayout(btn_box)
        lay.addLayout(form_row)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_accounts_list(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ: آیکون + عنوان + تعداد
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("💳")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_SLATE}; font-size: 15px;")
        title = QLabel("فهرست حساب‌ها")
        title.setObjectName("panelTitle")
        self.accounts_count_chip = QLabel("0 حساب")
        self.accounts_count_chip.setObjectName("chip")
        self.accounts_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.accounts_count_chip)
        lay.addLayout(header_row)

        # جدول حساب‌ها
        self.accounts_table = QTableWidget()
        self.accounts_table.setObjectName("accountsTable")
        self.accounts_table.setColumnCount(4)
        self.accounts_table.setHorizontalHeaderLabels(
            ["شناسه", "نام حساب", "موجودی (ریال)", "اقدامات"])
        self._style_table()

        self.accounts_empty_label = QLabel("🏦 هنوز حسابی ثبت نشده است")
        self.accounts_empty_label.setObjectName("emptyLabel")
        self.accounts_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accounts_empty_label.setVisible(False)

        lay.addWidget(self.accounts_table, 1)
        lay.addWidget(self.accounts_empty_label, 1)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _style_table(self):
        table = self.accounts_table
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        vertical_header = table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(46)

        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setWordWrap(False)

        horizontal_header = table.horizontalHeader()
        horizontal_header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setMinimumSectionSize(64)
        horizontal_header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter)

    def _apply_shadow(self, widget, blur=18, alpha=28, dy=3):
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(15, 40, 30, alpha))
        effect.setOffset(0, dy)
        widget.setGraphicsEffect(effect)

    # ================================================================== #
    # بارگذاری داده‌ها
    # ================================================================== #
    def load_accounts_table(self):
        """فقط جدول حساب‌ها را به‌روز می‌کند (توسط main.py فراخوانی می‌شود)"""
        try:
            self.db_manager.execute(
                "SELECT id, name, balance FROM accounts ORDER BY id ASC")
            accounts = self.db_manager.fetchall()

            if not accounts:
                self.accounts_table.setRowCount(0)
                self.accounts_table.setVisible(False)
                self.accounts_empty_label.setVisible(True)
                self.accounts_count_chip.setText("0 حساب")
                self.total_balance_label.setText("0 ریال")
                return

            self.accounts_table.setVisible(True)
            self.accounts_empty_label.setVisible(False)

            total_balance = 0
            self.accounts_table.setRowCount(len(accounts))
            for row, (id, name, balance) in enumerate(accounts):
                balance = balance or 0
                total_balance += balance

                # شناسه (کم‌رنگ و ظریف)
                id_item = QTableWidgetItem(str(id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setForeground(QColor(TEXT_MUTED))

                # نام حساب (درشت)
                name_item = QTableWidgetItem(str(name))
                name_font = name_item.font()
                name_font.setBold(True)
                name_item.setFont(name_font)
                name_item.setForeground(QColor(TEXT_DARK))
                name_item.setToolTip(str(name))

                # موجودی (سبز اگر مثبت، قرمز اگر منفی)
                balance_item = QTableWidgetItem(format_amount(balance))
                balance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                balance_font = balance_item.font()
                balance_font.setBold(True)
                balance_item.setFont(balance_font)
                balance_item.setForeground(
                    QColor(GREEN if balance >= 0 else RED))

                self.accounts_table.setItem(row, 0, id_item)
                self.accounts_table.setItem(row, 1, name_item)
                self.accounts_table.setItem(row, 2, balance_item)

                edit_btn = QPushButton("ویرایش")
                edit_btn.setObjectName("editBtn")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.clicked.connect(
                    lambda checked, acc_id=id: self.edit_account(acc_id))
                self.accounts_table.setCellWidget(row, 3, edit_btn)

            # به‌روزرسانی هدر
            self.accounts_count_chip.setText(f"{len(accounts)} حساب")
            self.total_balance_label.setText(
                f"{format_amount(total_balance)} ریال")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # عملیات حساب‌ها (منطق بدون تغییر)
    # ================================================================== #
    def add_account(self):
        """افزودن حساب جدید به دیتابیس"""
        name = self.account_name_input.text().strip()
        balance = self.account_balance_input.get_raw_value() \
            if self.account_balance_input.text() else 0

        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب نمی‌تواند خالی باشد!")
            return

        try:
            self.db_manager.execute(
                "INSERT INTO accounts (name, balance) VALUES (?, ?)",
                (name, balance))
            self.db_manager.commit()

            self.account_name_input.clear()
            self.account_balance_input.clear()

            # فراخوانی تابع اصلی برای آپدیت همزمان جدول تب فعلی و کامبوباکس‌های سایر تب‌ها
            if hasattr(self.parent_window, 'load_accounts'):
                self.parent_window.load_accounts()

            QMessageBox.information(self, "موفق", "حساب با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_account(self, account_id):
        """باز کردن دیالوگ ویرایش نام حساب"""
        try:
            self.db_manager.execute(
                "SELECT name FROM accounts WHERE id = ?", (account_id,))
            account = self.db_manager.fetchone()
            if not account:
                QMessageBox.warning(self, "خطا", "حساب یافت نشد!")
                return
            name = account[0]

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش نام حساب")
            dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            dialog.setStyleSheet(f"""
                QDialog {{ background-color: {PAGE_BG};
                          font-family: 'Vazir', 'Arial'; }}
                QLabel {{ color: {TEXT_DARK}; font-size: 13px; }}
                QLineEdit {{ background-color: white;
                            border: 1px solid #d3dce6; border-radius: 8px;
                            padding: 8px 10px; font-size: 13px; }}
                QLineEdit:focus {{ border: 2px solid {GREEN}; }}
            """)

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(12)

            form = QFormLayout()
            form.setSpacing(10)
            edit_name = QLineEdit(name)
            edit_name.setMinimumWidth(280)
            form.addRow("نام حساب:", edit_name)
            layout.addLayout(form)

            save_btn = QPushButton("ذخیره تغییرات")
            save_btn.setObjectName("primaryBtn")
            save_btn.setMinimumHeight(40)
            save_btn.clicked.connect(
                lambda: self.save_account(
                    account_id, edit_name.text().strip(), dialog))
            layout.addWidget(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_account(self, account_id, name, dialog):
        """ذخیره تغییرات نام حساب"""
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب نمی‌تواند خالی باشد!")
            return

        try:
            self.db_manager.execute(
                "SELECT id FROM accounts WHERE name = ? AND id != ?",
                (name, account_id))
            if self.db_manager.fetchone():
                QMessageBox.warning(
                    self, "خطا", "حسابی با این نام قبلاً وجود دارد!")
                return

            self.db_manager.execute(
                "UPDATE accounts SET name = ? WHERE id = ?",
                (name, account_id))
            self.db_manager.commit()

            # فراخوانی آپدیت سراسری
            if hasattr(self.parent_window, 'load_accounts'):
                self.parent_window.load_accounts()

            dialog.accept()
            QMessageBox.information(
                self, "موفق", "نام حساب با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
