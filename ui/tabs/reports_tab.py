# -*- coding: utf-8 -*-
"""
ui/tabs/reports_tab.py
======================
تب «گزارش‌ها» — ماژول مستقل و حرفه‌ای (جدا شده از main.py)

ساختار صفحه (راست‌به‌چپ):

    ┌────────────────────────────────────────────────────────────┐
    │  📊 مرکز گزارش‌ها          (عنوان + توضیح کوتاه)             │
    ├────────────────────────────────────────────────────────────┤
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
    │  │ گزارش کلی │  │ هزینه/   │  │ ماهانه   │  … ۹ کارت گزارش │
    │  │          │  │ درآمد    │  │ + نمودار │                  │
    │  └──────────┘  └──────────┘  └──────────┘                  │
    │         (اسکرول عمودی + شبکه ۳ ستونه)                       │
    ├────────────────────────────────────────────────────────────┤
    │  💡 نکته: همه خروجی‌ها با ردیف «جمع کل» ساخته می‌شوند        │
    └────────────────────────────────────────────────────────────┘

هر کارت یک دیالوگ پارامتر باز می‌کند (تاریخ‌ها اختیاری و
تک‌طرفه: فقط «از تاریخ» یا فقط «تا تاریخ» هم کار می‌کند) و پس از
تولید، گزارش در یک پنجره حرفه‌ای نمایش داده می‌شود:

    • چیپ‌های KPI (جمع‌های کلیدی رنگی)
    • جدول استایل‌دار با ردیف «جمع کل» در انتهای جدول
    • نمودار میله‌ای (برای گزارش ماهانه)
    • دکمه‌های مستقیم خروجی اکسل / CSV / PDF (با ردیف جمع کل)
    • دکمه باز کردن پوشه گزارش‌ها

خروجی‌ها از موتور مشترک core/report_exporter.py ساخته می‌شوند.
"""

import os
import sqlite3

import jdatetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, QLabel,
    QFrame, QLineEdit, QComboBox, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QScrollArea, QHeaderView,
    QGraphicsDropShadowEffect, QSizePolicy,
)

from ui.components.custom_widgets import PersianCalendarPopup
from core.utils import (
    format_amount, gregorian_to_shamsi, shamsi_to_gregorian,
    is_valid_shamsi_date,
)
from core import report_exporter

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با سایر تب‌ها)
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

PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


class ClickableFrame(QFrame):
    """کارت قابل کلیک (برای گالری گزارش‌ها)."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ReportsTab(QWidget):
    """تب گزارش‌ها: گالری گزارش‌های حرفه‌ای با فیلتر، KPI، نمودار و خروجی."""

    def __init__(self, db_manager, parent_window=None):
        super().__init__()
        self.db_manager = db_manager
        self.parent_window = parent_window
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # بدون این صفت، QWidget زیرکلاس‌شده پس‌زمینه استایل‌شیت را رسم نمی‌کند
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.STYLESHEET)
        self.setup_ui()

    # ================================================================== #
    # استایل
    # ================================================================== #
    STYLESHEET = f"""
    ReportsTab {{
        background-color: {PAGE_BG};
        font-family: 'Vazir', 'Arial';
    }}

    QLabel {{
        color: {TEXT_DARK};
    }}

    QFrame#pageHeaderCard {{
        background-color: #ffffff;
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
    }}
    QLabel#headerIcon {{
        background-color: {SOFT_GREEN};
        border-radius: 12px;
        font-size: 20px;
    }}
    QLabel#headerTitle {{
        color: {TEXT_DARK};
        font-size: 17px;
        font-weight: bold;
    }}
    QLabel#headerSubtitle {{
        color: {TEXT_MUTED};
        font-size: 12px;
    }}

    QFrame#reportCard {{
        background-color: #ffffff;
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
    }}
    QFrame#reportCard:hover {{
        border: 2px solid {GREEN};
        background-color: #fbfefc;
    }}
    QLabel#cardIcon {{
        border-radius: 11px;
        font-size: 17px;
    }}
    QLabel#cardTitle {{
        color: {TEXT_DARK};
        font-size: 13.5px;
        font-weight: bold;
    }}
    QLabel#cardDesc {{
        color: {TEXT_MUTED};
        font-size: 11px;
    }}
    QLabel#cardAction {{
        color: {GREEN};
        font-size: 11px;
        font-weight: bold;
    }}

    QFrame#hintBar {{
        background-color: {SOFT_SLATE};
        border: 1px solid {CARD_BORDER};
        border-radius: 10px;
    }}
    QLabel#hintText {{
        color: {SLATE};
        font-size: 12px;
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
    QLabel#formLabel {{
        color: {TEXT_MUTED};
        font-size: 12px;
        font-weight: bold;
    }}
    """

    # ================================================================== #
    # ساخت رابط کاربری
    # ================================================================== #
    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(12)

        root.addWidget(self._build_header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QWidget#reportsContainer { background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; }"
            "QScrollBar::handle:vertical { background: #cbd5e1;"
            " border-radius: 4px; min-height: 30px; }"
            "QScrollBar::add-line:vertical,"
            " QScrollBar::sub-line:vertical { height: 0; }"
        )
        content = QWidget()
        content.setObjectName("reportsContainer")
        self._content_lay = QVBoxLayout(content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(12)

        self._content_lay.addWidget(self._build_gallery())
        self._content_lay.addWidget(self._build_hint_bar())
        self._content_lay.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _build_header(self):
        card = QFrame()
        card.setObjectName("pageHeaderCard")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(12)

        icon = QLabel("📊")
        icon.setObjectName("headerIcon")
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title = QLabel("مرکز گزارش‌ها")
        title.setObjectName("headerTitle")
        subtitle = QLabel(
            "گزارش‌های حرفه‌ای مالی همراه با جمع‌های کلیدی، نمودار و "
            "خروجی اکسل / CSV / PDF با ردیف «جمع کل»")
        subtitle.setObjectName("headerSubtitle")
        text_box.addWidget(title)
        text_box.addWidget(subtitle)

        lay.addWidget(icon)
        lay.addLayout(text_box, 1)
        self._apply_shadow(card, blur=22, alpha=32, dy=4)
        return card

    def _build_gallery(self):
        """گالری کارت‌های گزارش (۳ ستونه)."""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(0, 2, 0, 2)
        grid.setSpacing(12)

        cards = [
            ("📈", SOFT_GREEN, "گزارش کلی",
             "خلاصه وضعیت مالی: درآمد، هزینه، بدهی/طلب و مانده حساب‌ها",
             self.open_general_report),
            ("💵", SOFT_RED, "گزارش هزینه/درآمد",
             "ریز تراکنش‌ها با فیلتر حساب، شخص، نوع و بازه تاریخ",
             self.open_cost_income_report),
            ("🗓️", SOFT_SLATE, "گزارش ماهانه",
             "مقایسه ماهانه هزینه و درآمد + نمودار و جمع کل سال",
             self.open_monthly_report),
            ("👤", SOFT_GREEN, "گزارش اشخاص",
             "تراکنش‌های یک شخص یا خلاصه گردش همه اشخاص",
             self.open_person_report),
            ("🧾", SOFT_SLATE, "گزارش تراکنش‌ها",
             "جستجوی پیشرفته تراکنش‌ها با فیلتر نوع، شخص و تاریخ",
             self.open_transactions_report),
            ("⚖️", SOFT_RED, "گزارش بدهی/طلب",
             "بدهی‌ها و طلب‌ها با وضعیت تسویه و جمع باقی‌مانده",
             self.open_debts_report),
            ("🏷️", SOFT_GREEN, "گزارش دسته‌بندی‌ها",
             "سهم هر دسته از هزینه‌ها یا درآمدها با درصد",
             self.open_category_report),
            ("🏦", SOFT_SLATE, "گزارش حساب‌ها",
             "مانده و گردش حساب‌ها + جمع کل دارایی",
             self.open_accounts_report),
            ("🏠", SOFT_RED, "گزارش وام‌ها",
             "خلاصه وام‌ها، پرداختی‌ها و باقی‌مانده هر وام",
             self.open_loans_report),
        ]

        for index, (icon_text, icon_bg, title, desc, callback) in enumerate(cards):
            card = self._build_report_card(icon_text, icon_bg, title, desc, callback)
            grid.addWidget(card, index // 3, index % 3)

        # ستون‌ها با عرض برابر در پهنای‌های مختلف
        for col in range(3):
            grid.setColumnStretch(col, 1)
        grid.setRowMinimumHeight(0, 0)
        return container

    def _build_report_card(self, icon_text, icon_bg, title, desc, callback):
        card = ClickableFrame()
        card.setObjectName("reportCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(138)
        card.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        icon = QLabel(icon_text)
        icon.setObjectName("cardIcon")
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background-color: {icon_bg}; font-size: 17px;"
            f" border-radius: 11px;")

        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("cardDesc")
        desc_lbl.setWordWrap(True)

        action_lbl = QLabel("ایجاد گزارش  ←")
        action_lbl.setObjectName("cardAction")

        lay.addWidget(icon)
        lay.addWidget(title_lbl)
        lay.addWidget(desc_lbl, 1)
        lay.addWidget(action_lbl)

        card.clicked.connect(callback)
        self._apply_shadow(card, blur=18, alpha=26, dy=3)
        return card

    def _build_hint_bar(self):
        bar = QFrame()
        bar.setObjectName("hintBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 10, 14, 10)
        text = QLabel(
            "💡 تاریخ‌ها در همه گزارش‌ها اختیاری‌اند؛ فقط «از تاریخ» یا فقط "
            "«تا تاریخ» را هم می‌توانید انتخاب کنید. همه فایل‌های خروجی "
            "(اکسل/CSV/PDF) با ردیف «جمع کل» در انتهای گزارش ساخته می‌شوند.")
        text.setObjectName("hintText")
        text.setWordWrap(True)
        lay.addWidget(text)
        return bar

    # ================================================================== #
    # ابزارهای مشترک
    # ================================================================== #
    def _apply_shadow(self, widget, blur=18, alpha=28, dy=3):
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, dy)
        effect.setColor(QColor(15, 40, 80, alpha))
        widget.setGraphicsEffect(effect)

    def _popup_calendar(self, date_edit):
        popup = PersianCalendarPopup(date_edit, self)
        popup.exec()

    def _make_date_edit(self, placeholder="اختیاری"):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setReadOnly(True)
        edit.mousePressEvent = lambda event: self._popup_calendar(edit)
        return edit

    def _person_combo(self, with_all=True):
        combo = QComboBox()
        if with_all:
            combo.addItem("همه اشخاص", None)
        else:
            combo.addItem("-", None)
        try:
            self.db_manager.execute("SELECT id, name FROM persons ORDER BY name")
            for pid, name in self.db_manager.fetchall():
                combo.addItem(name, pid)
        except sqlite3.Error:
            pass
        return combo

    def _account_combo(self):
        combo = QComboBox()
        combo.addItem("همه حساب‌ها", None)
        try:
            self.db_manager.execute("SELECT id, name FROM accounts ORDER BY name")
            for aid, name in self.db_manager.fetchall():
                combo.addItem(name, aid)
        except sqlite3.Error:
            pass
        return combo

    def _resolve_optional_dates(self, start_edit, end_edit):
        """اعتبارسنجی تاریخ‌های اختیاری تک‌طرفه.

        خروجی: (start_g, end_g, error) — تاریخ‌های میلادی یا پیام خطا.
        """
        start_text = start_edit.text().strip()
        end_text = end_edit.text().strip()
        start_g = end_g = None

        if start_text:
            if not is_valid_shamsi_date(start_text):
                return None, None, "فرمت تاریخ شروع باید به صورت 1404/02/19 باشد!"
            start_g = shamsi_to_gregorian(start_text)
            if not start_g:
                return None, None, "تاریخ شروع شمسی نامعتبر است!"
        if end_text:
            if not is_valid_shamsi_date(end_text):
                return None, None, "فرمت تاریخ پایان باید به صورت 1404/02/19 باشد!"
            end_g = shamsi_to_gregorian(end_text)
            if not end_g:
                return None, None, "تاریخ پایان شمسی نامعتبر است!"
        if start_text and end_text and start_text > end_text:
            return None, None, "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد!"
        return start_g, end_g, None

    def _dates_subtitle(self, start_edit, end_edit):
        start_text = start_edit.text().strip()
        end_text = end_edit.text().strip()
        if start_text and end_text:
            return f"بازه: از {start_text} تا {end_text}"
        if start_text:
            return f"بازه: از {start_text} به بعد"
        if end_text:
            return f"بازه: تا {end_text}"
        return "بازه: همه تاریخ‌ها"

    def _date_clauses(self, start_g, end_g, column="t.date"):
        clauses, params = [], []
        if start_g:
            clauses.append(f"{column} >= ?")
            params.append(start_g)
        if end_g:
            clauses.append(f"{column} <= ?")
            params.append(end_g)
        return clauses, params

    def _open_param_dialog(self, title, rows, on_generate):
        """دیالوگ عمومی پارامترهای گزارش.

        rows: لیست (label, widget) — آخرین ردیف دکمه تولید است.
        on_generate: تابع callback برای ساخت گزارش.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {PAGE_BG};
                      font-family: 'Vazir', 'Arial'; }}
            QLabel {{ color: {TEXT_DARK}; font-size: 13px; }}
        """)

        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        header = QLabel(f"⚙️ {title}")
        header.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 15px; font-weight: bold;")
        lay.addWidget(header)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        for label, widget in rows:
            form.addRow(label, widget)
        lay.addLayout(form)

        hint = QLabel("💡 تاریخ‌ها اختیاری‌اند و تک‌طرفه هم کار می‌کنند.")
        hint.setObjectName("formLabel")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(hint)

        btn = QPushButton("📊 نمایش گزارش")
        btn.setMinimumHeight(42)
        btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                color: white; border: none; border-radius: 9px;
                font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background-color: #15803d; }
        """)
        btn.clicked.connect(lambda: on_generate(dialog))
        lay.addWidget(btn)

        dialog.exec()

    # ================================================================== #
    # دیالوگ نمایش گزارش + KPI + جدول + جمع کل + خروجی‌ها
    # ================================================================== #
    def _kpi_chip(self, label, value, fg=TEXT_DARK, bg=SOFT_SLATE):
        chip = QFrame()
        chip.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border-radius: 10px;"
            f" border: 1px solid {CARD_BORDER}; }}")
        lay = QVBoxLayout(chip)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        val_lbl = QLabel(str(value))
        val_lbl.setStyleSheet(
            f"color: {fg}; font-size: 14px; font-weight: bold;"
            f" background: transparent;")
        lbl = QLabel(str(label))
        lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; background: transparent;")
        lay.addWidget(val_lbl)
        lay.addWidget(lbl)
        return chip

    def _show_report_dialog(self, *, title, subtitle, columns, rows,
                            report_type, raw_data, total_row=None,
                            kpis=None, chart_widget=None, date_range=None):
        """نمایش حرفه‌ای گزارش.

        rows: ردیف‌های نمایشی (رشته‌ای) — total_row هم رشته‌ای است.
        raw_data: داده خام برای موتور خروجی (report_exporter).
        kpis: لیست (label, value, fg, bg)
        """
        if not rows:
            QMessageBox.information(
                self, "بدون نتیجه",
                "هیچ داده‌ای برای نمایش در این بازه یافت نشد.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # با نمودار، دیالوگ بلندتر تا جدول و ردیف جمع کل دیده شود
        dialog.resize(980, 800 if chart_widget is not None else 680)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {PAGE_BG};
                      font-family: 'Vazir', 'Arial'; }}
            QLabel {{ color: {TEXT_DARK}; }}
        """)

        lay = QVBoxLayout(dialog)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # --- سربرگ ---
        header = QLabel(title)
        header.setStyleSheet(
            f"color: {TEXT_DARK}; font-size: 16px; font-weight: bold;")
        sub = QLabel(subtitle)
        sub.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        lay.addWidget(header)
        lay.addWidget(sub)

        # --- چیپ‌های KPI ---
        if kpis:
            kpi_row = QHBoxLayout()
            kpi_row.setSpacing(10)
            for label, value, fg, bg in kpis:
                kpi_row.addWidget(self._kpi_chip(label, value, fg, bg), 1)
            lay.addLayout(kpi_row)

        # --- نمودار (اختیاری) ---
        if chart_widget is not None:
            lay.addWidget(chart_widget)

        # --- جدول ---
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white; alternate-background-color: #f8fafc;
                border: 1px solid {CARD_BORDER}; border-radius: 10px;
                gridline-color: #eef2f7; font-size: 12.5px;
                selection-background-color: {SOFT_GREEN};
                selection-color: #14532d;
            }}
            QHeaderView::section {{
                background-color: #f1f5f9; color: #334155;
                font-weight: bold; font-size: 12px; padding: 7px 6px;
                border: none; border-bottom: 2px solid #e2e8f0;
            }}
        """)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        display_rows = [list(r) for r in rows]
        if total_row is not None:
            display_rows.append(list(total_row))

        table.setRowCount(len(display_rows))
        from PyQt6.QtGui import QColor
        for row_idx, row_data in enumerate(display_rows):
            is_total = total_row is not None and row_idx == len(display_rows) - 1
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "-")
                if is_total:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setBackground(QColor(SOFT_SLATE))
                    item.setForeground(QColor(TEXT_DARK))
                table.setItem(row_idx, col_idx, item)

        header_view = table.horizontalHeader()
        header_view.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        table.resizeColumnsToContents()
        lay.addWidget(table, 1)

        # --- دکمه‌های خروجی ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        def _export(fmt):
            report_exporter.export_report_as(
                dialog, raw_data, report_type, fmt, date_range)

        for text, fmt in [("📊 خروجی اکسل", "excel"),
                          ("🧾 خروجی CSV", "csv"),
                          ("📄 خروجی PDF", "pdf")]:
            b = QPushButton(text)
            b.setMinimumHeight(38)
            b.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #16a34a, stop:1 #15803d);
                    color: white; border: none; border-radius: 9px;
                    padding: 8px 18px; font-size: 12.5px; font-weight: bold;
                }
                QPushButton:hover { background-color: #15803d; }
            """)
            b.clicked.connect(lambda _=False, f=fmt: _export(f))
            btn_row.addWidget(b, 1)

        folder_btn = QPushButton("📂 پوشه گزارش‌ها")
        folder_btn.setMinimumHeight(38)
        folder_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #ffffff; color: {SLATE};
                border: 1px solid #cbd5e1; border-radius: 9px;
                padding: 8px 16px; font-size: 12.5px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {SOFT_SLATE};
                                border-color: {SLATE}; }}
        """)
        folder_btn.clicked.connect(self._open_reports_folder)
        btn_row.addWidget(folder_btn, 1)

        lay.addLayout(btn_row)
        dialog.exec()

    def _open_reports_folder(self):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        from core.paths import reports_dir
        folder = reports_dir()
        os.makedirs(folder, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    # ================================================================== #
    # ۱) گزارش کلی (خلاصه وضعیت مالی)
    # ================================================================== #
    def open_general_report(self):
        start_edit = self._make_date_edit()
        end_edit = self._make_date_edit()
        self._open_param_dialog(
            "گزارش کلی وضعیت مالی",
            [("از تاریخ (شمسی):", start_edit),
             ("تا تاریخ (شمسی):", end_edit)],
            lambda dlg: self._generate_general(dlg, start_edit, end_edit))

    def _generate_general(self, dialog, start_edit, end_edit):
        start_g, end_g, error = self._resolve_optional_dates(start_edit, end_edit)
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        try:
            date_sql, date_params = self._date_clauses(start_g, end_g)

            def _scalar(sql, params):
                self.db_manager.execute(sql, params)
                row = self.db_manager.fetchone()
                return row[0] if row and row[0] is not None else 0

            where = ("WHERE " + " AND ".join(date_sql)) if date_sql else ""
            total_income = _scalar(
                f"SELECT SUM(t.amount) FROM transactions t "
                f"JOIN categories c ON t.category_id = c.id "
                f"{where} AND c.type = 'income'"
                if date_sql else
                f"SELECT SUM(t.amount) FROM transactions t "
                f"JOIN categories c ON t.category_id = c.id "
                f"WHERE c.type = 'income'",
                date_params)
            total_expense = _scalar(
                f"SELECT SUM(t.amount) FROM transactions t "
                f"JOIN categories c ON t.category_id = c.id "
                f"{where} AND c.type = 'expense'"
                if date_sql else
                f"SELECT SUM(t.amount) FROM transactions t "
                f"JOIN categories c ON t.category_id = c.id "
                f"WHERE c.type = 'expense'",
                date_params)
            tx_count = _scalar(
                f"SELECT COUNT(*) FROM transactions t {where}",
                date_params)

            # بدهی/طلب در جریان (مستقل از بازه)
            open_debt = _scalar(
                "SELECT COALESCE(SUM(amount - paid_amount), 0) FROM debts "
                "WHERE is_paid = 0 AND is_credit = 0", [])
            open_credit = _scalar(
                "SELECT COALESCE(SUM(amount - paid_amount), 0) FROM debts "
                "WHERE is_paid = 0 AND is_credit = 1", [])
            accounts_total = _scalar(
                "SELECT COALESCE(SUM(balance), 0) FROM accounts", [])

            net = total_income - total_expense

            rows = [
                ["مجموع درآمدها", format_amount(total_income)],
                ["مجموع هزینه‌ها", format_amount(total_expense)],
                ["مانده خالص (درآمد − هزینه)", format_amount(net)],
                ["تعداد تراکنش‌ها", format_amount(tx_count)],
                ["جمع بدهی‌های در جریان (بدهکار من)", format_amount(open_debt)],
                ["جمع طلب‌های در جریان (طلبکار من)", format_amount(open_credit)],
                ["جمع مانده حساب‌ها", format_amount(accounts_total)],
            ]
            dialog.accept()

            self._show_report_dialog(
                title="گزارش کلی وضعیت مالی",
                subtitle=self._dates_subtitle(start_edit, end_edit),
                columns=["معیار", "مقدار (ریال)"],
                rows=rows,
                report_type="general",
                raw_data=rows,
                kpis=[
                    ("جمع درآمد (ریال)", format_amount(total_income), GREEN, SOFT_GREEN),
                    ("جمع هزینه (ریال)", format_amount(total_expense), RED, SOFT_RED),
                    ("مانده خالص (ریال)", format_amount(net), TEXT_DARK, SOFT_SLATE),
                ],
                date_range=self._dates_subtitle(start_edit, end_edit))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۲) گزارش هزینه/درآمد
    # ================================================================== #
    def open_cost_income_report(self):
        account_combo = self._account_combo()
        type_combo = QComboBox()
        type_combo.addItems(["هزینه", "درآمد"])
        person_combo = self._person_combo()
        start_edit = self._make_date_edit()
        end_edit = self._make_date_edit()

        self._open_param_dialog(
            "گزارش هزینه/درآمد",
            [("حساب:", account_combo),
             ("نوع:", type_combo),
             ("شخص:", person_combo),
             ("از تاریخ (شمسی):", start_edit),
             ("تا تاریخ (شمسی):", end_edit)],
            lambda dlg: self._generate_cost_income(
                dlg, account_combo, type_combo, person_combo,
                start_edit, end_edit))

    def _generate_cost_income(self, dialog, account_combo, type_combo,
                              person_combo, start_edit, end_edit):
        start_g, end_g, error = self._resolve_optional_dates(start_edit, end_edit)
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        try:
            report_type = "expense" if type_combo.currentText() == "هزینه" else "income"
            date_clauses, date_params = self._date_clauses(start_g, end_g)
            clauses = ["c.type = ?"] + date_clauses
            params = [report_type] + date_params

            account_id = account_combo.currentData()
            if account_id:
                clauses.append("t.account_id = ?")
                params.append(account_id)
            person_id = person_combo.currentData()
            if person_id:
                clauses.append("t.person_id = ?")
                params.append(person_id)

            query = f"""
                SELECT c.name, t.amount, t.date, a.name, p.name, t.description
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN persons p ON t.person_id = p.id
                WHERE {' AND '.join(clauses)}
                ORDER BY t.date DESC, t.id DESC
            """
            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()

            type_label = "هزینه" if report_type == "expense" else "درآمد"
            display_rows = [
                [type_label, format_amount(r[1]), gregorian_to_shamsi(r[2]),
                 r[3] or "-", r[4] or "-", r[5] or "-"]
                for r in results
            ]
            total = sum((r[1] or 0) for r in results)
            total_row = ["جمع کل", format_amount(total), "", "", "",
                         f"{len(results)} تراکنش"]
            dialog.accept()

            self._show_report_dialog(
                title="گزارش هزینه/درآمد",
                subtitle=(f"نوع: {type_label} — "
                          + self._dates_subtitle(start_edit, end_edit)),
                columns=["نوع", "مبلغ", "تاریخ", "حساب", "شخص", "توضیحات"],
                rows=display_rows,
                report_type="cost_income",
                raw_data=results,
                total_row=total_row,
                kpis=[
                    (f"جمع {type_label} (ریال)", format_amount(total),
                     RED if report_type == "expense" else GREEN,
                     SOFT_RED if report_type == "expense" else SOFT_GREEN),
                    ("تعداد تراکنش", format_amount(len(results)),
                     TEXT_DARK, SOFT_SLATE),
                ],
                date_range=self._dates_subtitle(start_edit, end_edit))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۳) گزارش ماهانه (+ نمودار)
    # ================================================================== #
    def open_monthly_report(self):
        from PyQt6.QtGui import QIntValidator
        year_edit = QLineEdit(str(jdatetime.date.today().year))
        year_edit.setValidator(QIntValidator(1300, 1500))
        self._open_param_dialog(
            "گزارش تفصیلی ماهانه",
            [("سال (شمسی):", year_edit)],
            lambda dlg: self._generate_monthly(dlg, year_edit))

    @staticmethod
    def _shamsi_month_bounds(year, month):
        """روز اول و آخر ماه شمسی (رفع باگ ماه‌های ۳۱ روزه و اسفند)."""
        if month <= 6:
            last_day = 31
        elif month <= 11:
            last_day = 30
        else:
            try:
                last_day = 30 if jdatetime.date(year, 1, 1).isleap() else 29
            except Exception:
                last_day = 29
        return f"{year}/{month:02d}/01", f"{year}/{month:02d}/{last_day:02d}"

    def _generate_monthly(self, dialog, year_edit):
        year_text = year_edit.text().strip()
        if not year_text:
            QMessageBox.warning(self, "خطا", "فیلد سال ضروری است!")
            return
        year = int(year_text)
        if year < 1300 or year > 1500:
            QMessageBox.warning(self, "خطا", "سال باید بین 1300 تا 1500 باشد!")
            return
        try:
            raw_rows = []
            costs, incomes, month_labels = [], [], []
            for month in range(1, 13):
                start_s, end_s = self._shamsi_month_bounds(year, month)
                start_g = shamsi_to_gregorian(start_s)
                end_g = shamsi_to_gregorian(end_s)
                self.db_manager.execute(
                    """
                    SELECT COUNT(*),
                        COALESCE(SUM(CASE WHEN c.type = 'expense'
                                  THEN t.amount ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN c.type = 'income'
                                  THEN t.amount ELSE 0 END), 0)
                    FROM transactions t
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.date BETWEEN ? AND ?
                    """,
                    (start_g, end_g))
                count, cost, income = self.db_manager.fetchone() or (0, 0, 0)
                balance = (income or 0) - (cost or 0)
                label = f"{PERSIAN_MONTHS[month - 1]} ({year}/{month:02d})"
                raw_rows.append((label, count or 0, cost or 0,
                                 income or 0, balance))
                costs.append(cost or 0)
                incomes.append(income or 0)
                month_labels.append(PERSIAN_MONTHS[month - 1])

            display_rows = [
                [label, format_amount(cnt), format_amount(cost),
                 format_amount(inc), format_amount(balance)]
                for (label, cnt, cost, inc, balance) in raw_rows
            ]
            total_cost = sum(costs)
            total_income = sum(incomes)
            total_row = ["جمع کل",
                         format_amount(sum(r[1] for r in raw_rows)),
                         format_amount(total_cost),
                         format_amount(total_income),
                         format_amount(total_income - total_cost)]
            dialog.accept()

            chart = self._build_monthly_chart(month_labels, costs, incomes)
            self._show_report_dialog(
                title="گزارش تفصیلی ماهانه",
                subtitle=f"سال {year} شمسی — هزینه و درآمد به تفکیک ماه",
                columns=["ماه", "تعداد تراکنش", "هزینه",
                         "درآمد", "مانده (درآمد − هزینه)"],
                rows=display_rows,
                report_type="monthly",
                raw_data=raw_rows,
                total_row=total_row,
                kpis=[
                    ("جمع هزینه سال (ریال)", format_amount(total_cost), RED, SOFT_RED),
                    ("جمع درآمد سال (ریال)", format_amount(total_income), GREEN, SOFT_GREEN),
                    ("مانده سال (ریال)", format_amount(total_income - total_cost),
                     TEXT_DARK, SOFT_SLATE),
                ],
                chart_widget=chart,
                date_range=f"سال {year}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def _build_monthly_chart(self, labels, costs, incomes):
        """نمودار میله‌ای هزینه/درآمد ماهانه (با فونت وزیر)."""
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.ticker import FuncFormatter
            from matplotlib import font_manager, rcParams
            from arabic_reshaper import reshape
            from bidi.algorithm import get_display

            # ثبت فونت وزیر برای متون فارسی نمودار (از ماژول مرکزی مسیرها)
            from core.paths import register_matplotlib_font
            register_matplotlib_font()

            fig = Figure(figsize=(8.8, 2.9), dpi=100, facecolor="white")
            ax = fig.add_subplot(111)

            x = list(range(len(labels)))
            ax.bar([i - 0.2 for i in x], costs, width=0.4,
                   color="#dc2626", label=get_display(reshape("هزینه")))
            ax.bar([i + 0.2 for i in x], incomes, width=0.4,
                   color="#16a34a", label=get_display(reshape("درآمد")))

            ax.set_xticks(x)
            ax.set_xticklabels(
                [get_display(reshape(l)) for l in labels], fontsize=8)
            # محور زمان راست‌به‌چپ: فروردین سمت راست (قرارداد فارسی)
            ax.invert_xaxis()
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda v, _p: f"{int(v):,}"))
            ax.tick_params(axis='y', labelsize=8)
            ax.legend(fontsize=9, frameon=False)
            ax.grid(axis="y", alpha=0.25)
            ax.set_axisbelow(True)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            fig.tight_layout()

            canvas = FigureCanvasQTAgg(fig)
            canvas.setMinimumHeight(210)
            return canvas
        except Exception:
            return None

    # ================================================================== #
    # ۴) گزارش اشخاص
    # ================================================================== #
    def open_person_report(self):
        person_combo = self._person_combo()
        start_edit = self._make_date_edit()
        end_edit = self._make_date_edit()
        self._open_param_dialog(
            "گزارش اشخاص",
            [("شخص:", person_combo),
             ("از تاریخ (شمسی):", start_edit),
             ("تا تاریخ (شمسی):", end_edit)],
            lambda dlg: self._generate_person(
                dlg, person_combo, start_edit, end_edit))

    def _generate_person(self, dialog, person_combo, start_edit, end_edit):
        start_g, end_g, error = self._resolve_optional_dates(start_edit, end_edit)
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        try:
            person_id = person_combo.currentData()
            date_clauses, date_params = self._date_clauses(start_g, end_g)

            if person_id:
                # ریز تراکنش‌های یک شخص
                clauses = ["t.person_id = ?"] + date_clauses
                params = [person_id] + date_params
                query = f"""
                    SELECT c.name, t.date, a.name, t.amount, t.description
                    FROM transactions t
                    JOIN categories c ON t.category_id = c.id
                    JOIN accounts a ON t.account_id = a.id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY t.date DESC, t.id DESC
                """
                self.db_manager.execute(query, params)
                results = self.db_manager.fetchall()

                person_name = person_combo.currentText()
                display_rows = [
                    [r[0] or "-", gregorian_to_shamsi(r[1]) if r[1] else "-",
                     r[2] or "-", format_amount(r[3]), r[4] or "-"]
                    for r in results
                ]
                total = sum((r[3] or 0) for r in results)
                total_row = ["جمع کل", "", "", format_amount(total),
                             f"{len(results)} تراکنش"]
                dialog.accept()
                self._show_report_dialog(
                    title=f"گزارش تراکنش‌های {person_name}",
                    subtitle=self._dates_subtitle(start_edit, end_edit),
                    columns=["دسته‌بندی", "تاریخ", "حساب", "مبلغ", "توضیحات"],
                    rows=display_rows,
                    report_type="person",
                    raw_data=results,
                    total_row=total_row,
                    kpis=[
                        ("جمع مبالغ (ریال)", format_amount(total),
                         TEXT_DARK, SOFT_SLATE),
                        ("تعداد تراکنش", format_amount(len(results)),
                         TEXT_DARK, SOFT_SLATE),
                    ],
                    date_range=self._dates_subtitle(start_edit, end_edit))
            else:
                # خلاصه همه اشخاص
                clauses = date_clauses
                where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
                query = f"""
                    SELECT p.name, COUNT(t.id),
                        COALESCE(SUM(CASE WHEN c.type = 'expense'
                                  THEN t.amount ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN c.type = 'income'
                                  THEN t.amount ELSE 0 END), 0)
                    FROM transactions t
                    JOIN persons p ON t.person_id = p.id
                    JOIN categories c ON t.category_id = c.id
                    {where}
                    GROUP BY p.id
                    ORDER BY p.name
                """
                self.db_manager.execute(query, date_params)
                results = self.db_manager.fetchall()

                raw_rows = [
                    (name, count, expense, income, income - expense)
                    for (name, count, expense, income) in results
                ]
                display_rows = [
                    [name, format_amount(cnt), format_amount(expense),
                     format_amount(income), format_amount(income - expense)]
                    for (name, cnt, expense, income) in results
                ]
                total_row = [
                    "جمع کل",
                    format_amount(sum(r[1] for r in raw_rows)),
                    format_amount(sum(r[2] for r in raw_rows)),
                    format_amount(sum(r[3] for r in raw_rows)),
                    format_amount(sum(r[4] for r in raw_rows)),
                ]
                dialog.accept()
                self._show_report_dialog(
                    title="گزارش خلاصه اشخاص",
                    subtitle="گردش مالی به تفکیک شخص — "
                             + self._dates_subtitle(start_edit, end_edit),
                    columns=["شخص", "تعداد تراکنش", "جمع هزینه",
                             "جمع درآمد", "مانده"],
                    rows=display_rows,
                    report_type="person_grouped",
                    raw_data=raw_rows,
                    total_row=total_row,
                    kpis=[
                        ("جمع هزینه (ریال)",
                         format_amount(sum(r[2] for r in raw_rows)), RED, SOFT_RED),
                        ("جمع درآمد (ریال)",
                         format_amount(sum(r[3] for r in raw_rows)), GREEN, SOFT_GREEN),
                        ("مانده خالص (ریال)",
                         format_amount(sum(r[4] for r in raw_rows)),
                         TEXT_DARK, SOFT_SLATE),
                    ],
                    date_range=self._dates_subtitle(start_edit, end_edit))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۵) گزارش تراکنش‌ها (جستجوی پیشرفته)
    # ================================================================== #
    def open_transactions_report(self):
        type_combo = QComboBox()
        type_combo.addItems(["همه", "برداشت", "واریز", "انتقال"])
        person_combo = self._person_combo()
        start_edit = self._make_date_edit()
        end_edit = self._make_date_edit()
        self._open_param_dialog(
            "گزارش تراکنش‌ها",
            [("نوع تراکنش:", type_combo),
             ("شخص:", person_combo),
             ("از تاریخ (شمسی):", start_edit),
             ("تا تاریخ (شمسی):", end_edit)],
            lambda dlg: self._generate_transactions(
                dlg, type_combo, person_combo, start_edit, end_edit))

    def _generate_transactions(self, dialog, type_combo, person_combo,
                               start_edit, end_edit):
        start_g, end_g, error = self._resolve_optional_dates(start_edit, end_edit)
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        try:
            trans_type = type_combo.currentText()
            clauses, params = self._date_clauses(start_g, end_g)

            if trans_type == "برداشت":
                clauses.append("c.type = 'expense' AND c.name != 'انتقال بین حساب‌ها (خروج)'")
            elif trans_type == "واریز":
                clauses.append("c.type = 'income' AND c.name != 'انتقال بین حساب‌ها (ورود)'")
            elif trans_type == "انتقال":
                clauses.append("c.name IN ('انتقال بین حساب‌ها (ورود)', 'انتقال بین حساب‌ها (خروج)')")

            person_id = person_combo.currentData()
            if person_id:
                clauses.append("t.person_id = ?")
                params.append(person_id)

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            query = f"""
                SELECT t.id, t.date, a.name, p.name, c.name,
                       t.amount, t.description, c.type
                FROM transactions t
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN persons p ON t.person_id = p.id
                JOIN categories c ON t.category_id = c.id
                {where}
                ORDER BY t.date DESC, t.id DESC
            """
            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()

            income = sum(r[5] or 0 for r in results if r[7] == "income")
            expense = sum(r[5] or 0 for r in results if r[7] != "income")

            display_rows = [
                [str(r[0]), gregorian_to_shamsi(r[1]), r[2] or "-",
                 r[3] or "-", r[4] or "-", format_amount(r[5]),
                 r[6] or "-", "درآمد" if r[7] == "income" else "هزینه"]
                for r in results
            ]
            total_row = ["", "جمع کل", "", "", "",
                         format_amount(income - expense),
                         f"جمع درآمد: {format_amount(income)} | "
                         f"جمع هزینه: {format_amount(expense)}", "خالص"]
            dialog.accept()

            self._show_report_dialog(
                title="گزارش تراکنش‌ها",
                subtitle=f"نوع: {trans_type} — "
                         + self._dates_subtitle(start_edit, end_edit),
                columns=["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی",
                         "مبلغ", "توضیحات", "نوع"],
                rows=display_rows,
                report_type="transactions",
                raw_data=results,
                total_row=total_row,
                kpis=[
                    ("جمع درآمد (ریال)", format_amount(income), GREEN, SOFT_GREEN),
                    ("جمع هزینه (ریال)", format_amount(expense), RED, SOFT_RED),
                    ("مانده خالص (ریال)", format_amount(income - expense),
                     TEXT_DARK, SOFT_SLATE),
                ],
                date_range=self._dates_subtitle(start_edit, end_edit))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۶) گزارش بدهی/طلب
    # ================================================================== #
    def open_debts_report(self):
        person_combo = self._person_combo()
        type_combo = QComboBox()
        type_combo.addItems(["همه", "بدهی", "طلب"])
        status_combo = QComboBox()
        status_combo.addItems(["همه", "در جریان", "تسویه‌شده"])
        start_edit = self._make_date_edit()
        end_edit = self._make_date_edit()
        self._open_param_dialog(
            "گزارش بدهی/طلب",
            [("شخص:", person_combo),
             ("نوع:", type_combo),
             ("وضعیت:", status_combo),
             ("از تاریخ (سررسید شمسی):", start_edit),
             ("تا تاریخ (سررسید شمسی):", end_edit)],
            lambda dlg: self._generate_debts(
                dlg, person_combo, type_combo, status_combo,
                start_edit, end_edit))

    def _generate_debts(self, dialog, person_combo, type_combo,
                        status_combo, start_edit, end_edit):
        start_g, end_g, error = self._resolve_optional_dates(start_edit, end_edit)
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        try:
            clauses, params = self._date_clauses(start_g, end_g, column="d.due_date")

            debt_type = type_combo.currentText()
            if debt_type == "بدهی":
                clauses.append("d.is_credit = 0")
            elif debt_type == "طلب":
                clauses.append("d.is_credit = 1")

            status = status_combo.currentText()
            if status == "در جریان":
                clauses.append("d.is_paid = 0")
            elif status == "تسویه‌شده":
                clauses.append("d.is_paid = 1")

            person_id = person_combo.currentData()
            if person_id:
                clauses.append("d.person_id = ?")
                params.append(person_id)

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            query = f"""
                SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date,
                       d.is_paid, COALESCE(a.name, '-'), d.is_credit,
                       d.description, d.settled_date
                FROM debts d
                LEFT JOIN persons p ON d.person_id = p.id
                LEFT JOIN accounts a ON d.account_id = a.id
                {where}
                ORDER BY d.id DESC
            """
            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()

            # جمع‌های باقی‌مانده بدهی/طلب
            debt_remaining = credit_remaining = 0.0
            for r in results:
                if r[5]:
                    continue
                remaining = (r[2] or 0) - (r[3] or 0)
                if r[7]:
                    credit_remaining += remaining
                else:
                    debt_remaining += remaining

            total_amount = sum((r[2] or 0) for r in results)
            total_paid = sum((r[3] or 0) for r in results)

            display_rows = [
                [str(r[0]), r[1] or "-", format_amount(r[2]),
                 format_amount(r[3]),
                 gregorian_to_shamsi(r[4]) if r[4] else "-",
                 "تسویه‌شده" if r[5] else "در جریان",
                 gregorian_to_shamsi(r[9]) if r[9] else "—",
                 r[6] or "-", "طلب" if r[7] else "بدهی", r[8] or "-"]
                for r in results
            ]
            total_row = ["", "جمع کل", format_amount(total_amount),
                         format_amount(total_paid), "",
                         f"{len(results)} مورد", "", "", "",
                         f"باقی‌مانده: {format_amount(total_amount - total_paid)}"]
            dialog.accept()

            self._show_report_dialog(
                title="گزارش بدهی/طلب",
                subtitle=(f"نوع: {debt_type} — وضعیت: {status} — "
                          + self._dates_subtitle(start_edit, end_edit)),
                columns=["شناسه", "شخص", "مبلغ", "پرداخت‌شده", "سررسید",
                         "وضعیت", "تاریخ تسویه", "حساب", "نوع", "توضیحات"],
                rows=display_rows,
                report_type="debts",
                raw_data=results,
                total_row=total_row,
                kpis=[
                    ("جمع بدهی باقی‌مانده (ریال)",
                     format_amount(debt_remaining), RED, SOFT_RED),
                    ("جمع طلب باقی‌مانده (ریال)",
                     format_amount(credit_remaining), GREEN, SOFT_GREEN),
                    ("مانده خالص (ریال)",
                     format_amount(credit_remaining - debt_remaining),
                     TEXT_DARK, SOFT_SLATE),
                ],
                date_range=self._dates_subtitle(start_edit, end_edit))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۷) گزارش دسته‌بندی‌ها
    # ================================================================== #
    def open_category_report(self):
        direction_combo = QComboBox()
        direction_combo.addItems(["هزینه", "درآمد"])
        start_edit = self._make_date_edit()
        end_edit = self._make_date_edit()
        self._open_param_dialog(
            "گزارش دسته‌بندی‌ها",
            [("جهت:", direction_combo),
             ("از تاریخ (شمسی):", start_edit),
             ("تا تاریخ (شمسی):", end_edit)],
            lambda dlg: self._generate_category(
                dlg, direction_combo, start_edit, end_edit))

    def _generate_category(self, dialog, direction_combo, start_edit, end_edit):
        start_g, end_g, error = self._resolve_optional_dates(start_edit, end_edit)
        if error:
            QMessageBox.warning(self, "خطا", error)
            return
        try:
            cat_type = "expense" if direction_combo.currentText() == "هزینه" else "income"
            clauses, params = self._date_clauses(start_g, end_g)
            clauses.insert(0, "c.type = ?")
            params.insert(0, cat_type)

            query = f"""
                SELECT c.name, COUNT(t.id), COALESCE(SUM(t.amount), 0)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE {' AND '.join(clauses)}
                GROUP BY c.id
                ORDER BY SUM(t.amount) DESC
            """
            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()

            grand_total = sum((r[2] or 0) for r in results) or 1
            raw_rows = [
                (name, count, amount,
                 (amount or 0) * 100.0 / grand_total)
                for (name, count, amount) in results
            ]
            display_rows = [
                [name, format_amount(count), format_amount(amount),
                 f"{(amount or 0) * 100.0 / grand_total:.1f}%"]
                for (name, count, amount) in results
            ]
            total_row = [
                "جمع کل",
                format_amount(sum(r[1] for r in raw_rows)),
                format_amount(sum(r[2] for r in raw_rows)),
                "100%",
            ]
            dialog.accept()

            direction_label = direction_combo.currentText()
            self._show_report_dialog(
                title="گزارش دسته‌بندی‌ها",
                subtitle=(f"سهم دسته‌ها از {direction_label}‌ها — "
                          + self._dates_subtitle(start_edit, end_edit)),
                columns=["دسته‌بندی", "تعداد تراکنش",
                         "جمع مبلغ", "سهم از کل"],
                rows=display_rows,
                report_type="category",
                raw_data=raw_rows,
                total_row=total_row,
                kpis=[
                    (f"جمع {direction_label}‌ها (ریال)",
                     format_amount(grand_total if grand_total != 1 else 0),
                     RED if cat_type == "expense" else GREEN,
                     SOFT_RED if cat_type == "expense" else SOFT_GREEN),
                    ("تعداد دسته فعال",
                     format_amount(len(results)), TEXT_DARK, SOFT_SLATE),
                ],
                date_range=self._dates_subtitle(start_edit, end_edit))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۸) گزارش حساب‌ها
    # ================================================================== #
    def open_accounts_report(self):
        self._generate_accounts()

    def _generate_accounts(self):
        try:
            query = """
                SELECT a.name, COUNT(t.id),
                    COALESCE(SUM(CASE WHEN c.type = 'income'
                              THEN t.amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN c.type = 'expense'
                              THEN t.amount ELSE 0 END), 0),
                    a.balance
                FROM accounts a
                LEFT JOIN transactions t ON t.account_id = a.id
                LEFT JOIN categories c ON t.category_id = c.id
                GROUP BY a.id
                ORDER BY a.name
            """
            self.db_manager.execute(query)
            results = self.db_manager.fetchall()

            raw_rows = [
                (name, count, income, expense, balance)
                for (name, count, income, expense, balance) in results
            ]
            display_rows = [
                [name, format_amount(count), format_amount(income),
                 format_amount(expense), format_amount(balance)]
                for (name, count, income, expense, balance) in results
            ]
            total_balance = sum(r[4] or 0 for r in raw_rows)
            total_row = [
                "جمع کل",
                format_amount(sum(r[1] for r in raw_rows)),
                format_amount(sum(r[2] for r in raw_rows)),
                format_amount(sum(r[3] for r in raw_rows)),
                format_amount(total_balance),
            ]

            self._show_report_dialog(
                title="گزارش حساب‌ها",
                subtitle="مانده و گردش حساب‌ها (مجموع مانده = دارایی فعلی)",
                columns=["حساب", "تعداد تراکنش", "جمع واریز",
                         "جمع برداشت", "مانده"],
                rows=display_rows,
                report_type="accounts",
                raw_data=raw_rows,
                total_row=total_row,
                kpis=[
                    ("مجموع مانده حساب‌ها (ریال)", format_amount(total_balance),
                     GREEN if total_balance >= 0 else RED, SOFT_GREEN),
                    ("تعداد حساب", format_amount(len(results)),
                     TEXT_DARK, SOFT_SLATE),
                ],
                date_range="وضعیت فعلی")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ================================================================== #
    # ۹) گزارش وام‌ها
    # ================================================================== #
    def open_loans_report(self):
        self._generate_loans()

    def _generate_loans(self):
        try:
            query = """
                SELECT l.type, COALESCE(l.bank_name, '-'),
                       l.total_amount, l.paid_amount,
                       (l.total_amount - l.paid_amount),
                       (l.installments_paid || '/' || l.installments_total)
                FROM loans l
                ORDER BY l.id DESC
            """
            self.db_manager.execute(query)
            results = self.db_manager.fetchall()

            type_labels = {"taken": "گرفته‌شده", "given": "داده‌شده"}
            raw_rows = [
                (type_labels.get(r[0], str(r[0])), r[1], r[2] or 0,
                 r[3] or 0, r[4] or 0, r[5] or "-")
                for r in results
            ]
            display_rows = [
                [type_labels.get(r[0], str(r[0])), r[1],
                 format_amount(r[2]), format_amount(r[3]),
                 format_amount(r[4]), r[5] or "-"]
                for r in results
            ]
            total_remaining = sum(r[4] for r in raw_rows)
            total_row = [
                "", "جمع کل",
                format_amount(sum(r[2] for r in raw_rows)),
                format_amount(sum(r[3] for r in raw_rows)),
                format_amount(total_remaining),
                f"{len(results)} وام",
            ]

            self._show_report_dialog(
                title="گزارش وام‌ها",
                subtitle="خلاصه وام‌ها: مبلغ، پرداخت‌شده، باقی‌مانده و پیشرفت اقساط",
                columns=["نوع", "عنوان", "مبلغ کل", "پرداخت‌شده",
                         "باقی‌مانده", "پیشرفت اقساط"],
                rows=display_rows,
                report_type="loans",
                raw_data=raw_rows,
                total_row=total_row,
                kpis=[
                    ("جمع باقی‌مانده وام‌ها (ریال)",
                     format_amount(total_remaining), RED, SOFT_RED),
                    ("تعداد وام", format_amount(len(results)),
                     TEXT_DARK, SOFT_SLATE),
                ],
                date_range="وضعیت فعلی")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
