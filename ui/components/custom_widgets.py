# -*- coding: utf-8 -*-
"""
ui/components/custom_widgets.py
===============================
ویجت‌های مشترک برنامه:

۱) PersianCalendarWidget / PersianCalendarPopup — تقویم شمسی سه‌مرحله‌ای
۲) NumberInput — ورودی عددی صحیح با قالب‌بندی هزارگان

تقویم سه‌مرحله‌ای (نسخه ۳.۰):
    • نمای روز: هدر سبز «نام ماه + سال» + دکمه‌های ماه قبل/بعد
    • کلیک روی هدر ← نمای انتخاب ماه (۱۲ ماه + دکمه‌های سال قبل/بعد)
    • کلیک روی سال ← نمای انتخاب سال (دههٔ ۱۰ ساله + دهه قبل/بعد)
    • دکمهٔ «امروز» برای بازگشت فوری به ماه جاری
    • باز شدن تقویم روی تاریخ فعلی فیلد (اگر معتبر باشد)
    • پس‌زمینهٔ روشن صریح — سازگار با «تم تاریک» ویندوز

NumberInput (نسخه ۳.۰):
    • اعتبارسنج جدید: فقط رقم (لاتین/فارسی) و جداکنندهٔ کاما مجاز
      است؛ نقطهٔ اعشار (.)، ممیز فارسی (٫)، علامت منفی و حروف هنگام
      تایپ یا Paste رد می‌شوند — ورود عدد اعشاری عملاً ممکن نیست.
"""

import jdatetime
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QValidator
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QStackedLayout, QPushButton, QLabel, QLineEdit, QFrame,
)

from core import utils

PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

# تبدیل ارقام لاتین به فارسی برای نمایش در هدر تقویم
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _to_fa(text):
    """تبدیل ارقام لاتین متن به ارقام فارسی."""
    return str(text).translate(_FA_DIGITS)


# ------------------------------------------------------------------ #
# تقویم شمسی سه‌مرحله‌ای
# ------------------------------------------------------------------ #
class PersianCalendarWidget(QWidget):
    """
    ویجت اختصاصی تقویم شمسی با سه نمای روز / ماه / سال.

    ناوبری:
        نمای روز  ← [► ماه قبل] [نام ماه + سال (کلیک = نمای ماه)] [◄ ماه بعد]
        نمای ماه  ← [► سال قبل] [سال (کلیک = نمای سال)] [◄ سال بعد] + ۱۲ ماه
        نمای سال  ← [► دهه قبل] [بازهٔ دهه] [◄ دهه بعد] + ۱۰ سال
    """

    MIN_YEAR, MAX_YEAR = 1300, 1500

    def __init__(self, date_field, parent=None):
        super().__init__(parent)
        # بدون این صفت، قاعدهٔ «PersianCalendarWidget { background ... }»
        # روی QWidget سفارشی رنگ نمی‌شود و در ویندوز با تم تاریک،
        # پس‌زمینهٔ تیرهٔ دیالوگ از پشت دیده می‌شد (متن هدر ناخوانا).
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.date_field = date_field
        self.today = jdatetime.date.today()
        # اگر فیلد از قبل تاریخ معتبر دارد، تقویم روی همان باز شود
        self.current_date = self._initial_date()
        self._view = "days"  # days | months | years

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.stack = QStackedLayout()
        root.addLayout(self.stack)
        self.stack.addWidget(self._build_days_page())    # index 0
        self.stack.addWidget(self._build_months_page())  # index 1
        self.stack.addWidget(self._build_years_page())   # index 2

        root.addWidget(self._build_today_button())

        self.setMinimumSize(320, 330)
        self._apply_style()
        self.refresh()

    # ---------------- جریان تاریخ ---------------- #
    def _initial_date(self):
        """تاریخ اولیهٔ تقویم: تاریخ فعلی فیلد یا امروز."""
        try:
            text = (self.date_field.text() or "").strip()
        except Exception:  # noqa: BLE001 - فیلد بدون متن
            text = ""
        if utils.is_valid_shamsi_date(text):
            try:
                y, m, d = map(int, text.split("/"))
                return jdatetime.date(y, m, d)
            except ValueError:
                pass
        return jdatetime.date.today()

    def get_days_in_month(self, year, month):
        # پیدا کردن تعداد روزهای ماه در تقویم جلالی
        for day in range(31, 27, -1):
            try:
                jdatetime.date(year, month, day)
                return day
            except ValueError:
                continue
        return 28

    def _shift_month(self, delta):
        y, m = self.current_date.year, self.current_date.month + delta
        if m == 0:
            m, y = 12, y - 1
        elif m == 13:
            m, y = 1, y + 1
        if not (self.MIN_YEAR <= y <= self.MAX_YEAR):
            return
        self.current_date = jdatetime.date(y, m, 1)
        self.refresh()

    def _shift_year(self, delta):
        y = self.current_date.year + delta
        if not (self.MIN_YEAR <= y <= self.MAX_YEAR):
            return
        try:
            self.current_date = jdatetime.date(y, self.current_date.month, 1)
        except ValueError:
            self.current_date = jdatetime.date(y, 1, 1)
        self.refresh()

    def _pick_month(self, month):
        try:
            self.current_date = jdatetime.date(
                self.current_date.year, month, 1)
        except ValueError:
            return
        self._view = "days"
        self.refresh()

    def _pick_year(self, year):
        try:
            self.current_date = jdatetime.date(
                year, self.current_date.month, 1)
        except ValueError:
            self.current_date = jdatetime.date(year, 1, 1)
        self._view = "months"
        self.refresh()

    def go_today(self):
        """بازگشت فوری به ماه جاری."""
        self.current_date = self.today
        self._view = "days"
        self.refresh()

    def day_clicked(self, day):
        # درج تاریخ انتخاب‌شده در فیلد مربوطه
        selected_date = jdatetime.date(
            self.current_date.year, self.current_date.month, day)
        self.date_field.setText(selected_date.strftime("%Y/%m/%d"))

        # اگر ویجت درون یک دیالوگ باز شده باشد، به‌طور خودکار بسته شود
        parent_window = self.window()
        if isinstance(parent_window, QDialog):
            parent_window.accept()

    # ---------------- ساخت صفحات ---------------- #
    def _make_nav_button(self, glyph, tooltip, on_click):
        btn = QPushButton(glyph)
        btn.setObjectName("calNavBtn")
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(on_click)
        return btn

    def _make_header_bar(self, prev_btn, center_widget, next_btn):
        """نوار سبز هدر: در چیدمان راست‌به‌چپ دکمهٔ «قبل» سمت راست است."""
        bar = QFrame()
        bar.setObjectName("calHeaderBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 5, 8, 5)
        lay.setSpacing(6)
        lay.addWidget(prev_btn)
        lay.addStretch(1)
        lay.addWidget(center_widget)
        lay.addStretch(1)
        lay.addWidget(next_btn)
        return bar

    def _build_days_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.prev_month_btn = self._make_nav_button(
            "►", "ماه قبل", lambda: self._shift_month(-1))
        self.next_month_btn = self._make_nav_button(
            "◄", "ماه بعد", lambda: self._shift_month(1))

        self.month_year_btn = QPushButton()
        self.month_year_btn.setObjectName("calTitleBtn")
        self.month_year_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_year_btn.setToolTip("انتخاب ماه و سال")
        self.month_year_btn.clicked.connect(
            lambda: self._set_view("months"))

        lay.addWidget(self._make_header_bar(
            self.prev_month_btn, self.month_year_btn, self.next_month_btn))

        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(4)
        lay.addLayout(self.calendar_grid)
        lay.addStretch(1)
        return page

    def _build_months_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.prev_year_btn = self._make_nav_button(
            "►", "سال قبل", lambda: self._shift_year(-1))
        self.next_year_btn = self._make_nav_button(
            "◄", "سال بعد", lambda: self._shift_year(1))

        self.year_btn = QPushButton()
        self.year_btn.setObjectName("calTitleBtn")
        self.year_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.year_btn.setToolTip("انتخاب سال")
        self.year_btn.clicked.connect(lambda: self._set_view("years"))

        lay.addWidget(self._make_header_bar(
            self.prev_year_btn, self.year_btn, self.next_year_btn))

        self.months_grid = QGridLayout()
        self.months_grid.setSpacing(6)
        lay.addLayout(self.months_grid)
        lay.addStretch(1)
        return page

    def _build_years_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.prev_decade_btn = self._make_nav_button(
            "►", "ده سال قبل", lambda: self._shift_year(-10))
        self.next_decade_btn = self._make_nav_button(
            "◄", "ده سال بعد", lambda: self._shift_year(10))

        self.decade_label = QLabel()
        self.decade_label.setObjectName("calTitleLbl")
        self.decade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(self._make_header_bar(
            self.prev_decade_btn, self.decade_label, self.next_decade_btn))

        self.years_grid = QGridLayout()
        self.years_grid.setSpacing(6)
        lay.addLayout(self.years_grid)
        lay.addStretch(1)
        return page

    def _build_today_button(self):
        self.today_btn = QPushButton(
            f"امروز: {_to_fa(self.today.strftime('%Y/%m/%d'))}")
        self.today_btn.setObjectName("calTodayBtn")
        self.today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.today_btn.setToolTip("رفتن به ماه جاری")
        self.today_btn.clicked.connect(self.go_today)
        return self.today_btn

    # ---------------- رندر ---------------- #
    def _set_view(self, view):
        self._view = view
        self.refresh()

    def refresh(self):
        if self._view == "months":
            self._render_months()
            self.stack.setCurrentIndex(1)
        elif self._view == "years":
            self._render_years()
            self.stack.setCurrentIndex(2)
        else:
            self._render_days()
            self.stack.setCurrentIndex(0)

    @staticmethod
    def _clear_layout(layout):
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def _render_days(self):
        y, m = self.current_date.year, self.current_date.month
        self.month_year_btn.setText(
            f"{PERSIAN_MONTHS[m - 1]} {_to_fa(y)}")
        self._clear_layout(self.calendar_grid)

        # حروف اول روزهای هفته — ستون ۰ در چیدمان راست‌به‌چپ = «ش»
        for col, day in enumerate(["ش", "ی", "د", "س", "چ", "پ", "ج"]):
            label = QLabel(day)
            label.setObjectName("calWeekday")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.calendar_grid.addWidget(label, 0, col)

        first_day = jdatetime.date(y, m, 1)
        last_day = self.get_days_in_month(y, m)
        start_col = first_day.weekday()
        in_today_month = (y == self.today.year and m == self.today.month)

        day_count = 1
        for row in range(6):  # حداکثر ۶ ردیف برای تقویم
            for col in range(7):
                if (row == 0 and col < start_col) or day_count > last_day:
                    continue
                is_today = in_today_month and day_count == self.today.day
                button = QPushButton(str(day_count))
                button.setObjectName("calDayToday" if is_today else "calDay")
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.clicked.connect(
                    lambda _=False, d=day_count: self.day_clicked(d))
                self.calendar_grid.addWidget(button, row + 1, col)
                day_count += 1

    def _render_months(self):
        y = self.current_date.year
        self.year_btn.setText(_to_fa(y))
        self._clear_layout(self.months_grid)

        for idx, name in enumerate(PERSIAN_MONTHS):
            month = idx + 1
            is_browsed = (month == self.current_date.month)
            is_today = (month == self.today.month and y == self.today.year)
            button = QPushButton(name)
            if is_browsed:
                button.setObjectName("calMonthSelected")
            elif is_today:
                button.setObjectName("calMonthToday")
            else:
                button.setObjectName("calMonth")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _=False, m=month: self._pick_month(m))
            self.months_grid.addWidget(button, idx // 4, idx % 4)

    def _render_years(self):
        y = self.current_date.year
        decade_start = y - (y % 10)
        self.decade_label.setText(
            f"{_to_fa(decade_start)} – {_to_fa(decade_start + 9)}")
        self._clear_layout(self.years_grid)

        for i in range(10):
            year = decade_start + i
            is_browsed = (year == self.current_date.year)
            is_today = (year == self.today.year)
            button = QPushButton(_to_fa(year))
            if is_browsed:
                button.setObjectName("calMonthSelected")
            elif is_today:
                button.setObjectName("calMonthToday")
            else:
                button.setObjectName("calMonth")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _=False, yr=year: self._pick_year(yr))
            self.years_grid.addWidget(button, i // 5, i % 5)

    # ---------------- استایل ---------------- #
    def _apply_style(self):
        self.setStyleSheet("""
            PersianCalendarWidget {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }

            /* نوار سبز هدر — متن سفید درشت و کاملاً خوانا */
            QFrame#calHeaderBar {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                border-radius: 10px;
            }
            QPushButton#calNavBtn {
                background-color: rgba(255, 255, 255, 0.20);
                color: white;
                border: none;
                border-radius: 7px;
                font-family: 'Vazir', 'Arial';
                font-size: 13px;
                font-weight: bold;
                min-width: 34px;
                min-height: 28px;
            }
            QPushButton#calNavBtn:hover {
                background-color: rgba(255, 255, 255, 0.34);
            }
            QPushButton#calTitleBtn {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 8px;
                font-family: 'Vazir', 'Arial';
                font-size: 15px;
                font-weight: bold;
                padding: 4px 14px;
            }
            QPushButton#calTitleBtn:hover {
                background-color: rgba(255, 255, 255, 0.16);
            }
            QLabel#calTitleLbl {
                color: white;
                font-family: 'Vazir', 'Arial';
                font-size: 15px;
                font-weight: bold;
                padding: 4px 10px;
                background: transparent;
            }

            /* روزهای هفته */
            QLabel#calWeekday {
                color: #64748b;
                font-family: 'Vazir', 'Arial';
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }

            /* سلول‌های روز */
            QPushButton#calDay {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #e5eaf1;
                border-radius: 8px;
                font-family: 'Vazir', 'Arial';
                font-size: 12.5px;
                min-width: 36px;
                min-height: 30px;
            }
            QPushButton#calDay:hover {
                background-color: #dcfce7;
                color: #14532d;
                border-color: #86efac;
            }
            QPushButton#calDayToday {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                color: white;
                border: none;
                border-radius: 8px;
                font-family: 'Vazir', 'Arial';
                font-size: 12.5px;
                font-weight: bold;
                min-width: 36px;
                min-height: 30px;
            }
            QPushButton#calDayToday:hover {
                background-color: #15803d;
            }

            /* دکمه‌های ماه/سال در نماهای انتخاب */
            QPushButton#calMonth {
                background-color: #ffffff;
                color: #1e293b;
                border: 1px solid #e5eaf1;
                border-radius: 9px;
                font-family: 'Vazir', 'Arial';
                font-size: 13px;
                min-height: 38px;
            }
            QPushButton#calMonth:hover {
                background-color: #dcfce7;
                color: #14532d;
                border-color: #86efac;
            }
            QPushButton#calMonthToday {
                background-color: #ffffff;
                color: #166534;
                border: 2px solid #16a34a;
                border-radius: 9px;
                font-family: 'Vazir', 'Arial';
                font-size: 13px;
                font-weight: bold;
                min-height: 38px;
            }
            QPushButton#calMonthToday:hover {
                background-color: #dcfce7;
            }
            QPushButton#calMonthSelected {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                color: white;
                border: none;
                border-radius: 9px;
                font-family: 'Vazir', 'Arial';
                font-size: 13px;
                font-weight: bold;
                min-height: 38px;
            }
            QPushButton#calMonthSelected:hover {
                background-color: #15803d;
            }

            /* دکمهٔ امروز */
            QPushButton#calTodayBtn {
                background-color: #f1f5f9;
                color: #166534;
                border: 1px solid #e2e8f0;
                border-radius: 9px;
                font-family: 'Vazir', 'Arial';
                font-size: 12.5px;
                font-weight: bold;
                padding: 7px;
            }
            QPushButton#calTodayBtn:hover {
                background-color: #dcfce7;
                border-color: #86efac;
            }
        """)


class PersianCalendarPopup(QDialog):
    """
    دیالوگی که ویجت تقویم شمسی را به صورت پاپ‌آپ نمایش می‌دهد.

    پس‌زمینهٔ صریح روشن دارد؛ در ویندوز با «تم تاریک»، دیالوگِ بدون
    استایل از پالت سیستم رنگ تیره می‌گرفت و متن‌های تقویم ناخوانا
    می‌شدند (مشابه اصلاح QMessageBox در styles.qss).
    """
    def __init__(self, date_edit, parent=None):
        super().__init__(parent)
        self.date_edit = date_edit
        self.setWindowTitle("انتخاب تاریخ")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("QDialog { background-color: #ffffff; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        # پاس دادن date_edit به PersianCalendarWidget تا تاریخ در آن نوشته شود
        self.calendar = PersianCalendarWidget(self.date_edit)
        layout.addWidget(self.calendar)

        self.setFixedWidth(378)
        self.adjustSize()


# ------------------------------------------------------------------ #
# ورودی عددی صحیح
# ------------------------------------------------------------------ #
class _DigitsOnlyValidator(QValidator):
    """اعتبارسنج ورودی عددی: فقط ارقام و جداکنندهٔ هزارگان.

    نقطهٔ اعشار (.)، ممیز اعشار فارسی (٫)، علامت منفی، فاصله و حروف
    — همگی پیش از نمایش در فیلد رد می‌شوند؛ در نتیجه ورود عدد اعشاری
    از طریق تایپ یا Paste عملاً ممکن نیست.
    """

    def validate(self, text, pos):
        cleaned = str(text).replace(",", "")
        if cleaned == "" or cleaned.isdigit():
            return QValidator.State.Acceptable, text, pos
        return QValidator.State.Invalid, text, pos


class NumberInput(QLineEdit):
    """
    تکست‌باکس سفارشی برای ورود مقادیر پولی و عددی.

    • فقط اعداد صحیح مثبت پذیرفته می‌شود (اعشار و منفی رد می‌شود).
    • قالب‌بندی هزارگان خودکار حین تایپ (مثلاً 14,000,000).
    • ارقام فارسی هم پذیرفته و به قالب لاتین نرمال می‌شوند.
    • مقدار صفر با پس‌زمینهٔ قرمز کم‌رنگ مشخص می‌شود.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setValidator(_DigitsOnlyValidator(self))
        self.textChanged.connect(self.format_input)

    def format_input(self):
        text = self.text().replace(",", "")  # حذف جداکننده‌ها برای پردازش

        if text and text == "0":
            self.setStyleSheet("background-color: #ffe6e6;")  # خطا: صفر
            return

        if text.isdigit():
            # format_amount همیشه جداکنندهٔ کاما تولید می‌کند — مستقل از
            # locale سیستم (در ویندوز با لوکیل فارسی گروه‌بندی نمی‌شد).
            formatted = utils.format_amount(int(text))
            self.blockSignals(True)  # جلوگیری از فراخوانی دوباره
            self.setText(formatted)
            self.setCursorPosition(len(formatted))  # مکان‌نما به انتها
            self.blockSignals(False)
            self.setStyleSheet("")  # بازگرداندن استایل پیش‌فرض

    def get_raw_value(self):
        # برگرداندن عدد صحیح خالص جهت ذخیره در دیتابیس
        text = self.text().replace(",", "")
        if text.isdigit():
            value = int(text)
            if value <= 0:
                return None  # مقادیر صفر یا منفی نامعتبر هستند
            return value
        return None
