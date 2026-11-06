# -*- coding: utf-8 -*-
"""تب وام‌ها — ماژول مستقل (جدا شده از main.py)

ساختار صفحه (راست‌به‌چپ):
    ┌────────────────┬───────────────────────────────────┐
    │  ستون راست      │  ستون چپ                          │
    │  (اسکرول)       │  ┌─────────────────────────────┐  │
    │  ┌────────────┐ │  │ خلاصه وضعیت (۳ کارت)         │  │
    │  │ ثبت وام    │ │  ├─────────────────────────────┤  │
    │  └────────────┘ │  │ فیلترها (نوع/وضعیت/جستجو)    │  │
    │                │  ├─────────────────────────────┤  │
    │                │  │ لیست وام‌ها (جدید → قدیم)     │  │
    │                │  │ + نشان «✓ تسویه‌شده»          │  │
    │                │  │ + صفحه‌بندی                    │  │
    │                │  └─────────────────────────────┘  │
    └────────────────┴───────────────────────────────────┘
    جداکننده دو ستون با QSplitter قابل درگ است.

- وام‌هایی که کامل تسویه شده‌اند (همه اقساط پرداخت یا رسیدن مبلغ
  پرداخت‌شده به مبلغ کل) با نشان سبز «✓ تسویه‌شده» و پس‌زمینه
  روشن‌سبز مشخص می‌شوند.
- پس از هر تغییر داده (ثبت/ویرایش/تسویه قسط) سیگنال data_changed
  منتشر می‌شود تا main.py حساب‌ها و داشبورد را تازه‌سازی کند.
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
import jdatetime

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با داشبورد، حساب‌ها، تراکنش‌ها و بدهی/طلب)
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
ROW_SETTLED_BG = "#f0fdf4"   # پس‌زمینه ردیف‌های تسویه‌شده

# عبارت SQL برای تشخیص وام تسویه‌شده:
# ۱) اگر وام ردیف قسط دارد: هیچ قسط پرداخت‌نشده نمانده باشد؛
# ۲) یا همه اقساط پرداخت شده باشند؛
# ۳) یا مبلغ پرداختی به مبلغ کل رسیده باشد (وام‌های بدون ردیف قسط).
SETTLED_SQL = (
    "((EXISTS (SELECT 1 FROM loan_installments li WHERE li.loan_id = l.id) "
    "AND COALESCE((SELECT SUM(li.amount) FROM loan_installments li "
    "              WHERE li.loan_id = l.id AND li.is_paid = 0), 0) <= 0) "
    "OR (COALESCE(l.installments_total, 0) > 0 "
    "AND COALESCE(l.installments_paid, 0) >= COALESCE(l.installments_total, 0)) "
    "OR (COALESCE(l.total_amount, 0) > 0 "
    "AND COALESCE(l.paid_amount, 0) >= COALESCE(l.total_amount, 0)))"
)

# محاسبهٔ مقادیر مؤثر هر وام بر اساس جدول اقساط (منبع حقیقت).
# اگر وام ردیف قسط دارد، «کل بازپرداخت» و «پرداخت‌شده» و «باقی‌مانده»
# از خود اقساط ساخته می‌شوند (جمع اقساط شامل سود است و ممکن است از اصل
# وام بیشتر باشد). برای وام‌های بدون ردیف قسط، مقادیر ستون‌های جدول
# loans استفاده می‌شوند.
LOAN_TOTAL_SQL = (
    "CASE WHEN EXISTS (SELECT 1 FROM loan_installments li "
    "                   WHERE li.loan_id = l.id) "
    "THEN COALESCE((SELECT SUM(li.amount) FROM loan_installments li "
    "               WHERE li.loan_id = l.id), 0) "
    "ELSE COALESCE(l.total_amount, 0) END"
)
LOAN_PAID_SQL = (
    "CASE WHEN EXISTS (SELECT 1 FROM loan_installments li "
    "                   WHERE li.loan_id = l.id) "
    "THEN COALESCE((SELECT SUM(li.amount) FROM loan_installments li "
    "               WHERE li.loan_id = l.id AND li.is_paid = 1), 0) "
    "ELSE COALESCE(l.paid_amount, 0) END"
)
LOAN_REMAINING_SQL = (
    "CASE WHEN EXISTS (SELECT 1 FROM loan_installments li "
    "                   WHERE li.loan_id = l.id) "
    "THEN COALESCE((SELECT SUM(li.amount) FROM loan_installments li "
    "               WHERE li.loan_id = l.id AND li.is_paid = 0), 0) "
    "ELSE MAX(COALESCE(l.total_amount, 0) - COALESCE(l.paid_amount, 0), 0) END"
)

# نگاشت عدد ماه → متن فارسی فاصله اقساط
_MONTH_WORDS = {
    1: "هر یک ماه", 2: "هر دو ماه", 3: "هر سه ماه",
    4: "هر چهار ماه", 5: "هر پنج ماه", 6: "هر شش ماه",
    12: "هر یک سال",
}

# نگاشت کلمه فارسی → عدد (برای تبدیل «هر دو ماه» → 2)
_WORD_TO_NUM = {
    "یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6,
}


def _interval_label(interval):
    """متن فارسی فاصله اقساط بر اساس مقدار ذخیره‌شده."""
    if not interval:
        return "-"
    interval = int(interval)
    if interval in _MONTH_WORDS:
        return _MONTH_WORDS[interval]
    return f"هر {format_number(interval)} روز"


def _parse_interval(interval_type_text, custom_value):
    """تبدیل متن فاصله اقساط به مقدار عددی.

    خروجی: (مقدار یا None، پیام خطا یا None)
    مقادیر 1 تا 12 = تعداد ماه، بقیه = تعداد روز (فاصله دلخواه).
    """
    if interval_type_text == "فاصله دلخواه":
        if not custom_value or custom_value <= 0:
            return None, "برای فاصله دلخواه، باید یک عدد مثبت وارد کنید!"
        return custom_value, None

    parts = interval_type_text.split(" ")
    if len(parts) >= 2 and parts[1] in _WORD_TO_NUM:
        num = _WORD_TO_NUM[parts[1]]
        if "ماه" in interval_type_text:
            return num, None
        if "سال" in interval_type_text:
            return num * 12, None
    return None, "نوع فاصله اقساط نامعتبر است. لطفاً یک گزینه معتبر انتخاب کنید."


class LoansTab(QWidget):
    """تب وام‌ها: ثبت، ویرایش، اقساط، تسویه، فیلتر و لیست."""

    # پس از هر ثبت/ویرایش/تسویه منتشر می‌شود
    data_changed = pyqtSignal()

    # ------------------------------------------------------------------ #
    # استایل کلی تب
    # ------------------------------------------------------------------ #
    STYLESHEET = f"""
    LoansTab {{
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
    /* رنگ پایه برای همه لیبل‌ها؛ در ویندوز با تم تاریک، پالت سیستم
       متن لیبل‌های بی‌رنگ را سفید می‌کند — این قانون صریح از آن
       جلوگیری می‌کند. */
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

    /* دکمه‌های ریز داخل جدول */
    QPushButton#rowBtn {{
        background-color: #ffffff;
        color: {SLATE};
        border: 1px solid #cbd5e1;
        border-radius: 7px;
        padding: 5px 12px;
        font-size: 11px;
        font-weight: bold;
    }}
    QPushButton#rowBtn:hover {{
        background-color: {SOFT_SLATE};
        border-color: {SLATE};
    }}
    QPushButton#rowBtnGreen {{
        background-color: {SOFT_GREEN};
        color: #166534;
        border: 1px solid #86efac;
        border-radius: 7px;
        padding: 5px 12px;
        font-size: 11px;
        font-weight: bold;
    }}
    QPushButton#rowBtnGreen:hover {{
        background-color: #bbf7d0;
        border-color: {GREEN};
    }}

    /* ---------- جدول‌ها ---------- */
    QTableWidget#loansTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#loansTable QHeaderView::section {{
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

    # استایل مشترک دیالوگ‌ها (ویندوز با تم تاریک متن لیبل‌های بی‌رنگ
    # را سفید می‌کند — رنگ همه ویجت‌های متنی صریح است.)
    DIALOG_STYLE = f"""
        QDialog {{
            background-color: {PAGE_BG};
            font-family: 'Vazir', 'Arial';
        }}
        QLabel {{
            color: {TEXT_DARK};
            font-size: 13px;
            font-weight: bold;
        }}
        QCheckBox {{
            color: {TEXT_DARK};
            font-size: 13px;
        }}
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
        QLabel#dialogTitle {{
            font-size: 15px;
            font-weight: bold;
            color: {TEXT_DARK};
        }}
        QLabel#dialogHint {{
            font-size: 12px;
            font-weight: normal;
            color: {TEXT_MUTED};
        }}
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
        QPushButton#rowBtn {{
            background-color: #ffffff;
            color: {SLATE};
            border: 1px solid #cbd5e1;
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
        }}
        QPushButton#rowBtn:hover {{
            background-color: {SOFT_SLATE};
            border-color: {SLATE};
        }}
        QPushButton#rowBtnGreen {{
            background-color: {SOFT_GREEN};
            color: #166534;
            border: 1px solid #86efac;
            border-radius: 7px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: bold;
        }}
        QPushButton#rowBtnGreen:hover {{
            background-color: #bbf7d0;
            border-color: {GREEN};
        }}
        QTableWidget#dialogTable {{
            background-color: #ffffff;
            alternate-background-color: #f8fafc;
            border: 1px solid {CARD_BORDER};
            border-radius: 10px;
            gridline-color: #eef2f7;
            selection-background-color: #dcfce7;
            selection-color: #14532d;
            font-size: 12px;
        }}
        QTableWidget#dialogTable QHeaderView::section {{
            background-color: #f1f5f9;
            color: #334155;
            font-weight: bold;
            font-size: 11px;
            padding: 6px 5px;
            border: none;
            border-bottom: 2px solid #e2e8f0;
        }}
        QFrame#dialogSummaryCard {{
            background-color: #ffffff;
            border: 1px solid {CARD_BORDER};
            border-radius: 12px;
        }}
    """

    # ================================================================== #
    # ساختار کلی
    # ================================================================== #
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent  # ارجاع به پنجره اصلی (برای export_report)

        # وضعیت صفحه‌بندی
        self.loans_current_page = 1
        self.loans_per_page = 50
        self.loans_total_pages = 1

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.STYLESHEET)

        self.setup_ui()
        self.reload_accounts()
        self.load_loans()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(0)

        # جداکننده افقی قابل درگ:
        # در RTL ویجت اول سمت «راست» قرار می‌گیرد؛
        # بنابراین پنل فرم (راست) قبل از پنل لیست (چپ) اضافه می‌شود.
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
    # پنل راست: فرم ثبت وام
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
        container_layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _build_entry_card(self):
        """کارت ثبت وام جدید"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🏦")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("ثبت وام جدید")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        # فرم
        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.loan_type = QComboBox()
        self.loan_type.addItems(["وام گرفته‌شده", "وام داده‌شده"])

        self.loan_title = QLineEdit()
        self.loan_title.setPlaceholderText("مثلاً: وام مسکن بانک ملی")

        self.loan_amount = NumberInput()
        self.loan_amount.setPlaceholderText("مبلغ به ریال")

        self.loan_interest = NumberInput()
        self.loan_interest.setPlaceholderText("اختیاری — مثلاً 20")

        self.loan_account = QComboBox()

        self.loan_add_to_account_checkbox = QCheckBox(
            "مبلغ وام به حساب اضافه/کم شود؟")
        self.loan_add_to_account_checkbox.setChecked(True)

        self.loan_start_date = QLineEdit()
        today = datetime.now().date()
        self.loan_start_date.setText(
            gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.loan_start_date.setPlaceholderText("1404/02/13")
        self.loan_start_date.setReadOnly(True)
        self.loan_start_date.mousePressEvent = \
            lambda event: self._popup_calendar(self.loan_start_date)
        self.loan_start_date.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        self.loan_installments_total = NumberInput()
        self.loan_installments_total.setPlaceholderText("مثلاً: 12")

        self.loan_installments_paid = NumberInput()
        self.loan_installments_paid.setPlaceholderText("اختیاری — پیش‌فرض 0")

        self.loan_installment_amount = NumberInput()
        self.loan_installment_amount.setPlaceholderText("مبلغ به ریال")

        self.loan_interval_type_combo = QComboBox()
        self.loan_interval_type_combo.addItems([
            "هر یک ماه", "هر دو ماه", "هر سه ماه", "هر چهار ماه",
            "هر پنج ماه", "هر شش ماه", "هر یک سال", "فاصله دلخواه",
        ])
        self.loan_interval_type_combo.currentTextChanged.connect(
            self._toggle_custom_interval_field)

        self.loan_custom_interval_input = NumberInput()
        self.loan_custom_interval_input.setPlaceholderText(
            "فاصله دلخواه (بر حسب روز)")
        self.loan_custom_interval_input.setVisible(False)

        form.addRow("نوع وام:", self.loan_type)
        form.addRow("عنوان وام:", self.loan_title)
        form.addRow("مبلغ کل:", self.loan_amount)
        form.addRow("نرخ سود (%):", self.loan_interest)
        form.addRow("حساب مرتبط:", self.loan_account)
        form.addRow("", self.loan_add_to_account_checkbox)
        form.addRow("تاریخ دریافت وام:", self.loan_start_date)
        form.addRow("تعداد اقساط کل:", self.loan_installments_total)
        form.addRow("تعداد اقساط پرداخت‌شده:", self.loan_installments_paid)
        form.addRow("مبلغ هر قسط:", self.loan_installment_amount)
        form.addRow("فاصله اقساط:", self.loan_interval_type_combo)
        form.addRow("", self.loan_custom_interval_input)
        lay.addLayout(form)

        add_loan_btn = QPushButton("✅ ثبت وام")
        add_loan_btn.setObjectName("primaryBtn")
        add_loan_btn.setMinimumHeight(42)
        add_loan_btn.clicked.connect(self.add_loan)
        lay.addWidget(add_loan_btn)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # پنل چپ: خلاصه + فیلترها + لیست وام‌ها
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
        icon = QLabel("📋")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("لیست وام‌ها")
        title.setObjectName("panelTitle")
        self.loans_count_chip = QLabel("0 مورد")
        self.loans_count_chip.setObjectName("chip")
        self.loans_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.loans_count_chip)
        lay.addLayout(header_row)

        # ---- خلاصه وضعیت کلی ----
        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        summary_row.addWidget(self._build_summary_chip(
            "💳", "باقی‌مانده وام‌های گرفته‌شده",
            SOFT_RED, RED, "summary_taken"), 1)
        summary_row.addWidget(self._build_summary_chip(
            "🤝", "باقی‌مانده وام‌های داده‌شده",
            SOFT_GREEN, GREEN, "summary_given"), 1)
        summary_row.addWidget(self._build_summary_chip(
            "✅", "وام‌های تسویه‌شده",
            SOFT_SLATE, SLATE, "summary_settled"), 1)
        lay.addLayout(summary_row)

        # ---- نوار فیلترها ----
        filters_card = QFrame()
        filters_card.setStyleSheet(
            f"QFrame {{ background-color: {SOFT_SLATE};"
            f" border-radius: 10px; }}")
        filters_lay = QVBoxLayout(filters_card)
        filters_lay.setContentsMargins(12, 10, 12, 10)
        filters_lay.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(10)

        search_box = QVBoxLayout()
        search_box.setSpacing(3)
        search_label = QLabel("جستجو:")
        search_label.setObjectName("formLabel")
        self.filter_search = QLineEdit()
        self.filter_search.setPlaceholderText("بر اساس عنوان وام...")
        self.filter_search.textChanged.connect(self.apply_filters)
        search_box.addWidget(search_label)
        search_box.addWidget(self.filter_search)

        type_box = QVBoxLayout()
        type_box.setSpacing(3)
        type_label = QLabel("نوع:")
        type_label.setObjectName("formLabel")
        self.filter_type = QComboBox()
        self.filter_type.addItems(["همه", "وام گرفته‌شده", "وام داده‌شده"])
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

        row1.addLayout(search_box, 3)
        row1.addLayout(type_box, 2)
        row1.addLayout(status_box, 2)
        filters_lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        apply_btn = QPushButton("اعمال فیلتر")
        apply_btn.setObjectName("primaryBtn")
        apply_btn.clicked.connect(self.apply_filters)
        clear_btn = QPushButton("پاک کردن")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self.clear_filters)
        row2.addStretch(1)
        row2.addWidget(apply_btn)
        row2.addWidget(clear_btn)
        filters_lay.addLayout(row2)

        lay.addWidget(filters_card)

        # ---- جدول وام‌ها ----
        # نکته RTL: ستون «عملیات» عمداً اولین ستون (سمت راست) است تا
        # در پنجره‌های باریک، دکمه‌ها همیشه داخل دید بمانند.
        self.loans_table = QTableWidget()
        self.loans_table.setObjectName("loansTable")
        self.loans_table.setColumnCount(12)
        self.loans_table.setHorizontalHeaderLabels(
            ["عملیات", "وضعیت", "نوع", "عنوان", "کل بازپرداخت", "پرداخت‌شده",
             "باقی‌مانده", "سود", "شروع", "اقساط", "مبلغ قسط", "فاصله"])
        self._style_table(self.loans_table, stretch_column=3)
        self.loans_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)
        self.loans_table.setColumnWidth(0, 246)
        lay.addWidget(self.loans_table, 1)

        # حالت خالی
        self.loans_empty_label = QLabel("📝 وامی برای نمایش وجود ندارد")
        self.loans_empty_label.setObjectName("emptyLabel")
        self.loans_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loans_empty_label.setVisible(False)
        lay.addWidget(self.loans_empty_label, 1)

        # ---- صفحه‌بندی ----
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(8)
        self.loans_prev_btn = QPushButton("صفحه قبل")
        self.loans_prev_btn.setObjectName("pageBtn")
        self.loans_next_btn = QPushButton("صفحه بعد")
        self.loans_next_btn.setObjectName("pageBtn")
        self.loans_page_label = QLabel("صفحه 1")
        self.loans_page_label.setObjectName("pageLabel")
        self.loans_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loans_prev_btn.clicked.connect(self.prev_loans_page)
        self.loans_next_btn.clicked.connect(self.next_loans_page)

        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.loans_prev_btn)
        pagination_layout.addWidget(self.loans_page_label)
        pagination_layout.addWidget(self.loans_next_btn)
        pagination_layout.addStretch(1)
        lay.addLayout(pagination_layout)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_summary_chip(self, icon_text, title, soft_bg, value_color,
                            attr_prefix):
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
        value_label = QLabel("0")
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

    def _toggle_custom_interval_field(self):
        """نمایش یا پنهان کردن فیلد وارد کردن فاصله دلخواه."""
        if self.loan_interval_type_combo.currentText() == "فاصله دلخواه":
            self.loan_custom_interval_input.setVisible(True)
        else:
            self.loan_custom_interval_input.setVisible(False)
            self.loan_custom_interval_input.clear()

    @staticmethod
    def _is_settled(total_amount, paid_amount, installments_total,
                    installments_paid):
        """وام تسویه‌شده یعنی همه اقساط پرداخت شده یا مبلغ پرداختی
        به مبلغ کل رسیده باشد."""
        if installments_total and \
                (installments_paid or 0) >= installments_total:
            return True
        if total_amount and (paid_amount or 0) >= total_amount:
            return True
        return False

    @staticmethod
    def _generate_installment_dates(start_date_gregorian,
                                    installments_total,
                                    installment_interval_value):
        """تولید تاریخ سررسید شمسی اقساط (منطق مشترک ثبت/ویرایش).

        فاصله‌های 1 تا 12 = تعداد ماه، بقیه = تعداد روز.
        """
        start_jdate = jdatetime.date.fromgregorian(
            date=datetime.strptime(start_date_gregorian, "%Y-%m-%d"))
        is_custom_interval = installment_interval_value not in \
            (1, 2, 3, 4, 5, 6, 12)

        due_dates = []
        for i in range(installments_total):
            if is_custom_interval:
                due_jdate = start_jdate + jdatetime.timedelta(
                    days=installment_interval_value * (i + 1))
            else:
                months_to_add = installment_interval_value * (i + 1)
                new_year = start_jdate.year
                new_month = start_jdate.month + months_to_add
                while new_month > 12:
                    new_month -= 12
                    new_year += 1
                try:
                    due_jdate = jdatetime.date(
                        new_year, new_month, start_jdate.day)
                except ValueError:
                    days_in_target_month = jdatetime.date(
                        new_year, new_month, 1).days_in_month
                    due_jdate = jdatetime.date(
                        new_year, new_month, days_in_target_month)
            due_dates.append(due_jdate.strftime("%Y/%m/%d"))
        return due_dates

    # ------------------------------------------------------------------ #
    # تازه‌سازی
    # ------------------------------------------------------------------ #
    def reload_accounts(self):
        """پر کردن کامبوباکس حساب مرتبط در فرم ثبت وام."""
        try:
            self.db_manager.execute(
                "SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        self.loan_account.blockSignals(True)
        self.loan_account.clear()
        for acc_id, name, balance in accounts:
            display_text = \
                f"{name} (موجودی: {format_number(balance)} ریال)"
            self.loan_account.addItem(display_text, acc_id)
        self.loan_account.blockSignals(False)

    def refresh(self):
        """تازه‌سازی کامل تب (لیست، خلاصه و کامبوباکس حساب‌ها)."""
        self.reload_accounts()
        self.load_loans()

    # ------------------------------------------------------------------ #
    # فیلترها و بارگذاری لیست (جدید → قدیم)
    # ------------------------------------------------------------------ #
    def apply_filters(self):
        self.loans_current_page = 1
        self.load_loans()

    def clear_filters(self):
        self.filter_search.clear()
        self.filter_type.setCurrentIndex(0)
        self.filter_status.setCurrentIndex(0)
        self.apply_filters()

    def load_loans(self):
        """بارگذاری وام‌های صفحه فعلی با فیلترهای فعال (جدیدترین اول)."""
        try:
            clauses, params = [], []

            type_text = self.filter_type.currentText()
            if type_text == "وام گرفته‌شده":
                clauses.append("l.type = 'taken'")
            elif type_text == "وام داده‌شده":
                clauses.append("l.type = 'given'")

            status_text = self.filter_status.currentText()
            if status_text == "در جریان":
                clauses.append(f"NOT ({SETTLED_SQL})")
            elif status_text == "تسویه‌شده":
                clauses.append(SETTLED_SQL)

            search_text = self.filter_search.text().strip()
            if search_text:
                clauses.append("l.bank_name LIKE ?")
                params.append(f"%{search_text}%")

            where_sql = ""
            if clauses:
                where_sql = "WHERE " + " AND ".join(clauses)

            # ۱. تعداد کل موارد منطبق بر فیلتر
            self.db_manager.execute(
                f"SELECT COUNT(*) FROM loans l {where_sql}", tuple(params))
            total_loans = self.db_manager.fetchone()[0]
            self.loans_total_pages = max(
                1, (total_loans + self.loans_per_page - 1)
                // self.loans_per_page)
            if self.loans_current_page > self.loans_total_pages:
                self.loans_current_page = self.loans_total_pages

            # ۲. واکشی موارد صفحه فعلی — جدیدترین در صفحه اول
            # مقادیر پولی از جدول اقساط ساخته می‌شوند (منبع حقیقت) تا
            # وام تسویه‌شده هرگز باقی‌مانده نشان ندهد و وام سوددار
            # باقی‌ماندهٔ منفی پیدا نکند.
            offset = (self.loans_current_page - 1) * self.loans_per_page
            self.db_manager.execute(
                f"SELECT l.id, l.type, l.bank_name, l.total_amount, "
                f"l.paid_amount, l.interest_rate, l.start_date, "
                f"l.account_id, l.installments_total, "
                f"l.installments_paid, l.installment_amount, "
                f"l.installment_interval, a.name, "
                f"({LOAN_TOTAL_SQL}), ({LOAN_PAID_SQL}), "
                f"({LOAN_REMAINING_SQL}), "
                f"EXISTS (SELECT 1 FROM loan_installments li "
                f"        WHERE li.loan_id = l.id) "
                f"FROM loans l "
                f"LEFT JOIN accounts a ON l.account_id = a.id "
                f"{where_sql} "
                f"ORDER BY l.id DESC LIMIT ? OFFSET ?",
                tuple(params) + (self.loans_per_page, offset))
            loans = self.db_manager.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        self.loans_count_chip.setText(f"{total_loans} مورد")
        self._update_summary()

        # حالت خالی
        if not loans:
            self.loans_table.setRowCount(0)
            self.loans_table.setVisible(False)
            self.loans_empty_label.setVisible(True)
        else:
            self.loans_table.setVisible(True)
            self.loans_empty_label.setVisible(False)

            self.loans_table.setRowCount(len(loans))
            for row, (loan_id, loan_type, bank_name, total_amount,
                      paid_amount, interest_rate, start_date, account_id,
                      installments_total, installments_paid,
                      installment_amount, installment_interval,
                      account_name, eff_total, eff_paid, eff_remaining,
                      has_installments) in enumerate(loans):

                # مقادیر مؤثر: برای وام دارای قسط، از خود اقساط محاسبه
                # شده‌اند (شامل سود)؛ وگرنه از ستون‌های جدول loans.
                settled = (
                    (has_installments and (eff_remaining or 0) <= 0)
                    or self._is_settled(
                        total_amount, paid_amount, installments_total,
                        installments_paid))
                remaining = max(eff_remaining or 0, 0)

                # پس‌زمینه ردیف تسویه‌شده روشن‌سبز است
                row_bg = QColor(ROW_SETTLED_BG) if settled else None

                # ---- ستون عملیات (ویرایش + اقساط + خروجی) ----
                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                edit_btn = QPushButton("ویرایش")
                edit_btn.setObjectName("rowBtn")
                edit_btn.clicked.connect(
                    lambda checked, l_id=loan_id: self.edit_loan(l_id))

                view_btn = QPushButton("اقساط")
                view_btn.setObjectName("rowBtn")
                view_btn.clicked.connect(
                    lambda checked, l_id=loan_id: self.view_installments(l_id))

                export_btn = QPushButton("خروجی")
                export_btn.setObjectName("rowBtn")
                export_btn.clicked.connect(
                    lambda checked, l_id=loan_id:
                        self.export_single_loan_report(l_id))

                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(view_btn)
                actions_layout.addWidget(export_btn)
                self.loans_table.setCellWidget(row, 0, actions)

                # ---- ستون وضعیت ----
                if settled:
                    status_text, status_color = "✓ تسویه‌شده", QColor(GREEN)
                else:
                    status_text, status_color = "در جریان", QColor(AMBER)
                status_item = QTableWidgetItem(status_text)
                status_font = status_item.font()
                status_font.setBold(True)
                status_item.setFont(status_font)
                status_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter)
                status_item.setForeground(status_color)
                if row_bg:
                    status_item.setBackground(row_bg)
                self.loans_table.setItem(row, 1, status_item)

                # ---- ستون نوع ----
                is_taken = (loan_type == "taken")
                type_item = QTableWidgetItem(
                    "گرفته‌شده" if is_taken else "داده‌شده")
                type_font = type_item.font()
                type_font.setBold(True)
                type_item.setFont(type_font)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                type_item.setForeground(
                    QColor(RED if is_taken else GREEN))
                if row_bg:
                    type_item.setBackground(row_bg)
                self.loans_table.setItem(row, 2, type_item)

                # ---- ستون عنوان ----
                title_item = QTableWidgetItem(bank_name or "-")
                title_font = title_item.font()
                title_font.setBold(True)
                title_item.setFont(title_font)
                title_item.setForeground(QColor(TEXT_DARK))
                if row_bg:
                    title_item.setBackground(row_bg)
                title_item.setToolTip(
                    f"حساب: {account_name or '-'}")
                self.loans_table.setItem(row, 3, title_item)

                # ---- ستون کل بازپرداخت ----
                # برای وام دارای قسط، جمع واقعی اقساط (اصل + سود) است؛
                # برای وام بدون قسط همان مبلغ کل.
                amount_item = QTableWidgetItem(format_amount(eff_total))
                amount_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter)
                amount_item.setForeground(QColor(TEXT_DARK))
                if row_bg:
                    amount_item.setBackground(row_bg)
                self.loans_table.setItem(row, 4, amount_item)

                # ---- ستون پرداخت‌شده ----
                paid_item = QTableWidgetItem(format_amount(eff_paid))
                paid_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter)
                paid_item.setForeground(QColor(TEXT_MUTED))
                if row_bg:
                    paid_item.setBackground(row_bg)
                self.loans_table.setItem(row, 5, paid_item)

                # ---- ستون باقی‌مانده ----
                remaining_item = QTableWidgetItem(format_amount(remaining))
                remaining_font = remaining_item.font()
                remaining_font.setBold(True)
                remaining_item.setFont(remaining_font)
                remaining_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter)
                remaining_item.setForeground(
                    QColor(TEXT_MUTED if settled
                           else (RED if is_taken else GREEN)))
                if row_bg:
                    remaining_item.setBackground(row_bg)
                self.loans_table.setItem(row, 6, remaining_item)

                # ---- ستون سود ----
                interest_item = QTableWidgetItem(
                    f"{interest_rate or 0}%")
                interest_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter)
                interest_item.setForeground(QColor(TEXT_MUTED))
                if row_bg:
                    interest_item.setBackground(row_bg)
                self.loans_table.setItem(row, 7, interest_item)

                # ---- ستون شروع ----
                start_item = QTableWidgetItem(
                    gregorian_to_shamsi(start_date) or "-")
                start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                start_item.setForeground(QColor(TEXT_DARK))
                if row_bg:
                    start_item.setBackground(row_bg)
                self.loans_table.setItem(row, 8, start_item)

                # ---- ستون اقساط (X از Y) ----
                installments_item = QTableWidgetItem(
                    f"{installments_paid or 0} از "
                    f"{installments_total or 0}")
                installments_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter)
                installments_item.setForeground(QColor(
                    GREEN if settled else SLATE))
                if row_bg:
                    installments_item.setBackground(row_bg)
                self.loans_table.setItem(row, 9, installments_item)

                # ---- ستون مبلغ قسط ----
                installment_item = QTableWidgetItem(
                    format_amount(installment_amount)
                    if installment_amount is not None else "0")
                installment_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft
                    | Qt.AlignmentFlag.AlignVCenter)
                installment_item.setForeground(QColor(TEXT_MUTED))
                if row_bg:
                    installment_item.setBackground(row_bg)
                self.loans_table.setItem(row, 10, installment_item)

                # ---- ستون فاصله ----
                interval_item = QTableWidgetItem(
                    _interval_label(installment_interval))
                interval_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                interval_item.setForeground(QColor(TEXT_MUTED))
                if row_bg:
                    interval_item.setBackground(row_bg)
                self.loans_table.setItem(row, 11, interval_item)

        self.loans_page_label.setText(
            f"صفحه {self.loans_current_page} از {self.loans_total_pages}")
        self.loans_prev_btn.setEnabled(self.loans_current_page > 1)
        self.loans_next_btn.setEnabled(
            self.loans_current_page < self.loans_total_pages)

    def _update_summary(self):
        """به‌روزرسانی کارت‌های خلاصه (بر اساس کل داده‌ها).

        باقی‌ماندهٔ هر وام از اقساط پرداخت‌نشده محاسبه می‌شود (منبع
        حقیقت)؛ وام‌های بدون ردیف قسط از ستون‌های جدول loans.
        """
        try:
            self.db_manager.execute(
                f"SELECT COALESCE(SUM({LOAN_REMAINING_SQL}), 0) "
                f"FROM loans l WHERE l.type = 'taken' "
                f"AND NOT ({SETTLED_SQL})")
            remaining_taken = self.db_manager.fetchone()[0]

            self.db_manager.execute(
                f"SELECT COALESCE(SUM({LOAN_REMAINING_SQL}), 0) "
                f"FROM loans l WHERE l.type = 'given' "
                f"AND NOT ({SETTLED_SQL})")
            remaining_given = self.db_manager.fetchone()[0]

            self.db_manager.execute(
                f"SELECT COUNT(*) FROM loans l WHERE {SETTLED_SQL}")
            settled_count = self.db_manager.fetchone()[0]
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        self.summary_taken_value.setText(
            f"{format_amount(remaining_taken)} ریال")
        self.summary_given_value.setText(
            f"{format_amount(remaining_given)} ریال")
        self.summary_settled_value.setText(f"{settled_count} وام")

    def prev_loans_page(self):
        if self.loans_current_page > 1:
            self.loans_current_page -= 1
            self.load_loans()

    def next_loans_page(self):
        if self.loans_current_page < self.loans_total_pages:
            self.loans_current_page += 1
            self.load_loans()

    # ------------------------------------------------------------------ #
    # ثبت وام جدید
    # ------------------------------------------------------------------ #
    def add_loan(self):
        loan_type = "taken" \
            if self.loan_type.currentText() == "وام گرفته‌شده" else "given"
        loan_title = self.loan_title.text()
        total_amount = self.loan_amount.get_raw_value()
        interest_rate = self.loan_interest.get_raw_value() or 0
        account_id = self.loan_account.currentData()
        start_date_shamsi = self.loan_start_date.text()
        installments_total = self.loan_installments_total.get_raw_value()
        installments_paid = \
            self.loan_installments_paid.get_raw_value() or 0
        installment_amount = self.loan_installment_amount.get_raw_value()

        installment_interval_value, error = _parse_interval(
            self.loan_interval_type_combo.currentText(),
            self.loan_custom_interval_input.get_raw_value())
        if error:
            QMessageBox.warning(self, "خطا", error)
            return

        add_to_account = self.loan_add_to_account_checkbox.isChecked()

        if not loan_title:
            QMessageBox.warning(self, "خطا", "عنوان وام نمی‌تواند خالی باشد!")
            return
        if not total_amount:
            QMessageBox.warning(self, "خطا", "مبلغ وام نمی‌تواند خالی باشد!")
            return
        if not account_id:
            QMessageBox.warning(self, "خطا", "لطفاً حساب مرتبط را انتخاب کنید!")
            return
        if not installments_total:
            QMessageBox.warning(
                self, "خطا", "تعداد اقساط نمی‌تواند خالی باشد!")
            return
        if not installment_amount:
            QMessageBox.warning(self, "خطا", "مبلغ قسط نمی‌تواند خالی باشد!")
            return
        if not is_valid_shamsi_date(start_date_shamsi):
            QMessageBox.warning(
                self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        if installments_paid > installments_total:
            QMessageBox.warning(
                self, "خطا",
                "تعداد اقساط پرداخت‌شده نمی‌تواند بیشتر از کل اقساط باشد!")
            return

        try:
            start_date_gregorian = shamsi_to_gregorian(start_date_shamsi)
            if not start_date_gregorian:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            try:
                datetime.strptime(start_date_gregorian, "%Y-%m-%d")
            except ValueError:
                QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است!")
                return

            if add_to_account:
                if loan_type == "taken":
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? "
                        "WHERE id = ?", (total_amount, account_id))
                else:
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? "
                        "WHERE id = ?", (total_amount, account_id))

            self.db_manager.execute(
                """
                INSERT INTO loans (type, bank_name, total_amount,
                                paid_amount, interest_rate, start_date,
                                account_id, installments_total,
                                installments_paid, installment_amount,
                                installment_interval)
                VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
                """,
                (loan_type, loan_title, total_amount, interest_rate,
                 start_date_gregorian, account_id, installments_total,
                 installments_paid, installment_amount,
                 installment_interval_value))
            loan_id = self.db_manager.cursor.lastrowid

            due_dates = self._generate_installment_dates(
                start_date_gregorian, installments_total,
                installment_interval_value)
            for i, due_date_shamsi in enumerate(due_dates):
                due_date_gregorian = shamsi_to_gregorian(due_date_shamsi)
                is_paid = 1 if i < installments_paid else 0
                self.db_manager.execute(
                    "INSERT INTO loan_installments "
                    "(loan_id, amount, due_date, is_paid) "
                    "VALUES (?, ?, ?, ?)",
                    (loan_id, installment_amount, due_date_gregorian,
                     is_paid))

            # همگام‌سازی paid_amount با اقساط پرداخت‌شده (رفع باگ:
            # ثبت وام با اقساط پرداخت‌شده، paid_amount را صفر می‌گذاشت
            # و باقی‌ماندهٔ وام تسویه‌شده به‌اشتباه نمایش داده می‌شد).
            self.db_manager.execute(
                """
                UPDATE loans SET paid_amount = COALESCE((
                    SELECT SUM(amount) FROM loan_installments
                    WHERE loan_id = ? AND is_paid = 1), 0)
                WHERE id = ?
                """,
                (loan_id, loan_id))

            self.db_manager.commit()

            # پاک‌سازی فرم (تاریخ به امروز برمی‌گردد)
            self.loan_title.clear()
            self.loan_amount.clear()
            self.loan_interest.clear()
            self.loan_installments_total.clear()
            self.loan_installments_paid.clear()
            self.loan_installment_amount.clear()
            self.loan_custom_interval_input.clear()
            today = datetime.now().date()
            self.loan_start_date.setText(
                gregorian_to_shamsi(today.strftime("%Y-%m-%d")))

            self.refresh()
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "وام با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback()

    # ------------------------------------------------------------------ #
    # ویرایش وام
    # ------------------------------------------------------------------ #
    def edit_loan(self, loan_id):
        try:
            self.db_manager.execute(
                """
                SELECT type, bank_name, total_amount, paid_amount,
                    interest_rate, start_date, account_id,
                    installments_total, installments_paid,
                    installment_amount, installment_interval
                FROM loans WHERE id = ?
                """,
                (loan_id,))
            loan = self.db_manager.fetchone()
            if not loan:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                return
            (loan_type, bank_name, total_amount, paid_amount,
             interest_rate, start_date, account_id, installments_total,
             installments_paid, installment_amount,
             installment_interval) = loan
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش وام")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setStyleSheet(self.DIALOG_STYLE)

        outer = QVBoxLayout(dialog)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        header = QLabel("✏️ ویرایش وام")
        header.setObjectName("dialogTitle")
        outer.addWidget(header)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        edit_type = QComboBox()
        edit_type.addItems(["وام گرفته‌شده", "وام داده‌شده"])
        edit_type.setCurrentText(
            "وام گرفته‌شده" if loan_type == "taken" else "وام داده‌شده")

        edit_title = QLineEdit(bank_name)

        edit_amount = NumberInput()
        # ستون REAL است؛ بدون int() مقدار «123000000.0» در فیلد می‌افتاد
        edit_amount.setText(
            str(int(total_amount)) if total_amount else "")

        edit_interest = NumberInput()
        edit_interest.setText(
            str(int(interest_rate)) if interest_rate else "")

        edit_account = QComboBox()
        try:
            self.db_manager.execute(
                "SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
        except sqlite3.Error:
            accounts = []
        for acc_id, name, balance in accounts:
            display_text = \
                f"{name} (موجودی: {format_number(balance)} ریال)"
            edit_account.addItem(display_text, acc_id)
        if account_id:
            for index in range(edit_account.count()):
                if edit_account.itemData(index) == account_id:
                    edit_account.setCurrentIndex(index)
                    break

        edit_start_date = QLineEdit(
            gregorian_to_shamsi(start_date) if start_date else "")
        edit_start_date.setReadOnly(True)
        edit_start_date.setPlaceholderText("1404/02/13")
        edit_start_date.mousePressEvent = \
            lambda event: self._popup_calendar(edit_start_date)
        edit_start_date.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        edit_installments_total = NumberInput()
        edit_installments_total.setText(
            str(installments_total) if installments_total else "")

        edit_installments_paid = NumberInput()
        edit_installments_paid.setText(
            str(installments_paid) if installments_paid else "")

        edit_installment_amount = NumberInput()
        edit_installment_amount.setText(
            str(int(installment_amount)) if installment_amount else "")

        edit_interval_type_combo = QComboBox()
        edit_interval_type_combo.addItems([
            "هر یک ماه", "هر دو ماه", "هر سه ماه", "هر چهار ماه",
            "هر پنج ماه", "هر شش ماه", "هر یک سال", "فاصله دلخواه",
        ])

        edit_custom_interval_input = NumberInput()
        edit_custom_interval_input.setPlaceholderText(
            "فاصله دلخواه (بر حسب روز)")

        if installment_interval in (1, 2, 3, 4, 5, 6, 12):
            if installment_interval == 12:
                edit_interval_type_combo.setCurrentText("هر یک سال")
            else:
                edit_interval_type_combo.setCurrentText(
                    f"هر {installment_interval} ماه")
            edit_custom_interval_input.setVisible(False)
        else:
            edit_interval_type_combo.setCurrentText("فاصله دلخواه")
            edit_custom_interval_input.setText(
                str(installment_interval or ""))
            edit_custom_interval_input.setVisible(True)

        def toggle_edit_custom_interval_field(_text=None):
            if edit_interval_type_combo.currentText() == "فاصله دلخواه":
                edit_custom_interval_input.setVisible(True)
            else:
                edit_custom_interval_input.setVisible(False)
                edit_custom_interval_input.clear()

        edit_interval_type_combo.currentTextChanged.connect(
            toggle_edit_custom_interval_field)
        toggle_edit_custom_interval_field()

        edit_add_to_account_checkbox = QCheckBox(
            "مبلغ وام به حساب اضافه/کم شود؟")
        edit_add_to_account_checkbox.setChecked(True)

        form.addRow("نوع وام:", edit_type)
        form.addRow("عنوان وام:", edit_title)
        form.addRow("مبلغ کل:", edit_amount)
        form.addRow("نرخ سود (%):", edit_interest)
        form.addRow("حساب مرتبط:", edit_account)
        form.addRow("", edit_add_to_account_checkbox)
        form.addRow("تاریخ شروع (شمسی):", edit_start_date)
        form.addRow("تعداد اقساط کل:", edit_installments_total)
        form.addRow("تعداد اقساط پرداخت‌شده:", edit_installments_paid)
        form.addRow("مبلغ هر قسط:", edit_installment_amount)
        form.addRow("فاصله اقساط:", edit_interval_type_combo)
        form.addRow("", edit_custom_interval_input)
        outer.addLayout(form)

        def on_save():
            interval_value, error = _parse_interval(
                edit_interval_type_combo.currentText(),
                edit_custom_interval_input.get_raw_value())
            if error:
                QMessageBox.warning(dialog, "خطا", error)
                return
            self.save_loan(
                loan_id, edit_type.currentText(), edit_title.text(),
                edit_amount.get_raw_value(),
                edit_interest.get_raw_value() or 0,
                edit_account.currentData(), edit_start_date.text(),
                edit_installments_total.get_raw_value(),
                edit_installments_paid.get_raw_value() or 0,
                edit_installment_amount.get_raw_value(),
                interval_value,
                edit_add_to_account_checkbox.isChecked(), dialog)

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(42)
        save_btn.clicked.connect(on_save)
        outer.addWidget(save_btn)

        dialog.resize(440, 680)
        dialog.exec()

    def save_loan(self, loan_id, type_text, loan_title, total_amount,
                  interest_rate, account_id, start_date_shamsi,
                  installments_total, installments_paid,
                  installment_amount, installment_interval_value,
                  add_to_account_on_edit, dialog):
        # اعتبارسنجی‌ها
        if not loan_title:
            QMessageBox.warning(
                dialog, "خطا", "عنوان وام نمی‌تواند خالی باشد!")
            return
        if not total_amount:
            QMessageBox.warning(
                dialog, "خطا", "مبلغ وام نمی‌تواند خالی باشد!")
            return
        if not account_id:
            QMessageBox.warning(
                dialog, "خطا", "لطفاً حساب مرتبط را انتخاب کنید!")
            return
        if not installments_total:
            QMessageBox.warning(
                dialog, "خطا", "تعداد اقساط نمی‌تواند خالی باشد!")
            return
        if not installment_amount:
            QMessageBox.warning(
                dialog, "خطا", "مبلغ قسط نمی‌تواند خالی باشد!")
            return
        if not is_valid_shamsi_date(start_date_shamsi):
            QMessageBox.warning(
                dialog, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        if installments_paid > installments_total:
            QMessageBox.warning(
                dialog, "خطا",
                "تعداد اقساط پرداخت‌شده نمی‌تواند بیشتر از کل اقساط باشد!")
            return
        if installment_interval_value is None \
                or installment_interval_value <= 0:
            QMessageBox.warning(
                dialog, "خطا",
                "برای فاصله دلخواه، باید یک عدد مثبت وارد کنید!")
            return

        try:
            start_date_gregorian = \
                shamsi_to_gregorian(start_date_shamsi)
            if not start_date_gregorian:
                QMessageBox.warning(dialog, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            loan_type = "taken" if type_text == "وام گرفته‌شده" else "given"

            self.db_manager.execute(
                "SELECT type, total_amount, account_id FROM loans "
                "WHERE id = ?", (loan_id,))
            old_loan = self.db_manager.fetchone()
            if not old_loan:
                QMessageBox.warning(dialog, "خطا", "وام یافت نشد!")
                self.db_manager.rollback()
                return
            old_type, old_total_amount, old_account_id = old_loan

            # برگرداندن اثر وام قبلی روی حساب
            if old_account_id:
                if old_type == "taken":
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? "
                        "WHERE id = ?",
                        (old_total_amount, old_account_id))
                else:
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? "
                        "WHERE id = ?",
                        (old_total_amount, old_account_id))

            # اعمال اثر وام جدید روی حساب
            if add_to_account_on_edit:
                if loan_type == "taken":
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? "
                        "WHERE id = ?", (total_amount, account_id))
                else:
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? "
                        "WHERE id = ?", (total_amount, account_id))

            self.db_manager.execute(
                """
                UPDATE loans SET type = ?, bank_name = ?,
                                total_amount = ?, interest_rate = ?,
                                start_date = ?, account_id = ?,
                                installments_total = ?,
                                installments_paid = ?,
                                installment_amount = ?,
                                installment_interval = ?
                WHERE id = ?
                """,
                (loan_type, loan_title, total_amount, interest_rate,
                 start_date_gregorian, account_id, installments_total,
                 installments_paid, installment_amount,
                 installment_interval_value, loan_id))

            # بازسازی اقساط
            self.db_manager.execute(
                "DELETE FROM loan_installments WHERE loan_id = ?",
                (loan_id,))

            due_dates = self._generate_installment_dates(
                start_date_gregorian, installments_total,
                installment_interval_value)
            for i, due_date_shamsi in enumerate(due_dates):
                due_date_gregorian = \
                    shamsi_to_gregorian(due_date_shamsi)
                is_paid = 1 if i < installments_paid else 0
                self.db_manager.execute(
                    "INSERT INTO loan_installments "
                    "(loan_id, amount, due_date, is_paid) "
                    "VALUES (?, ?, ?, ?)",
                    (loan_id, installment_amount, due_date_gregorian,
                     is_paid))

            # همگام‌سازی paid_amount با اقساط بازسازی‌شده (رفع باگ:
            # ویرایش وام، paid_amount قدیمی را نگه می‌داشت و باقی‌ماندهٔ
            # وام تسویه‌شده اشتباه/منفی نمایش داده می‌شد).
            self.db_manager.execute(
                """
                UPDATE loans SET paid_amount = COALESCE((
                    SELECT SUM(amount) FROM loan_installments
                    WHERE loan_id = ? AND is_paid = 1), 0)
                WHERE id = ?
                """,
                (loan_id, loan_id))

            self.db_manager.commit()
            dialog.accept()
            self.refresh()
            self.data_changed.emit()
            QMessageBox.information(
                self, "موفق", "وام با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback()

    # ------------------------------------------------------------------ #
    # اقساط وام
    # ------------------------------------------------------------------ #
    def view_installments(self, loan_id):
        try:
            self.db_manager.execute(
                """
                SELECT bank_name, type, total_amount, paid_amount,
                    installments_total, installments_paid,
                    installment_amount
                FROM loans WHERE id = ?
                """,
                (loan_id,))
            loan = self.db_manager.fetchone()
            if not loan:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                return
            (bank_name, loan_type, total_amount, paid_amount,
             installments_total, installments_paid,
             installment_amount) = loan

            self.db_manager.execute(
                "SELECT id, amount, due_date, is_paid, paid_date "
                "FROM loan_installments WHERE loan_id = ? "
                "ORDER BY due_date",
                (loan_id,))
            installments = self.db_manager.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        # مقادیر مؤثر از خود اقساط (منبع حقیقت): وام تسویه‌شده هرگز
        # باقی‌مانده نشان نمی‌دهد و وام سوددار باقی‌ماندهٔ منفی نمی‌گیرد.
        if installments:
            eff_total = sum(a for _, a, _, _, _ in installments)
            eff_paid = sum(a for _, a, _, is_paid, _ in installments
                           if is_paid)
            eff_remaining = max(eff_total - eff_paid, 0)
            settled = (eff_total - eff_paid) <= 0
        else:
            eff_total = total_amount or 0
            eff_paid = paid_amount or 0
            eff_remaining = max(
                (total_amount or 0) - (paid_amount or 0), 0)
            settled = self._is_settled(
                total_amount, paid_amount, installments_total,
                installments_paid)
        today = datetime.now().date()

        dialog = QDialog(self)
        dialog.setWindowTitle("اقساط وام")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setStyleSheet(self.DIALOG_STYLE)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # ---- کارت خلاصه وام ----
        summary_card = QFrame()
        summary_card.setObjectName("dialogSummaryCard")
        summary_lay = QVBoxLayout(summary_card)
        summary_lay.setContentsMargins(14, 12, 14, 12)
        summary_lay.setSpacing(6)

        title_label = QLabel(f"🏦 {bank_name or '-'}")
        title_label.setObjectName("dialogTitle")
        summary_lay.addWidget(title_label)

        is_taken = (loan_type == "taken")
        info_label = QLabel(
            f"نوع: <b style='color:{RED if is_taken else GREEN};'>"
            f"{'گرفته‌شده' if is_taken else 'داده‌شده'}</b>"
            f" &nbsp;|&nbsp; کل بازپرداخت: <b>{format_amount(eff_total)}"
            f" ریال</b>"
            f" &nbsp;|&nbsp; پرداخت‌شده: <b>{format_amount(eff_paid)}"
            f" ریال</b>"
            f" &nbsp;|&nbsp; باقی‌مانده: <b>{format_amount(eff_remaining)}"
            f" ریال</b>"
            f" &nbsp;|&nbsp; اقساط: <b>{installments_paid or 0} از "
            f"{installments_total or 0}</b>"
            f" &nbsp;|&nbsp; وضعیت: <b style='color:"
            f"{GREEN if settled else AMBER};'>"
            f"{'✓ تسویه‌شده' if settled else 'در جریان'}</b>")
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setWordWrap(True)
        info_label.setObjectName("dialogHint")
        summary_lay.addWidget(info_label)
        layout.addWidget(summary_card)

        # ---- جدول اقساط ----
        table = QTableWidget()
        table.setObjectName("dialogTable")
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["#", "مبلغ", "سررسید", "تاریخ پرداخت", "وضعیت", "عملیات"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(False)

        table.setRowCount(len(installments))
        for row, (inst_id, amount, due_date, is_paid, paid_date) in \
                enumerate(installments):
            # شماره قسط
            number_item = QTableWidgetItem(str(row + 1))
            number_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter)
            number_item.setForeground(QColor(TEXT_MUTED))
            table.setItem(row, 0, number_item)

            # مبلغ
            amount_item = QTableWidgetItem(format_amount(amount))
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter)
            amount_item.setForeground(QColor(TEXT_DARK))
            table.setItem(row, 1, amount_item)

            # سررسید (رنگ‌بندی برای اقساط عقب‌افتاده)
            try:
                is_overdue = (not is_paid) and (
                    datetime.strptime(due_date, "%Y-%m-%d").date() < today)
            except (ValueError, TypeError):
                is_overdue = False

            due_item = QTableWidgetItem(
                gregorian_to_shamsi(due_date) or "-")
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_overdue:
                due_item.setForeground(QColor(RED))
                due_item.setToolTip("سررسید این قسط گذشته است")
            else:
                due_item.setForeground(QColor(TEXT_DARK))
            table.setItem(row, 2, due_item)

            # تاریخ پرداخت واقعی (نسخه ۲.۳) — اقساط قدیمی «—» نشان می‌دهند
            paid_date_item = QTableWidgetItem(
                gregorian_to_shamsi(paid_date) if paid_date else "—")
            paid_date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            paid_date_item.setForeground(
                QColor(TEXT_MUTED) if not paid_date else QColor(GREEN))
            table.setItem(row, 3, paid_date_item)

            # وضعیت
            if is_paid:
                status_text, status_color = "✓ پرداخت‌شده", QColor(GREEN)
            elif is_overdue:
                status_text, status_color = "سررسید گذشته", QColor(RED)
            else:
                status_text, status_color = "در جریان", QColor(AMBER)
            status_item = QTableWidgetItem(status_text)
            status_font = status_item.font()
            status_font.setBold(True)
            status_item.setFont(status_font)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(status_color)
            table.setItem(row, 4, status_item)

            # عملیات
            if not is_paid:
                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                edit_btn = QPushButton("ویرایش")
                edit_btn.setObjectName("rowBtn")
                edit_btn.clicked.connect(
                    lambda checked, inst_id=inst_id:
                        self.edit_installment(
                            inst_id, loan_id, dialog))

                settle_btn = QPushButton("تسویه")
                settle_btn.setObjectName("rowBtnGreen")
                settle_btn.clicked.connect(
                    lambda checked, inst_id=inst_id:
                        self.settle_installment(
                            inst_id, loan_id, dialog))

                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(settle_btn)
                table.setCellWidget(row, 5, actions)
            else:
                dash_item = QTableWidgetItem("—")
                dash_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                dash_item.setForeground(QColor(TEXT_MUTED))
                table.setItem(row, 5, dash_item)

        layout.addWidget(table, 1)
        dialog.resize(720, 560)
        dialog.exec()

    def edit_installment(self, installment_id, loan_id, parent_dialog):
        try:
            self.db_manager.execute(
                "SELECT amount, due_date FROM loan_installments "
                "WHERE id = ?",
                (installment_id,))
            installment = self.db_manager.fetchone()
            if not installment:
                QMessageBox.warning(self, "خطا", "قسط یافت نشد!")
                return
            amount, due_date = installment
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش قسط")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setStyleSheet(self.DIALOG_STYLE)

        layout = QFormLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)

        edit_amount = NumberInput()
        edit_amount.setText(str(int(amount)) if amount else "")
        edit_due_date = QLineEdit(gregorian_to_shamsi(due_date))
        edit_due_date.setReadOnly(True)
        edit_due_date.setPlaceholderText("1404/02/13")
        edit_due_date.mousePressEvent = \
            lambda event: self._popup_calendar(edit_due_date)
        edit_due_date.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(42)
        save_btn.clicked.connect(
            lambda: self.save_installment(
                installment_id, loan_id, edit_amount.get_raw_value(),
                edit_due_date.text(), dialog, parent_dialog))

        layout.addRow("مبلغ قسط:", edit_amount)
        layout.addRow("تاریخ سررسید (شمسی):", edit_due_date)
        layout.addRow(save_btn)
        dialog.exec()

    def save_installment(self, installment_id, loan_id, amount, due_date,
                         dialog, parent_dialog):
        if not amount:
            QMessageBox.warning(dialog, "خطا", "مبلغ قسط نمی‌تواند خالی باشد!")
            return
        if not is_valid_shamsi_date(due_date):
            QMessageBox.warning(
                dialog, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            date = shamsi_to_gregorian(due_date)
            if not date:
                QMessageBox.warning(dialog, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            self.db_manager.execute(
                "UPDATE loan_installments SET amount = ?, due_date = ? "
                "WHERE id = ?",
                (amount, date, installment_id))
            self.db_manager.commit()

            dialog.accept()
            parent_dialog.accept()  # بستن دیالوگ اصلی و باز کردن مجدد
            QMessageBox.information(
                self, "موفق", "قسط با موفقیت ویرایش شد!")
            self.view_installments(loan_id)  # باز کردن مجدد دیالوگ اقساط
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def settle_installment(self, installment_id, loan_id, parent_dialog):
        try:
            self.db_manager.execute(
                "SELECT amount, is_paid FROM loan_installments "
                "WHERE id = ?",
                (installment_id,))
            installment = self.db_manager.fetchone()
            if not installment:
                QMessageBox.warning(self, "خطا", "قسط یافت نشد!")
                return
            amount, is_paid = installment
            if is_paid:
                QMessageBox.warning(
                    self, "خطا", "این قسط قبلاً تسویه شده است!")
                return
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        # نوع وام جهت جهت‌گذاری صحیح گردش پول (نسخه ۲.۴):
        # وام گرفته‌شده → پرداخت قسط = برداشت از حساب
        # وام داده‌شده  → دریافت قسط = واریز به حساب
        is_taken = True
        try:
            self.db_manager.execute(
                "SELECT type FROM loans WHERE id = ?", (loan_id,))
            loan_row = self.db_manager.fetchone()
            if loan_row:
                is_taken = (loan_row[0] == "taken")
        except sqlite3.Error:
            pass

        dialog = QDialog(self)
        dialog.setWindowTitle("تسویه قسط")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setStyleSheet(self.DIALOG_STYLE)

        layout = QFormLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)

        amount_label = QLabel(
            f"مبلغ این قسط: {format_amount(amount)} ریال")
        account_combo = QComboBox()
        try:
            self.db_manager.execute(
                "SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
        except sqlite3.Error:
            accounts = []
        for acc_id, name, balance in accounts:
            display_text = \
                f"{name} (موجودی: {format_number(balance)} ریال)"
            account_combo.addItem(display_text, acc_id)

        # تاریخ پرداخت واقعی (نسخه ۲.۳) — اگر قسط در روزی غیر از امروز
        # پرداخت شده، تاریخ واقعی انتخاب شود تا سابقه دقیق بماند.
        settle_date_edit = QLineEdit(
            gregorian_to_shamsi(datetime.now().date().strftime("%Y-%m-%d")))
        settle_date_edit.setReadOnly(True)
        settle_date_edit.setPlaceholderText("1404/02/13")
        settle_date_edit.mousePressEvent = \
            lambda event: self._popup_calendar(settle_date_edit)
        settle_date_edit.setStyleSheet(
            "QLineEdit { color: #166534; font-weight: bold; }")

        settle_date_hint = QLabel(
            "💡 تاریخ واقعی پرداخت قسط را انتخاب کنید (پیش‌فرض: امروز). "
            "تراکنش مرتبط نیز با همین تاریخ ثبت می‌شود.")
        settle_date_hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; font-weight: normal;")
        settle_date_hint.setWordWrap(True)

        save_btn = QPushButton("✅ تسویه")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(42)
        save_btn.clicked.connect(
            lambda: self.confirm_settle_installment(
                installment_id, loan_id, amount,
                account_combo.currentData(),
                settle_date_edit.text().strip(),
                dialog, parent_dialog))

        account_label = "حساب برای برداشت:" if is_taken \
            else "حساب برای واریز:"
        layout.addRow(amount_label)
        layout.addRow(account_label, account_combo)
        layout.addRow("تاریخ پرداخت (شمسی):", settle_date_edit)
        layout.addRow("", settle_date_hint)
        layout.addRow(save_btn)
        dialog.exec()

    def confirm_settle_installment(self, installment_id, loan_id, amount,
                                   account_id, shamsi_settle_date,
                                   dialog, parent_dialog):
        # اعتبارسنجی تاریخ پرداخت واقعی قسط (نسخه ۲.۳)
        paid_date = datetime.now().strftime("%Y-%m-%d")
        if shamsi_settle_date:
            if not is_valid_shamsi_date(shamsi_settle_date):
                QMessageBox.warning(
                    dialog, "خطا",
                    "فرمت تاریخ پرداخت باید به صورت 1404/02/19 باشد!")
                return
            paid_date = shamsi_to_gregorian(shamsi_settle_date)
            if not paid_date:
                QMessageBox.warning(dialog, "خطا", "تاریخ پرداخت نامعتبر است!")
                return

        try:
            # اطلاعات وام (نوع + عنوان) برای جهت گردش پول و شرح تراکنش
            self.db_manager.execute(
                "SELECT type, bank_name FROM loans WHERE id = ?", (loan_id,))
            loan_row = self.db_manager.fetchone()
            if not loan_row:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                return
            loan_type, loan_title = loan_row
            is_taken = (loan_type == "taken")

            # شماره ترتیبی قسط برای شرح تراکنش
            self.db_manager.execute(
                """
                SELECT COUNT(*) FROM loan_installments
                WHERE loan_id = ? AND (
                    due_date < (SELECT due_date FROM loan_installments
                                WHERE id = ?)
                    OR (due_date = (SELECT due_date FROM loan_installments
                                    WHERE id = ?)
                        AND id <= ?))
                """,
                (loan_id, installment_id, installment_id, installment_id))
            count_row = self.db_manager.fetchone()
            installment_number = count_row[0] if count_row else 1

            # بررسی موجودی حساب (فقط برای وام گرفته‌شده — برداشت پول)
            self.db_manager.execute(
                "SELECT balance FROM accounts WHERE id = ?", (account_id,))
            row = self.db_manager.fetchone()
            if not row:
                QMessageBox.warning(self, "خطا", "حساب یافت نشد!")
                return
            balance = row[0]
            if is_taken and balance < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                return

            # به‌روزرسانی موجودی حساب
            # وام گرفته‌شده → پرداخت قسط (کم از حساب)
            # وام داده‌شده → دریافت قسط (اضافه به حساب)
            if is_taken:
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance - ? "
                    "WHERE id = ?", (amount, account_id))
            else:
                self.db_manager.execute(
                    "UPDATE accounts SET balance = balance + ? "
                    "WHERE id = ?", (amount, account_id))

            # ثبت تراکنش مرتبط (نسخه ۲.۴) — با تاریخ واقعی پرداخت قسط،
            # تا در تب تراکنش‌ها و گزارش‌ها دیده شود.
            category_name = "پرداخت قسط وام" if is_taken \
                else "دریافت قسط وام"
            category_type = "expense" if is_taken else "income"
            self.db_manager.execute(
                "SELECT id FROM categories WHERE name = ? AND type = ?",
                (category_name, category_type))
            category_row = self.db_manager.fetchone()
            if not category_row:
                QMessageBox.critical(
                    self, "خطا",
                    f"خطای سیستمی: دسته‌بندی '{category_name}' یافت نشد. "
                    "لطفاً برنامه را مجدداً راه‌اندازی کنید یا با پشتیبانی "
                    "تماس بگیرید.")
                self.db_manager.rollback()
                return
            category_id = category_row[0]

            action_word = "پرداخت" if is_taken else "دریافت"
            description = (
                f"{action_word} قسط {installment_number or 1} از وام "
                f"«{loan_title or '-'}» به مبلغ {format_amount(amount)} ریال")
            self.db_manager.execute(
                "INSERT INTO transactions (account_id, person_id, category_id, "
                "amount, date, description) VALUES (?, NULL, ?, ?, ?, ?)",
                (account_id, category_id, amount, paid_date, description))

            # علامت‌گذاری قسط به‌عنوان پرداخت‌شده + ثبت تاریخ واقعی پرداخت
            self.db_manager.execute(
                "UPDATE loan_installments SET is_paid = 1, paid_date = ? "
                "WHERE id = ?",
                (paid_date, installment_id))

            # به‌روزرسانی تعداد اقساط پرداخت‌شده و مبلغ پرداخت‌شده وام
            self.db_manager.execute(
                """
                UPDATE loans
                SET installments_paid = installments_paid + 1,
                    paid_amount = paid_amount + ?
                WHERE id = ?
                """,
                (amount, loan_id))

            self.db_manager.commit()
            dialog.accept()          # بستن دیالوگ تسویه
            parent_dialog.accept()   # بستن دیالوگ لیست اقساط
            self.refresh()
            self.data_changed.emit()
            QMessageBox.information(
                self, "موفق",
                f"قسط در تاریخ {gregorian_to_shamsi(paid_date)} "
                "با موفقیت تسویه شد!\n"
                f"یک تراکنش «{category_name}» نیز در تب تراکنش‌ها "
                "ثبت شد.")
            self.view_installments(loan_id)  # باز کردن مجدد لیست اقساط
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback()

    # ------------------------------------------------------------------ #
    # خروجی گزارش اقساط یک وام
    # ------------------------------------------------------------------ #
    def export_single_loan_report(self, loan_id):
        try:
            self.db_manager.execute(
                """
                SELECT id, amount, due_date, is_paid, paid_date
                FROM loan_installments WHERE loan_id = ?
                ORDER BY due_date
                """,
                (loan_id,))
            installments = self.db_manager.fetchall()

            # گرفتن اطلاعات کلی وام برای عنوان گزارش
            self.db_manager.execute(
                "SELECT bank_name, total_amount, type FROM loans "
                "WHERE id = ?", (loan_id,))
            loan_info = self.db_manager.fetchone()
            loan_title = loan_info[0] if loan_info else "وام"

            # پردازش داده‌ها برای خروجی
            processed_data = []
            for id, amount, due_date, is_paid, paid_date in installments:
                status_text = "پرداخت‌شده" if is_paid else "پرداخت‌نشده"
                processed_data.append(
                    (id, format_number(amount),
                     gregorian_to_shamsi(due_date),
                     gregorian_to_shamsi(paid_date) if paid_date else "-",
                     status_text))

            if self.parent_window is not None and \
                    hasattr(self.parent_window, 'export_report'):
                self.parent_window.export_report(
                    processed_data, "loan_installments_report")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
        except Exception as e:
            QMessageBox.critical(
                self, "خطا", f"خطای عمومی در تولید گزارش وام: {e}")
