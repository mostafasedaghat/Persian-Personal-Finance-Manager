# -*- coding: utf-8 -*-
"""
ui/tabs/transactions_tab.py
===========================
تب «تراکنش‌ها» برنامه حسابداری شخصی (جداسازی‌شده از main.py)

چیدمان جدید:

    ┌──────────────────────────────┬─────────────────────────────────┐
    │  سمت راست (فرم‌ها، اسکرول‌شو): │  سمت چپ (لیست تراکنش‌ها):        │
    │  ┌────────────────────────┐  │  ┌───────────────────────────┐  │
    │  │ ➕ ثبت تراکنش جدید      │  │  │ 📜 تراکنش‌ها (N تراکنش)    │  │
    │  │ حساب/شخص/نوع/دسته/...  │  │  │ فیلترها: حساب، نوع، تاریخ │  │
    │  └────────────────────────┘  │  │ جدول + ویرایش/حذف          │  │
    │  ┌────────────────────────┐  │  │ صفحه‌بندی                   │  │
    │  │ 🔁 انتقال پول           │  │  └───────────────────────────┘  │
    │  └────────────────────────┘  │                                  │
    │  ┌────────────────────────┐  │                                  │
    │  │ 🔍 جستجو و گزارش‌گیری   │  │  ◀ خط جداکننده QSplitter ▶     │
    │  └────────────────────────┘  │     (درگ برای تغییر پهنا)        │
    └──────────────────────────────┴─────────────────────────────────┘

نکته مهم درباره جهت چیدمان:
    کل صفحه راست‌به‌چپ (RTL) است؛ در QSplitter (افقی) ویجتی که «اول»
    اضافه شود در سمت «راست» قرار می‌گیرد؛ بنابراین پنل فرم‌ها قبل از
    پنل لیست اضافه می‌شود.

ارتباط با پنجره اصلی:
    - پس از هر تغییر داده (ثبت/ویرایش/حذف/انتقال) سیگنال data_changed
      منتشر می‌شود تا main.py موجودی حساب‌ها و داشبورد را به‌روز کند.
    - خروجی گزارش از طریق parent_window.export_report گرفته می‌شود.
"""

import sqlite3
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QFrame,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QScrollArea, QSplitter, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect,
)

from ui.components.custom_widgets import NumberInput, PersianCalendarPopup
from core.utils import (
    format_number, format_amount, gregorian_to_shamsi,
    shamsi_to_gregorian, is_valid_shamsi_date,
)

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با داشبورد و تب حساب‌ها)
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


class TransactionsTab(QWidget):
    """تب تراکنش‌ها: ثبت، انتقال، جستجو و فیلتر لیست تراکنش‌ها."""

    # پس از هر ثبت/ویرایش/حذف/انتقال منتشر می‌شود
    data_changed = pyqtSignal()

    # ------------------------------------------------------------------ #
    # استایل کلی تب
    # ------------------------------------------------------------------ #
    STYLESHEET = f"""
    TransactionsTab {{
        background-color: {PAGE_BG};
        font-family: 'Vazir', 'Arial';
    }}

    /* ---------- جداکننده قابل درگ ---------- */
    QSplitter::handle {{
        background-color: #d9e0e9;
    }}
    QSplitter::handle:horizontal {{
        width: 7px;
        border-radius: 3px;
    }}
    QSplitter::handle:horizontal:hover {{
        background-color: {GREEN};
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

    /* ---------- فرم‌ها ---------- */
    QLineEdit, QComboBox {{
        background-color: #ffffff;
        border: 1px solid #d3dce6;
        border-radius: 9px;
        padding: 7px 10px;
        font-size: 13px;
        color: {TEXT_DARK};
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 2px solid {GREEN};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #ffffff;
        color: {TEXT_DARK};
        selection-background-color: {SOFT_GREEN};
        selection-color: #14532d;
        border: 1px solid #d3dce6;
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
    QPushButton#secondaryBtn {{
        background-color: #ffffff;
        color: {SLATE};
        border: 1px solid #cbd5e1;
        border-radius: 9px;
        padding: 7px 16px;
        font-size: 12px;
        font-weight: bold;
    }}
    QPushButton#secondaryBtn:hover {{
        background-color: {SOFT_SLATE};
        border-color: {SLATE};
    }}
    QPushButton#pageBtn {{
        background-color: #ffffff;
        color: #166534;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: bold;
        font-size: 12px;
    }}
    QPushButton#pageBtn:hover {{
        background-color: #f0fdf4;
        border-color: {GREEN};
    }}
    QPushButton#pageBtn:disabled {{
        color: #94a3b8;
        background-color: #f8fafc;
        border-color: #e2e8f0;
    }}

    /* ---------- جدول‌ها ---------- */
    QTableWidget#transactionsTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#transactionsTable QHeaderView::section {{
        background-color: #f1f5f9;
        color: #334155;
        font-weight: bold;
        font-size: 12px;
        padding: 7px 6px;
        border: none;
        border-bottom: 2px solid #e2e8f0;
    }}
    QLabel#pageLabel {{
        color: {SLATE};
        font-size: 12px;
        font-weight: bold;
    }}

    /* ---------- حالت خالی ---------- */
    QLabel#emptyLabel {{
        background-color: #f8fafc;
        color: {TEXT_MUTED};
        border: 1px dashed #cbd5e1;
        border-radius: 10px;
        padding: 26px;
        font-size: 13px;
    }}
    """

    # ================================================================== #
    # ساختار کلی
    # ================================================================== #
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent  # ارجاع به پنجره اصلی (برای export_report)

        # وضعیت صفحه‌بندی لیست تراکنش‌ها
        self.transactions_current_page = 1
        self.transactions_per_page = 50
        self.transactions_total_pages = 1

        # وضعیت صفحه‌بندی گزارش جستجو
        self.transaction_report_current_page = 1
        self.transaction_report_per_page = 50
        self.transaction_report_results = []
        self.transaction_report_total_pages = 1

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.STYLESHEET)

        self.setup_ui()
        self.reload_categories()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(0)

        # جداکننده افقی قابل درگ:
        # در RTL ویجت اول سمت «راست» قرار می‌گیرد؛
        # بنابراین پنل فرم‌ها (راست) قبل از پنل لیست (چپ) اضافه می‌شود.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(7)
        splitter.addWidget(self._build_forms_panel())   # سمت راست
        splitter.addWidget(self._build_list_panel())    # سمت چپ
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 760])

        layout.addWidget(splitter)

    # ------------------------------------------------------------------ #
    # پنل راست: فرم‌ها (ثبت تراکنش، انتقال پول، جستجو و گزارش)
    # ------------------------------------------------------------------ #
    def _build_forms_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(360)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QWidget#formsContainer { background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; }"
            "QScrollBar::handle:vertical { background: #cbd5e1;"
            " border-radius: 4px; min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        container = QWidget()
        container.setObjectName("formsContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(16)

        container_layout.addWidget(self._build_entry_card())
        container_layout.addWidget(self._build_transfer_card())
        container_layout.addWidget(self._build_search_card())
        container_layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _build_entry_card(self):
        """کارت ثبت تراکنش جدید (هزینه/درآمد)"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("➕")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("ثبت تراکنش جدید")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        # فرم
        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.transaction_account = QComboBox()
        self.transaction_person = QComboBox()
        self.transaction_person.addItem("-", None)
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(["درآمد", "هزینه"])
        self.transaction_type.currentTextChanged.connect(self.update_categories)
        self.transaction_category = QComboBox()
        self.transaction_amount = NumberInput()
        self.transaction_amount.setPlaceholderText("مبلغ به ریال")

        self.transaction_date = QLineEdit()
        today = datetime.now().date()
        self.transaction_date.setText(
            gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.transaction_date.setPlaceholderText("1404/02/13")
        self.transaction_date.setReadOnly(True)
        self.transaction_date.mousePressEvent = \
            lambda a0: self._popup_calendar(self.transaction_date)
        self.transaction_date.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        self.transaction_desc = QLineEdit()
        self.transaction_desc.setPlaceholderText("توضیح اختیاری...")

        form.addRow("حساب:", self.transaction_account)
        form.addRow("شخص:", self.transaction_person)
        form.addRow("نوع:", self.transaction_type)
        form.addRow("دسته‌بندی:", self.transaction_category)
        form.addRow("مبلغ:", self.transaction_amount)
        form.addRow("تاریخ (شمسی):", self.transaction_date)
        form.addRow("توضیحات:", self.transaction_desc)
        lay.addLayout(form)

        add_transaction_btn = QPushButton("✅ ثبت تراکنش")
        add_transaction_btn.setObjectName("primaryBtn")
        add_transaction_btn.setMinimumHeight(42)
        add_transaction_btn.clicked.connect(self.add_transaction)
        lay.addWidget(add_transaction_btn)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_transfer_card(self):
        """کارت انتقال پول بین حساب‌ها"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🔁")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_SLATE}; font-size: 15px;")
        title = QLabel("انتقال پول بین حساب‌ها")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.transfer_from_account = QComboBox()
        self.transfer_to_account = QComboBox()
        self.transfer_amount = NumberInput()
        self.transfer_amount.setPlaceholderText("مبلغ به ریال")

        self.transfer_date = QLineEdit()
        today = datetime.now().date()
        self.transfer_date.setText(
            gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.transfer_date.setPlaceholderText("1404/02/13")
        self.transfer_date.setReadOnly(True)
        self.transfer_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.transfer_date)
        self.transfer_date.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        form.addRow("از حساب:", self.transfer_from_account)
        form.addRow("به حساب:", self.transfer_to_account)
        form.addRow("مبلغ:", self.transfer_amount)
        form.addRow("تاریخ (شمسی):", self.transfer_date)
        lay.addLayout(form)

        transfer_btn = QPushButton("🔁 انتقال")
        transfer_btn.setObjectName("primaryBtn")
        transfer_btn.setMinimumHeight(40)
        transfer_btn.clicked.connect(self.transfer_money)
        lay.addWidget(transfer_btn)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_search_card(self):
        """کارت جستجو و گزارش‌گیری تراکنش‌ها"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🔍")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_RED}; font-size: 15px;")
        title = QLabel("جستجو و گزارش‌گیری")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.transaction_search_type = QComboBox()
        self.transaction_search_type.addItems(["همه", "برداشت", "واریز", "انتقال"])
        self.transaction_search_person = QComboBox()
        self.transaction_search_person.addItem("-", None)
        self.transaction_search_amount = NumberInput()
        self.transaction_search_amount.setPlaceholderText("0")

        self.transaction_search_start_date = QLineEdit()
        self.transaction_search_start_date.setPlaceholderText("1404/02/13")
        self.transaction_search_start_date.setReadOnly(True)
        self.transaction_search_start_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.transaction_search_start_date)
        self.transaction_search_end_date = QLineEdit()
        self.transaction_search_end_date.setPlaceholderText("1404/02/13")
        self.transaction_search_end_date.setReadOnly(True)
        self.transaction_search_end_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.transaction_search_end_date)

        form.addRow("نوع تراکنش:", self.transaction_search_type)
        form.addRow("شخص:", self.transaction_search_person)
        form.addRow("مبلغ:", self.transaction_search_amount)
        form.addRow("از تاریخ (شمسی):", self.transaction_search_start_date)
        form.addRow("تا تاریخ (شمسی):", self.transaction_search_end_date)
        lay.addLayout(form)

        search_btn = QPushButton("📊 نمایش گزارش")
        search_btn.setObjectName("primaryBtn")
        search_btn.setMinimumHeight(40)
        search_btn.clicked.connect(self.search_transactions)
        lay.addWidget(search_btn)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # پنل چپ: فیلترها + لیست تراکنش‌ها + صفحه‌بندی
    # ------------------------------------------------------------------ #
    def _build_list_panel(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ: عنوان + تعداد
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("📜")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("لیست تراکنش‌ها")
        title.setObjectName("panelTitle")
        self.transactions_count_chip = QLabel("0 تراکنش")
        self.transactions_count_chip.setObjectName("chip")
        self.transactions_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.transactions_count_chip)
        lay.addLayout(header_row)

        # ---- نوار فیلترها ----
        filters_card = QFrame()
        filters_card.setStyleSheet(
            f"QFrame {{ background-color: {SOFT_SLATE};"
            f" border-radius: 10px; }}")
        filters_lay = QVBoxLayout(filters_card)
        filters_lay.setContentsMargins(12, 10, 12, 10)
        filters_lay.setSpacing(8)

        # ردیف اول: حساب + نوع
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        account_box = QVBoxLayout()
        account_box.setSpacing(3)
        account_label = QLabel("حساب:")
        account_label.setObjectName("formLabel")
        self.filter_account = QComboBox()
        self.filter_account.addItem("همه حساب‌ها", None)
        self.filter_account.currentIndexChanged.connect(
            lambda _: self.apply_filters())
        account_box.addWidget(account_label)
        account_box.addWidget(self.filter_account)

        type_box = QVBoxLayout()
        type_box.setSpacing(3)
        type_label = QLabel("نوع تراکنش:")
        type_label.setObjectName("formLabel")
        self.filter_type = QComboBox()
        self.filter_type.addItems(["همه", "هزینه", "درآمد"])
        self.filter_type.currentIndexChanged.connect(
            lambda _: self.apply_filters())
        type_box.addWidget(type_label)
        type_box.addWidget(self.filter_type)

        row1.addLayout(account_box, 3)
        row1.addLayout(type_box, 2)
        filters_lay.addLayout(row1)

        # ردیف دوم: بازه تاریخ + دکمه‌ها
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        start_box = QVBoxLayout()
        start_box.setSpacing(3)
        start_label = QLabel("از تاریخ:")
        start_label.setObjectName("formLabel")
        self.filter_start_date = QLineEdit()
        self.filter_start_date.setPlaceholderText("بدون محدودیت")
        self.filter_start_date.setReadOnly(True)
        self.filter_start_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.filter_start_date)
        start_box.addWidget(start_label)
        start_box.addWidget(self.filter_start_date)

        end_box = QVBoxLayout()
        end_box.setSpacing(3)
        end_label = QLabel("تا تاریخ:")
        end_label.setObjectName("formLabel")
        self.filter_end_date = QLineEdit()
        self.filter_end_date.setPlaceholderText("بدون محدودیت")
        self.filter_end_date.setReadOnly(True)
        self.filter_end_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.filter_end_date)
        end_box.addWidget(end_label)
        end_box.addWidget(self.filter_end_date)

        apply_btn = QPushButton("اعمال فیلتر")
        apply_btn.setObjectName("primaryBtn")
        apply_btn.clicked.connect(self.apply_filters)
        clear_btn = QPushButton("پاک کردن")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self.clear_filters)

        btn_box = QVBoxLayout()
        btn_box.addStretch(1)
        btn_box.addWidget(apply_btn)
        btn_box.addWidget(clear_btn)

        row2.addLayout(start_box, 3)
        row2.addLayout(end_box, 3)
        row2.addLayout(btn_box, 2)
        filters_lay.addLayout(row2)

        lay.addWidget(filters_card)

        # ---- جدول تراکنش‌ها ----
        self.transactions_table = QTableWidget()
        self.transactions_table.setObjectName("transactionsTable")
        self.transactions_table.setColumnCount(9)
        self.transactions_table.setHorizontalHeaderLabels(
            ["تاریخ", "حساب", "شخص", "دسته‌بندی",
             "مبلغ", "توضیحات", "نوع", "ویرایش", "حذف"])
        self._style_table(self.transactions_table, stretch_column=5)
        lay.addWidget(self.transactions_table, 1)

        # حالت خالی
        self.transactions_empty_label = QLabel("📝 تراکنشی برای نمایش وجود ندارد")
        self.transactions_empty_label.setObjectName("emptyLabel")
        self.transactions_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transactions_empty_label.setVisible(False)
        lay.addWidget(self.transactions_empty_label, 1)

        # ---- صفحه‌بندی ----
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)
        self.transactions_prev_btn = QPushButton("صفحه قبل")
        self.transactions_prev_btn.setObjectName("pageBtn")
        self.transactions_next_btn = QPushButton("صفحه بعد")
        self.transactions_next_btn.setObjectName("pageBtn")
        self.transactions_page_label = QLabel("صفحه 1")
        self.transactions_page_label.setObjectName("pageLabel")
        self.transactions_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.transactions_prev_btn.clicked.connect(self.prev_transactions_page)
        self.transactions_next_btn.clicked.connect(self.next_transactions_page)

        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.transactions_prev_btn)
        pagination_layout.addWidget(self.transactions_page_label)
        pagination_layout.addWidget(self.transactions_next_btn)
        pagination_layout.addStretch(1)
        lay.addLayout(pagination_layout)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # ابزارهای مشترک
    # ------------------------------------------------------------------ #
    def _style_table(self, table, stretch_column):
        """تنظیمات ظاهری و رفتاری مشترک جدول‌ها."""
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        vertical_header = table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(42)

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
            stretch_column, QHeaderView.ResizeMode.Stretch)
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setMinimumSectionSize(56)
        horizontal_header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter)

    def _apply_shadow(self, widget, blur=18, alpha=28, dy=3):
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(15, 40, 30, alpha))
        effect.setOffset(0, dy)
        widget.setGraphicsEffect(effect)

    def _popup_calendar(self, date_edit):
        """نمایش تقویم شمسی برای انتخاب تاریخ."""
        popup = PersianCalendarPopup(date_edit, self)
        popup.exec()

    # ================================================================== #
    # پرکردن کامبوباکس‌ها (توسط main.py فراخوانی می‌شوند)
    # ================================================================== #
    def reload_accounts(self, accounts):
        """پرکردن کامبوباکس‌های حساب (فرم ثبت، انتقال و فیلتر لیست)."""
        try:
            display_items = []
            for id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                display_items.append((display_text, id))

            for combo in (self.transaction_account,
                          self.transfer_from_account,
                          self.transfer_to_account):
                combo.clear()
                for display_text, id in display_items:
                    combo.addItem(display_text, id)

            # فیلتر لیست: نام ساده + گزینه «همه حساب‌ها»
            # (بدون ارسال سیگنال تا بارگذاری مجدد تکراری رخ ندهد)
            self.filter_account.blockSignals(True)
            self.filter_account.clear()
            self.filter_account.addItem("همه حساب‌ها", None)
            for id, name, balance in accounts:
                self.filter_account.addItem(name, id)
            self.filter_account.blockSignals(False)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def reload_persons(self, persons):
        """پرکردن کامبوباکس‌های شخص (فرم ثبت و جستجو)."""
        try:
            self.transaction_person.clear()
            self.transaction_person.addItem("-", None)
            for id, name in persons:
                self.transaction_person.addItem(name, id)

            self.transaction_search_person.clear()
            self.transaction_search_person.addItem("-", None)
            for id, name in persons:
                self.transaction_search_person.addItem(name, id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def update_categories(self):
        """به‌روزرسانی لیست دسته‌بندی‌ها بر اساس نوع تراکنش انتخاب‌شده."""
        category_type = \
            "income" if self.transaction_type.currentText() == "درآمد" else "expense"
        self.transaction_category.clear()
        try:
            self.db_manager.execute(
                "SELECT id, name FROM categories WHERE type = ?",
                (category_type,))
            categories = self.db_manager.fetchall()
            for cat_id, name in categories:
                self.transaction_category.addItem(name, cat_id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def reload_categories(self):
        """بارگذاری دسته‌بندی‌ها (نقطه ورود اصلی از main.py)."""
        self.update_categories()

    # ================================================================== #
    # فیلترها و لیست تراکنش‌ها
    # ================================================================== #
    def _current_filter_clauses(self):
        """ساخت شرط WHERE بر اساس فیلترهای فعال (account/type/date)."""
        clauses = []
        params = []

        # فیلتر حساب
        account_id = self.filter_account.currentData()
        if account_id:
            clauses.append("t.account_id = ?")
            params.append(account_id)

        # فیلتر نوع (هزینه/درآمد)
        filter_type = self.filter_type.currentText()
        if filter_type == "هزینه":
            clauses.append("c.type = 'expense'")
        elif filter_type == "درآمد":
            clauses.append("c.type = 'income'")

        # فیلتر بازه تاریخ (شمسی → میلادی)
        start_text = self.filter_start_date.text().strip()
        if start_text:
            start_g = shamsi_to_gregorian(start_text)
            if not start_g:
                return None, None, "تاریخ «از» نامعتبر است!"
            clauses.append("t.date >= ?")
            params.append(start_g)

        end_text = self.filter_end_date.text().strip()
        if end_text:
            end_g = shamsi_to_gregorian(end_text)
            if not end_g:
                return None, None, "تاریخ «تا» نامعتبر است!"
            clauses.append("t.date <= ?")
            params.append(end_g)

        if start_text and end_text and start_text > end_text:
            return None, None, "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد!"

        return clauses, params, None

    def apply_filters(self):
        """اعمال فیلترهای انتخاب‌شده و بازگشت به صفحه اول."""
        _, _, error = self._current_filter_clauses()
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        self.transactions_current_page = 1
        self.load_transactions()

    def clear_filters(self):
        """پاک کردن همه فیلترها و نمایش کل تراکنش‌ها."""
        self.filter_account.blockSignals(True)
        self.filter_account.setCurrentIndex(0)
        self.filter_account.blockSignals(False)
        self.filter_type.blockSignals(True)
        self.filter_type.setCurrentIndex(0)
        self.filter_type.blockSignals(False)
        self.filter_start_date.clear()
        self.filter_end_date.clear()
        self.transactions_current_page = 1
        self.load_transactions()

    def refresh(self):
        """به‌روزرسانی لیست با حفظ صفحه فعلی (فراخوانی از main.py)."""
        self.load_transactions()

    def load_transactions(self):
        """بارگذاری تراکنش‌های صفحه فعلی با فیلترهای فعال."""
        try:
            clauses, params, error = self._current_filter_clauses()
            if error:
                QMessageBox.warning(self, "خطا", error)
                return

            where_sql = ""
            if clauses:
                where_sql = "WHERE " + " AND ".join(clauses)

            # ۱. تعداد کل تراکنش‌های منطبق بر فیلتر
            self.db_manager.execute(
                f"SELECT COUNT(*) FROM transactions t "
                f"JOIN categories c ON t.category_id = c.id {where_sql}",
                params)
            total_transactions = self.db_manager.fetchone()[0]
            self.transactions_total_pages = (
                total_transactions + self.transactions_per_page - 1
            ) // self.transactions_per_page
            if self.transactions_total_pages == 0:
                self.transactions_total_pages = 1
            # اگر صفحه فعلی خارج از بازه شد (مثلاً بعد از حذف)
            if self.transactions_current_page > self.transactions_total_pages:
                self.transactions_current_page = self.transactions_total_pages

            # ۲. واکشی تراکنش‌های صفحه فعلی
            offset = (self.transactions_current_page - 1) * self.transactions_per_page
            self.db_manager.execute(
                f"SELECT t.id, t.date, a.name, p.name, c.name, "
                f"t.amount, t.description, c.type "
                f"FROM transactions t "
                f"JOIN accounts a ON t.account_id = a.id "
                f"LEFT JOIN persons p ON t.person_id = p.id "
                f"JOIN categories c ON t.category_id = c.id "
                f"{where_sql} "
                f"ORDER BY t.date DESC, t.id DESC LIMIT ? OFFSET ?",
                params + [self.transactions_per_page, offset])
            transactions = self.db_manager.fetchall()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        self.transactions_count_chip.setText(f"{total_transactions} تراکنش")

        # حالت خالی
        if not transactions:
            self.transactions_table.setRowCount(0)
            self.transactions_table.setVisible(False)
            self.transactions_empty_label.setVisible(True)
        else:
            self.transactions_table.setVisible(True)
            self.transactions_empty_label.setVisible(False)

            self.transactions_table.setRowCount(len(transactions))
            for row, (id, date, account, person, category, amount,
                       desc, category_type) in enumerate(transactions):
                is_income = (category_type == "income")
                type_color = QColor(GREEN if is_income else RED)

                date_item = QTableWidgetItem(
                    gregorian_to_shamsi(date) if date else "-")
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                date_item.setForeground(QColor(SLATE))

                account_item = QTableWidgetItem(account or "-")
                account_item.setForeground(QColor(TEXT_DARK))

                person_item = QTableWidgetItem(person or "-")
                person_item.setForeground(QColor(TEXT_MUTED))

                category_item = QTableWidgetItem(category or "-")
                category_item.setForeground(QColor(TEXT_MUTED))

                # مبلغ: تراز سمت چپ برای هم‌ترازی ارقام (اعداد چپ‌به‌راست خوانده می‌شوند)
                amount_item = QTableWidgetItem(format_amount(amount))
                amount_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                amount_font = amount_item.font()
                amount_font.setBold(True)
                amount_item.setFont(amount_font)
                amount_item.setForeground(type_color)

                desc_item = QTableWidgetItem(desc or "")
                desc_item.setForeground(QColor(TEXT_MUTED))
                if desc:
                    desc_item.setToolTip(str(desc))

                type_item = QTableWidgetItem("درآمد" if is_income else "هزینه")
                type_font = type_item.font()
                type_font.setBold(True)
                type_item.setFont(type_font)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                type_item.setForeground(type_color)

                for column, item in enumerate([
                        date_item, account_item, person_item,
                        category_item, amount_item, desc_item, type_item]):
                    self.transactions_table.setItem(row, column, item)

                # دکمه ویرایش
                edit_btn = QPushButton("ویرایش")
                edit_btn.setObjectName("editBtn")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {SOFT_GREEN}; color: #166534;
                        border: 1px solid #bbe7c9; border-radius: 8px;
                        padding: 5px 10px; font-size: 12px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: #d1f0da;
                        border-color: {GREEN}; }}
                """)
                edit_btn.clicked.connect(
                    lambda checked, t_id=id: self.edit_transaction(t_id))
                self.transactions_table.setCellWidget(row, 7, edit_btn)

                # دکمه حذف
                delete_btn = QPushButton("حذف")
                delete_btn.setObjectName("deleteBtn")
                delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {SOFT_RED}; color: #b91c1c;
                        border: 1px solid #f5c2c2; border-radius: 8px;
                        padding: 5px 10px; font-size: 12px; font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: #fde3e3;
                        border-color: {RED}; }}
                """)
                delete_btn.clicked.connect(
                    lambda checked, t_id=id: self.delete_transaction(t_id))
                self.transactions_table.setCellWidget(row, 8, delete_btn)

        # وضعیت دکمه‌های صفحه‌بندی
        self.transactions_page_label.setText(
            f"صفحه {self.transactions_current_page} از {self.transactions_total_pages}")
        self.transactions_prev_btn.setEnabled(self.transactions_current_page > 1)
        self.transactions_next_btn.setEnabled(
            self.transactions_current_page < self.transactions_total_pages)

    def prev_transactions_page(self):
        if self.transactions_current_page > 1:
            self.transactions_current_page -= 1
            self.load_transactions()

    def next_transactions_page(self):
        if self.transactions_current_page < self.transactions_total_pages:
            self.transactions_current_page += 1
            self.load_transactions()

    # ================================================================== #
    # عملیات تراکنش‌ها (منطق منتقل‌شده از main.py)
    # ================================================================== #
    def add_transaction(self):
        account_id = self.transaction_account.currentData()
        person_id = self.transaction_person.currentData()
        if person_id is None or person_id == "":
            person_id = None  # صریح مشخص کنیم
        category_id = self.transaction_category.currentData()
        amount = self.transaction_amount.get_raw_value()
        shamsi_date = self.transaction_date.text()
        desc = self.transaction_desc.text()
        category_type = \
            "income" if self.transaction_type.currentText() == "درآمد" else "expense"

        if account_id is None:
            QMessageBox.warning(self, "خطا", "ابتدا یک حساب انتخاب کنید!")
            return
        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ نمی‌تواند خالی باشد!")
            return
        if not shamsi_date:
            shamsi_date = gregorian_to_shamsi(datetime.now().date().strftime("%Y-%m-%d"))
        if not is_valid_shamsi_date(shamsi_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            date = shamsi_to_gregorian(shamsi_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
        except ValueError:
            QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است!")
            return
        try:
            self.db_manager.execute(
                "INSERT INTO transactions (account_id, person_id, category_id, amount, date, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, person_id, category_id, amount, date, desc)
            )
            if category_type == "income":
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (amount, account_id))
            else:
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (amount, account_id))
            self.db_manager.commit()
            self.transaction_amount.clear()
            self.transaction_date.setText(
                gregorian_to_shamsi(datetime.now().date().strftime("%Y-%m-%d")))
            self.transaction_desc.clear()
            self.load_transactions()
            # اطلاع‌رسانی به پنجره اصلی برای به‌روزرسانی موجودی‌ها و داشبورد
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_transaction(self, transaction_id):
        try:
            self.db_manager.execute(
                "SELECT t.account_id, t.person_id, t.category_id, t.amount, t.date, t.description, c.type "
                "FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.id = ?",
                (transaction_id,)
            )
            transaction = self.db_manager.fetchone()
            if not transaction:
                QMessageBox.warning(self, "خطا", "تراکنش یافت نشد!")
                return
            account_id, person_id, category_id, amount, date, desc, category_type = transaction

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش تراکنش")
            dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            dialog.setStyleSheet(f"""
                QDialog {{ background-color: {PAGE_BG};
                          font-family: 'Vazir', 'Arial'; }}
            """)
            layout = QFormLayout(dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(9)

            edit_account = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                edit_account.addItem(display_text, acc_id)
            if account_id:
                for index in range(edit_account.count()):
                    if edit_account.itemData(index) == account_id:
                        edit_account.setCurrentIndex(index)
                        break

            edit_person = QComboBox()
            edit_person.addItem("-", None)
            self.db_manager.execute("SELECT id, name FROM persons")
            persons = self.db_manager.fetchall()
            for p_id, name in persons:
                edit_person.addItem(name, p_id)
            if person_id:
                for index in range(edit_person.count()):
                    if edit_person.itemData(index) == person_id:
                        edit_person.setCurrentIndex(index)
                        break

            edit_type = QComboBox()
            edit_type.addItems(["درآمد", "هزینه"])
            edit_type.setCurrentText("درآمد" if category_type == "income" else "هزینه")

            edit_category = QComboBox()

            def fill_categories():
                edit_category.clear()
                current_type = \
                    "income" if edit_type.currentText() == "درآمد" else "expense"
                self.db_manager.execute(
                    "SELECT id, name FROM categories WHERE type = ?",
                    (current_type,))
                categories = self.db_manager.fetchall()
                for cat_id, name in categories:
                    edit_category.addItem(name, cat_id)
                if category_id:
                    for index in range(edit_category.count()):
                        if edit_category.itemData(index) == category_id:
                            edit_category.setCurrentIndex(index)
                            break

            fill_categories()
            edit_type.currentTextChanged.connect(
                lambda _: fill_categories())

            edit_amount = NumberInput()
            edit_amount.setText(str(int(amount)) if amount == int(amount) else str(amount))
            edit_date = QLineEdit(gregorian_to_shamsi(date))
            edit_date.setReadOnly(True)
            edit_date.setPlaceholderText("1404/02/13")
            edit_date.mousePressEvent = \
                lambda event: self._popup_calendar(edit_date)
            edit_desc = QLineEdit(desc)

            save_btn = QPushButton("ذخیره تغییرات")
            save_btn.setObjectName("primaryBtn")
            save_btn.setMinimumHeight(40)
            save_btn.clicked.connect(lambda: self.save_transaction(
                transaction_id, edit_account.currentData(), edit_person.currentData(),
                edit_category.currentData(), edit_amount.get_raw_value(), edit_date.text(),
                edit_desc.text(), edit_type.currentText(), dialog, account_id, amount, category_type
            ))

            layout.addRow("حساب:", edit_account)
            layout.addRow("شخص:", edit_person)
            layout.addRow("نوع:", edit_type)
            layout.addRow("دسته‌بندی:", edit_category)
            layout.addRow("مبلغ:", edit_amount)
            layout.addRow("تاریخ (شمسی):", edit_date)
            layout.addRow("توضیحات:", edit_desc)
            layout.addRow(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_transaction(self, transaction_id, account_id, person_id, category_id,
                         amount, shamsi_date, desc, type_text, dialog,
                         old_account_id, old_amount, old_category_type):
        if not amount or not shamsi_date:
            QMessageBox.warning(self, "خطا", "مبلغ و تاریخ نمی‌توانند خالی باشند!")
            return
        if not is_valid_shamsi_date(shamsi_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            amount = float(amount)
            date = shamsi_to_gregorian(shamsi_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ یا تاریخ نامعتبر است!")
            return
        try:
            new_category_type = "income" if type_text == "درآمد" else "expense"

            # خنثی کردن اثر تراکنش قدیمی
            if old_category_type == "income":
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (old_amount, old_account_id))
            else:
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (old_amount, old_account_id))

            # اعمال اثر تراکنش جدید
            if new_category_type == "income":
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (amount, account_id))
            else:
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (amount, account_id))

            # بروزرسانی در دیتابیس
            self.db_manager.execute(
                "UPDATE transactions SET account_id = ?, person_id = ?, category_id = ?, amount = ?, date = ?, description = ? WHERE id = ?",
                (account_id, person_id, category_id, amount, date, desc, transaction_id)
            )

            self.db_manager.commit()
            self.load_transactions()
            self.data_changed.emit()
            dialog.accept()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def delete_transaction(self, transaction_id):
        # دریافت اطلاعات تراکنش برای معکوس کردن اثر آن
        try:
            self.db_manager.execute(
                "SELECT t.account_id, t.amount, c.type "
                "FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.id = ?",
                (transaction_id,)
            )
            transaction = self.db_manager.fetchone()
            if not transaction:
                QMessageBox.warning(self, "خطا", "تراکنش یافت نشد!")
                return
            account_id, amount, category_type = transaction

            # تأیید حذف از کاربر
            reply = QMessageBox.question(
                self, "تأیید حذف", "آیا مطمئن هستید که می‌خواهید این تراکنش را حذف کنید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # معکوس کردن اثر تراکنش روی موجودی حساب
            if category_type == "income":
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                    (amount, account_id))
            else:
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                    (amount, account_id))

            # حذف تراکنش از دیتابیس
            self.db_manager.execute(
                "DELETE FROM transactions WHERE id = ?", (transaction_id,))
            self.db_manager.commit()

            self.load_transactions()
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت حذف شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def transfer_money(self):
        from_account_id = self.transfer_from_account.currentData()
        to_account_id = self.transfer_to_account.currentData()
        amount = self.transfer_amount.get_raw_value()
        shamsi_date = self.transfer_date.text()

        # بررسی ورودی‌ها
        if not amount or not shamsi_date:
            QMessageBox.warning(self, "خطا", "مبلغ و تاریخ نمی‌توانند خالی باشند!")
            return
        if not is_valid_shamsi_date(shamsi_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        if from_account_id == to_account_id:
            QMessageBox.warning(self, "خطا", "حساب مبدأ و مقصد نمی‌توانند یکسان باشند!")
            return

        try:
            # تبدیل تاریخ شمسی به میلادی
            date = shamsi_to_gregorian(shamsi_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            # بررسی موجودی حساب مبدأ
            self.db_manager.execute(
                "SELECT balance FROM accounts WHERE id = ?", (from_account_id,))
            balance = self.db_manager.fetchone()
            if not balance or balance[0] < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب مبدأ کافی نیست!")
                return

            # پیدا کردن دسته‌بندی‌های انتقال
            self.db_manager.execute(
                "SELECT id FROM categories WHERE name = 'انتقال بین حساب‌ها (خروج)' AND type = 'expense'")
            expense_category_id = self.db_manager.fetchone()
            if not expense_category_id:
                QMessageBox.critical(
                    self, "خطا", "دسته‌بندی 'انتقال بین حساب‌ها (خروج)' یافت نشد!")
                return
            expense_category_id = expense_category_id[0]

            self.db_manager.execute(
                "SELECT id FROM categories WHERE name = 'انتقال بین حساب‌ها (ورود)' AND type = 'income'")
            income_category_id = self.db_manager.fetchone()
            if not income_category_id:
                QMessageBox.critical(
                    self, "خطا", "دسته‌بندی 'انتقال بین حساب‌ها (ورود)' یافت نشد!")
                return
            income_category_id = income_category_id[0]

            # ثبت تراکنش خروج
            self.db_manager.execute(
                "INSERT INTO transactions (account_id, category_id, amount, date, description) VALUES (?, ?, ?, ?, ?)",
                (from_account_id, expense_category_id, amount, date, "انتقال به حساب دیگر")
            )

            # ثبت تراکنش ورود
            self.db_manager.execute(
                "INSERT INTO transactions (account_id, category_id, amount, date, description) VALUES (?, ?, ?, ?, ?)",
                (to_account_id, income_category_id, amount, date, "دریافت از حساب دیگر")
            )

            # به‌روزرسانی موجودی حساب‌ها
            self.db_manager.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (amount, from_account_id))
            self.db_manager.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                (amount, to_account_id))

            # کامیت تراکنش
            self.db_manager.commit()

            # پاک کردن فرم و به‌روزرسانی UI
            self.transfer_amount.clear()
            self.transfer_date.setText(
                gregorian_to_shamsi(datetime.now().date().strftime("%Y-%m-%d")))
            self.load_transactions()
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "انتقال با موفقیت انجام شد!")

        except sqlite3.Error as e:
            # رول‌بک در صورت خطا
            self.db_manager.rollback()
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # جستجو و گزارش‌گیری (منطق منتقل‌شده از main.py)
    # ================================================================== #
    def search_transactions(self):
        try:
            trans_type = self.transaction_search_type.currentText()
            person_id = self.transaction_search_person.currentData()
            amount = self.transaction_search_amount.get_raw_value()
            start_date = self.transaction_search_start_date.text()
            end_date = self.transaction_search_end_date.text()

            if not start_date or not end_date:
                QMessageBox.warning(
                    self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
                return
            if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
                QMessageBox.warning(
                    self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = shamsi_to_gregorian(start_date)
            end_date_g = shamsi_to_gregorian(end_date)
            if not start_date_g or not end_date_g:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            query = """
                SELECT t.id, t.date, a.name, p.name, c.name, t.amount, t.description, c.type
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN persons p ON t.person_id = p.id
                JOIN categories c ON t.category_id = c.id
                WHERE t.date BETWEEN ? AND ?
            """
            params = [start_date_g, end_date_g]

            if trans_type == "برداشت":
                query += " AND c.type = 'expense' AND c.name != 'انتقال بین حساب‌ها (خروج)'"
            elif trans_type == "واریز":
                query += " AND c.type = 'income' AND c.name != 'انتقال بین حساب‌ها (ورود)'"
            elif trans_type == "انتقال":
                query += " AND c.name IN ('انتقال بین حساب‌ها (ورود)', 'انتقال بین حساب‌ها (خروج)')"

            if person_id:
                query += " AND t.person_id = ?"
                params.append(person_id)
            if amount:
                query += " AND t.amount = ?"
                params.append(amount)

            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()
            self.show_transaction_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def show_transaction_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش تراکنش‌ها")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.resize(900, 620)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {PAGE_BG};
                      font-family: 'Vazir', 'Arial'; }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        dialog.setLayout(layout)

        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            ["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"])
        self._style_table(table, stretch_column=6)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white; alternate-background-color: #f8fafc;
                border: 1px solid {CARD_BORDER}; border-radius: 10px;
                gridline-color: #eef2f7; font-size: 13px;
                selection-background-color: {SOFT_GREEN};
                selection-color: #14532d;
            }}
            QHeaderView::section {{
                background-color: #f1f5f9; color: #334155;
                font-weight: bold; font-size: 12px; padding: 7px 6px;
                border: none; border-bottom: 2px solid #e2e8f0;
            }}
        """)

        self.transaction_report_current_page = 1
        self.transaction_report_results = results
        self.transaction_report_total_pages = (
            len(results) + self.transaction_report_per_page - 1
        ) // self.transaction_report_per_page
        if self.transaction_report_total_pages == 0:
            self.transaction_report_total_pages = 1

        self.update_transaction_report_table(table)

        layout.addWidget(table, 1)

        pagination_layout = QHBoxLayout()
        prev_btn = QPushButton("صفحه قبل")
        prev_btn.setObjectName("pageBtn")
        next_btn = QPushButton("صفحه بعد")
        next_btn.setObjectName("pageBtn")
        page_label = QLabel(
            f"صفحه {self.transaction_report_current_page} از {self.transaction_report_total_pages}")
        page_label.setObjectName("pageLabel")
        prev_btn.clicked.connect(
            lambda: self.prev_transaction_report_page(table, page_label))
        next_btn.clicked.connect(
            lambda: self.next_transaction_report_page(table, page_label))
        pagination_layout.addStretch(1)
        pagination_layout.addWidget(prev_btn)
        pagination_layout.addWidget(page_label)
        pagination_layout.addWidget(next_btn)
        pagination_layout.addStretch(1)
        layout.addLayout(pagination_layout)

        export_btn = QPushButton("📥 خروجی (اکسل/CSV/PDF)")
        export_btn.setObjectName("primaryBtn")
        export_btn.clicked.connect(
            lambda: self._export_results(results))
        layout.addWidget(export_btn)

        dialog.exec()

    def _export_results(self, results):
        """گرفتن خروجی از نتایج جستجو از طریق پنجره اصلی."""
        if self.parent_window is not None and \
                hasattr(self.parent_window, 'export_report'):
            self.parent_window.export_report(results, "transactions")

    def update_transaction_report_table(self, table):
        start = (self.transaction_report_current_page - 1) * self.transaction_report_per_page
        end = start + self.transaction_report_per_page
        page_results = self.transaction_report_results[start:end]
        table.setRowCount(len(page_results))
        for row, (id, date, account, person, category, amount, desc, cat_type) in enumerate(page_results):
            is_income = (cat_type == "income")
            type_color = QColor(GREEN if is_income else RED)

            id_item = QTableWidgetItem(str(id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setForeground(QColor(TEXT_MUTED))

            date_item = QTableWidgetItem(gregorian_to_shamsi(date))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_item.setForeground(QColor(SLATE))

            account_item = QTableWidgetItem(account or "-")
            account_item.setForeground(QColor(TEXT_DARK))

            person_item = QTableWidgetItem(person or "-")
            person_item.setForeground(QColor(TEXT_MUTED))

            category_item = QTableWidgetItem(category or "-")
            category_item.setForeground(QColor(TEXT_MUTED))

            amount_item = QTableWidgetItem(format_amount(amount))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_item.setForeground(type_color)

            desc_item = QTableWidgetItem(desc or "-")
            desc_item.setForeground(QColor(TEXT_MUTED))

            type_item = QTableWidgetItem("درآمد" if is_income else "هزینه")
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_item.setForeground(type_color)

            for column, item in enumerate([
                    id_item, date_item, account_item, person_item,
                    category_item, amount_item, desc_item, type_item]):
                table.setItem(row, column, item)

    def prev_transaction_report_page(self, table, page_label):
        if self.transaction_report_current_page > 1:
            self.transaction_report_current_page -= 1
            self.update_transaction_report_table(table)
            page_label.setText(
                f"صفحه {self.transaction_report_current_page} از {self.transaction_report_total_pages}")

    def next_transaction_report_page(self, table, page_label):
        if self.transaction_report_current_page < self.transaction_report_total_pages:
            self.transaction_report_current_page += 1
            self.update_transaction_report_table(table)
            page_label.setText(
                f"صفحه {self.transaction_report_current_page} از {self.transaction_report_total_pages}")
