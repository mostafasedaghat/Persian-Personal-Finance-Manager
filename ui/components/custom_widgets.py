import jdatetime
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QPushButton, QLabel, QLineEdit
)
from PyQt6.QtCore import Qt
from core import utils  # ایمپورت توابع کمکی برای استفاده در NumberInput

class PersianCalendarWidget(QWidget):
    """
    ویجت اختصاصی برای نمایش تقویم شمسی به صورت درون‌برنامه‌ای
    """
    def __init__(self, date_field, parent=None):
        super().__init__(parent)
        self.date_field = date_field
        self.current_date = jdatetime.date.today()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setMinimumSize(300, 250)  # اندازه کلی برای خوانایی بهتر

        # هدر تقویم
        self.header_layout = QHBoxLayout()
        self.prev_month_btn = QPushButton("<")
        self.next_month_btn = QPushButton(">")
        self.month_label = QLabel()
        self.update_month_label()
        
        self.header_layout.addWidget(self.prev_month_btn)
        self.header_layout.addWidget(self.month_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.header_layout.addWidget(self.next_month_btn)
        self.main_layout.addLayout(self.header_layout)

        # گرید روزهای هفته
        self.calendar_grid = QGridLayout()
        self.main_layout.addLayout(self.calendar_grid)

        # استایل‌دهی
        self.setStyleSheet("""
            PersianCalendarWidget {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 3px;
                font-family: Vazir, Arial;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLabel {
                font-family: Vazir, Arial;
                font-size: 14px;
                color: #333;
                padding: 5px;
            }
            QGridLayout {
                margin: 5px;
            }
        """)

        # اتصال سیگنال‌ها
        self.prev_month_btn.clicked.connect(self.prev_month)
        self.next_month_btn.clicked.connect(self.next_month)
        self.update_calendar()

    def update_month_label(self):
        self.month_label.setText(f"{self.current_date.year}/{self.current_date.month:02d}")

    def get_days_in_month(self, year, month):
        # پیدا کردن تعداد روزهای ماه در تقویم جلالی
        for day in range(31, 27, -1):
            try:
                jdatetime.date(year, month, day)
                return day
            except ValueError:
                continue
        return 28

    def update_calendar(self):
        # پاک کردن روزهای قبلی از گرید
        for i in reversed(range(self.calendar_grid.count())):
            widget = self.calendar_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # نمایش حروف اول روزهای هفته
        days = ["ش", "ی", "د", "س", "چ", "پ", "ج"]
        for col, day in enumerate(days):
            label = QLabel(day)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: bold; color: #444;")
            self.calendar_grid.addWidget(label, 0, col)

        # محاسبه روزهای ماه
        first_day = jdatetime.date(self.current_date.year, self.current_date.month, 1)
        last_day = self.get_days_in_month(self.current_date.year, self.current_date.month)
        start_col = first_day.weekday()
        day_count = 1

        # تنظیم ارتفاع ردیف‌ها و افزودن دکمه‌های روز
        for row in range(6):  # حداکثر ۶ ردیف برای تقویم
            self.calendar_grid.setRowMinimumHeight(row + 1, 40)
            for col in range(7):
                if (row == 0 and col < start_col) or day_count > last_day:
                    continue
                
                button = QPushButton(str(day_count))
                button.clicked.connect(lambda checked, d=day_count: self.day_clicked(d))
                button.setMinimumSize(40, 40)
                button.setStyleSheet("""
                    QPushButton {
                        background-color: #fff;
                        color: #333;
                        border: 1px solid #ddd;
                        border-radius: 3px;
                        font-family: Vazir, Arial;
                        font-size: 12px;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                """)
                self.calendar_grid.addWidget(button, row + 1, col)
                day_count += 1

    def prev_month(self):
        year = self.current_date.year
        month = self.current_date.month - 1
        if month == 0:
            month = 12
            year -= 1
        self.current_date = jdatetime.date(year, month, 1)
        self.update_month_label()
        self.update_calendar()

    def next_month(self):
        year = self.current_date.year
        month = self.current_date.month + 1
        if month == 13:
            month = 1
            year += 1
        self.current_date = jdatetime.date(year, month, 1)
        self.update_month_label()
        self.update_calendar()

    def day_clicked(self, day):
        # درج تاریخ انتخاب شده در فیلد مربوطه
        selected_date = jdatetime.date(self.current_date.year, self.current_date.month, day)
        self.date_field.setText(selected_date.strftime("%Y/%m/%d"))
        
        # اگر ویجت درون یک دیالوگ (مثل PersianCalendarPopup) باز شده است، دیالوگ به طور خودکار بسته شود
        parent_window = self.window()
        if isinstance(parent_window, QDialog):
            parent_window.accept()


class PersianCalendarPopup(QDialog):
    """
    دیالوگی که ویجت تقویم شمسی را به صورت پاپ‌آپ روی صفحه نمایش می‌دهد
    """
    def __init__(self, date_edit, parent=None):
        super().__init__(parent)
        self.date_edit = date_edit
        self.setWindowTitle("انتخاب تاریخ")
        
        layout = QVBoxLayout()
        # پاس دادن date_edit به PersianCalendarWidget تا تاریخ در آن نوشته شود
        self.calendar = PersianCalendarWidget(self.date_edit)
        layout.addWidget(self.calendar)
        
        self.setLayout(layout)


class NumberInput(QLineEdit):
    """
    تکست‌باکس سفارشی برای ورود مقادیر پولی و عددی
    همراه با قالب‌بندی هزارگان و اعتبارسنجی مقادیر منفی/صفر
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.textChanged.connect(self.format_input)

    def format_input(self):
        text = self.text().replace(",", "")  # حذف جداکننده‌ها برای پردازش
        
        if text and (text.startswith('-') or text == '0'):
            self.setStyleSheet("background-color: #ffe6e6;")  # رنگ پس‌زمینه قرمز برای خطا
            return
            
        if text.isdigit():
            # استفاده از تابع کمکی در فایل core/utils.py
            formatted = utils.format_number(int(text))
            self.setText(formatted)
            self.setStyleSheet("")  # بازگرداندن استایل پیش‌فرض
            self.setCursorPosition(len(formatted))  # انتقال مکان‌نما به انتهای متن

    def get_raw_value(self):
        # برگرداندن عدد صحیح خالص جهت ذخیره در دیتابیس
        text = self.text().replace(",", "")
        if text.isdigit():
            value = int(text)
            if value <= 0:
                return None  # مقادیر صفر یا منفی نامعتبر هستند
            return value
        return None
