import sys
import locale
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                             QTableWidgetItem, QLabel, QLineEdit, QComboBox,
                             QMessageBox, QFormLayout, QGridLayout, QScrollArea, 
                             QDialog, QCheckBox, QCalendarWidget)
from PyQt6.QtCore import QDate, Qt, QTimer, QLocale  # اضافه کردن QLocale
from PyQt6.QtGui import QIcon, QFont, QColor
import sqlite3
import jdatetime
from datetime import datetime

# تنظیم locale برای جداکننده اعداد
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# توابع تبدیل تاریخ
def gregorian_to_shamsi(date):
    try:
        if isinstance(date, QDate):
            date_str = date.toString("yyyy-MM-dd")
        else:
            date_str = date
        g_date = QDate.fromString(date_str, "yyyy-MM-dd")
        if not g_date.isValid():
            return date_str
        j_date = jdatetime.date.fromgregorian(year=g_date.year(), month=g_date.month(), day=g_date.day())
        return j_date.strftime("%Y/%m/%d")
    except Exception:
        return str(date)

def shamsi_to_gregorian(date_str):
    try:
        j_year, j_month, j_day = map(int, date_str.replace('/', '-').split('-'))
        jdatetime.date(j_year, j_month, j_day)  # بررسی اعتبار تاریخ شمسی
        g_date = jdatetime.date(j_year, j_month, j_day).togregorian()
        return f"{g_date.year}-{g_date.month:02d}-{g_date.day:02d}"
    except Exception:
        return None  # یا یک مقدار پیش‌فرض

def is_valid_shamsi_date(date_str):
    return bool(re.match(r"^\d{4}/\d{2}/\d{2}$", date_str))

def format_number(number):
    return locale.format_string("%d", int(number), grouping=True)

# ویجت تقویم شمسی
class PersianCalendarWidget(QWidget):
    def __init__(self, date_field, parent=None):
        super().__init__(parent)
        self.date_field = date_field
        self.current_date = jdatetime.date.today()
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.setMinimumSize(300, 250)  # افزایش اندازه کلی برای خوانایی بهتر

        # هدر تقویم
        self.header_layout = QHBoxLayout()
        self.prev_month_btn = QPushButton("<")
        self.next_month_btn = QPushButton(">")
        self.month_label = QLabel()
        self.update_month_label()
        self.header_layout.addWidget(self.prev_month_btn)
        self.header_layout.addWidget(self.month_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.header_layout.addWidget(self.next_month_btn)
        self.layout.addLayout(self.header_layout)

        # گرید روزهای هفته
        self.calendar_grid = QGridLayout()
        self.layout.addLayout(self.calendar_grid)

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

        self.prev_month_btn.clicked.connect(self.prev_month)
        self.next_month_btn.clicked.connect(self.next_month)
        self.update_calendar()

    def update_month_label(self):
        self.month_label.setText(f"{self.current_date.year}/{self.current_date.month:02d}")

    def get_days_in_month(self, year, month):
        for day in range(31, 27, -1):
            try:
                jdatetime.date(year, month, day)
                return day
            except ValueError:
                continue
        return 28

    def update_calendar(self):
        for i in reversed(range(self.calendar_grid.count())):
            self.calendar_grid.itemAt(i).widget().setParent(None)
        
        # نمایش روزهای هفته
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

        # تنظیم ارتفاع ردیف‌ها برای جلوگیری از برش متن
        for row in range(6):  # حداکثر 6 ردیف برای تقویم
            self.calendar_grid.setRowMinimumHeight(row + 1, 40)  # ارتفاع ردیف‌ها
            for col in range(7):
                if (row == 0 and col < start_col) or day_count > last_day:
                    continue
                button = QPushButton(str(day_count))
                button.clicked.connect(lambda checked, d=day_count: self.day_clicked(d))
                button.setMinimumSize(40, 40)  # اندازه حداقل دکمه برای نمایش اعداد بزرگ
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
        selected_date = jdatetime.date(self.current_date.year, self.current_date.month, day)
        self.date_field.setText(selected_date.strftime("%Y/%m/%d"))

class PersianCalendarPopup(QDialog):
    def __init__(self, date_edit, parent=None):
        super().__init__(parent)
        self.date_edit = date_edit
        self.setWindowTitle("انتخاب تاریخ")
        layout = QVBoxLayout()
        self.calendar = PersianCalendarWidget(self.date_edit)  # پاس دادن date_edit به PersianCalendarWidget
        layout.addWidget(self.calendar)
        self.setLayout(layout)

    # نیازی به متد set_date نیست چون PersianCalendarWidget خودش تاریخ رو ست می‌کنه

class NumberInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.textChanged.connect(self.format_input)

    def format_input(self):
        text = self.text().replace(",", "")  # حذف جداکننده‌ها برای پردازش
        if text.isdigit():
            formatted = format_number(int(text))
            self.setText(formatted)
            self.setCursorPosition(len(formatted))  # مکان‌نما رو آخر متن می‌بره

    def get_raw_value(self):
        text = self.text().replace(",", "")
        if text.isdigit():
            return int(text)
        return 0  # یا مقدار پیش‌فرض دیگر

class FinanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نرم‌افزار حسابداری شخصی - حرفه‌ای")
        self.setGeometry(100, 100, 1200, 900)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                font-family: Vazir, Arial;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-family: Vazir, Arial;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTableWidget {
                background-color: white;
                color: black;
                font-family: Vazir, Arial;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #4CAF50;
                border: none;
            }
            QTableWidget QHeaderView::section {
                background-color: #4CAF50;
                color: white;
                padding: 5px;
                border: none;
                font-family: Vazir, Arial;
            }
            QLineEdit, QComboBox, QLabel {
                background-color: white;
                color: black;
                font-family: Vazir, Arial;
            }
            PersianCalendarWidget QPushButton {
                background-color: #666;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-family: Vazir, Arial;
            }
            PersianCalendarWidget QPushButton:hover {
                background-color: #555;
            }
        """)
        
        self.init_db()
        self.init_ui()
        self.load_data()
        
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(86400000)

    def init_db(self):
        try:
            self.conn = sqlite3.connect('finance.db')
            self.cursor = self.conn.cursor()
            
            self.cursor.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    balance REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE,
                    type TEXT CHECK(type IN ('income', 'expense'))
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    account_id INTEGER,
                    person_id INTEGER,
                    category_id INTEGER,
                    amount REAL,
                    date TEXT,
                    description TEXT,
                    FOREIGN KEY (account_id) REFERENCES accounts(id),
                    FOREIGN KEY (person_id) REFERENCES persons(id),
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                );
                CREATE TABLE IF NOT EXISTS debts (
                    id INTEGER PRIMARY KEY,
                    person_id INTEGER,
                    amount REAL,
                    paid_amount REAL DEFAULT 0,
                    due_date TEXT,  -- nullable
                    is_paid INTEGER DEFAULT 0,
                    account_id INTEGER,
                    show_in_dashboard INTEGER DEFAULT 0,  -- ستون جدید
                    FOREIGN KEY (person_id) REFERENCES persons(id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                );
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY,
                    type TEXT CHECK(type IN ('taken', 'given')),
                    bank_name TEXT,
                    total_amount REAL,
                    paid_amount REAL DEFAULT 0,
                    interest_rate REAL,
                    start_date TEXT,
                    end_date TEXT,
                    account_id INTEGER,
                    installments_total INTEGER,
                    installments_paid INTEGER DEFAULT 0,
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                );
                CREATE TABLE IF NOT EXISTS loan_installments (
                    id INTEGER PRIMARY KEY,
                    loan_id INTEGER,
                    amount REAL,
                    due_date TEXT,
                    is_paid INTEGER DEFAULT 0,
                    FOREIGN KEY (loan_id) REFERENCES loans(id)
                );
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE
                );
            """)
            self.conn.commit()

            # اضافه کردن ستون show_in_dashboard اگر وجود نداشته باشه
            self.cursor.execute("PRAGMA table_info(debts)")
            columns = [col[1] for col in self.cursor.fetchall()]
            if "show_in_dashboard" not in columns:
                self.cursor.execute("ALTER TABLE debts ADD COLUMN show_in_dashboard INTEGER DEFAULT 0")
                self.conn.commit()

            # بررسی وجود دسته‌بندی‌ها قبل از درج
            self.cursor.execute("SELECT COUNT(*) FROM categories")
            if self.cursor.fetchone()[0] == 0:
                self.cursor.executescript("""
                    INSERT OR IGNORE INTO categories (name, type) VALUES
                    ('حقوق', 'income'), ('فروش', 'income'), ('سایر درآمدها', 'income'),
                    ('خوراک', 'expense'), ('حمل‌ونقل', 'expense'), ('مسکن', 'expense'),
                    ('تفریح', 'expense'), ('خرید', 'expense'), ('سلامتی', 'expense'),
                    ('سایر هزینه‌ها', 'expense'),
                    ('انتقال بین حساب‌ها (خروج)', 'expense'), ('انتقال بین حساب‌ها (ورود)', 'income');
                """)
                self.conn.commit()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            raise

    def init_ui(self):
        app.setFont(QFont("Vazir", 10))
        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        dashboard_tab = self.create_dashboard_tab()
        accounts_tab = self.create_accounts_tab()
        transactions_tab = self.create_transactions_tab()
        debts_tab = self.create_debts_tab()
        loans_tab = self.create_loans_tab()
        reports_tab = self.create_reports_tab()
        persons_tab = self.create_persons_tab()
        categories_tab = self.create_categories_tab()

        tabs.addTab(dashboard_tab, "داشبورد")
        tabs.addTab(accounts_tab, "حساب‌ها")
        tabs.addTab(transactions_tab, "تراکنش‌ها")
        tabs.addTab(debts_tab, "بدهی/طلب")
        tabs.addTab(loans_tab, "وام‌ها")
        tabs.addTab(reports_tab, "گزارش‌ها")
        tabs.addTab(persons_tab, "اشخاص")
        tabs.addTab(categories_tab, "دسته‌بندی‌ها")

        # فراخوانی update_dashboard هنگام تغییر تب
        tabs.currentChanged.connect(self.on_tab_changed)

        scroll = QScrollArea()
        scroll.setWidget(tabs)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

    def on_tab_changed(self, index):
        if index == 0:  # تب داشبورد
            self.update_dashboard()

    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        header = QWidget()
        header_layout = QHBoxLayout()
        header.setStyleSheet("background-color: #4CAF50; border-radius: 10px; padding: 10px;")
        title_label = QLabel("📊 داشبورد مالی")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.total_balance_label = QLabel("موجودی کل: ۰ تومان")
        self.total_balance_label.setStyleSheet("font-size: 18px; color: white;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.total_balance_label)
        header.setLayout(header_layout)
        layout.addWidget(header)

        # بخش بدهی‌ها و طلب‌ها
        debts_widget = QWidget()
        debts_layout = QVBoxLayout()
        debts_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px; margin-top: 10px;")
        debts_label = QLabel("💸 بدهی‌ها و طلب‌های مهم")
        debts_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        debts_layout.addWidget(debts_label)

        # جدول بدهی‌ها و طلب‌ها
        scroll_area_debts = QScrollArea()
        self.important_debts_table = QTableWidget()
        self.important_debts_table.setColumnCount(5)
        self.important_debts_table.setHorizontalHeaderLabels(["شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت"])
        self.important_debts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.important_debts_table.verticalHeader().setDefaultSectionSize(40)
        self.important_debts_table.setColumnWidth(0, 150)  # شخص
        self.important_debts_table.setColumnWidth(1, 100)  # مبلغ
        self.important_debts_table.setColumnWidth(2, 100)  # پرداخت شده
        self.important_debts_table.setColumnWidth(3, 100)  # سررسید
        self.important_debts_table.setColumnWidth(4, 80)   # وضعیت
        scroll_area_debts.setWidget(self.important_debts_table)
        scroll_area_debts.setWidgetResizable(True)
        scroll_area_debts.setMinimumHeight(200)
        debts_layout.addWidget(scroll_area_debts)
        debts_widget.setLayout(debts_layout)
        layout.addWidget(debts_widget)

        recent_widget = QWidget()
        recent_layout = QVBoxLayout()
        recent_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px; margin-top: 10px;")
        recent_label = QLabel("📜 تراکنش‌های اخیر")
        recent_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        recent_layout.addWidget(recent_label)

        # جدول تراکنش‌های اخیر با اسکرول
        scroll_area = QScrollArea()
        self.recent_transactions_table = QTableWidget()
        self.recent_transactions_table.setColumnCount(6)
        self.recent_transactions_table.setHorizontalHeaderLabels(["تاریخ", "حساب", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"])
        self.recent_transactions_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.recent_transactions_table.verticalHeader().setDefaultSectionSize(40)
        scroll_area.setWidget(self.recent_transactions_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        recent_layout.addWidget(scroll_area)

        # اضافه کردن دکمه‌های صفحه‌بندی
        self.recent_current_page = 1
        self.recent_per_page = 50
        pagination_layout = QHBoxLayout()
        self.recent_prev_btn = QPushButton("صفحه قبلی")
        self.recent_next_btn = QPushButton("صفحه بعدی")
        self.recent_page_label = QLabel("صفحه 1")
        self.recent_prev_btn.clicked.connect(self.prev_recent_page)
        self.recent_next_btn.clicked.connect(self.next_recent_page)
        pagination_layout.addWidget(self.recent_prev_btn)
        pagination_layout.addWidget(self.recent_page_label)
        pagination_layout.addWidget(self.recent_next_btn)
        recent_layout.addLayout(pagination_layout)

        recent_widget.setLayout(recent_layout)
        layout.addWidget(recent_widget)

        tab.setLayout(layout)
        return tab

    def create_accounts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.account_name_input = QLineEdit()
        self.account_balance_input = NumberInput()  # جایگزینی با NumberInput
        add_account_btn = QPushButton("افزودن حساب")
        add_account_btn.clicked.connect(self.add_account)
        form_layout.addRow("نام حساب:", self.account_name_input)
        form_layout.addRow("موجودی اولیه:", self.account_balance_input)
        form_layout.addRow(add_account_btn)
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)
        self.accounts_table.setHorizontalHeaderLabels(["شناسه", "نام حساب", "موجودی"])
        self.accounts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addLayout(form_layout)
        layout.addWidget(self.accounts_table)
        tab.setLayout(layout)
        return tab

    # اصلاح متد create_transactions_tab
    def create_transactions_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # فرم ثبت تراکنش
        transaction_form = QFormLayout()
        self.transaction_account = QComboBox()
        self.transaction_person = QComboBox()
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(["درآمد", "هزینه"])
        self.transaction_category = QComboBox()
        self.transaction_type.currentTextChanged.connect(self.update_categories)
        self.load_categories()
        self.transaction_amount = NumberInput()
        self.transaction_date = QLineEdit()
        # تنظیم تاریخ پیش‌فرض به امروز
        today = datetime.now().date()
        self.transaction_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.transaction_date.setPlaceholderText("1404/02/13")
        self.transaction_date.setReadOnly(True)
        self.transaction_date.mousePressEvent = lambda event: self.show_calendar_popup(self.transaction_date)
        self.transaction_desc = QLineEdit()
        add_transaction_btn = QPushButton("ثبت تراکنش")
        add_transaction_btn.clicked.connect(self.add_transaction)
        transaction_form.addRow("حساب:", self.transaction_account)
        transaction_form.addRow("شخص:", self.transaction_person)
        transaction_form.addRow("نوع:", self.transaction_type)
        transaction_form.addRow("دسته‌بندی:", self.transaction_category)
        transaction_form.addRow("مبلغ:", self.transaction_amount)
        transaction_form.addRow("تاریخ (شمسی):", self.transaction_date)
        transaction_form.addRow(add_transaction_btn)
        layout.addLayout(transaction_form)

        # فرم انتقال پول بین حساب‌ها
        transfer_form = QFormLayout()
        transfer_label = QLabel("انتقال پول بین حساب‌ها")
        transfer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.transfer_from_account = QComboBox()
        self.transfer_to_account = QComboBox()
        self.transfer_amount = NumberInput()
        self.transfer_date = QLineEdit()
        self.transfer_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.transfer_date.setPlaceholderText("1404/02/13")
        self.transfer_date.setReadOnly(True)
        self.transfer_date.mousePressEvent = lambda event: self.show_calendar_popup(self.transfer_date)
        transfer_btn = QPushButton("انتقال")
        transfer_btn.clicked.connect(self.transfer_money)
        transfer_form.addRow(transfer_label)
        transfer_form.addRow("از حساب:", self.transfer_from_account)
        transfer_form.addRow("به حساب:", self.transfer_to_account)
        transfer_form.addRow("مبلغ:", self.transfer_amount)
        transfer_form.addRow("تاریخ (شمسی):", self.transfer_date)
        transfer_form.addRow(transfer_btn)
        layout.addLayout(transfer_form)

        # جدول تراکنش‌ها با اسکرول
        scroll_area = QScrollArea()
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(10)
        self.transactions_table.setHorizontalHeaderLabels(["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات", "نوع", "ویرایش", "حذف"])
        self.transactions_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.transactions_table.verticalHeader().setDefaultSectionSize(40)
        scroll_area.setWidget(self.transactions_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        # اضافه کردن دکمه‌های صفحه‌بندی
        self.transactions_current_page = 1
        self.transactions_per_page = 50
        pagination_layout = QHBoxLayout()
        self.transactions_prev_btn = QPushButton("صفحه قبلی")
        self.transactions_next_btn = QPushButton("صفحه بعدی")
        self.transactions_page_label = QLabel("صفحه 1")
        self.transactions_prev_btn.clicked.connect(self.prev_transactions_page)
        self.transactions_next_btn.clicked.connect(self.next_transactions_page)
        pagination_layout.addWidget(self.transactions_prev_btn)
        pagination_layout.addWidget(self.transactions_page_label)
        pagination_layout.addWidget(self.transactions_next_btn)
        layout.addLayout(pagination_layout)

        tab.setLayout(layout)
        return tab
    
    def show_calendar_popup(self, date_edit):
        popup = PersianCalendarPopup(date_edit, self)
        popup.exec()

    # اصلاح متد create_debts_tab
    def create_debts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.debt_person = QComboBox()
        self.debt_amount = NumberInput()
        self.debt_account = QComboBox()
        self.debt_account.setEnabled(False)  # غیرفعال کردن پیش‌فرض
        self.debt_due_date = QLineEdit()
        # تنظیم تاریخ پیش‌فرض به امروز (اختیاری)
        today = datetime.now().date()
        self.debt_due_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.debt_due_date.setPlaceholderText("1404/02/13")
        self.debt_due_date.setReadOnly(True)
        self.debt_due_date.mousePressEvent = lambda event: self.show_calendar_popup(self.debt_due_date)
        self.debt_is_credit = QComboBox()
        self.debt_is_credit.addItems(["بدهی من", "طلب من"])
        # چک‌باکس برای "آیا پولی دریافت/پرداخت شده؟"
        self.debt_has_payment = QCheckBox("آیا پولی دریافت/پرداخت شده؟")
        self.debt_has_payment.stateChanged.connect(self.toggle_account_field)
        # چک‌باکس برای "نمایش در داشبورد"
        self.debt_show_in_dashboard = QCheckBox("نمایش در داشبورد")
        add_debt_btn = QPushButton("ثبت بدهی/طلب")
        add_debt_btn.clicked.connect(self.add_debt)
        form_layout.addRow("شخص:", self.debt_person)
        form_layout.addRow("مبلغ:", self.debt_amount)
        form_layout.addRow("حساب مرتبط:", self.debt_account)
        form_layout.addRow("", self.debt_has_payment)  # چک‌باکس
        form_layout.addRow("تاریخ سررسید (شمسی - اختیاری):", self.debt_due_date)
        form_layout.addRow("نوع:", self.debt_is_credit)
        form_layout.addRow("", self.debt_show_in_dashboard)  # چک‌باکس نمایش در داشبورد
        form_layout.addRow(add_debt_btn)
        layout.addLayout(form_layout)

        # جدول بدهی‌ها با اسکرول
        scroll_area = QScrollArea()
        self.debts_table = QTableWidget()
        self.debts_table.setColumnCount(10)  # اضافه کردن ستون تسویه
        self.debts_table.setHorizontalHeaderLabels(["شناسه", "شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت", "حساب", "ویرایش", "حذف", "تسویه"])
        self.debts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.debts_table.verticalHeader().setDefaultSectionSize(40)
        scroll_area.setWidget(self.debts_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        # اضافه کردن دکمه‌های صفحه‌بندی
        self.debts_current_page = 1
        self.debts_per_page = 50
        pagination_layout = QHBoxLayout()
        self.debts_prev_btn = QPushButton("صفحه قبلی")
        self.debts_next_btn = QPushButton("صفحه بعدی")
        self.debts_page_label = QLabel("صفحه 1")
        self.debts_prev_btn.clicked.connect(self.prev_debts_page)
        self.debts_next_btn.clicked.connect(self.next_debts_page)
        pagination_layout.addWidget(self.debts_prev_btn)
        pagination_layout.addWidget(self.debts_page_label)
        pagination_layout.addWidget(self.debts_next_btn)
        layout.addLayout(pagination_layout)

        tab.setLayout(layout)
        return tab

    def toggle_account_field(self, state):
        """فعال/غیرفعال کردن لیست حساب‌ها بر اساس وضعیت چک‌باکس"""
        self.debt_account.setEnabled(state == Qt.CheckState.Checked.value)

    # اصلاح متد create_loans_tab
    def create_loans_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.loan_type = QComboBox()
        self.loan_type.addItems(["وام گرفته‌شده", "وام داده‌شده"])
        self.loan_bank = QLineEdit()
        self.loan_amount = NumberInput()
        self.loan_interest = NumberInput()
        self.loan_account = QComboBox()
        self.loan_start_date = QLineEdit()
        # تنظیم تاریخ پیش‌فرض به امروز
        today = datetime.now().date()
        self.loan_start_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.loan_start_date.setPlaceholderText("1404/02/13")
        self.loan_start_date.setReadOnly(True)
        self.loan_start_date.mousePressEvent = lambda event: self.show_calendar_popup(self.loan_start_date)
        self.loan_installments_total = NumberInput()
        self.loan_installments_paid = NumberInput()
        self.loan_end_date = QLineEdit()
        self.loan_end_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.loan_end_date.setPlaceholderText("1405/02/13")
        self.loan_end_date.setReadOnly(True)
        self.loan_end_date.mousePressEvent = lambda event: self.show_calendar_popup(self.loan_end_date)
        add_loan_btn = QPushButton("ثبت وام")
        add_loan_btn.clicked.connect(self.add_loan)
        form_layout.addRow("نوع وام:", self.loan_type)
        form_layout.addRow("نام بانک:", self.loan_bank)
        form_layout.addRow("مبلغ:", self.loan_amount)
        form_layout.addRow("نرخ سود (%):", self.loan_interest)
        form_layout.addRow("حساب مرتبط:", self.loan_account)
        form_layout.addRow("تاریخ شروع (شمسی):", self.loan_start_date)
        form_layout.addRow("تعداد اقساط کل:", self.loan_installments_total)
        form_layout.addRow("تعداد اقساط پرداخت‌شده:", self.loan_installments_paid)
        form_layout.addRow("تاریخ پایان (شمسی):", self.loan_end_date)
        form_layout.addRow(add_loan_btn)
        layout.addLayout(form_layout)

        # جدول وام‌ها با اسکرول
        scroll_area = QScrollArea()
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(11)
        self.loans_table.setHorizontalHeaderLabels(["شناسه", "نوع", "بانک", "مبلغ", "پرداخت‌شده", "سود", "شروع", "پایان", "اقساط کل", "اقساط پرداخت", "اقدامات"])
        self.loans_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.loans_table.verticalHeader().setDefaultSectionSize(40)
        scroll_area.setWidget(self.loans_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        # اضافه کردن دکمه‌های صفحه‌بندی
        self.loans_current_page = 1
        self.loans_per_page = 50
        pagination_layout = QHBoxLayout()
        self.loans_prev_btn = QPushButton("صفحه قبلی")
        self.loans_next_btn = QPushButton("صفحه بعدی")
        self.loans_page_label = QLabel("صفحه 1")
        self.loans_prev_btn.clicked.connect(self.prev_loans_page)
        self.loans_next_btn.clicked.connect(self.next_loans_page)
        pagination_layout.addWidget(self.loans_prev_btn)
        pagination_layout.addWidget(self.loans_page_label)
        pagination_layout.addWidget(self.loans_next_btn)
        layout.addLayout(pagination_layout)

        tab.setLayout(layout)
        return tab

    def create_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.report_date_start = QLineEdit()
        self.report_date_start.setPlaceholderText("1404/02/19")
        self.report_date_start.setReadOnly(True)
        self.report_date_start_calendar = PersianCalendarWidget(self.report_date_start)
        self.report_date_end = QLineEdit()
        self.report_date_end.setPlaceholderText("1404/02/19")
        self.report_date_end.setReadOnly(True)
        self.report_date_end_calendar = PersianCalendarWidget(self.report_date_end)
        self.report_person = QComboBox()
        self.report_type = QComboBox()
        self.report_type.addItems(["تراکنش‌ها", "درآمد", "هزینه", "بدهی/طلب شخص", "بدهی/طلب کل"])
        generate_report_btn = QPushButton("نمایش گزارش")
        generate_report_btn.clicked.connect(self.generate_custom_report)
        form_layout.addRow("تاریخ شروع:", self.report_date_start)
        form_layout.addRow(self.report_date_start_calendar)
        form_layout.addRow("تاریخ پایان:", self.report_date_end)
        form_layout.addRow(self.report_date_end_calendar)
        form_layout.addRow("شخص (اختیاری):", self.report_person)
        form_layout.addRow("نوع گزارش:", self.report_type)
        form_layout.addRow(generate_report_btn)
        layout.addLayout(form_layout)
        tab.setLayout(layout)
        return tab
    
    def create_persons_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.person_name_input = QLineEdit()
        add_person_btn = QPushButton("افزودن شخص")
        add_person_btn.clicked.connect(self.add_person)
        form_layout.addRow("نام شخص:", self.person_name_input)
        form_layout.addRow(add_person_btn)
        self.persons_table = QTableWidget()
        self.persons_table.setColumnCount(3)
        self.persons_table.setHorizontalHeaderLabels(["شناسه", "نام", "اقدامات"])
        self.persons_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addLayout(form_layout)
        layout.addWidget(self.persons_table)
        tab.setLayout(layout)
        return tab

    def create_categories_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.category_name_input = QLineEdit()
        self.category_type = QComboBox()
        self.category_type.addItems(["درآمد", "هزینه"])
        add_category_btn = QPushButton("افزودن دسته‌بندی")
        add_category_btn.clicked.connect(self.add_category)
        form_layout.addRow("نام دسته‌بندی:", self.category_name_input)
        form_layout.addRow("نوع:", self.category_type)
        form_layout.addRow(add_category_btn)
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(4)
        self.categories_table.setHorizontalHeaderLabels(["شناسه", "نام", "نوع", "اقدامات"])
        self.categories_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addLayout(form_layout)
        layout.addWidget(self.categories_table)
        self.load_categories_table()  # بارگذاری اولیه جدول
        tab.setLayout(layout)
        return tab

    def load_data(self):
        self.load_accounts()
        self.load_categories()
        self.load_persons()
        self.load_transactions()
        self.load_debts()
        self.load_loans()
        self.load_report_persons()  # اضافه کردن این خط
        self.update_dashboard()

    def load_accounts(self):
        try:
            self.cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = self.cursor.fetchall()
            self.accounts_table.setRowCount(len(accounts))
            self.transaction_account.clear()
            self.debt_account.clear()
            self.loan_account.clear()
            self.transfer_from_account.clear()
            self.transfer_to_account.clear()
            for row, (id, name, balance) in enumerate(accounts):
                self.accounts_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.accounts_table.setItem(row, 1, QTableWidgetItem(name))
                self.accounts_table.setItem(row, 2, QTableWidgetItem(format_number(balance)))
                display_text = f"{name} (موجودی: {format_number(balance)} تومان)"
                self.transaction_account.addItem(display_text, id)
                self.debt_account.addItem(display_text, id)
                self.loan_account.addItem(display_text, id)
                self.transfer_from_account.addItem(display_text, id)
                self.transfer_to_account.addItem(display_text, id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def add_account(self):
        name = self.account_name_input.text()
        balance = self.account_balance_input.get_raw_value() if self.account_balance_input.text() else 0
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب نمی‌تواند خالی باشد!")
            return
        try:
            self.cursor.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
            self.conn.commit()
            self.account_name_input.clear()
            self.account_balance_input.clear()
            self.load_accounts()
            QMessageBox.information(self, "موفق", "حساب با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def update_categories(self):
        """به‌روزرسانی لیست دسته‌بندی‌ها بر اساس نوع تراکنش"""
        category_type = "income" if self.transaction_type.currentText() == "درآمد" else "expense"
        self.transaction_category.clear()
        try:
            self.cursor.execute("SELECT id, name FROM categories WHERE type = ?", (category_type,))
            categories = self.cursor.fetchall()
            for cat_id, name in categories:
                self.transaction_category.addItem(name, cat_id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_categories(self):
        """بارگذاری اولیه دسته‌بندی‌ها"""
        self.update_categories()  # به جای کد قبلی، از متد جدید استفاده می‌کنیم

    def load_categories_table(self):
        """به‌روزرسانی جدول دسته‌بندی‌ها در تب دسته‌بندی‌ها"""
        try:
            self.cursor.execute("SELECT id, name, type FROM categories")
            categories = self.cursor.fetchall()
            self.categories_table.setRowCount(len(categories))
            for row, (id, name, category_type) in enumerate(categories):
                self.categories_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.categories_table.setItem(row, 1, QTableWidgetItem(name))
                self.categories_table.setItem(row, 2, QTableWidgetItem("درآمد" if category_type == "income" else "هزینه"))
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, cat_id=id: self.edit_category(cat_id))
                self.categories_table.setCellWidget(row, 3, edit_btn)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_category(self, category_id):
        try:
            self.cursor.execute("SELECT name, type FROM categories WHERE id = ?", (category_id,))
            category = self.cursor.fetchone()
            if not category:
                QMessageBox.warning(self, "خطا", "دسته‌بندی یافت نشد!")
                return
            name, category_type = category

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش دسته‌بندی")
            layout = QFormLayout()
            edit_name = QLineEdit(name)
            edit_type = QComboBox()
            edit_type.addItems(["درآمد", "هزینه"])
            edit_type.setCurrentText("درآمد" if category_type == "income" else "هزینه")
            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_category(category_id, edit_name.text(), edit_type.currentText(), dialog))
            layout.addRow("نام دسته‌بندی:", edit_name)
            layout.addRow("نوع:", edit_type)
            layout.addRow(save_btn)
            dialog.setLayout(layout)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_category(self, category_id, name, type_text, dialog):
        if not name:
            QMessageBox.warning(self, "خطا", "نام دسته‌بندی نمی‌تواند خالی باشد!")
            return
        category_type = "income" if type_text == "درآمد" else "expense"
        try:
            self.cursor.execute("UPDATE categories SET name = ?, type = ? WHERE id = ?", (name, category_type, category_id))
            self.conn.commit()
            self.load_categories()
            self.load_categories_table()
            self.load_transactions()
            dialog.accept()
            QMessageBox.information(self, "موفق", "دسته‌بندی با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_report_persons(self):
        try:
            self.report_person.clear()
            self.report_person.addItem("-", None)
            self.cursor.execute("SELECT id, name FROM persons")
            persons = self.cursor.fetchall()
            for id, name in persons:
                self.report_person.addItem(name, id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def add_category(self):
        name = self.category_name_input.text()
        category_type = "income" if self.category_type.currentText() == "درآمد" else "expense"
        if not name:
            QMessageBox.warning(self, "خطا", "نام دسته‌بندی نمی‌تواند خالی باشد!")
            return
        try:
            self.cursor.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, category_type))
            self.conn.commit()
            self.category_name_input.clear()
            self.load_categories()  # به‌روزرسانی لیست دسته‌بندی‌ها برای بخش تراکنش
            self.load_categories_table()  # به‌روزرسانی جدول دسته‌بندی‌ها
            self.load_transactions()  # به‌روزرسانی جدول تراکنش‌ها (برای نمایش دسته‌بندی‌های جدید)
            QMessageBox.information(self, "موفق", "دسته‌بندی با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def add_transaction(self):
        account_id = self.transaction_account.currentData()
        person_id = self.transaction_person.currentData()
        category_id = self.transaction_category.currentData()
        amount = self.transaction_amount.get_raw_value()
        shamsi_date = self.transaction_date.text()
        desc = self.transaction_desc.text()
        category_type = "income" if self.transaction_type.currentText() == "درآمد" else "expense"
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
            QDate.fromString(date, "yyyy-MM-dd")
        except ValueError:
            QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است!")
            return
        try:
            self.cursor.execute(
                "INSERT INTO transactions (account_id, person_id, category_id, amount, date, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, person_id, category_id, amount, date, desc)
            )
            if category_type == "income":
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            else:
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            self.conn.commit()
            self.transaction_amount.clear()
            self.transaction_date.clear()
            self.transaction_desc.clear()
            self.load_transactions()
            self.load_accounts()
            self.update_dashboard()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_transaction(self, transaction_id):
        try:
            self.cursor.execute(
                "SELECT t.account_id, t.person_id, t.category_id, t.amount, t.date, t.description, c.type "
                "FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.id = ?",
                (transaction_id,)
            )
            transaction = self.cursor.fetchone()
            if not transaction:
                QMessageBox.warning(self, "خطا", "تراکنش یافت نشد!")
                return
            account_id, person_id, category_id, amount, date, desc, category_type = transaction

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش تراکنش")
            layout = QFormLayout()
            dialog.setLayout(layout)

            edit_account = QComboBox()
            self.cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = self.cursor.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} تومان)"
                edit_account.addItem(display_text, acc_id)
            edit_account.setCurrentText([f"{name} (موجودی: {format_number(balance)} تومان)" for acc_id, name, balance in accounts if acc_id == account_id][0])

            edit_person = QComboBox()
            edit_person.addItem("-", None)
            self.cursor.execute("SELECT id, name FROM persons")
            persons = self.cursor.fetchall()
            for p_id, name in persons:
                edit_person.addItem(name, p_id)
            if person_id:
                edit_person.setCurrentText([name for p_id, name in persons if p_id == person_id][0])

            edit_type = QComboBox()
            edit_type.addItems(["درآمد", "هزینه"])
            edit_type.setCurrentText("درآمد" if category_type == "income" else "هزینه")

            edit_category = QComboBox()
            def update_categories():
                edit_category.clear()
                current_type = "income" if edit_type.currentText() == "درآمد" else "expense"
                self.cursor.execute("SELECT id, name FROM categories WHERE type = ?", (current_type,))
                categories = self.cursor.fetchall()
                for cat_id, name in categories:
                    edit_category.addItem(name, cat_id)
                if category_id:
                    for index in range(edit_category.count()):
                        if edit_category.itemData(index) == category_id:
                            edit_category.setCurrentIndex(index)
                            break
            update_categories()
            edit_type.currentTextChanged.connect(update_categories)

            edit_amount = NumberInput()
            edit_amount.setText(str(amount))
            edit_date = QLineEdit(gregorian_to_shamsi(date))
            edit_date.setReadOnly(True)
            edit_date.setPlaceholderText("1404/02/13")
            edit_date.mousePressEvent = lambda event: self.show_calendar_popup(edit_date)
            edit_desc = QLineEdit(desc)

            save_btn = QPushButton("ذخیره")
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

    def save_transaction(self, transaction_id, account_id, person_id, category_id, amount, shamsi_date, desc, type_text, dialog, old_account_id, old_amount, old_category_type):
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
            QDate.fromString(date, "yyyy-MM-dd")
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ یا تاریخ نامعتبر است!")
            return
        try:
            # دریافت نوع جدید تراکنش
            new_category_type = "income" if type_text == "درآمد" else "expense"

            # ۱. معکوس کردن اثر تراکنش قدیمی
            if old_category_type == "income":
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_amount, old_account_id))
            else:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (old_amount, old_account_id))

            # ۲. اعمال اثر تراکنش جدید
            if new_category_type == "income":
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            else:
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))

            # ۳. به‌روزرسانی تراکنش در دیتابیس (حذف ستون type)
            self.cursor.execute(
                "UPDATE transactions SET account_id = ?, person_id = ?, category_id = ?, amount = ?, date = ?, description = ? WHERE id = ?",
                (account_id, person_id, category_id, amount, date, desc, transaction_id)
            )
            self.conn.commit()
            self.load_transactions()
            self.load_accounts()
            self.update_dashboard()
            dialog.accept()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def transfer_money(self):
        from_account_id = self.transfer_from_account.currentData()
        to_account_id = self.transfer_to_account.currentData()
        amount = self.transfer_amount.get_raw_value()
        shamsi_date = self.transfer_date.text()
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
            date = shamsi_to_gregorian(shamsi_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            QDate.fromString(date, "yyyy-MM-dd")
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ یا تاریخ نامعتبر است!")
            return
        try:
            # بررسی موجودی حساب مبدأ
            self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (from_account_id,))
            balance = self.cursor.fetchone()[0]
            if balance < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب مبدأ کافی نیست!")
                return

            # بررسی وجود هر دو دسته‌بندی
            self.cursor.execute("SELECT id FROM categories WHERE name = 'انتقال بین حساب‌ها (خروج)' AND type = 'expense'")
            expense_result = self.cursor.fetchone()
            self.cursor.execute("SELECT id FROM categories WHERE name = 'انتقال بین حساب‌ها (ورود)' AND type = 'income'")
            income_result = self.cursor.fetchone()
            if not expense_result or not income_result:
                QMessageBox.critical(self, "خطا", "دسته‌بندی‌های انتقال (ورود یا خروج) یافت نشدند!")
                return
            expense_category_id = expense_result[0]
            income_category_id = income_result[0]

            # انجام تمام عملیات در یک تراکنش
            with self.conn:
                # ثبت تراکنش خروج
                self.cursor.execute(
                    "INSERT INTO transactions (account_id, category_id, amount, date, description) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (from_account_id, expense_category_id, amount, date, "انتقال به حساب دیگر")
                )
                # ثبت تراکنش ورود
                self.cursor.execute(
                    "INSERT INTO transactions (account_id, category_id, amount, date, description) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (to_account_id, income_category_id, amount, date, "دریافت از حساب دیگر")
                )
                # به‌روزرسانی موجودی حساب‌ها
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

            self.transfer_amount.clear()
            self.transfer_date.clear()
            self.load_transactions()
            self.load_accounts()
            self.update_dashboard()
            QMessageBox.information(self, "موفق", "انتقال با موفقیت انجام شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_transactions(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM transactions")
            total_transactions = self.cursor.fetchone()[0]
            self.transactions_total_pages = (total_transactions + self.transactions_per_page - 1) // self.transactions_per_page
            self.recent_total_pages = (total_transactions + self.recent_per_page - 1) // self.recent_per_page

            offset = (self.transactions_current_page - 1) * self.transactions_per_page
            self.cursor.execute(
                "SELECT t.id, t.date, a.name, p.name, c.name, t.amount, t.description, c.type "
                "FROM transactions t "
                "JOIN accounts a ON t.account_id = a.id "
                "LEFT JOIN persons p ON t.person_id = p.id "
                "JOIN categories c ON t.category_id = c.id "
                "ORDER BY t.date DESC LIMIT ? OFFSET ?",
                (self.transactions_per_page, offset)
            )
            transactions = self.cursor.fetchall()

            offset_recent = (self.recent_current_page - 1) * self.recent_per_page
            self.cursor.execute(
                "SELECT t.id, t.date, a.name, p.name, c.name, t.amount, t.description, c.type "
                "FROM transactions t "
                "JOIN accounts a ON t.account_id = a.id "
                "LEFT JOIN persons p ON t.person_id = p.id "
                "JOIN categories c ON t.category_id = c.id "
                "ORDER BY t.date DESC LIMIT ? OFFSET ?",
                (self.recent_per_page, offset_recent)
            )
            recent_transactions = self.cursor.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        # به‌روزرسانی جدول تراکنش‌ها
        self.transactions_table.setRowCount(min(len(transactions), self.transactions_per_page))
        self.transactions_table.setColumnWidth(0, 50)
        self.transactions_table.setColumnWidth(1, 100)
        self.transactions_table.setColumnWidth(2, 150)
        self.transactions_table.setColumnWidth(3, 100)
        self.transactions_table.setColumnWidth(4, 120)
        self.transactions_table.setColumnWidth(5, 100)
        self.transactions_table.setColumnWidth(6, 200)
        self.transactions_table.setColumnWidth(7, 80)
        self.transactions_table.setColumnWidth(8, 80)
        self.transactions_table.setColumnWidth(9, 80)  # ستون حذف
        for row, (id, date, account, person, category, amount, desc, category_type) in enumerate(transactions):
            shamsi_date = gregorian_to_shamsi(date)
            self.transactions_table.setItem(row, 0, QTableWidgetItem(str(id)))
            self.transactions_table.setItem(row, 1, QTableWidgetItem(shamsi_date))
            self.transactions_table.setItem(row, 2, QTableWidgetItem(account))
            self.transactions_table.setItem(row, 3, QTableWidgetItem(person or "-"))
            self.transactions_table.setItem(row, 4, QTableWidgetItem(category))
            self.transactions_table.setItem(row, 5, QTableWidgetItem(format_number(amount)))
            self.transactions_table.setItem(row, 6, QTableWidgetItem(desc))
            self.transactions_table.setItem(row, 7, QTableWidgetItem("درآمد" if category_type == "income" else "هزینه"))
            edit_btn = QPushButton("ویرایش")
            edit_btn.clicked.connect(lambda checked, t_id=id: self.edit_transaction(t_id))
            self.transactions_table.setCellWidget(row, 8, edit_btn)
            delete_btn = QPushButton("حذف")
            delete_btn.clicked.connect(lambda checked, t_id=id: self.delete_transaction(t_id))
            self.transactions_table.setCellWidget(row, 9, delete_btn)

        # به‌روزرسانی جدول تراکنش‌های اخیر
        self.recent_transactions_table.setRowCount(min(len(recent_transactions), self.recent_per_page))
        self.recent_transactions_table.setColumnWidth(0, 100)
        self.recent_transactions_table.setColumnWidth(1, 150)
        self.recent_transactions_table.setColumnWidth(2, 120)
        self.recent_transactions_table.setColumnWidth(3, 100)
        self.recent_transactions_table.setColumnWidth(4, 200)
        self.recent_transactions_table.setColumnWidth(5, 80)
        for row, (id, date, account, person, category, amount, desc, category_type) in enumerate(recent_transactions):
            shamsi_date = gregorian_to_shamsi(date)
            self.recent_transactions_table.setItem(row, 0, QTableWidgetItem(shamsi_date))
            self.recent_transactions_table.setItem(row, 1, QTableWidgetItem(account))
            self.recent_transactions_table.setItem(row, 2, QTableWidgetItem(category))
            self.recent_transactions_table.setItem(row, 3, QTableWidgetItem(format_number(amount)))
            self.recent_transactions_table.setItem(row, 4, QTableWidgetItem(desc))
            self.recent_transactions_table.setItem(row, 5, QTableWidgetItem("درآمد" if category_type == "income" else "هزینه"))

        # به‌روزرسانی لیبل صفحه
        self.transactions_page_label.setText(f"صفحه {self.transactions_current_page} از {self.transactions_total_pages}")
        self.transactions_prev_btn.setEnabled(self.transactions_current_page > 1)
        self.transactions_next_btn.setEnabled(self.transactions_current_page < self.transactions_total_pages)

        self.recent_page_label.setText(f"صفحه {self.recent_current_page} از {self.recent_total_pages}")
        self.recent_prev_btn.setEnabled(self.recent_current_page > 1)
        self.recent_next_btn.setEnabled(self.recent_current_page < self.recent_total_pages)
    
    def delete_transaction(self, transaction_id):
        # دریافت اطلاعات تراکنش برای معکوس کردن اثر آن
        try:
            self.cursor.execute(
                "SELECT t.account_id, t.amount, c.type "
                "FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.id = ?",
                (transaction_id,)
            )
            transaction = self.cursor.fetchone()
            if not transaction:
                QMessageBox.warning(self, "خطا", "تراکنش یافت نشد!")
                return
            account_id, amount, category_type = transaction

            # تأیید حذف از کاربر
            reply = QMessageBox.question(
                self, "تأیید حذف", "آیا مطمئن هستید که می‌خواهید این تراکنش را حذف کنید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # معکوس کردن اثر تراکنش روی موجودی حساب
            if category_type == "income":
                # اگر تراکنش درآمد بوده، مبلغ رو از حساب کم می‌کنیم
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            else:
                # اگر تراکنش هزینه بوده، مبلغ رو به حساب برمی‌گردونیم
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))

            # حذف تراکنش از دیتابیس
            self.cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            self.conn.commit()

            # به‌روزرسانی جداول و داشبورد
            self.load_transactions()
            self.load_accounts()
            self.update_dashboard()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت حذف شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def prev_recent_page(self):
        if self.recent_current_page > 1:
            self.recent_current_page -= 1
            self.load_transactions()

    def next_recent_page(self):
        if self.recent_current_page < self.recent_total_pages:
            self.recent_current_page += 1
            self.load_transactions()

    def prev_transactions_page(self):
        if self.transactions_current_page > 1:
            self.transactions_current_page -= 1
            self.load_transactions()

    def next_transactions_page(self):
        if self.transactions_current_page < self.transactions_total_pages:
            self.transactions_current_page += 1
            self.load_transactions()

    def add_debt(self):
        person_id = self.debt_person.currentData()
        amount = self.debt_amount.get_raw_value()
        account_id = self.debt_account.currentData()
        shamsi_due_date = self.debt_due_date.text()
        is_credit = self.debt_is_credit.currentText() == "طلب من"
        has_payment = self.debt_has_payment.isChecked()
        show_in_dashboard = self.debt_show_in_dashboard.isChecked()

        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ نمی‌تواند خالی باشد!")
            return
        # بررسی تاریخ فقط در صورتی که وارد شده باشه
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
                QDate.fromString(due_date, "yyyy-MM-dd")
            except ValueError:
                QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است!")
                return

        try:
            self.cursor.execute(
                "INSERT INTO debts (person_id, amount, due_date, is_paid, account_id, show_in_dashboard) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (person_id, amount, due_date, 0, account_id if has_payment and not is_credit else None, 1 if show_in_dashboard else 0)
            )
            # اگر پولی دریافت/پرداخت شده و نوع "بدهی من" هست، موجودی حساب رو تغییر بده
            if has_payment and not is_credit and account_id:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            self.conn.commit()
            self.debt_amount.clear()
            self.debt_due_date.clear()
            self.debt_has_payment.setChecked(False)
            self.debt_show_in_dashboard.setChecked(False)
            self.load_debts()
            self.load_accounts()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_debt(self, debt_id):
        try:
            self.cursor.execute(
                "SELECT person_id, amount, account_id, due_date, is_paid, show_in_dashboard FROM debts WHERE id = ?",
                (debt_id,)
            )
            debt = self.cursor.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            person_id, amount, account_id, due_date, is_paid, show_in_dashboard = debt

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش بدهی/طلب")
            layout = QFormLayout()
            dialog.setLayout(layout)

            edit_person = QComboBox()
            self.cursor.execute("SELECT id, name FROM persons")
            persons = self.cursor.fetchall()
            for p_id, name in persons:
                edit_person.addItem(name, p_id)
            edit_person.setCurrentText([name for p_id, name in persons if p_id == person_id][0])

            edit_amount = NumberInput()
            edit_amount.setText(str(amount))

            edit_account = QComboBox()
            self.cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = self.cursor.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} تومان)"
                edit_account.addItem(display_text, acc_id)
            if account_id:
                edit_account.setCurrentText([f"{name} (موجودی: {format_number(balance)} تومان)" for acc_id, name, balance in accounts if acc_id == account_id][0])
            edit_account.setEnabled(bool(account_id))  # فعال/غیرفعال بر اساس وجود account_id

            edit_has_payment = QCheckBox("آیا پولی دریافت/پرداخت شده؟")
            edit_has_payment.setChecked(bool(account_id))
            edit_has_payment.stateChanged.connect(lambda state: edit_account.setEnabled(state == Qt.CheckState.Checked.value))

            edit_due_date = QLineEdit(gregorian_to_shamsi(due_date) if due_date else "")
            edit_due_date.setReadOnly(True)
            edit_due_date.setPlaceholderText("1404/02/13")
            edit_due_date.mousePressEvent = lambda event: self.show_calendar_popup(edit_due_date)

            edit_is_credit = QComboBox()
            edit_is_credit.addItems(["بدهی من", "طلب من"])
            edit_is_credit.setCurrentText("طلب من" if not account_id else "بدهی من")

            edit_show_in_dashboard = QCheckBox("نمایش در داشبورد")
            edit_show_in_dashboard.setChecked(show_in_dashboard)

            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_debt(
                debt_id, edit_person.currentData(), edit_amount.get_raw_value(),
                edit_account.currentData(), edit_due_date.text(),
                edit_is_credit.currentText() == "طلب من",
                edit_has_payment.isChecked(), edit_show_in_dashboard.isChecked(), dialog
            ))

            layout.addRow("شخص:", edit_person)
            layout.addRow("مبلغ:", edit_amount)
            layout.addRow("حساب مرتبط:", edit_account)
            layout.addRow("", edit_has_payment)
            layout.addRow("تاریخ سررسید (شمسی - اختیاری):", edit_due_date)
            layout.addRow("نوع:", edit_is_credit)
            layout.addRow("", edit_show_in_dashboard)
            layout.addRow(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_debt(self, debt_id, person_id, amount, account_id, shamsi_due_date, is_credit, has_payment, show_in_dashboard, dialog):
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
                QDate.fromString(due_date, "yyyy-MM-dd")
            except ValueError:
                QMessageBox.warning(self, "خطا", "مبلغ یا تاریخ نامعتبر است!")
                return
        try:
            # دریافت اطلاعات بدهی قدیمی برای معکوس کردن اثر
            self.cursor.execute("SELECT amount, account_id FROM debts WHERE id = ?", (debt_id,))
            old_debt = self.cursor.fetchone()
            if not old_debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            old_amount, old_account_id = old_debt

            # تعیین account_id جدید
            account_id_to_save = account_id if has_payment and not is_credit else None

            # بررسی موجودی حساب در صورت نیاز
            if has_payment and not is_credit and account_id:
                self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
                balance = self.cursor.fetchone()[0]
                if balance < amount:
                    QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                    return

            # معکوس کردن اثر بدهی قدیمی (اگر account_id وجود داشت)
            if old_account_id:
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_amount, old_account_id))

            # اعمال اثر بدهی جدید
            if has_payment and not is_credit and account_id:
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))

            # به‌روزرسانی بدهی/طلب
            self.cursor.execute(
                "UPDATE debts SET person_id = ?, amount = ?, account_id = ?, due_date = ?, is_paid = 0, show_in_dashboard = ? WHERE id = ?",
                (person_id, amount, account_id_to_save, due_date, 1 if show_in_dashboard else 0, debt_id)
            )
            self.conn.commit()
            self.load_debts()
            self.load_accounts()
            dialog.accept()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_debts(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM debts")
            total_debts = self.cursor.fetchone()[0]
            self.debts_total_pages = (total_debts + self.debts_per_page - 1) // self.debts_per_page

            offset = (self.debts_current_page - 1) * self.debts_per_page
            self.cursor.execute(
                "SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, d.is_paid, COALESCE(a.name, '-') "
                "FROM debts d JOIN persons p ON d.person_id = p.id LEFT JOIN accounts a ON d.account_id = a.id "
                "LIMIT ? OFFSET ?",
                (self.debts_per_page, offset)
            )
            debts = self.cursor.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return
        self.debts_table.setRowCount(min(len(debts), self.debts_per_page))
        self.debts_table.setColumnWidth(0, 50)
        self.debts_table.setColumnWidth(1, 120)
        self.debts_table.setColumnWidth(2, 100)
        self.debts_table.setColumnWidth(3, 100)
        self.debts_table.setColumnWidth(4, 100)
        self.debts_table.setColumnWidth(5, 80)
        self.debts_table.setColumnWidth(6, 120)
        self.debts_table.setColumnWidth(7, 80)
        self.debts_table.setColumnWidth(8, 80)  # ستون حذف
        self.debts_table.setColumnWidth(9, 80)  # ستون تسویه

        for row, (id, person, amount, paid, due_date, is_paid, account) in enumerate(debts):
            shamsi_due_date = gregorian_to_shamsi(due_date) if due_date else "-"
            self.debts_table.setItem(row, 0, QTableWidgetItem(str(id)))
            self.debts_table.setItem(row, 1, QTableWidgetItem(person))
            self.debts_table.setItem(row, 2, QTableWidgetItem(format_number(amount)))
            self.debts_table.setItem(row, 3, QTableWidgetItem(format_number(paid)))
            self.debts_table.setItem(row, 4, QTableWidgetItem(shamsi_due_date))
            self.debts_table.setItem(row, 5, QTableWidgetItem("پرداخت شده" if is_paid else "در جریان"))
            self.debts_table.setItem(row, 6, QTableWidgetItem(account))
            edit_btn = QPushButton("ویرایش")
            edit_btn.clicked.connect(lambda checked, d_id=id: self.edit_debt(d_id))
            self.debts_table.setCellWidget(row, 7, edit_btn)
            delete_btn = QPushButton("حذف")
            delete_btn.clicked.connect(lambda checked, d_id=id: self.delete_debt(d_id))
            self.debts_table.setCellWidget(row, 8, delete_btn)
            # دکمه تسویه فقط برای موارد پرداخت‌نشده
            if not is_paid:
                settle_btn = QPushButton("تسویه")
                settle_btn.clicked.connect(lambda checked, d_id=id: self.settle_debt(d_id))
                self.debts_table.setCellWidget(row, 9, settle_btn)
            else:
                self.debts_table.setItem(row, 9, QTableWidgetItem("-"))

        self.debts_page_label.setText(f"صفحه {self.debts_current_page} از {self.debts_total_pages}")
        self.debts_prev_btn.setEnabled(self.debts_current_page > 1)
        self.debts_next_btn.setEnabled(self.debts_current_page < self.debts_total_pages)

    def settle_debt(self, debt_id):
        try:
            self.cursor.execute(
                "SELECT d.person_id, d.amount, d.paid_amount, d.account_id, p.name "
                "FROM debts d JOIN persons p ON d.person_id = p.id WHERE d.id = ?",
                (debt_id,)
            )
            debt = self.cursor.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            person_id, amount, paid_amount, account_id, person_name = debt
            remaining_amount = amount - paid_amount

            dialog = QDialog(self)
            dialog.setWindowTitle(f"تسویه بدهی/طلب با {person_name}")
            layout = QFormLayout()
            dialog.setLayout(layout)

            # نوع بدهی/طلب
            is_credit = not account_id  # اگر account_id وجود نداشته باشه، یعنی طلب منه
            type_label = QLabel("طلب من" if is_credit else "بدهی من")
            layout.addRow("نوع:", type_label)

            # مبلغ باقی‌مانده
            remaining_label = QLabel(format_number(remaining_amount))
            layout.addRow("مبلغ باقی‌مانده:", remaining_label)

            # انتخاب حساب
            settle_account = QComboBox()
            self.cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = self.cursor.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} تومان)"
                settle_account.addItem(display_text, acc_id)
            settle_account.setEnabled(False)  # غیرفعال کردن پیش‌فرض

            # چک‌باکس برای پرداخت/دریافت
            settle_has_payment = QCheckBox("آیا پولی پرداخت/دریافت می‌شود؟")
            settle_has_payment.stateChanged.connect(lambda state: settle_account.setEnabled(state == Qt.CheckState.Checked.value))
            layout.addRow("", settle_has_payment)

            layout.addRow("حساب مرتبط:", settle_account)

            # دکمه تأیید
            confirm_btn = QPushButton("تأیید تسویه")
            confirm_btn.clicked.connect(lambda: self.confirm_settle_debt(
                debt_id, remaining_amount, settle_account.currentData(),
                settle_has_payment.isChecked(), is_credit, dialog
            ))
            layout.addRow(confirm_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    
    def confirm_settle_debt(self, debt_id, remaining_amount, account_id, has_payment, is_credit, dialog):
        try:
            # بررسی اینکه برای طلب، حساب مرتبط انتخاب شده باشه
            if is_credit and not has_payment:
                QMessageBox.warning(self, "خطا", "برای تسویه طلب، باید حساب مرتبط برای دریافت پول انتخاب شود!")
                return

            # بررسی موجودی حساب در صورت نیاز
            if has_payment and account_id:
                self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
                balance = self.cursor.fetchone()[0]
                if is_credit:  # طلب من: دریافت پول (اضافه کردن به حساب)
                    pass  # نیازی به بررسی موجودی نیست چون پول اضافه می‌شه
                else:  # بدهی من: پرداخت پول (کم کردن از حساب)
                    if balance < remaining_amount:
                        QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                        return

            # به‌روزرسانی وضعیت بدهی/طلب
            self.cursor.execute(
                "UPDATE debts SET is_paid = 1, paid_amount = amount WHERE id = ?",
                (debt_id,)
            )

            # به‌روزرسانی حساب در صورت پرداخت/دریافت
            if has_payment and account_id:
                if is_credit:  # طلب من: پول دریافت می‌شه
                    self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (remaining_amount, account_id))
                else:  # بدهی من: پول پرداخت می‌شه
                    self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (remaining_amount, account_id))

            self.conn.commit()
            self.load_debts()
            self.load_accounts()
            self.update_dashboard()
            dialog.accept()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت تسویه شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def delete_debt(self, debt_id):
        try:
            # دریافت اطلاعات بدهی برای معکوس کردن اثر آن
            self.cursor.execute(
                "SELECT d.account_id, d.amount, d.paid_amount FROM debts d WHERE d.id = ?",
                (debt_id,)
            )
            debt = self.cursor.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            account_id, amount, paid_amount = debt

            # تأیید حذف از کاربر
            reply = QMessageBox.question(
                self, "تأیید حذف", "آیا مطمئن هستید که می‌خواهید این بدهی/طلب را حذف کنید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # معکوس کردن اثر بدهی روی موجودی حساب (اگر پولی دریافت شده و نوع "بدهی من" باشد)
            if account_id:  # account_id وجود داره، یعنی پولی دریافت شده
                remaining_amount = amount - paid_amount  # فقط مبلغ باقی‌مانده رو معکوس می‌کنیم
                self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (remaining_amount, account_id))

            # حذف بدهی/طلب از دیتابیس
            self.cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
            self.conn.commit()

            # به‌روزرسانی جدول و حساب‌ها
            self.load_debts()
            self.load_accounts()
            self.update_dashboard()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت حذف شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def prev_debts_page(self):
        if self.debts_current_page > 1:
            self.debts_current_page -= 1
            self.load_debts()

    def next_debts_page(self):
        if self.debts_current_page < self.debts_total_pages:
            self.debts_current_page += 1
            self.load_debts()
            self.debts_table.setCellWidget(row, 7, edit_btn)

    def add_loan(self):
        loan_type = "taken" if self.loan_type.currentText() == "وام گرفته‌شده" else "given"
        bank_name = self.loan_bank.text()
        amount = self.loan_amount.get_raw_value()
        interest = self.loan_interest.get_raw_value()
        account_id = self.loan_account.currentData()
        shamsi_start_date = self.loan_start_date.text()
        shamsi_end_date = self.loan_end_date.text()
        installments_total = self.loan_installments_total.get_raw_value()
        installments_paid = self.loan_installments_paid.get_raw_value()
        if not amount or not shamsi_start_date or not shamsi_end_date or not installments_total:
            QMessageBox.warning(self, "خطا", "فیلدهای ضروری را پر کنید!")
            return
        if not is_valid_shamsi_date(shamsi_start_date) or not is_valid_shamsi_date(shamsi_end_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            interest = float(interest) if interest else 0.0
            start_date = shamsi_to_gregorian(shamsi_start_date)
            if not start_date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            end_date = shamsi_to_gregorian(shamsi_end_date)
            if not end_date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            installments_total = int(installments_total)
            installments_paid = int(installments_paid) if installments_paid else 0
            if installments_paid > installments_total:
                raise ValueError("تعداد اقساط پرداخت‌شده نمی‌تواند بیشتر از کل اقساط باشد!")
            QDate.fromString(start_date, "yyyy-MM-dd")
            QDate.fromString(end_date, "yyyy-MM-dd")
        except ValueError as e:
            QMessageBox.warning(self, "خطا", f"مقادیر عددی یا تاریخ‌ها نامعتبر! {str(e)}")
            return
        try:
            self.cursor.execute(
                "INSERT INTO loans (type, bank_name, total_amount, paid_amount, interest_rate, start_date, end_date, account_id, installments_total, installments_paid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (loan_type, bank_name, amount, 0, interest, start_date, end_date, account_id, installments_total, installments_paid)
            )
            if loan_type == "taken":
                self.cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            self.conn.commit()
            self.loan_bank.clear()
            self.loan_amount.clear()
            self.loan_interest.clear()
            self.loan_start_date.clear()
            self.loan_end_date.clear()
            self.loan_installments_total.clear()
            self.loan_installments_paid.clear()
            self.load_loans()
            self.load_accounts()
            QMessageBox.information(self, "موفق", "وام با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_loan(self, loan_id):
        try:
            self.cursor.execute(
                "SELECT type, bank_name, total_amount, interest_rate, account_id, start_date, end_date, installments_total, installments_paid "
                "FROM loans WHERE id = ?",
                (loan_id,)
            )
            loan = self.cursor.fetchone()
            if not loan:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                return
            loan_type, bank_name, total_amount, interest_rate, account_id, start_date, end_date, installments_total, installments_paid = loan

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش وام")
            layout = QFormLayout()
            dialog.setLayout(layout)

            edit_loan_type = QComboBox()
            edit_loan_type.addItems(["وام گرفته‌شده", "وام داده‌شده"])
            edit_loan_type.setCurrentText("وام گرفته‌شده" if loan_type == "taken" else "وام داده‌شده")

            edit_bank = QLineEdit(bank_name)
            edit_amount = NumberInput()
            edit_amount.setText(str(total_amount))
            edit_interest = NumberInput()
            edit_interest.setText(str(interest_rate))

            edit_account = QComboBox()
            self.cursor.execute("SELECT id, name, balance FROM accounts")
            accounts = self.cursor.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} تومان)"
                edit_account.addItem(display_text, acc_id)
            edit_account.setCurrentText([f"{name} (موجودی: {format_number(balance)} تومان)" for acc_id, name, balance in accounts if acc_id == account_id][0])

            edit_start_date = QLineEdit(gregorian_to_shamsi(start_date))
            edit_start_date.setReadOnly(True)
            edit_start_date.setPlaceholderText("1404/02/13")
            edit_start_date.mousePressEvent = lambda event: self.show_calendar_popup(edit_start_date)

            edit_installments_total = NumberInput()
            edit_installments_total.setText(str(installments_total))
            edit_installments_paid = NumberInput()
            edit_installments_paid.setText(str(installments_paid))

            edit_end_date = QLineEdit(gregorian_to_shamsi(end_date))
            edit_end_date.setReadOnly(True)
            edit_end_date.setPlaceholderText("1405/02/13")
            edit_end_date.mousePressEvent = lambda event: self.show_calendar_popup(edit_end_date)

            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_loan(
                loan_id, edit_loan_type.currentText(), edit_bank.text(),
                edit_amount.get_raw_value(), edit_interest.get_raw_value(), edit_account.currentData(),
                edit_start_date.text(), edit_end_date.text(),
                edit_installments_total.get_raw_value(), edit_installments_paid.get_raw_value(), dialog
            ))

            layout.addRow("نوع وام:", edit_loan_type)
            layout.addRow("نام بانک:", edit_bank)
            layout.addRow("مبلغ:", edit_amount)
            layout.addRow("نرخ سود (%):", edit_interest)
            layout.addRow("حساب مرتبط:", edit_account)
            layout.addRow("تاریخ شروع (شمسی):", edit_start_date)
            layout.addRow("تعداد اقساط کل:", edit_installments_total)
            layout.addRow("تعداد اقساط پرداخت‌شده:", edit_installments_paid)
            layout.addRow("تاریخ پایان (شمسی):", edit_end_date)
            layout.addRow(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_loan(self, loan_id, loan_type_text, bank_name, amount, interest, account_id, shamsi_start_date, shamsi_end_date, installments_total, installments_paid, dialog):
        loan_type = "taken" if loan_type_text == "وام گرفته‌شده" else "given"
        if not amount or not shamsi_start_date or not shamsi_end_date or not installments_total:
            QMessageBox.warning(self, "خطا", "فیلدهای ضروری را پر کنید!")
            return
        if not is_valid_shamsi_date(shamsi_start_date) or not is_valid_shamsi_date(shamsi_end_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            amount = float(amount)
            interest = float(interest) if interest else 0.0
            start_date = shamsi_to_gregorian(shamsi_start_date)
            if not start_date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            end_date = shamsi_to_gregorian(shamsi_end_date)
            if not end_date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            installments_total = int(installments_total)
            installments_paid = int(installments_paid) if installments_paid else 0
            if installments_paid > installments_total:
                raise ValueError("تعداد اقساط پرداخت‌شده نمی‌تواند بیشتر از کل اقساط باشد!")
            QDate.fromString(start_date, "yyyy-MM-dd")
            QDate.fromString(end_date, "yyyy-MM-dd")
        except ValueError as e:
            QMessageBox.warning(self, "خطا", f"مقادیر عددی یا تاریخ‌ها نامعتبر! {str(e)}")
            return
        try:
            self.cursor.execute(
                "UPDATE loans SET type = ?, bank_name = ?, total_amount = ?, interest_rate = ?, account_id = ?, start_date = ?, end_date = ?, installments_total = ?, installments_paid = ? WHERE id = ?",
                (loan_type, bank_name, amount, interest, account_id, start_date, end_date, installments_total, installments_paid, loan_id)
            )
            self.conn.commit()
            self.load_loans()
            self.load_accounts()
            dialog.accept()
            QMessageBox.information(self, "موفق", "وام با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_loans(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM loans")
            total_loans = self.cursor.fetchone()[0]
            self.loans_total_pages = (total_loans + self.loans_per_page - 1) // self.loans_per_page

            offset = (self.loans_current_page - 1) * self.loans_per_page
            self.cursor.execute(
                "SELECT l.id, l.type, l.bank_name, l.total_amount, l.paid_amount, l.interest_rate, l.start_date, l.end_date, l.installments_total, l.installments_paid "
                "FROM loans l LEFT JOIN accounts a ON l.account_id = a.id "
                "LIMIT ? OFFSET ?",
                (self.loans_per_page, offset)
            )
            loans = self.cursor.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return
        self.loans_table.setRowCount(min(len(loans), self.loans_per_page))
        self.loans_table.setColumnWidth(0, 50)
        self.loans_table.setColumnWidth(1, 100)
        self.loans_table.setColumnWidth(2, 150)
        self.loans_table.setColumnWidth(3, 100)
        self.loans_table.setColumnWidth(4, 100)
        self.loans_table.setColumnWidth(5, 80)
        self.loans_table.setColumnWidth(6, 100)
        self.loans_table.setColumnWidth(7, 100)
        self.loans_table.setColumnWidth(8, 80)
        self.loans_table.setColumnWidth(9, 100)
        self.loans_table.setColumnWidth(10, 80)

        for row, (id, type_, bank, total, paid, interest, start, end, installments_total, installments_paid) in enumerate(loans):
            shamsi_start = gregorian_to_shamsi(start)
            shamsi_end = gregorian_to_shamsi(end)
            self.loans_table.setItem(row, 0, QTableWidgetItem(str(id)))
            self.loans_table.setItem(row, 1, QTableWidgetItem("گرفته‌شده" if type_ == "taken" else "داده‌شده"))
            self.loans_table.setItem(row, 2, QTableWidgetItem(bank or "-"))
            self.loans_table.setItem(row, 3, QTableWidgetItem(format_number(total)))
            self.loans_table.setItem(row, 4, QTableWidgetItem(format_number(paid)))
            self.loans_table.setItem(row, 5, QTableWidgetItem(f"{interest}%"))
            self.loans_table.setItem(row, 6, QTableWidgetItem(shamsi_start))
            self.loans_table.setItem(row, 7, QTableWidgetItem(shamsi_end))
            self.loans_table.setItem(row, 8, QTableWidgetItem(str(installments_total)))
            self.loans_table.setItem(row, 9, QTableWidgetItem(str(installments_paid)))
            edit_btn = QPushButton("ویرایش")
            edit_btn.clicked.connect(lambda checked, l_id=id: self.edit_loan(l_id))
            self.loans_table.setCellWidget(row, 10, edit_btn)

        self.loans_page_label.setText(f"صفحه {self.loans_current_page} از {self.loans_total_pages}")
        self.loans_prev_btn.setEnabled(self.loans_current_page > 1)
        self.loans_next_btn.setEnabled(self.loans_current_page < self.loans_total_pages)

    def prev_loans_page(self):
        if self.loans_current_page > 1:
            self.loans_current_page -= 1
            self.load_loans()

    def next_loans_page(self):
        if self.loans_current_page < self.loans_total_pages:
            self.loans_current_page += 1
            self.load_loans()

    def edit_loan_installments(self, loan_id):
        try:
            self.cursor.execute("SELECT total_amount, installments_total, installments_paid, start_date FROM loans WHERE id = ?", (loan_id,))
            loan = self.cursor.fetchone()
            if not loan:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                return
            total_amount, installments_total, installments_paid, start_date = loan
            if installments_total == 0:
                QMessageBox.warning(self, "خطا", "تعداد اقساط نمی‌تواند صفر باشد!")
                return
            installment_amount = total_amount / installments_total
            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش اقساط")
            layout = QVBoxLayout()
            installments_table = QTableWidget()
            installments_table.setColumnCount(5)
            installments_table.setHorizontalHeaderLabels(["شماره قسط", "مبلغ", "سررسید", "پرداخت شده", "اقدام"])
            installments_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.cursor.execute("SELECT id, amount, due_date, is_paid FROM loan_installments WHERE loan_id = ?", (loan_id,))
            installments = self.cursor.fetchall()
            if not installments:
                start_date = jdatetime.date.fromgregorian(date=datetime.strptime(start_date, "%Y-%m-%d"))
                for i in range(installments_total):
                    due_date = start_date + jdatetime.timedelta(days=i * 30)
                    due_date_str = due_date.togregorian().strftime("%Y-%m-%d")
                    self.cursor.execute("INSERT INTO loan_installments (loan_id, amount, due_date, is_paid) VALUES (?, ?, ?, ?)", 
                                    (loan_id, installment_amount, due_date_str, 1 if i < installments_paid else 0))
                    self.conn.commit()
                self.cursor.execute("SELECT id, amount, due_date, is_paid FROM loan_installments WHERE loan_id = ?", (loan_id,))
                installments = self.cursor.fetchall()
            installments_table.setRowCount(len(installments))
            for row, (inst_id, amount, due_date, is_paid) in enumerate(installments):
                installments_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
                installments_table.setItem(row, 1, QTableWidgetItem(format_number(amount)))
                installments_table.setItem(row, 2, QTableWidgetItem(gregorian_to_shamsi(due_date)))
                installments_table.setItem(row, 3, QTableWidgetItem("بله" if is_paid else "خیر"))
                if not is_paid:
                    btn_pay = QPushButton("پرداخت")
                    btn_pay.clicked.connect(lambda checked, r=row: self.pay_installment(loan_id, r))
                    installments_table.setCellWidget(row, 4, btn_pay)
                else:
                    installments_table.setItem(row, 4, QTableWidgetItem("-"))
            layout.addWidget(installments_table)
            dialog.setLayout(layout)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطای غیرمنتظره: {e}")

    def confirm_payment(self, loan_id, row, amount, account_id, dialog):
        try:
            self.cursor.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
            balance = self.cursor.fetchone()[0]
            if balance < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                return

            self.cursor.execute("UPDATE loan_installments SET is_paid = 1 WHERE loan_id = ? LIMIT 1 OFFSET ?", (loan_id, row))
            self.cursor.execute("UPDATE loans SET paid_amount = paid_amount + ?, installments_paid = installments_paid + 1 WHERE id = ?", (amount, loan_id))
            self.cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            self.conn.commit()
            self.load_loans()
            self.load_accounts()
            dialog.accept()
            QMessageBox.information(self, "موفق", "قسط با موفقیت پرداخت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def add_person(self):
        name = self.person_name_input.text()
        if not name:
            QMessageBox.warning(self, "خطا", "نام شخص نمی‌تواند خالی باشد!")
            return
        try:
            self.cursor.execute("INSERT INTO persons (name) VALUES (?)", (name,))
            self.conn.commit()
            self.person_name_input.clear()
            self.load_persons()
            self.load_report_persons()
            QMessageBox.information(self, "موفق", "شخص با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_persons(self):
        try:
            self.cursor.execute("SELECT id, name FROM persons")
            persons = self.cursor.fetchall()
            self.persons_table.setRowCount(len(persons))
            self.transaction_person.clear()
            self.debt_person.clear()
            # اضافه کردن گزینه پیش‌فرض
            self.transaction_person.addItem("-", None)
            self.debt_person.addItem("-", None)
            for row, (id, name) in enumerate(persons):
                self.persons_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.persons_table.setItem(row, 1, QTableWidgetItem(name))
                self.transaction_person.addItem(name, id)
                self.debt_person.addItem(name, id)
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, p_id=id: self.edit_person(p_id))
                self.persons_table.setCellWidget(row, 2, edit_btn)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_person(self, person_id):
        try:
            self.cursor.execute("SELECT name FROM persons WHERE id = ?", (person_id,))
            person = self.cursor.fetchone()
            if not person:
                QMessageBox.warning(self, "خطا", "شخص یافت نشد!")
                return
            name = person[0]

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش شخص")
            layout = QFormLayout()
            dialog.setLayout(layout)

            edit_name = QLineEdit(name)

            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_person(person_id, edit_name.text(), dialog))

            layout.addRow("نام شخص:", edit_name)
            layout.addRow(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_person(self, person_id, name, dialog):
        if not name:
            QMessageBox.warning(self, "خطا", "نام شخص نمی‌تواند خالی باشد!")
            return
        try:
            self.cursor.execute("UPDATE persons SET name = ? WHERE id = ?", (name, person_id))
            self.conn.commit()
            self.load_persons()
            self.load_report_persons()
            dialog.accept()
            QMessageBox.information(self, "موفق", "نام شخص با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def update_dashboard(self):
        try:
            # به‌روزرسانی موجودی کل
            self.cursor.execute("SELECT SUM(balance) FROM accounts")
            total_balance = self.cursor.fetchone()[0] or 0
            self.total_balance_label.setText(f"موجودی کل: {format_number(total_balance)} تومان")

            # بارگذاری بدهی‌ها و طلب‌های مهم
            today = jdatetime.date.today()
            fifteen_days_later = today + jdatetime.timedelta(days=15)
            today_str = today.togregorian().strftime("%Y-%m-%d")
            fifteen_days_later_str = fifteen_days_later.togregorian().strftime("%Y-%m-%d")

            self.cursor.execute(
                "SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, d.is_paid, COALESCE(a.name, '-') "
                "FROM debts d JOIN persons p ON d.person_id = p.id LEFT JOIN accounts a ON d.account_id = a.id "
                "WHERE d.show_in_dashboard = 1 AND d.is_paid = 0 AND d.due_date IS NOT NULL "
                "AND (d.due_date <= ? OR (d.due_date >= ? AND d.due_date <= ?))",
                (today_str, today_str, fifteen_days_later_str)
            )
            debts = self.cursor.fetchall()

            self.important_debts_table.setRowCount(len(debts))
            for row, (id, person, amount, paid, due_date, is_paid, account) in enumerate(debts):
                shamsi_due_date = gregorian_to_shamsi(due_date) if due_date else "-"
                self.important_debts_table.setItem(row, 0, QTableWidgetItem(person))
                self.important_debts_table.setItem(row, 1, QTableWidgetItem(format_number(amount)))
                self.important_debts_table.setItem(row, 2, QTableWidgetItem(format_number(paid)))
                self.important_debts_table.setItem(row, 3, QTableWidgetItem(shamsi_due_date))
                self.important_debts_table.setItem(row, 4, QTableWidgetItem("پرداخت شده" if is_paid else "در جریان"))

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def check_reminders(self):
        today = jdatetime.date.today().togregorian().strftime("%Y-%m-%d")
        try:
            self.cursor.execute("SELECT id, amount, due_date FROM debts WHERE is_paid = 0 AND due_date IS NOT NULL AND due_date <= ?", (today,))
            debts = self.cursor.fetchall()
            for debt in debts:
                QMessageBox.warning(self, "یادآوری", f"بدهی به مبلغ {format_number(debt[1])} تومان تا {gregorian_to_shamsi(debt[2])} سررسید شده!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def generate_custom_report(self):
        start_date = self.report_date_start.text()
        end_date = self.report_date_end.text()
        person_id = self.report_person.currentData()
        report_type = self.report_type.currentText()
        if not start_date or not end_date:
            QMessageBox.warning(self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
            return
        if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            start_date_g = shamsi_to_gregorian(start_date)
            if not start_date_g:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
            end_date_g = shamsi_to_gregorian(end_date)
            if not end_date_g:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
            QDate.fromString(start_date_g, "yyyy-MM-dd")
            QDate.fromString(end_date_g, "yyyy-MM-dd")
        except ValueError:
            QMessageBox.warning(self, "خطا", "فرمت تاریخ‌ها نامعتبر است!")
            return

        try:
            query = ""
            if report_type == "تراکنش‌ها":
                query = """
                    SELECT t.date, a.name, p.name, c.name, t.amount, t.description
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.id
                    LEFT JOIN persons p ON t.person_id = p.id
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.date BETWEEN ? AND ?
                """
                params = (start_date_g, end_date_g)
                if person_id:
                    query += " AND t.person_id = ?"
                    params += (person_id,)
            elif report_type == "درآمد":
                query = """
                    SELECT t.date, a.name, c.name, t.amount, t.description
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.id
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.date BETWEEN ? AND ? AND c.type = 'income'
                """
                params = (start_date_g, end_date_g)
                if person_id:
                    query += " AND t.person_id = ?"
                    params += (person_id,)
            elif report_type == "هزینه":
                query = """
                    SELECT t.date, a.name, c.name, t.amount, t.description
                    FROM transactions t
                    JOIN accounts a ON t.account_id = a.id
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.date BETWEEN ? AND ? AND c.type = 'expense'
                """
                params = (start_date_g, end_date_g)
                if person_id:
                    query += " AND t.person_id = ?"
                    params += (person_id,)
            elif report_type == "بدهی/طلب شخص":
                if not person_id:
                    QMessageBox.warning(self, "خطا", "برای گزارش بدهی/طلب شخص، باید شخص انتخاب شود!")
                    return
                query = """
                    SELECT d.due_date, p.name, d.amount, d.paid_amount, d.is_paid
                    FROM debts d
                    JOIN persons p ON d.person_id = p.id
                    WHERE d.person_id = ? AND d.due_date BETWEEN ? AND ?
                """
                params = (person_id, start_date_g, end_date_g)
            elif report_type == "بدهی/طلب کل":
                query = """
                    SELECT d.due_date, p.name, d.amount, d.paid_amount, d.is_paid
                    FROM debts d
                    JOIN persons p ON d.person_id = p.id
                    WHERE d.due_date BETWEEN ? AND ?
                """
                params = (start_date_g, end_date_g)

            if query:
                self.cursor.execute(query, params)
                results = self.cursor.fetchall()
                report_dialog = QDialog(self)
                report_dialog.setWindowTitle("گزارش مالی")
                layout = QVBoxLayout()
                report_table = QTableWidget()
                if report_type in ["تراکنش‌ها", "درآمد", "هزینه"]:
                    column_count = 6 if report_type == "تراکنش‌ها" else 5
                    headers = ["تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات"][:column_count]
                    report_table.setColumnCount(column_count)
                    report_table.setHorizontalHeaderLabels(headers)
                    report_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    report_table.setRowCount(len(results))
                    for row, result in enumerate(results):
                        shamsi_date = gregorian_to_shamsi(result[0])
                        report_table.setItem(row, 0, QTableWidgetItem(shamsi_date))
                        report_table.setItem(row, 1, QTableWidgetItem(result[1] or "-"))
                        if column_count == 6:
                            report_table.setItem(row, 2, QTableWidgetItem(result[2] or "-"))
                            report_table.setItem(row, 3, QTableWidgetItem(result[3]))
                            report_table.setItem(row, 4, QTableWidgetItem(format_number(result[4])))
                            report_table.setItem(row, 5, QTableWidgetItem(result[5] or "-"))
                        else:
                            report_table.setItem(row, 2, QTableWidgetItem(result[2]))
                            report_table.setItem(row, 3, QTableWidgetItem(format_number(result[3])))
                            report_table.setItem(row, 4, QTableWidgetItem(result[4] or "-"))
                else:
                    report_table.setColumnCount(5)
                    report_table.setHorizontalHeaderLabels(["تاریخ", "شخص", "مبلغ کل", "مبلغ پرداخت‌شده", "وضعیت"])
                    report_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    report_table.setRowCount(len(results))
                    for row, result in enumerate(results):
                        shamsi_date = gregorian_to_shamsi(result[0])
                        report_table.setItem(row, 0, QTableWidgetItem(shamsi_date))
                        report_table.setItem(row, 1, QTableWidgetItem(result[1]))
                        report_table.setItem(row, 2, QTableWidgetItem(format_number(result[2])))
                        report_table.setItem(row, 3, QTableWidgetItem(format_number(result[3])))
                        report_table.setItem(row, 4, QTableWidgetItem("پرداخت شده" if result[4] else "در جریان"))

                layout.addWidget(report_table)
                report_dialog.setLayout(layout)
                report_dialog.exec()
            else:
                QMessageBox.warning(self, "خطا", "نوع گزارش نامعتبر است!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FinanceApp()
    window.show()
    sys.exit(app.exec())