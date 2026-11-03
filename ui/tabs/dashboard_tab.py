# -*- coding: utf-8 -*-
"""
ui/tabs/dashboard_tab.py
========================
تب «داشبورد مالی» برنامه حسابداری شخصی

چیدمان جدید داشبورد:

    ┌──────────────────────────────────────────────────────────────┐
    │  هدر گرادیانی: عنوان + تاریخ امروز | نشان موجودی کل          │
    ├──────────────────────────────────────────────────────────────┤
    │  ۵ کارت آمار ماه جاری (هزینه، درآمد، تراز، طلب، بدهی)        │
    ├───────────────────────────────┬──────────────────────────────┤
    │  📜 تراکنش‌های اخیر (چپ)       │ 💸 بدهی و طلب‌های مهم (راست) │
    │  فقط ۵۰ تراکنش آخر            │ جمع بدهی/طلب + جدول رنگی     │
    └───────────────────────────────┴──────────────────────────────┘

نکته مهم درباره جهت چیدمان:
    کل صفحه راست‌به‌چپ (RTL) است؛ بنابراین در QHBoxLayout هر ویجتی
    که «اول» اضافه شود در سمت «راست» قرار می‌گیرد. به همین دلیل
    پنل بدهی/طلب (که باید سمت راست باشد) قبل از پنل تراکنش‌ها
    به چیدمان اضافه می‌شود.

این تب کاملاً مستقل از main.py است و فقط از db_manager و توابع
کمکی core.utils استفاده می‌کند؛ بنابراین سایر بخش‌های برنامه به
هیچ جزئیات داخلی این کلاس وابسته نیستند.
"""

import sqlite3
from datetime import date as gregorian_date

import jdatetime
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect,
)

from core.utils import format_amount, gregorian_to_shamsi


# ----------------------------------------------------------------------------
# پالت رنگی داشبورد (هماهنگ با تم سبز برنامه)
# ----------------------------------------------------------------------------
PAGE_BG = "#eef1f6"          # پس‌زمینه کلی صفحه
CARD_BORDER = "#e5eaf1"      # حاشیه کارت‌ها

TEXT_DARK = "#1e293b"        # متن اصلی
TEXT_MUTED = "#64748b"       # متن ثانویه

GREEN = "#16a34a"            # درآمد / طلب
RED = "#dc2626"              # هزینه / بدهی سررسید گذشته
AMBER = "#d97706"            # بدهی نزدیک به سررسید
TEAL = "#0d9488"             # طلب
SLATE = "#475569"            # خنثی

SOFT_RED = "#fee2e2"         # پس‌زمینه ملایم قرمز
SOFT_GREEN = "#dcfce7"       # پس‌زمینه ملایم سبز
SOFT_AMBER = "#fef3c7"       # پس‌زمینه ملایم کهربایی
SOFT_TEAL = "#ccfbf1"        # پس‌زمینه ملایم فیروزه‌ای
SOFT_SLATE = "#f1f5f9"       # پس‌زمینه ملایم خنثی

ROW_OVERDUE_BG = "#fef2f2"   # پس‌زمینه ردیف سررسید گذشته
ROW_SOON_BG = "#fffbeb"      # پس‌زمینه ردیف نزدیک به سررسید


class DashboardTab(QWidget):
    """تب داشبورد: نمای کلی وضعیت مالی کاربر."""

    # ------------------------------------------------------------------ #
    # استایل کلی داشبورد (بر اساس نام اشیاء تا با استایل سراسری برنامه
    # تداخل نکند)
    # ------------------------------------------------------------------ #
    STYLESHEET = f"""
    DashboardTab {{
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

    /* ---------- کارت‌های آمار ماه ---------- */
    QFrame#kpiCard {{
        background-color: #ffffff;
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
    }}
    QFrame#kpiCard:hover {{
        border: 1px solid #c3d0e0;
        background-color: #fcfdfe;
    }}
    QLabel#kpiTitle {{
        color: {TEXT_MUTED};
        font-size: 11px;
        background: transparent;
    }}
    QLabel#kpiValue {{
        font-size: 15px;
        font-weight: bold;
        background: transparent;
    }}

    /* ---------- پنل‌های محتوا ---------- */
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

    /* ---------- جدول‌ها ---------- */
    QTableWidget#recentTable, QTableWidget#debtsTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#recentTable QHeaderView::section,
    QTableWidget#debtsTable QHeaderView::section {{
        background-color: #f1f5f9;
        color: #334155;
        font-weight: bold;
        font-size: 12px;
        padding: 7px 6px;
        border: none;
        border-bottom: 2px solid #e2e8f0;
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

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        # فقط ۵۰ تراکنش آخر در داشبورد نمایش داده می‌شود (بدون صفحه‌بندی
        # و بدون شمارش کل جدول) تا این تب همیشه سریع بارگذاری شود؛
        # مرور کامل تاریخچه در تب «تراکنش‌ها» انجام می‌شود.
        self.recent_per_page = 50

        # جهت چیدمان راست‌به‌چپ (مطابق کل برنامه)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # برای اعمال پس‌زمینه QSS روی QWidget خام
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

        # ۱. هدر (موجودی کل + تاریخ امروز)
        layout.addWidget(self._build_header())

        # ۲. ردیف کارت‌های آمار ماه جاری
        layout.addWidget(self._build_kpi_row())

        # ۳. بدنه دوستونه
        #    نکته RTL: ویجتی که اول اضافه شود سمت «راست» قرار می‌گیرد؛
        #    بنابراین پنل بدهی/طلب (سمت راست) قبل از تراکنش‌ها اضافه می‌شود.
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        content_layout.addWidget(self._build_debts_panel(), 48)      # سمت راست
        content_layout.addWidget(self._build_recent_panel(), 52)     # سمت چپ
        layout.addLayout(content_layout, 1)

    # ------------------------------------------------------------------ #
    # هدر داشبورد
    # ------------------------------------------------------------------ #
    def _build_header(self):
        card = QFrame()
        card.setObjectName("headerCard")

        lay = QHBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        icon = QLabel("📊")
        icon.setObjectName("headerIcon")
        icon.setFixedSize(52, 52)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("داشبورد مالی")
        title.setObjectName("headerTitle")
        self.header_date_label = QLabel("")
        self.header_date_label.setObjectName("headerSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(self.header_date_label)
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

    # ------------------------------------------------------------------ #
    # ردیف کارت‌های آمار ماه جاری
    # ------------------------------------------------------------------ #
    def _build_kpi_row(self):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(12)

        self.kpi_expenses = self._build_kpi_card(
            row_layout, "🛒", "هزینه‌های ماه جاری", RED, SOFT_RED)
        self.kpi_income = self._build_kpi_card(
            row_layout, "💰", "درآمدهای ماه جاری", GREEN, SOFT_GREEN)
        self.kpi_balance = self._build_kpi_card(
            row_layout, "⚖️", "تراز ماه جاری", SLATE, SOFT_SLATE)
        self.kpi_credits = self._build_kpi_card(
            row_layout, "🤝", "طلب‌های ماه جاری", TEAL, SOFT_TEAL)
        self.kpi_debts = self._build_kpi_card(
            row_layout, "💳", "بدهی‌های ماه جاری", AMBER, SOFT_AMBER)

        return row

    def _build_kpi_card(self, parent_layout, icon_text, title, color, bubble_bg):
        """ساخت یک کارت آمار؛ لیبل مقدار را برمی‌گرداند تا بعداً به‌روز شود."""
        card = QFrame()
        card.setObjectName("kpiCard")

        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        # نوار رنگی بالای کارت
        accent = QFrame()
        accent.setFixedHeight(4)
        accent.setStyleSheet(
            f"background-color: {color}; border-radius: 2px;")

        row = QHBoxLayout()
        row.setSpacing(10)

        icon = QLabel(icon_text)
        icon.setObjectName("kpiIcon")
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background-color: {bubble_bg}; border-radius: 12px; font-size: 17px;")

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("kpiTitle")
        title_label.setWordWrap(True)
        value_label = QLabel("0 ریال")
        value_label.setObjectName("kpiValue")
        value_label.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {color};")
        text_box.addWidget(title_label)
        text_box.addWidget(value_label)
        text_box.addStretch()

        row.addWidget(icon)
        row.addLayout(text_box, 1)

        lay.addWidget(accent)
        lay.addLayout(row)

        self._apply_shadow(card, blur=14, alpha=22, dy=2)
        parent_layout.addWidget(card, 1)
        return value_label

    # ------------------------------------------------------------------ #
    # پنل بدهی‌ها و طلب‌های مهم (سمت راست)
    # ------------------------------------------------------------------ #
    def _build_debts_panel(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ پنل: آیکون + عنوان + تعداد
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("💸")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background-color: {SOFT_RED}; font-size: 15px;")
        title = QLabel("بدهی‌ها و طلب‌های مهم")
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

        # جمع باقی‌مانده بدهی و طلب
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        self.debts_sum_chip = QLabel("جمع بدهی: 0 ریال")
        self.debts_sum_chip.setObjectName("chip")
        self.debts_sum_chip.setStyleSheet(
            f"background-color: {SOFT_RED}; color: {RED};")
        self.credits_sum_chip = QLabel("جمع طلب: 0 ریال")
        self.credits_sum_chip.setObjectName("chip")
        self.credits_sum_chip.setStyleSheet(
            f"background-color: {SOFT_GREEN}; color: {GREEN};")
        chips_row.addWidget(self.debts_sum_chip)
        chips_row.addWidget(self.credits_sum_chip)
        chips_row.addStretch(1)
        lay.addLayout(chips_row)

        # جدول بدهی‌ها و طلب‌های مهم
        self.important_debts_table = QTableWidget()
        self.important_debts_table.setObjectName("debtsTable")
        self.important_debts_table.setColumnCount(5)
        self.important_debts_table.setHorizontalHeaderLabels(
            ["شخص", "نوع", "مبلغ", "باقی‌مانده", "سررسید"])
        # شخص(کش‌شونده) | نوع | مبلغ | باقی‌مانده | سررسید
        self._style_table(self.important_debts_table,
                          [None, 80, 130, 130, 130])
        self.important_debts_table.setMinimumHeight(380)
        lay.addWidget(self.important_debts_table, 1)

        # پیام حالت خالی
        self.debts_empty_label = QLabel(
            "✅ در ۱۵ روز آینده بدهی یا طلب مهمی برای نمایش وجود ندارد")
        self.debts_empty_label.setObjectName("emptyLabel")
        self.debts_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.debts_empty_label.setVisible(False)
        lay.addWidget(self.debts_empty_label, 1)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        self.debts_panel = card
        return card

    # ------------------------------------------------------------------ #
    # پنل تراکنش‌های اخیر (سمت چپ)
    # ------------------------------------------------------------------ #
    def _build_recent_panel(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ پنل: آیکون + عنوان + تعداد
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("📜")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("تراکنش‌های اخیر")
        title.setObjectName("panelTitle")
        self.recent_count_chip = QLabel("0 تراکنش اخیر")
        self.recent_count_chip.setObjectName("chip")
        self.recent_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.recent_count_chip)
        lay.addLayout(header_row)

        # جدول تراکنش‌های اخیر
        self.recent_transactions_table = QTableWidget()
        self.recent_transactions_table.setObjectName("recentTable")
        self.recent_transactions_table.setColumnCount(6)
        self.recent_transactions_table.setHorizontalHeaderLabels(
            ["تاریخ", "حساب", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"])
        # تاریخ | حساب | دسته‌بندی | مبلغ | توضیحات(کش‌شونده) | نوع
        self._style_table(self.recent_transactions_table,
                          [110, 130, 130, 130, None, 90])
        self.recent_transactions_table.setMinimumHeight(380)
        lay.addWidget(self.recent_transactions_table, 1)

        # پیام حالت خالی
        self.recent_empty_label = QLabel("📝 هنوز تراکنشی ثبت نشده است")
        self.recent_empty_label.setObjectName("emptyLabel")
        self.recent_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_empty_label.setVisible(False)
        lay.addWidget(self.recent_empty_label, 1)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        self.recent_panel = card
        return card

    # ------------------------------------------------------------------ #
    # ابزارهای مشترک ساخت رابط کاربری
    # ------------------------------------------------------------------ #
    def _style_table(self, table, column_widths):
        """تنظیمات ظاهری و رفتاری مشترک جدول‌های داشبورد.

        نکته کارایی: به‌جای حالت «ResizeToContents» (که با هر setItem
        کل جدول را دوباره اندازه‌گیری و چیدمان می‌کند و برای جدول‌های
        داخل QScrollArea بسیار کند است) از عرض ثابت استفاده می‌شود.
        ستونی که عرض آن «None» باشد کش‌شونده (Stretch) است و با
        تغییر اندازه پنجره تنظیم می‌شود.
        """
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # مخفی‌کردن شماره ردیف‌ها برای ظاهری تمیزتر
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

        # عرض ثابت ستون‌ها + ستون کش‌شونده (None)
        horizontal_header = table.horizontalHeader()
        horizontal_header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        for column, width in enumerate(column_widths):
            if width is None:
                horizontal_header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.Stretch)
            else:
                table.setColumnWidth(column, width)
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setMinimumSectionSize(64)
        horizontal_header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter)

    def _apply_shadow(self, widget, blur=18, alpha=28, dy=3):
        """افزودن سایه ملایم زیر کارت‌ها برای ایجاد عمق بصری."""
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(15, 40, 30, alpha))
        effect.setOffset(0, dy)
        widget.setGraphicsEffect(effect)

    # ================================================================== #
    # به‌روزرسانی داده‌ها
    # ================================================================== #
    def update_dashboard(self):
        """نقطه ورود اصلی؛ توسط main.py پس از هر تغییر فراخوانی می‌شود."""
        try:
            self._refresh_header()
            self._refresh_month_stats()
            self.load_important_debts()
            self.load_recent_transactions()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def _refresh_header(self):
        # موجودی کل
        self.db_manager.execute("SELECT SUM(balance) FROM accounts")
        total_balance = self.db_manager.fetchone()[0] or 0
        self.total_balance_label.setText(f"{format_amount(total_balance)} ریال")

        # تاریخ امروز (شمسی)
        self.header_date_label.setText(f"امروز: {self._today_text()}")

    def _refresh_month_stats(self):
        expenses = self.get_current_month_expenses()
        income = self.get_current_month_income()
        balance = income - expenses

        self.kpi_expenses.setText(f"{format_amount(expenses)} ریال")
        self.kpi_income.setText(f"{format_amount(income)} ریال")
        self.kpi_balance.setText(f"{format_amount(balance)} ریال")
        # رنگ تراز: سبز اگر مثبت، قرمز اگر منفی
        balance_color = GREEN if balance >= 0 else RED
        self.kpi_balance.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {balance_color};")
        self.kpi_credits.setText(
            f"{format_amount(self.get_current_month_credits())} ریال")
        self.kpi_debts.setText(
            f"{format_amount(self.get_current_month_debts())} ریال")

    def _today_text(self):
        """تاریخ امروز به شمسی همراه با نام روز و ماه."""
        try:
            jdatetime.set_locale("fa_IR")
            return jdatetime.date.today().strftime("%A %d %B %Y")
        except Exception:
            return jdatetime.date.today().strftime("%Y/%m/%d")

    # ------------------------------------------------------------------ #
    # بدهی‌ها و طلب‌های مهم
    # ------------------------------------------------------------------ #
    def load_important_debts(self):
        today = jdatetime.date.today()
        fifteen_days_later = today + jdatetime.timedelta(days=15)
        today_str = today.togregorian().strftime("%Y-%m-%d")
        fifteen_days_later_str = fifteen_days_later.togregorian().strftime("%Y-%m-%d")

        self.db_manager.execute(
            "SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, d.is_paid, "
            "COALESCE(a.name, '-'), d.is_credit "
            "FROM debts d JOIN persons p ON d.person_id = p.id "
            "LEFT JOIN accounts a ON d.account_id = a.id "
            "WHERE d.show_in_dashboard = 1 AND d.is_paid = 0 AND d.due_date IS NOT NULL "
            "AND (d.due_date <= ? OR (d.due_date >= ? AND d.due_date <= ?)) "
            "ORDER BY d.due_date ASC",
            (today_str, today_str, fifteen_days_later_str)
        )
        debts = self.db_manager.fetchall()

        if not isinstance(debts, (list, tuple)):
            debts = []

        if not debts:
            self.important_debts_table.setRowCount(0)
            self.important_debts_table.setVisible(False)
            self.debts_empty_label.setVisible(True)
            self.debts_count_chip.setText("0 مورد")
            self.debts_sum_chip.setText("جمع بدهی: 0 ریال")
            self.credits_sum_chip.setText("جمع طلب: 0 ریال")
            return
        self.important_debts_table.setVisible(True)
        self.debts_empty_label.setVisible(False)

        today_g = gregorian_date.today()
        total_debt_remaining = 0
        total_credit_remaining = 0

        self.important_debts_table.setRowCount(len(debts))
        for row, (debt_id, person, amount, paid, due_date,
                  is_paid, account, is_credit) in enumerate(debts):
            remaining = max((amount or 0) - (paid or 0), 0)
            if is_credit:
                total_credit_remaining += remaining
            else:
                total_debt_remaining += remaining

            # رنگ بر اساس نوع: طلب سبز، بدهی قرمز
            type_color = QColor(GREEN if is_credit else RED)
            type_text = "طلب" if is_credit else "بدهی"

            # ظاهر سررسید بر اساس فاصله تا امروز (متن کوتاه + راهنمای tooltip)
            days_left = self._days_until(due_date, today_g)
            due_text, due_color, row_bg, due_tooltip = self._due_appearance(
                due_date, days_left)

            # --- ساخت آیتم‌های ردیف ---
            person_item = QTableWidgetItem(str(person))
            person_font = person_item.font()
            person_font.setBold(True)
            person_item.setFont(person_font)
            person_item.setForeground(QColor(TEXT_DARK))
            person_item.setToolTip(str(person))

            type_item = QTableWidgetItem(type_text)
            type_font = type_item.font()
            type_font.setBold(True)
            type_item.setFont(type_font)
            type_item.setForeground(type_color)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            amount_item = QTableWidgetItem(format_amount(amount))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_item.setForeground(type_color)

            remaining_item = QTableWidgetItem(format_amount(remaining))
            remaining_font = remaining_item.font()
            remaining_font.setBold(True)
            remaining_item.setFont(remaining_font)
            remaining_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            remaining_item.setForeground(QColor(TEXT_DARK))

            due_item = QTableWidgetItem(due_text)
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            due_item.setForeground(due_color)
            due_item.setToolTip(due_tooltip)

            items = [person_item, type_item, amount_item,
                     remaining_item, due_item]
            for column, item in enumerate(items):
                if row_bg is not None:
                    item.setBackground(row_bg)
                self.important_debts_table.setItem(row, column, item)

        # به‌روزرسانی چیپ‌های خلاصه
        self.debts_count_chip.setText(f"{len(debts)} مورد")
        self.debts_sum_chip.setText(
            f"جمع بدهی: {format_amount(total_debt_remaining)} ریال")
        self.credits_sum_chip.setText(
            f"جمع طلب: {format_amount(total_credit_remaining)} ریال")

    def _days_until(self, due_date, today_g):
        """تعداد روز باقی‌مانده تا سررسید (میلادی برای محاسبه، نمایش شمسی)."""
        try:
            return (gregorian_date.fromisoformat(str(due_date)[:10]) - today_g).days
        except (ValueError, TypeError):
            return None

    def _due_appearance(self, due_date, days_left):
        """متن، رنگ، پس‌زمینه و tooltip ستون سررسید بر اساس وضعیت.

        برای صرفه‌جویی در عرض ستون، فقط خود تاریخ نمایش داده می‌شود و
        جزئیات («n روز مانده/گذشته») در tooltip همان سلول قرار می‌گیرد.
        """
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

    # ------------------------------------------------------------------ #
    # تراکنش‌های اخیر
    # ------------------------------------------------------------------ #
    def load_recent_transactions(self):
        """نمایش آخرین ۵۰ تراکنش ثبت‌شده.

        برای سرعت بالا:
          - بدون COUNT(*) روی کل جدول (در دیتابیس‌های بزرگ کند است)؛
          - بدون صفحه‌بندی — فقط یک کوئری با LIMIT 50.
        مرور و جستجوی کامل تاریخچه در تب «تراکنش‌ها» انجام می‌شود.
        """
        try:
            # واکشی ۵۰ تراکنش آخر (جدیدترین‌ها در بالا)
            self.db_manager.execute(
                "SELECT t.id, t.date, a.name, p.name, c.name, t.amount, t.description, c.type, "
                "COALESCE(t.is_transfer, 0) "
                "FROM transactions t "
                "JOIN accounts a ON t.account_id = a.id "
                "LEFT JOIN persons p ON t.person_id = p.id "
                "JOIN categories c ON t.category_id = c.id "
                "ORDER BY t.date DESC, t.id DESC LIMIT ?",
                (self.recent_per_page,)
            )
            recent_transactions = self.db_manager.fetchall()

            self.recent_count_chip.setText(
                f"{len(recent_transactions)} تراکنش اخیر")

            # حالت خالی
            if not recent_transactions:
                self.recent_transactions_table.setRowCount(0)
                self.recent_transactions_table.setVisible(False)
                self.recent_empty_label.setVisible(True)
            else:
                self.recent_transactions_table.setVisible(True)
                self.recent_empty_label.setVisible(False)

                self.recent_transactions_table.setRowCount(
                    min(len(recent_transactions), self.recent_per_page))
                for row, (id, date, account, person, category, amount,
                          desc, category_type, is_transfer) in enumerate(recent_transactions):
                    shamsi_date = gregorian_to_shamsi(date) if date else "-"
                    # انتقال بین حساب‌ها: نه درآمد است نه هزینه؛ رنگ خنثی
                    if is_transfer:
                        type_text, type_color = "انتقال", QColor(SLATE)
                    else:
                        is_income = (category_type == "income")
                        type_text = "درآمد" if is_income else "هزینه"
                        type_color = QColor(GREEN if is_income else RED)

                    date_item = QTableWidgetItem(shamsi_date)
                    date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    date_item.setForeground(QColor(SLATE))

                    account_item = QTableWidgetItem(account or "-")
                    account_item.setForeground(QColor(TEXT_DARK))

                    category_item = QTableWidgetItem(category or "-")
                    category_item.setForeground(QColor(TEXT_MUTED))

                    amount_item = QTableWidgetItem(format_amount(amount))
                    amount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    amount_font = amount_item.font()
                    amount_font.setBold(True)
                    amount_item.setFont(amount_font)
                    amount_item.setForeground(type_color)

                    desc_item = QTableWidgetItem(desc or "")
                    desc_item.setForeground(QColor(TEXT_MUTED))
                    if desc:
                        desc_item.setToolTip(str(desc))

                    type_item = QTableWidgetItem(type_text)
                    type_font = type_item.font()
                    type_font.setBold(True)
                    type_item.setFont(type_font)
                    type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    type_item.setForeground(type_color)

                    for column, item in enumerate([
                            date_item, account_item, category_item,
                            amount_item, desc_item, type_item]):
                        self.recent_transactions_table.setItem(row, column, item)

        except sqlite3.Error as e:
            QMessageBox.critical(
                self, "خطا", f"خطای پایگاه داده در تراکنش‌های اخیر: {e}")

    # ================================================================== #
    # آمار ماه جاری
    # ================================================================== #
    def _current_month_range(self):
        """بازه میلادی اول و پایان ماه شمسی جاری."""
        today = jdatetime.date.today()
        start_of_month = jdatetime.date(today.year, today.month, 1).togregorian()
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year + 1 if today.month == 12 else today.year
        end_of_month = (
            jdatetime.date(next_year, next_month, 1) - jdatetime.timedelta(days=1)
        ).togregorian()
        return (start_of_month.strftime("%Y-%m-%d"),
                end_of_month.strftime("%Y-%m-%d"))

    def get_current_month_expenses(self):
        start_str, end_str = self._current_month_range()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0)
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = 'expense' AND COALESCE(t.is_transfer, 0) = 0
              AND t.date BETWEEN ? AND ?
            """,
            (start_str, end_str)
        )
        return self.db_manager.fetchone()[0]

    def get_current_month_income(self):
        start_str, end_str = self._current_month_range()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0)
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = 'income' AND COALESCE(t.is_transfer, 0) = 0
              AND t.date BETWEEN ? AND ?
            """,
            (start_str, end_str)
        )
        return self.db_manager.fetchone()[0]

    def get_current_month_balance(self):
        return self.get_current_month_income() - self.get_current_month_expenses()

    def get_current_month_credits(self):
        start_str, end_str = self._current_month_range()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(amount - paid_amount), 0)
            FROM debts
            WHERE is_credit = 1 AND is_paid = 0 AND due_date BETWEEN ? AND ?
            """,
            (start_str, end_str)
        )
        return self.db_manager.fetchone()[0]

    def get_current_month_debts(self):
        start_str, end_str = self._current_month_range()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(amount - paid_amount), 0)
            FROM debts
            WHERE is_credit = 0 AND is_paid = 0 AND due_date BETWEEN ? AND ?
            """,
            (start_str, end_str)
        )
        return self.db_manager.fetchone()[0]
