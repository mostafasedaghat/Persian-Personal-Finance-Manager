# -*- coding: utf-8 -*-
"""تب بدهی/طلب — ماژول مستقل (جدا شده از main.py)

ساختار صفحه (راست‌به‌چپ):
    ┌────────────────┬───────────────────────────────────┐
    │  ستون راست      │  ستون چپ                          │
    │  (اسکرول)       │                                   │
    │  ┌────────────┐ │  ┌─────────────────────────────┐  │
    │  │ ثبت بدهی/طلب│ │  │ خلاصه وضعیت کلی (۳ کارت)     │  │
    │  └────────────┘ │  ├─────────────────────────────┤  │
    │  ┌────────────┐ │  │ فیلترها (شخص/نوع/وضعیت/زمان) │  │
    │  │ گزارش‌گیری  │ │  ├─────────────────────────────┤  │
    │  └────────────┘ │  │ لیست بدهی‌ها (جدید → قدیم)    │  │
    │                │  │ + نوار وضعیت شخص انتخاب‌شده    │  │
    │                │  │ + صفحه‌بندی                    │  │
    │                │  └─────────────────────────────┘  │
    └────────────────┴───────────────────────────────────┘
    جداکننده دو ستون با QSplitter قابل درگ است.

- پس از هر تغییر داده (ثبت/ویرایش/حذف/تسویه) سیگنال data_changed
  منتشر می‌شود تا main.py حساب‌ها، تراکنش‌ها و داشبورد را تازه‌سازی کند.
"""

from datetime import datetime

import sqlite3

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QFrame,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QScrollArea, QSplitter, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect, QCheckBox,
)

from ui.components.custom_widgets import NumberInput, PersianCalendarPopup
from core.utils import (
    format_number, format_amount, gregorian_to_shamsi,
    shamsi_to_gregorian, is_valid_shamsi_date,
)

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با داشبورد، حساب‌ها و تراکنش‌ها)
# ----------------------------------------------------------------------------
PAGE_BG = "#eef1f6"
CARD_BORDER = "#e5eaf1"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
GREEN = "#16a34a"
RED = "#dc2626"
AMBER = "#d97706"
SLATE = "#475569"
SOFT_GREEN = "#dcfce7"
SOFT_RED = "#fee2e2"
SOFT_AMBER = "#fef3c7"
SOFT_SLATE = "#f1f5f9"
ROW_OVERDUE_BG = "#fef2f2"
ROW_SOON_BG = "#fffbeb"
ROW_CREDIT_BG = "#f0fdf4"   # پس‌زمینه ردیف‌های «طلب من»
ROW_DEBT_BG = "#fef2f2"     # پس‌زمینه ردیف‌های «بدهی من»


class DebtsTab(QWidget):
    """تب بدهی/طلب: ثبت، تسویه، فیلتر، لیست و گزارش‌گیری."""

    # پس از هر ثبت/ویرایش/حذف/تسویه منتشر می‌شود
    data_changed = pyqtSignal()

    # ------------------------------------------------------------------ #
    # استایل کلی تب
    # ------------------------------------------------------------------ #
    STYLESHEET = f"""
    DebtsTab {{
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
    /* رنگ پایه برای همه لیبل‌ها (شامل لیبل‌های خودکار فرم‌ها)؛
       در ویندوز با تم تاریک، پالت سیستم متن لیبل‌های بی‌رنگ را سفید
       می‌کند — این قانون صریح از آن جلوگیری می‌کند. */
    QLabel {{
        color: {TEXT_DARK};
    }}
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
    QLineEdit:disabled, QComboBox:disabled {{
        background-color: #f1f5f9;
        color: #94a3b8;
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
    QCheckBox {{
        color: {TEXT_DARK};
        font-size: 12px;
        spacing: 6px;
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
    QTableWidget#debtsTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#debtsTable QHeaderView::section {{
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

    /* ---------- کارت‌های خلاصه ---------- */
    QFrame#summaryChip {{
        border-radius: 12px;
        border: 1px solid {CARD_BORDER};
    }}
    QLabel#summaryTitle {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: bold;
    }}
    QLabel#summaryValue {{
        font-size: 14px;
        font-weight: bold;
    }}

    /* ---------- نوار وضعیت شخص ---------- */
    QLabel#personStatusBar {{
        background-color: #f8fafc;
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
        padding: 9px 14px;
        color: {TEXT_DARK};
        font-size: 12px;
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

        # وضعیت صفحه‌بندی لیست بدهی‌ها
        self.debts_current_page = 1
        self.debts_per_page = 50
        self.debts_total_pages = 1

        # وضعیت صفحه‌بندی گزارش جستجو
        self.debt_report_current_page = 1
        self.debt_report_per_page = 50
        self.debt_report_results = []
        self.debt_report_total_pages = 1

        # نگاشت ردیف جدول → شناسه شخص (برای نوار وضعیت)
        self._row_person_ids = {}

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.STYLESHEET)

        self.setup_ui()

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
        splitter.setSizes([430, 770])

        layout.addWidget(splitter)

    # ------------------------------------------------------------------ #
    # پنل راست: فرم‌ها (ثبت بدهی/طلب + جستجو و گزارش)
    # ------------------------------------------------------------------ #
    def _build_forms_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(350)
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
        container_layout.addWidget(self._build_search_card())
        container_layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _build_entry_card(self):
        """کارت ثبت بدهی/طلب جدید"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🤝")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("ثبت بدهی/طلب جدید")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        # فرم
        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.debt_person = QComboBox()
        self.debt_amount = NumberInput()
        self.debt_amount.setPlaceholderText("مبلغ به ریال")

        self.debt_is_credit = QComboBox()
        self.debt_is_credit.addItems(["بدهی من", "طلب من"])

        self.debt_account = QComboBox()
        self.debt_account.setEnabled(False)
        self.debt_has_payment = QCheckBox("آیا پولی دریافت/پرداخت شده؟")
        self.debt_has_payment.stateChanged.connect(self._toggle_account_field)

        self.debt_due_date = QLineEdit()
        today = datetime.now().date()
        self.debt_due_date.setText(
            gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.debt_due_date.setPlaceholderText("1404/02/13")
        self.debt_due_date.setReadOnly(True)
        self.debt_due_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.debt_due_date)
        self.debt_due_date.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        self.debt_show_in_dashboard = QCheckBox("نمایش در داشبورد")
        self.debt_description = QLineEdit()
        self.debt_description.setPlaceholderText("توضیح اختیاری...")

        form.addRow("شخص:", self.debt_person)
        form.addRow("مبلغ:", self.debt_amount)
        form.addRow("نوع:", self.debt_is_credit)
        form.addRow("", self.debt_has_payment)
        form.addRow("حساب مرتبط:", self.debt_account)
        form.addRow("تاریخ سررسید (شمسی):", self.debt_due_date)
        form.addRow("", self.debt_show_in_dashboard)
        form.addRow("توضیحات:", self.debt_description)
        lay.addLayout(form)

        add_debt_btn = QPushButton("✅ ثبت بدهی/طلب")
        add_debt_btn.setObjectName("primaryBtn")
        add_debt_btn.setMinimumHeight(42)
        add_debt_btn.clicked.connect(self.add_debt)
        lay.addWidget(add_debt_btn)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_search_card(self):
        """کارت جستجو و گزارش‌گیری بدهی/طلب"""
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

        self.debt_search_type = QComboBox()
        self.debt_search_type.addItems(["همه", "بدهی", "طلب"])
        self.debt_search_person = QComboBox()
        self.debt_search_person.addItem("-", None)
        self.debt_search_amount = NumberInput()
        self.debt_search_amount.setPlaceholderText("0")

        self.debt_search_start_date = QLineEdit()
        self.debt_search_start_date.setPlaceholderText("اختیاری")
        self.debt_search_start_date.setReadOnly(True)
        self.debt_search_start_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.debt_search_start_date)
        self.debt_search_end_date = QLineEdit()
        self.debt_search_end_date.setPlaceholderText("اختیاری")
        self.debt_search_end_date.setReadOnly(True)
        self.debt_search_end_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.debt_search_end_date)

        form.addRow("نوع:", self.debt_search_type)
        form.addRow("شخص:", self.debt_search_person)
        form.addRow("مبلغ:", self.debt_search_amount)
        form.addRow("از تاریخ (شمسی):", self.debt_search_start_date)
        form.addRow("تا تاریخ (شمسی):", self.debt_search_end_date)
        lay.addLayout(form)

        # نکته: تاریخ‌ها اختیاری هستند
        hint = QLabel("💡 تاریخ‌ها اختیاری‌اند؛ خالی بمانند گزارش کلی ارائه می‌شود.")
        hint.setObjectName("formLabel")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        clear_dates_btn = QPushButton("پاک کردن تاریخ‌ها")
        clear_dates_btn.setObjectName("secondaryBtn")
        clear_dates_btn.clicked.connect(self._clear_search_dates)
        lay.addWidget(clear_dates_btn)

        search_btn = QPushButton("📊 نمایش گزارش")
        search_btn.setObjectName("primaryBtn")
        search_btn.setMinimumHeight(40)
        search_btn.clicked.connect(self.search_debts)
        lay.addWidget(search_btn)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # پنل چپ: خلاصه کلی + فیلترها + لیست بدهی‌ها + صفحه‌بندی
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
        title = QLabel("لیست بدهی‌ها و طلب‌ها")
        title.setObjectName("panelTitle")
        self.debts_count_chip = QLabel("0 مورد")
        self.debts_count_chip.setObjectName("chip")
        self.debts_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.debts_count_chip)
        lay.addLayout(header_row)

        # ---- خلاصه وضعیت کلی (غیر وابسته به فیلترها) ----
        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        summary_row.addWidget(self._build_summary_chip(
            "💳", "بدهی‌های باقی‌مانده من", SOFT_RED, RED, "summary_debt"), 1)
        summary_row.addWidget(self._build_summary_chip(
            "🤝", "طلب‌های باقی‌مانده من", SOFT_GREEN, GREEN, "summary_credit"), 1)
        summary_row.addWidget(self._build_summary_chip(
            "⚖️", "وضعیت خالص", SOFT_SLATE, SLATE, "summary_net"), 1)
        lay.addLayout(summary_row)

        # ---- نوار فیلترها ----
        filters_card = QFrame()
        filters_card.setStyleSheet(
            f"QFrame {{ background-color: {SOFT_SLATE};"
            f" border-radius: 10px; }}")
        filters_lay = QVBoxLayout(filters_card)
        filters_lay.setContentsMargins(12, 10, 12, 10)
        filters_lay.setSpacing(8)

        # ردیف اول: شخص + نوع + وضعیت
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        person_box = QVBoxLayout()
        person_box.setSpacing(3)
        person_label = QLabel("شخص:")
        person_label.setObjectName("formLabel")
        self.filter_person = QComboBox()
        self.filter_person.addItem("همه اشخاص", None)
        self.filter_person.currentIndexChanged.connect(
            lambda _: self.apply_filters())
        person_box.addWidget(person_label)
        person_box.addWidget(self.filter_person)

        type_box = QVBoxLayout()
        type_box.setSpacing(3)
        type_label = QLabel("نوع:")
        type_label.setObjectName("formLabel")
        self.filter_type = QComboBox()
        self.filter_type.addItems(["همه", "بدهی", "طلب"])
        self.filter_type.currentIndexChanged.connect(
            lambda _: self.apply_filters())
        type_box.addWidget(type_label)
        type_box.addWidget(self.filter_type)

        status_box = QVBoxLayout()
        status_box.setSpacing(3)
        status_label = QLabel("وضعیت:")
        status_label.setObjectName("formLabel")
        self.filter_status = QComboBox()
        self.filter_status.addItems(["همه", "در جریان", "تسویه‌شده"])
        self.filter_status.currentIndexChanged.connect(
            lambda _: self.apply_filters())
        status_box.addWidget(status_label)
        status_box.addWidget(self.filter_status)

        row1.addLayout(person_box, 3)
        row1.addLayout(type_box, 2)
        row1.addLayout(status_box, 2)
        filters_lay.addLayout(row1)

        # ردیف دوم: بازه تاریخ + دکمه‌ها
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        start_box = QVBoxLayout()
        start_box.setSpacing(3)
        start_label = QLabel("از تاریخ سررسید:")
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
        end_label = QLabel("تا تاریخ سررسید:")
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

        # ---- جدول بدهی‌ها ----
        # نکته RTL: ستون «عملیات» عمداً اولین ستون (سمت راست) است تا
        # در پنجره‌های باریک، دکمه‌ها همیشه داخل دید بمانند و فقط
        # ستون‌های کم‌اهمیت‌تر (حساب/توضیحات) زیر اسکرول افقی بروند.
        self.debts_table = QTableWidget()
        self.debts_table.setObjectName("debtsTable")
        self.debts_table.setColumnCount(11)
        self.debts_table.setHorizontalHeaderLabels(
            ["عملیات", "نوع", "شخص", "مبلغ", "پرداخت", "باقی‌مانده",
             "سررسید", "وضعیت", "تاریخ تسویه", "حساب", "توضیحات"])
        self._style_table(self.debts_table, stretch_column=10)
        # عرض ثابت برای ستون عملیات (ResizeToContents عرض ویجت‌های سلول را
        # محاسبه نمی‌کند؛ بدون این کار دکمه‌ها فشرده می‌شوند)
        self.debts_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)
        self.debts_table.setColumnWidth(0, 158)
        self.debts_table.itemSelectionChanged.connect(
            self._on_selection_changed)
        self.debts_table.cellClicked.connect(
            lambda row, col: self._on_selection_changed())
        lay.addWidget(self.debts_table, 1)

        # حالت خالی
        self.debts_empty_label = QLabel("📝 بدهی/طلبی برای نمایش وجود ندارد")
        self.debts_empty_label.setObjectName("emptyLabel")
        self.debts_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.debts_empty_label.setVisible(False)
        lay.addWidget(self.debts_empty_label, 1)

        # ---- نوار وضعیت شخص انتخاب‌شده ----
        self.person_status_bar = QLabel(
            "👤 برای مشاهده وضعیت مالی یک شخص، روی ردیف او در جدول کلیک کنید")
        self.person_status_bar.setObjectName("personStatusBar")
        self.person_status_bar.setTextFormat(Qt.TextFormat.RichText)
        self.person_status_bar.setWordWrap(True)
        lay.addWidget(self.person_status_bar)

        # ---- صفحه‌بندی ----
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)
        self.debts_prev_btn = QPushButton("صفحه قبل")
        self.debts_prev_btn.setObjectName("pageBtn")
        self.debts_next_btn = QPushButton("صفحه بعد")
        self.debts_next_btn.setObjectName("pageBtn")
        self.debts_page_label = QLabel("صفحه 1")
        self.debts_page_label.setObjectName("pageLabel")
        self.debts_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.debts_prev_btn.clicked.connect(self.prev_debts_page)
        self.debts_next_btn.clicked.connect(self.next_debts_page)

        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.debts_prev_btn)
        pagination_layout.addWidget(self.debts_page_label)
        pagination_layout.addWidget(self.debts_next_btn)
        pagination_layout.addStretch(1)
        lay.addLayout(pagination_layout)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_summary_chip(self, icon_text, title, soft_bg, value_color, attr_prefix):
        """ساخت یک کارت خلاصه کوچک (آیکون + عنوان + مقدار)."""
        chip = QFrame()
        chip.setObjectName("summaryChip")
        chip.setStyleSheet(
            f"QFrame#summaryChip {{ background-color: {soft_bg}; }}")

        row = QHBoxLayout(chip)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        icon = QLabel(icon_text)
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "background-color: rgba(255,255,255,0.65);"
            f"border-radius: 9px; font-size: 14px;")

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")
        value_label = QLabel("0 ریال")
        value_label.setObjectName("summaryValue")
        value_label.setStyleSheet(f"color: {value_color};")
        text_box.addWidget(title_label)
        text_box.addWidget(value_label)

        row.addWidget(icon)
        row.addLayout(text_box, 1)

        # نگهداری ارجاع برای به‌روزرسانی مقدار
        setattr(self, f"{attr_prefix}_value", value_label)

        return chip

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

    def _toggle_account_field(self, state):
        """فعال/غیرفعال کردن لیست حساب‌ها بر اساس وضعیت چک‌باکس."""
        self.debt_account.setEnabled(state == Qt.CheckState.Checked.value)

    def _clear_search_dates(self):
        """پاک کردن تاریخ‌های فرم گزارش (گزارش کلی)."""
        self.debt_search_start_date.clear()
        self.debt_search_end_date.clear()

    @staticmethod
    def _days_left(due_date):
        """تعداد روز باقی‌مانده تا سررسید (منفی = گذشته)."""
        try:
            d = datetime.strptime(due_date, "%Y-%m-%d").date()
            return (d - datetime.now().date()).days
        except (ValueError, TypeError):
            return None

    def _due_appearance(self, due_date, days_left):
        """متن، رنگ، پس‌زمینه و tooltip ستون سررسید بر اساس وضعیت."""
        shamsi_due_date = gregorian_to_shamsi(due_date) or "-"
        if days_left is None:
            return shamsi_due_date, QColor(SLATE), None, ""
        if days_left < 0:
            return (shamsi_due_date, QColor(RED), QColor(ROW_OVERDUE_BG),
                    f"{abs(days_left)} روز از سررسید گذشته است")
        if days_left == 0:
            return (shamsi_due_date, QColor(AMBER), QColor(ROW_SOON_BG),
                    "سررسید امروز است")
        if days_left <= 3:
            return (shamsi_due_date, QColor(AMBER), QColor(ROW_SOON_BG),
                    f"{days_left} روز تا سررسید مانده است")
        return (shamsi_due_date, QColor(SLATE), None,
                f"{days_left} روز تا سررسید مانده است")

    # ================================================================== #
    # پرکردن کامبوباکس‌ها (توسط main.py فراخوانی می‌شوند)
    # ================================================================== #
    def reload_accounts(self, accounts):
        """پرکردن کامبوباکس حساب فرم ثبت بدهی/طلب."""
        try:
            display_items = []
            for id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                display_items.append((display_text, id))

            selected = self.debt_account.currentData()
            self.debt_account.blockSignals(True)
            self.debt_account.clear()
            for display_text, id in display_items:
                self.debt_account.addItem(display_text, id)
            if selected is not None:
                for index in range(self.debt_account.count()):
                    if self.debt_account.itemData(index) == selected:
                        self.debt_account.setCurrentIndex(index)
                        break
            self.debt_account.blockSignals(False)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def reload_persons(self, persons):
        """پرکردن کامبوباکس‌های شخص (فرم ثبت، جستجو و فیلتر لیست)."""
        try:
            self.debt_person.blockSignals(True)
            self.debt_person.clear()
            self.debt_person.addItem("-", None)
            for id, name in persons:
                self.debt_person.addItem(name, id)
            self.debt_person.blockSignals(False)

            self.debt_search_person.clear()
            self.debt_search_person.addItem("-", None)
            for id, name in persons:
                self.debt_search_person.addItem(name, id)

            # فیلتر لیست: نام ساده + گزینه «همه اشخاص»
            # (بدون ارسال سیگنال تا بارگذاری مجدد تکراری رخ ندهد)
            self.filter_person.blockSignals(True)
            self.filter_person.clear()
            self.filter_person.addItem("همه اشخاص", None)
            for id, name in persons:
                self.filter_person.addItem(name, id)
            self.filter_person.blockSignals(False)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # فیلترها و لیست بدهی‌ها
    # ================================================================== #
    def _current_filter_clauses(self):
        """ساخت شرط WHERE بر اساس فیلترهای فعال (شخص/نوع/وضعیت/تاریخ)."""
        clauses = []
        params = []

        # فیلتر شخص
        person_id = self.filter_person.currentData()
        if person_id:
            clauses.append("d.person_id = ?")
            params.append(person_id)

        # فیلتر نوع (بدهی/طلب)
        filter_type = self.filter_type.currentText()
        if filter_type == "بدهی":
            clauses.append("d.is_credit = 0")
        elif filter_type == "طلب":
            clauses.append("d.is_credit = 1")

        # فیلتر وضعیت تسویه
        filter_status = self.filter_status.currentText()
        if filter_status == "در جریان":
            clauses.append("d.is_paid = 0")
        elif filter_status == "تسویه‌شده":
            clauses.append("d.is_paid = 1")

        # فیلتر بازه سررسید (شمسی → میلادی)
        start_text = self.filter_start_date.text().strip()
        if start_text:
            start_g = shamsi_to_gregorian(start_text)
            if not start_g:
                return None, None, "تاریخ «از» نامعتبر است!"
            clauses.append("d.due_date >= ?")
            params.append(start_g)

        end_text = self.filter_end_date.text().strip()
        if end_text:
            end_g = shamsi_to_gregorian(end_text)
            if not end_g:
                return None, None, "تاریخ «تا» نامعتبر است!"
            clauses.append("d.due_date <= ?")
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
        self.debts_current_page = 1
        self.load_debts()

    def clear_filters(self):
        """پاک کردن همه فیلترها و نمایش کل بدهی‌ها."""
        self.filter_person.blockSignals(True)
        self.filter_person.setCurrentIndex(0)
        self.filter_person.blockSignals(False)
        self.filter_type.blockSignals(True)
        self.filter_type.setCurrentIndex(0)
        self.filter_type.blockSignals(False)
        self.filter_status.blockSignals(True)
        self.filter_status.setCurrentIndex(0)
        self.filter_status.blockSignals(False)
        self.filter_start_date.clear()
        self.filter_end_date.clear()
        self.debts_current_page = 1
        self.load_debts()

    def refresh(self):
        """به‌روزرسانی لیست با حفظ صفحه فعلی (فراخوانی از main.py)."""
        self.load_debts()

    # ------------------------------------------------------------------ #
    # خلاصه وضعیت کلی
    # ------------------------------------------------------------------ #
    def _update_summary(self):
        """به‌روزرسانی کارت‌های خلاصه (جمع باقی‌مانده همه بدهی/طلب‌ها)."""
        try:
            self.db_manager.execute(
                "SELECT is_credit, COALESCE(SUM(amount - paid_amount), 0) "
                "FROM debts WHERE is_paid = 0 GROUP BY is_credit")
            totals = {int(row[0]): float(row[1])
                      for row in self.db_manager.fetchall()}
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        debt_total = totals.get(0, 0.0)    # بدهی‌های من (من بدهکارم)
        credit_total = totals.get(1, 0.0)  # طلب‌های من (من طلبکارم)

        self.summary_debt_value.setText(f"{format_amount(debt_total)} ریال")
        self.summary_credit_value.setText(f"{format_amount(credit_total)} ریال")

        net = credit_total - debt_total
        if net > 0:
            self.summary_net_value.setText(
                f"{format_amount(net)} ریال طلبکار")
            self.summary_net_value.setStyleSheet(f"color: {GREEN};")
        elif net < 0:
            self.summary_net_value.setText(
                f"{format_amount(-net)} ریال بدهکار")
            self.summary_net_value.setStyleSheet(f"color: {RED};")
        else:
            self.summary_net_value.setText("تسویه")
            self.summary_net_value.setStyleSheet(f"color: {SLATE};")

    # ------------------------------------------------------------------ #
    # نوار وضعیت شخص انتخاب‌شده
    # ------------------------------------------------------------------ #
    def _reset_person_status(self):
        self.person_status_bar.setText(
            "👤 برای مشاهده وضعیت مالی یک شخص، روی ردیف او در جدول کلیک کنید")

    def _on_selection_changed(self):
        """نمایش جمع بدهی/طلب شخصِ ردیف انتخاب‌شده."""
        row = self.debts_table.currentRow()
        person_id = self._row_person_ids.get(row)
        if not person_id:
            self._reset_person_status()
            return
        try:
            self.db_manager.execute(
                "SELECT name FROM persons WHERE id = ?", (person_id,))
            person = self.db_manager.fetchone()
            if not person:
                self._reset_person_status()
                return
            name = person[0]

            self.db_manager.execute(
                "SELECT is_credit, COALESCE(SUM(amount - paid_amount), 0) "
                "FROM debts WHERE person_id = ? AND is_paid = 0 "
                "GROUP BY is_credit", (person_id,))
            totals = {int(r[0]): float(r[1]) for r in self.db_manager.fetchall()}
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        debt_total = totals.get(0, 0.0)   # شما به این شخص بدهکارید
        credit_total = totals.get(1, 0.0)  # این شخص به شما بدهکار است
        net = credit_total - debt_total

        if net > 0:
            net_html = (f"خالص: این شخص <b>{format_amount(net)} ریال</b>"
                        f" به شما بدهکار است")
            net_color = GREEN
        elif net < 0:
            net_html = (f"خالص: شما <b>{format_amount(-net)} ریال</b>"
                        f" به این شخص بدهکارید")
            net_color = RED
        else:
            net_html = "خالص: تسویه"
            net_color = SLATE

        self.person_status_bar.setText(
            f"👤 <b>{name}</b> &nbsp;|&nbsp; "
            f"بدهی باقی‌مانده شما به این شخص: "
            f"<span style='color:{RED};'><b>{format_amount(debt_total)} ریال</b></span> &nbsp;|&nbsp; "
            f"طلب باقی‌مانده شما از این شخص: "
            f"<span style='color:{GREEN};'><b>{format_amount(credit_total)} ریال</b></span> &nbsp;|&nbsp; "
            f"<span style='color:{net_color};'>{net_html}</span>")

    # ------------------------------------------------------------------ #
    # بارگذاری لیست (جدید → قدیم)
    # ------------------------------------------------------------------ #
    def load_debts(self):
        """بارگذاری بدهی‌های صفحه فعلی با فیلترهای فعال (جدیدترین اول)."""
        try:
            clauses, params, error = self._current_filter_clauses()
            if error:
                QMessageBox.warning(self, "خطا", error)
                return

            where_sql = ""
            if clauses:
                where_sql = "WHERE " + " AND ".join(clauses)

            # ۱. تعداد کل موارد منطبق بر فیلتر
            self.db_manager.execute(
                f"SELECT COUNT(*) FROM debts d {where_sql}", params)
            total_debts = self.db_manager.fetchone()[0]
            self.debts_total_pages = (
                total_debts + self.debts_per_page - 1
            ) // self.debts_per_page
            if self.debts_total_pages == 0:
                self.debts_total_pages = 1
            # اگر صفحه فعلی خارج از بازه شد (مثلاً بعد از حذف)
            if self.debts_current_page > self.debts_total_pages:
                self.debts_current_page = self.debts_total_pages

            # ۲. واکشی موارد صفحه فعلی — جدیدترین در صفحه اول
            offset = (self.debts_current_page - 1) * self.debts_per_page
            self.db_manager.execute(
                f"SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, "
                f"d.is_paid, a.name, d.is_credit, d.description, d.person_id, "
                f"d.settled_date "
                f"FROM debts d "
                f"LEFT JOIN persons p ON d.person_id = p.id "
                f"LEFT JOIN accounts a ON d.account_id = a.id "
                f"{where_sql} "
                f"ORDER BY d.id DESC LIMIT ? OFFSET ?",
                params + [self.debts_per_page, offset])
            debts = self.db_manager.fetchall()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        self.debts_count_chip.setText(f"{total_debts} مورد")

        # خلاصه وضعیت کلی (همیشه از کل داده محاسبه می‌شود)
        self._update_summary()

        # نگاشت ردیف → شخص برای نوار وضعیت
        self._row_person_ids = {}
        self._reset_person_status()

        # حالت خالی
        if not debts:
            self.debts_table.setRowCount(0)
            self.debts_table.setVisible(False)
            self.debts_empty_label.setVisible(True)
        else:
            self.debts_table.setVisible(True)
            self.debts_empty_label.setVisible(False)

            self.debts_table.setRowCount(len(debts))
            for row, (id, person, amount, paid, due_date, is_paid,
                      account, is_credit, description, person_id,
                      settled_date) in enumerate(debts):
                is_credit = int(is_credit or 0)
                remaining = (amount or 0) - (paid or 0)
                self._row_person_ids[row] = person_id

                # پس‌زمینه ردیف بر اساس نوع
                row_bg = QColor(ROW_CREDIT_BG if is_credit else ROW_DEBT_BG)

                # ستون نوع
                type_text = "طلب من" if is_credit else "بدهی من"
                type_color = QColor(GREEN if is_credit else RED)
                type_item = QTableWidgetItem(type_text)
                type_font = type_item.font()
                type_font.setBold(True)
                type_item.setFont(type_font)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                type_item.setForeground(type_color)
                type_item.setBackground(row_bg)

                # ستون شخص
                person_item = QTableWidgetItem(person or "-")
                person_item.setForeground(QColor(TEXT_DARK))
                person_item.setBackground(row_bg)

                # ستون مبلغ کل
                amount_item = QTableWidgetItem(format_amount(amount))
                amount_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                amount_item.setForeground(QColor(TEXT_DARK))
                amount_item.setBackground(row_bg)

                # ستون پرداخت‌شده
                paid_item = QTableWidgetItem(format_amount(paid))
                paid_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                paid_item.setForeground(QColor(TEXT_MUTED))
                paid_item.setBackground(row_bg)

                # ستون باقی‌مانده
                remaining_item = QTableWidgetItem(format_amount(max(remaining, 0)))
                remaining_font = remaining_item.font()
                remaining_font.setBold(True)
                remaining_item.setFont(remaining_font)
                remaining_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                remaining_item.setForeground(type_color)
                remaining_item.setBackground(row_bg)

                # ستون سررسید (با رنگ‌بندی فوریت)
                days_left = self._days_left(due_date) if due_date else None
                due_text, due_color, due_bg, due_tip = \
                    self._due_appearance(due_date, days_left)
                due_item = QTableWidgetItem(due_text)
                due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                due_item.setForeground(due_color)
                due_item.setBackground(due_bg if due_bg else row_bg)
                if due_tip:
                    due_item.setToolTip(due_tip)

                # ستون وضعیت
                if is_paid:
                    status_text, status_color = "تسویه‌شده", QColor(TEXT_MUTED)
                else:
                    status_text, status_color = "در جریان", QColor(AMBER)
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setForeground(status_color)
                status_item.setBackground(row_bg)

                # ستون تاریخ تسویه (تاریخ واقعی پرداخت — نسخه ۲.۳)
                # ردیف‌های تسویه‌شدهٔ قدیمی که تاریخ ندارند «—» نشان می‌دهند
                settled_item = QTableWidgetItem(
                    gregorian_to_shamsi(settled_date) if settled_date else "—")
                settled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if settled_date:
                    settled_item.setForeground(QColor(TEXT_MUTED))
                    settled_item.setBackground(row_bg)
                    settled_item.setToolTip(
                        f"تاریخ واقعی تسویه: {gregorian_to_shamsi(settled_date)}")
                else:
                    settled_item.setForeground(QColor(TEXT_MUTED))
                    settled_item.setBackground(row_bg)

                # ستون حساب
                account_item = QTableWidgetItem(account or "-")
                account_item.setForeground(QColor(TEXT_MUTED))
                account_item.setBackground(row_bg)

                # ستون توضیحات
                desc_item = QTableWidgetItem(description or "")
                desc_item.setForeground(QColor(TEXT_MUTED))
                desc_item.setBackground(row_bg)
                if description:
                    desc_item.setToolTip(str(description))

                for column, item in enumerate([
                        type_item, person_item, amount_item, paid_item,
                        remaining_item, due_item, status_item, settled_item,
                        account_item, desc_item], start=1):
                    self.debts_table.setItem(row, column, item)

                # ستون عملیات (اولین ستون — سمت راست): ویرایش / حذف / تسویه
                if not is_paid:
                    actions = QWidget()
                    actions.setLayoutDirection(
                        Qt.LayoutDirection.RightToLeft)
                    actions_layout = QHBoxLayout(actions)
                    actions_layout.setContentsMargins(2, 2, 2, 2)
                    actions_layout.setSpacing(4)

                    edit_btn = QPushButton("ویرایش")
                    edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    edit_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {SOFT_GREEN}; color: #166534;
                            border: 1px solid #bbe7c9; border-radius: 8px;
                            padding: 4px 8px; font-size: 11px; font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: #d1f0da;
                            border-color: {GREEN}; }}
                    """)
                    edit_btn.clicked.connect(
                        lambda checked, d_id=id: self.edit_debt(d_id))

                    delete_btn = QPushButton("حذف")
                    delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    delete_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {SOFT_RED}; color: #b91c1c;
                            border: 1px solid #f5c2c2; border-radius: 8px;
                            padding: 4px 8px; font-size: 11px; font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: #fde3e3;
                            border-color: {RED}; }}
                    """)
                    delete_btn.clicked.connect(
                        lambda checked, d_id=id: self.delete_debt(d_id))

                    settle_btn = QPushButton("تسویه")
                    settle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    settle_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {SOFT_AMBER}; color: #92400e;
                            border: 1px solid #fde68a; border-radius: 8px;
                            padding: 4px 8px; font-size: 11px; font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: #fef9c3;
                            border-color: {AMBER}; }}
                    """)
                    settle_btn.clicked.connect(
                        lambda checked, d_id=id: self.settle_debt(d_id))

                    actions_layout.addWidget(edit_btn)
                    actions_layout.addWidget(delete_btn)
                    actions_layout.addWidget(settle_btn)
                    self.debts_table.setCellWidget(row, 0, actions)
                else:
                    dash_item = QTableWidgetItem("—")
                    dash_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    dash_item.setForeground(QColor(TEXT_MUTED))
                    self.debts_table.setItem(row, 0, dash_item)

        # وضعیت دکمه‌های صفحه‌بندی
        self.debts_page_label.setText(
            f"صفحه {self.debts_current_page} از {self.debts_total_pages}")
        self.debts_prev_btn.setEnabled(self.debts_current_page > 1)
        self.debts_next_btn.setEnabled(
            self.debts_current_page < self.debts_total_pages)

    def prev_debts_page(self):
        if self.debts_current_page > 1:
            self.debts_current_page -= 1
            self.load_debts()

    def next_debts_page(self):
        if self.debts_current_page < self.debts_total_pages:
            self.debts_current_page += 1
            self.load_debts()

    # ================================================================== #
    # عملیات بدهی/طلب (منطق منتقل‌شده از main.py)
    # ================================================================== #
    def add_debt(self):
        person_id = self.debt_person.currentData()
        amount = self.debt_amount.get_raw_value()
        account_id = self.debt_account.currentData()
        shamsi_due_date = self.debt_due_date.text()
        is_credit = self.debt_is_credit.currentText() == "طلب من"
        has_payment = self.debt_has_payment.isChecked()
        show_in_dashboard = self.debt_show_in_dashboard.isChecked()
        description = self.debt_description.text() or None

        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ نمی‌تواند خالی باشد!")
            return

        due_date = None
        if shamsi_due_date:
            if not is_valid_shamsi_date(shamsi_due_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return
            try:
                due_date = shamsi_to_gregorian(shamsi_due_date)
                if not due_date:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
            except ValueError:
                QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است!")
                return

        try:
            # اگر پولی رد و بدل نشده، حسابی ذخیره نمی‌شود
            account_id_to_save = account_id if has_payment else None

            self.db_manager.execute(
                "INSERT INTO debts (person_id, amount, due_date, is_paid, "
                "account_id, show_in_dashboard, is_credit, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (person_id, amount, due_date, 0, account_id_to_save,
                 1 if show_in_dashboard else 0, 1 if is_credit else 0,
                 description)
            )

            # اگر تیک پرداخت فعال باشد، موجودی حساب به‌روزرسانی می‌شود
            if has_payment and account_id:
                if is_credit:  # طلب من: من به کسی پول دادم، موجودی کم می‌شود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (amount, account_id))
                else:  # بدهی من: من از کسی پول گرفتم، موجودی زیاد می‌شود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (amount, account_id))

            self.db_manager.commit()
            self.debt_amount.clear()
            self.debt_due_date.setText(
                gregorian_to_shamsi(datetime.now().date().strftime("%Y-%m-%d")))
            self.debt_has_payment.setChecked(False)
            self.debt_show_in_dashboard.setChecked(False)
            self.debt_description.clear()
            self.load_debts()
            # اطلاع‌رسانی به پنجره اصلی برای به‌روزرسانی حساب‌ها و داشبورد
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_debt(self, debt_id):
        try:
            self.db_manager.execute(
                "SELECT person_id, amount, account_id, due_date, is_paid, "
                "show_in_dashboard, description, is_credit FROM debts WHERE id = ?",
                (debt_id,)
            )
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            (person_id, amount, account_id, due_date, is_paid,
             show_in_dashboard, description, is_credit) = debt
            is_credit = int(is_credit or 0)

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش بدهی/طلب")
            dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            # نکته: رنگ لیبل‌ها باید صریح باشد؛ در ویندوز با تم تاریک، پالت
            # سیستم متن لیبل‌های بی‌رنگ را سفید می‌کند و روی پس‌زمینه روشنِ
            # این دیالوگ نامرئی می‌شوند.
            dialog.setStyleSheet(f"""
                QDialog {{ background-color: {PAGE_BG};
                          font-family: 'Vazir', 'Arial'; }}
                QLabel {{ color: {TEXT_DARK}; font-size: 13px; font-weight: bold; }}
                QCheckBox {{ color: {TEXT_DARK}; font-size: 13px; }}
            """)
            layout = QFormLayout(dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(9)

            edit_person = QComboBox()
            self.db_manager.execute("SELECT id, name FROM persons")
            persons = self.db_manager.fetchall()
            for p_id, name in persons:
                edit_person.addItem(name, p_id)
            if person_id:
                for index in range(edit_person.count()):
                    if edit_person.itemData(index) == person_id:
                        edit_person.setCurrentIndex(index)
                        break

            edit_amount = NumberInput()
            edit_amount.setText(str(int(amount)) if amount == int(amount) else str(amount))

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
            edit_account.setEnabled(bool(account_id))

            edit_has_payment = QCheckBox("آیا پولی دریافت/پرداخت شده؟")
            edit_has_payment.setChecked(bool(account_id))
            edit_has_payment.stateChanged.connect(
                lambda state: edit_account.setEnabled(
                    state == Qt.CheckState.Checked.value))

            edit_due_date = QLineEdit(
                gregorian_to_shamsi(due_date) if due_date else "")
            edit_due_date.setReadOnly(True)
            edit_due_date.setPlaceholderText("1404/02/13")
            edit_due_date.mousePressEvent = \
                lambda event: self._popup_calendar(edit_due_date)

            edit_is_credit = QComboBox()
            edit_is_credit.addItems(["بدهی من", "طلب من"])
            edit_is_credit.setCurrentText("طلب من" if is_credit else "بدهی من")

            edit_show_in_dashboard = QCheckBox("نمایش در داشبورد")
            edit_show_in_dashboard.setChecked(bool(show_in_dashboard))

            edit_description = QLineEdit(description or "")
            edit_description.setPlaceholderText("توضیحات (اختیاری)")
            edit_description.setMaxLength(100)

            save_btn = QPushButton("ذخیره تغییرات")
            save_btn.setObjectName("primaryBtn")
            save_btn.setMinimumHeight(40)
            save_btn.clicked.connect(lambda: self.save_debt(
                debt_id, edit_person.currentData(), edit_amount.get_raw_value(),
                edit_account.currentData(), edit_due_date.text(),
                edit_is_credit.currentText() == "طلب من",
                edit_has_payment.isChecked(), edit_show_in_dashboard.isChecked(),
                edit_description.text() or None, dialog
            ))

            layout.addRow("شخص:", edit_person)
            layout.addRow("مبلغ:", edit_amount)
            layout.addRow("", edit_has_payment)
            layout.addRow("حساب مرتبط:", edit_account)
            layout.addRow("تاریخ سررسید (شمسی):", edit_due_date)
            layout.addRow("نوع:", edit_is_credit)
            layout.addRow("", edit_show_in_dashboard)
            layout.addRow("توضیحات:", edit_description)
            layout.addRow(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_debt(self, debt_id, person_id, amount, account_id,
                  shamsi_due_date, is_credit, has_payment,
                  show_in_dashboard, description, dialog):
        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ نمی‌تواند خالی باشد!")
            return

        due_date = None
        if shamsi_due_date:
            if not is_valid_shamsi_date(shamsi_due_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return
            try:
                due_date = shamsi_to_gregorian(shamsi_due_date)
                if not due_date:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
            except ValueError:
                QMessageBox.warning(self, "خطا", "مبلغ یا تاریخ نامعتبر است!")
                return

        try:
            # دریافت اطلاعات بدهی قبلی برای حذف اثر آن
            self.db_manager.execute(
                "SELECT amount, account_id, is_credit FROM debts WHERE id = ?",
                (debt_id,))
            old_debt = self.db_manager.fetchone()
            if not old_debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            old_amount, old_account_id, old_is_credit = old_debt
            old_is_credit = int(old_is_credit or 0)

            # اگر پولی رد و بدل نشده، حسابی ذخیره نمی‌شود
            account_id_to_save = account_id if has_payment else None

            # اعمال اثر جدید در صورت نیاز + بررسی موجودی برای خروج پول
            if has_payment and account_id:
                if is_credit:  # طلب من: پول از حساب خارج می‌شود
                    self.db_manager.execute(
                        "SELECT balance FROM accounts WHERE id = ?", (account_id,))
                    balance = self.db_manager.fetchone()[0]
                    if balance < amount:
                        QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                        return

            # حذف اثر قبلی از حساب قبلی (به‌صورت متقارن)
            if old_account_id:
                if old_is_credit:
                    # طلب قدیمی: موقع ثبت، پول از حساب کم شده بود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (old_amount, old_account_id))
                else:
                    # بدهی قدیمی: موقع ثبت، پول به حساب اضافه شده بود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (old_amount, old_account_id))

            # اعمال اثر جدید
            if has_payment and account_id:
                if is_credit:  # طلب من: پول به شخص داده می‌شود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (amount, account_id))
                else:  # بدهی من: پول از شخص دریافت می‌شود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (amount, account_id))

            # ذخیره در دیتابیس
            # نکته: دکمه ویرایش فقط برای موارد «در جریان» نمایش داده می‌شود؛
            # با این حال settled_date برای اطمینان پاک می‌شود تا وضعیت
            # «تسویه‌شده» و «تاریخ تسویه» همیشه هماهنگ بمانند.
            self.db_manager.execute(
                "UPDATE debts SET person_id = ?, amount = ?, account_id = ?, "
                "due_date = ?, is_paid = 0, show_in_dashboard = ?, "
                "description = ?, is_credit = ?, settled_date = NULL "
                "WHERE id = ?",
                (person_id, amount, account_id_to_save, due_date,
                 1 if show_in_dashboard else 0, description,
                 1 if is_credit else 0, debt_id)
            )
            self.db_manager.commit()
            self.load_debts()
            self.data_changed.emit()
            dialog.accept()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت ویرایش شد!")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def delete_debt(self, debt_id):
        try:
            # دریافت اطلاعات بدهی برای معکوس کردن اثر آن
            self.db_manager.execute(
                "SELECT account_id, amount, paid_amount, is_credit "
                "FROM debts WHERE id = ?",
                (debt_id,)
            )
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            account_id, amount, paid_amount, is_credit = debt
            is_credit = int(is_credit or 0)

            # تأیید حذف از کاربر
            reply = QMessageBox.question(
                self, "تأیید حذف",
                "آیا مطمئن هستید که می‌خواهید این بدهی/طلب را حذف کنید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # معکوس کردن اثر خالص بدهی روی موجودی حساب
            if account_id:
                remaining_amount = (amount or 0) - (paid_amount or 0)
                if is_credit:
                    # طلب: موقع ثبت پول کم شده بود → اثر خالص برگردانده می‌شود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (remaining_amount, account_id))
                else:
                    # بدهی: موقع ثبت پول اضافه شده بود
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (remaining_amount, account_id))

            # حذف بدهی/طلب از دیتابیس
            self.db_manager.execute(
                "DELETE FROM debts WHERE id = ?", (debt_id,))
            self.db_manager.commit()

            # به‌روزرسانی جدول و اطلاع به پنجره اصلی
            self.load_debts()
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت حذف شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ------------------------------------------------------------------ #
    # تسویه بدهی/طلب
    # ------------------------------------------------------------------ #
    def settle_debt(self, debt_id):
        try:
            self.db_manager.execute(
                "SELECT d.person_id, d.amount, d.paid_amount, d.account_id, "
                "p.name, d.is_credit "
                "FROM debts d LEFT JOIN persons p ON d.person_id = p.id "
                "WHERE d.id = ?",
                (debt_id,)
            )
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            person_id, amount, paid_amount, account_id, person_name, is_credit = debt
            remaining_amount = (amount or 0) - (paid_amount or 0)

            dialog = QDialog(self)
            dialog.setWindowTitle(f"تسویه بدهی/طلب با {person_name or '-'}")
            dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            # نکته: رنگ صریح لیبل‌ها برای جلوگیری از نامرئی شدن در تم تاریک ویندوز
            dialog.setStyleSheet(f"""
                QDialog {{ background-color: {PAGE_BG};
                          font-family: 'Vazir', 'Arial'; }}
                QLabel {{ color: {TEXT_DARK}; font-size: 13px; font-weight: bold; }}
                QCheckBox {{ color: {TEXT_DARK}; font-size: 13px; }}
            """)
            layout = QFormLayout(dialog)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(9)

            # نوع بدهی/طلب
            type_label_text = "طلب من (دریافت پول)" if is_credit else "بدهی من (پرداخت پول)"
            type_label = QLabel(type_label_text)
            type_label.setStyleSheet(
                f"color: {GREEN if is_credit else RED};")
            layout.addRow("نوع:", type_label)

            # مبلغ باقی‌مانده
            remaining_label = QLabel(f"{format_amount(remaining_amount)} ریال")
            layout.addRow("مبلغ باقی‌مانده:", remaining_label)

            # چک‌باکس انتقال وجه
            settle_has_payment_checkbox = QCheckBox("انتقال وجه انجام می‌شود؟")
            settle_has_payment_checkbox.setChecked(account_id is not None)
            layout.addRow("", settle_has_payment_checkbox)

            # ورودی مبلغ پرداخت‌شده
            settle_payment_input = NumberInput()
            settle_payment_input.setPlaceholderText("مبلغ پرداخت‌شده (اختیاری)")
            if account_id is not None and remaining_amount > 0:
                settle_payment_input.setText(str(int(remaining_amount)))
            layout.addRow("مبلغ پرداخت‌شده:", settle_payment_input)

            # انتخاب حساب
            settle_account_combo = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                settle_account_combo.addItem(display_text, acc_id)
            if account_id:
                for i in range(settle_account_combo.count()):
                    if settle_account_combo.itemData(i) == account_id:
                        settle_account_combo.setCurrentIndex(i)
                        break
            layout.addRow("حساب مرتبط:", settle_account_combo)

            # تاریخ تسویه (نسخه ۲.۳) — تاریخ واقعی پرداخت
            # اگر پول در روزی غیر از امروز رد و بدل شده، همان روز انتخاب شود؛
            # تراکنش مرتبط نیز با همین تاریخ ثبت می‌شود تا گزارش‌های ماهانه
            # دقیق بمانند (مثلاً پرداخت روز ۱۰ که روز ۱۵ در سیستم ثبت می‌شود).
            settle_date_edit = QLineEdit(
                gregorian_to_shamsi(datetime.now().date().strftime("%Y-%m-%d")))
            settle_date_edit.setReadOnly(True)
            settle_date_edit.setPlaceholderText("1404/02/13")
            settle_date_edit.mousePressEvent = \
                lambda event: self._popup_calendar(settle_date_edit)
            settle_date_edit.setStyleSheet(
                "QLineEdit { color: #166534; font-weight: bold; }")
            layout.addRow("تاریخ تسویه (شمسی):", settle_date_edit)

            settle_date_hint = QLabel(
                "💡 اگر پرداخت در تاریخ دیگری انجام شده، تاریخ واقعی را انتخاب کنید.")
            settle_date_hint.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 12px; font-weight: normal;")
            settle_date_hint.setWordWrap(True)
            layout.addRow("", settle_date_hint)

            # کنترل فعال/غیرفعال بودن فیلدها بر اساس چک‌باکس
            def toggle_settle_fields(state):
                is_checked = (state == Qt.CheckState.Checked.value)
                settle_payment_input.setEnabled(is_checked)
                settle_account_combo.setEnabled(is_checked)

                if not is_checked:
                    settle_payment_input.clear()
                    settle_account_combo.setCurrentIndex(0)
                else:
                    settle_payment_input.setText(str(int(remaining_amount)))

            settle_has_payment_checkbox.stateChanged.connect(toggle_settle_fields)
            toggle_settle_fields(settle_has_payment_checkbox.checkState().value)

            confirm_btn = QPushButton("✅ تأیید تسویه")
            confirm_btn.setObjectName("primaryBtn")
            confirm_btn.setMinimumHeight(40)
            confirm_btn.clicked.connect(lambda: self.confirm_partial_payment(
                debt_id,
                settle_payment_input.get_raw_value(),
                settle_account_combo.currentData(),
                is_credit,
                settle_has_payment_checkbox.isChecked(),
                settle_date_edit.text().strip(),
                dialog
            ))
            layout.addRow(confirm_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def confirm_partial_payment(self, debt_id, payment_amount, account_id,
                                is_credit, has_transfer_checked,
                                shamsi_settle_date, dialog):
        # اعتبارسنجی تاریخ تسویه (تاریخ واقعی پرداخت)
        settle_date = datetime.now().strftime("%Y-%m-%d")
        if shamsi_settle_date:
            if not is_valid_shamsi_date(shamsi_settle_date):
                QMessageBox.warning(
                    dialog, "خطا", "فرمت تاریخ تسویه باید به صورت 1404/02/19 باشد!")
                return
            settle_date = shamsi_to_gregorian(shamsi_settle_date)
            if not settle_date:
                QMessageBox.warning(dialog, "خطا", "تاریخ تسویه نامعتبر است!")
                return

        try:
            self.db_manager.execute(
                "SELECT amount, paid_amount, person_id FROM debts WHERE id = ?",
                (debt_id,))
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                self.db_manager.rollback()
                return
            total_debt_amount, current_paid_amount, person_id = debt
            remaining_amount = total_debt_amount - current_paid_amount

            if has_transfer_checked:
                if payment_amount is None or payment_amount <= 0:
                    QMessageBox.warning(self, "خطا", "مبلغ پرداخت‌شده باید بیشتر از صفر باشد!")
                    self.db_manager.rollback()
                    return
                if not account_id:
                    QMessageBox.warning(self, "خطا", "لطفاً حساب مرتبط را انتخاب کنید!")
                    self.db_manager.rollback()
                    return
                if payment_amount > remaining_amount:
                    QMessageBox.warning(self, "خطا", "مبلغ پرداخت‌شده نمی‌تواند بیشتر از مبلغ باقی‌مانده باشد!")
                    self.db_manager.rollback()
                    return

                # بررسی موجودی حساب برای بدهی (پرداخت پول)
                if not is_credit:
                    self.db_manager.execute(
                        "SELECT balance FROM accounts WHERE id = ?", (account_id,))
                    balance = self.db_manager.fetchone()[0]
                    if balance < payment_amount:
                        QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                        self.db_manager.rollback()
                        return

                # به‌روزرسانی paid_amount
                new_paid_amount = current_paid_amount + payment_amount

                # به‌روزرسانی موجودی حساب
                if is_credit:  # طلب من: دریافت پول (اضافه به حساب)
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (payment_amount, account_id))
                else:  # بدهی من: پرداخت پول (کم از حساب)
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (payment_amount, account_id))

                # ثبت تراکنش مرتبط
                category_name = "تسویه طلب" if is_credit else "تسویه بدهی"
                category_type = "income" if is_credit else "expense"
                self.db_manager.execute(
                    "SELECT id FROM categories WHERE name = ? AND type = ?",
                    (category_name, category_type))
                category_id_from_db = self.db_manager.fetchone()
                if not category_id_from_db:
                    QMessageBox.critical(
                        self, "خطا",
                        f"خطای سیستمی: دسته‌بندی '{category_name}' یافت نشد. "
                        "لطفاً برنامه را مجدداً راه‌اندازی کنید یا با پشتیبانی تماس بگیرید.")
                    self.db_manager.rollback()
                    return
                category_id_from_db = category_id_from_db[0]

                today_gregorian = settle_date  # تاریخ واقعی تسویه (نسخه ۲.۳)

                self.db_manager.execute(
                    "SELECT name FROM persons WHERE id = ?", (person_id,))
                person_row = self.db_manager.fetchone()
                person_name = person_row[0] if person_row else "-"

                description = (f"تسویه {format_amount(payment_amount)} از "
                               f"{'طلب' if is_credit else 'بدهی'} با شخص {person_name}")
                self.db_manager.execute(
                    "INSERT INTO transactions (account_id, person_id, category_id, "
                    "amount, date, description) VALUES (?, ?, ?, ?, ?, ?)",
                    (account_id, person_id, category_id_from_db,
                     payment_amount, today_gregorian, description))

            else:
                payment_amount = remaining_amount
                new_paid_amount = current_paid_amount + payment_amount
                account_id = None

            is_paid = 1 if new_paid_amount >= total_debt_amount else 0

            # تاریخ تسویه فقط برای تسویه کامل ذخیره می‌شود (تاریخ آخرین/
            # نهایی پرداخت)؛ در پرداخت جزئی مقدار قبلی حفظ می‌شود.
            self.db_manager.execute(
                "UPDATE debts SET paid_amount = ?, is_paid = ?, account_id = ?, "
                "settled_date = ? WHERE id = ?",
                (new_paid_amount, is_paid, account_id,
                 settle_date if is_paid else None, debt_id))

            self.db_manager.commit()
            self.load_debts()
            self.data_changed.emit()
            dialog.accept()
            QMessageBox.information(
                self, "موفق",
                f"پرداخت به مبلغ {format_amount(payment_amount)} ریال در تاریخ "
                f"{gregorian_to_shamsi(settle_date)} ثبت شد! "
                f"وضعیت تسویه: {'کامل' if is_paid else 'جزئی'}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback()

    # ================================================================== #
    # جستجو و گزارش‌گیری (تاریخ‌ها اختیاری)
    # ================================================================== #
    def search_debts(self):
        try:
            debt_type = self.debt_search_type.currentText()
            person_id = self.debt_search_person.currentData()
            amount = self.debt_search_amount.get_raw_value()
            start_date = self.debt_search_start_date.text().strip()
            end_date = self.debt_search_end_date.text().strip()

            clauses = []
            params = []

            # تاریخ‌ها اختیاری‌اند؛ فقط در صورت پر بودن اعمال می‌شوند
            if start_date:
                if not is_valid_shamsi_date(start_date):
                    QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                    return
                start_g = shamsi_to_gregorian(start_date)
                if not start_g:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
                clauses.append("d.due_date >= ?")
                params.append(start_g)

            if end_date:
                if not is_valid_shamsi_date(end_date):
                    QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                    return
                end_g = shamsi_to_gregorian(end_date)
                if not end_g:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
                clauses.append("d.due_date <= ?")
                params.append(end_g)

            if start_date and end_date and start_date > end_date:
                QMessageBox.warning(self, "خطا", "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد!")
                return

            if debt_type == "بدهی":
                clauses.append("d.is_credit = 0")
            elif debt_type == "طلب":
                clauses.append("d.is_credit = 1")

            if person_id:
                clauses.append("d.person_id = ?")
                params.append(person_id)
            if amount:
                clauses.append("d.amount = ?")
                params.append(amount)

            query = (
                "SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, "
                "d.is_paid, COALESCE(a.name, '-'), d.is_credit, d.description, "
                "d.settled_date "
                "FROM debts d "
                "LEFT JOIN persons p ON d.person_id = p.id "
                "LEFT JOIN accounts a ON d.account_id = a.id "
            )
            if clauses:
                query += "WHERE " + " AND ".join(clauses)
            query += " ORDER BY d.id DESC"

            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()
            self.show_debt_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ------------------------------------------------------------------ #
    # محاسبه جمع‌های گزارش (برای خلاصه انتهای گزارش)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _report_totals(results):
        """جمع باقی‌مانده بدهی/طلب از نتایج گزارش.

        خروجی: (جمع بدهی باقی‌مانده، جمع طلب باقی‌مانده،
                تعداد بدهی‌ها، تعداد طلب‌ها)
        """
        debt_total = credit_total = 0.0
        debt_count = credit_count = 0
        for (_id, _person, amount, paid, _due, is_paid,
             _account, is_credit, _desc, _settled) in results:
            if is_paid:
                continue
            remaining = (amount or 0) - (paid or 0)
            if is_credit:
                credit_total += remaining
                credit_count += 1
            else:
                debt_total += remaining
                debt_count += 1
        return debt_total, credit_total, debt_count, credit_count

    def show_debt_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش بدهی/طلب")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.resize(900, 640)
        # نکته: رنگ صریح لیبل‌ها برای جلوگیری از نامرئی شدن در تم تاریک ویندوز
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {PAGE_BG};
                      font-family: 'Vazir', 'Arial'; }}
            QLabel {{ color: {TEXT_DARK}; font-size: 13px; }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        dialog.setLayout(layout)

        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels(
            ["شناسه", "شخص", "مبلغ", "پرداخت‌شده", "سررسید",
             "وضعیت", "تاریخ تسویه", "حساب", "نوع", "توضیحات"])
        self._style_table(table, stretch_column=9)
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

        self.debt_report_current_page = 1
        self.debt_report_results = results
        self.debt_report_total_pages = (
            len(results) + self.debt_report_per_page - 1
        ) // self.debt_report_per_page
        if self.debt_report_total_pages == 0:
            self.debt_report_total_pages = 1

        self.update_debt_report_table(table)

        layout.addWidget(table, 1)

        # ---- خلاصه وضعیت (انتهای گزارش) ----
        summary_frame = QFrame()
        summary_frame.setStyleSheet(
            f"QFrame {{ background-color: {SOFT_SLATE};"
            f" border-radius: 10px; border: 1px solid {CARD_BORDER}; }}")
        summary_lay = QVBoxLayout(summary_frame)
        summary_lay.setContentsMargins(14, 10, 14, 10)
        summary_lay.setSpacing(4)

        debt_total, credit_total, debt_count, credit_count = \
            self._report_totals(results)

        person_id = self.debt_search_person.currentData()
        if person_id:
            person_name = self.debt_search_person.currentText()
            header = QLabel(f"👤 خلاصه وضعیت {person_name}:")
            header.setStyleSheet(
                f"color: {TEXT_DARK}; font-size: 13px; font-weight: bold;")
            summary_lay.addWidget(header)

            net = credit_total - debt_total
            if net > 0:
                result_text = (f"نتیجه خالص: این شخص "
                               f"{format_amount(net)} ریال به شما بدهکار است")
                result_color = GREEN
            elif net < 0:
                result_text = (f"نتیجه خالص: شما {format_amount(-net)} ریال "
                               f"به این شخص بدهکارید")
                result_color = RED
            else:
                result_text = "نتیجه خالص: تسویه"
                result_color = SLATE

            summary_lay.addWidget(QLabel(
                f"<span style='color:{RED};'><b>جمع بدهی باقی‌مانده شما به این شخص: "
                f"{format_amount(debt_total)} ریال</b></span>"
                f" <span style='color:{TEXT_MUTED};'>({debt_count} مورد)</span>"))
            summary_lay.addWidget(QLabel(
                f"<span style='color:{GREEN};'><b>جمع طلب باقی‌مانده شما از این شخص: "
                f"{format_amount(credit_total)} ریال</b></span>"
                f" <span style='color:{TEXT_MUTED};'>({credit_count} مورد)</span>"))
            result_label = QLabel(
                f"<span style='color:{result_color};'><b>{result_text}</b></span>")
            summary_lay.addWidget(result_label)
        else:
            header = QLabel("📊 خلاصه وضعیت کل گزارش:")
            header.setStyleSheet(
                f"color: {TEXT_DARK}; font-size: 13px; font-weight: bold;")
            summary_lay.addWidget(header)
            summary_lay.addWidget(QLabel(
                f"<span style='color:{RED};'><b>جمع بدهی‌های باقی‌مانده: "
                f"{format_amount(debt_total)} ریال</b></span>"
                f" <span style='color:{TEXT_MUTED};'>({debt_count} مورد)</span>"))
            summary_lay.addWidget(QLabel(
                f"<span style='color:{GREEN};'><b>جمع طلب‌های باقی‌مانده: "
                f"{format_amount(credit_total)} ریال</b></span>"
                f" <span style='color:{TEXT_MUTED};'>({credit_count} مورد)</span>"))
            summary_lay.addWidget(QLabel(
                f"<span style='color:{TEXT_MUTED};'>تعداد کل موارد گزارش: "
                f"{len(results)}</span>"))

        layout.addWidget(summary_frame)

        # ---- صفحه‌بندی ----
        pagination_layout = QHBoxLayout()
        prev_btn = QPushButton("صفحه قبل")
        prev_btn.setObjectName("pageBtn")
        next_btn = QPushButton("صفحه بعد")
        next_btn.setObjectName("pageBtn")
        page_label = QLabel(
            f"صفحه {self.debt_report_current_page} از {self.debt_report_total_pages}")
        page_label.setObjectName("pageLabel")
        prev_btn.clicked.connect(
            lambda: self.prev_debt_report_page(table, page_label))
        next_btn.clicked.connect(
            lambda: self.next_debt_report_page(table, page_label))
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
            self.parent_window.export_report(
                results, "debts", self._search_date_range_text())

    def _search_date_range_text(self):
        """متن بازه تاریخ جستجو برای درج در سربرگ خروجی‌ها."""
        start = self.debt_search_start_date.text().strip()
        end = self.debt_search_end_date.text().strip()
        if start and end:
            return f"از {start} تا {end}"
        if start:
            return f"از {start} به بعد"
        if end:
            return f"تا {end}"
        return "همه تاریخ‌ها"

    def update_debt_report_table(self, table):
        start = (self.debt_report_current_page - 1) * self.debt_report_per_page
        end = start + self.debt_report_per_page
        page_results = self.debt_report_results[start:end]
        table.setRowCount(len(page_results))
        for row, (id, person, amount, paid, due_date, is_paid,
                  account, is_credit, description, settled_date) in \
                enumerate(page_results):
            is_credit = int(is_credit or 0)
            type_color = QColor(GREEN if is_credit else RED)

            id_item = QTableWidgetItem(str(id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setForeground(QColor(TEXT_MUTED))

            person_item = QTableWidgetItem(person or "-")
            person_item.setForeground(QColor(TEXT_DARK))

            amount_item = QTableWidgetItem(format_amount(amount))
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            amount_item.setForeground(QColor(TEXT_DARK))

            paid_item = QTableWidgetItem(format_amount(paid))
            paid_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            paid_item.setForeground(QColor(TEXT_MUTED))

            due_item = QTableWidgetItem(
                gregorian_to_shamsi(due_date) if due_date else "-")
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            due_item.setForeground(QColor(SLATE))

            if is_paid:
                status_text, status_color = "تسویه‌شده", QColor(TEXT_MUTED)
            else:
                status_text, status_color = "در جریان", QColor(AMBER)
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(status_color)

            # تاریخ تسویه (نسخه ۲.۳) — برای موارد قدیمی «—»
            settled_item = QTableWidgetItem(
                gregorian_to_shamsi(settled_date) if settled_date else "—")
            settled_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            settled_item.setForeground(QColor(TEXT_MUTED))

            account_item = QTableWidgetItem(account or "-")
            account_item.setForeground(QColor(TEXT_MUTED))

            type_item = QTableWidgetItem("طلب" if is_credit else "بدهی")
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            type_font = type_item.font()
            type_font.setBold(True)
            type_item.setFont(type_font)
            type_item.setForeground(type_color)

            desc_item = QTableWidgetItem(description or "-")
            desc_item.setForeground(QColor(TEXT_MUTED))

            for column, item in enumerate([
                    id_item, person_item, amount_item, paid_item, due_item,
                    status_item, settled_item, account_item, type_item,
                    desc_item]):
                table.setItem(row, column, item)

        # ---- ردیف «جمع کل» در انتهای صفحه آخر ----
        if page_results and end >= len(self.debt_report_results):
            self._append_report_totals_row(table)

    def _append_report_totals_row(self, table):
        """افزودن ردیف جمع کل (مبلغ/پرداخت‌شده/باقی‌مانده) به جدول گزارش."""
        results = self.debt_report_results
        total_amount = sum((r[2] or 0) for r in results)
        total_paid = sum((r[3] or 0) for r in results)
        remaining = total_amount - total_paid

        row = table.rowCount()
        table.insertRow(row)

        cells = [
            "", "جمع کل",
            format_amount(total_amount),
            format_amount(total_paid),
            "",
            f"{len(results)} مورد",
            "",
            "", "",
            f"باقی‌مانده: {format_amount(remaining)}",
        ]
        for col, text in enumerate(cells):
            item = QTableWidgetItem(text)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setBackground(QColor(SOFT_SLATE))
            item.setForeground(QColor(TEXT_DARK))
            if col in (2, 3, 5):
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, col, item)

    def prev_debt_report_page(self, table, page_label):
        if self.debt_report_current_page > 1:
            self.debt_report_current_page -= 1
            self.update_debt_report_table(table)
            page_label.setText(
                f"صفحه {self.debt_report_current_page} از {self.debt_report_total_pages}")

    def next_debt_report_page(self, table, page_label):
        if self.debt_report_current_page < self.debt_report_total_pages:
            self.debt_report_current_page += 1
            self.update_debt_report_table(table)
            page_label.setText(
                f"صفحه {self.debt_report_current_page} از {self.debt_report_total_pages}")
