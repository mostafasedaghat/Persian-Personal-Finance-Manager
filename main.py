from database import DatabaseManager
from login_dialog import LoginDialog
from change_password_dialog import ChangePasswordDialog
import sys
import locale
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                             QTableWidgetItem, QLabel, QLineEdit, QComboBox,
                             QMessageBox, QFormLayout, QGridLayout, QScrollArea, 
                             QDialog, QCheckBox, QCalendarWidget,QSpacerItem, QSizePolicy, QFrame)
from PyQt6.QtCore import QDate, Qt, QTimer, QLocale  # اضافه کردن QLocale
from PyQt6.QtGui import QIcon, QFont, QColor, QIntValidator
import sqlite3
import jdatetime
from datetime import datetime, timedelta
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import matplotlib.pyplot as plt
from io import BytesIO
import os
import bcrypt
import dropbox
from dropbox.exceptions import ApiError


# تنظیم locale برای جداکننده اعداد
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

# توابع تبدیل تاریخ
def gregorian_to_shamsi(date):
    try:
        if not date:
            return ""
        if isinstance(date, QDate):
            date_str = date.toString("yyyy-MM-dd")
        else:
            date_str = str(date)
        g_date = QDate.fromString(date_str, "yyyy-MM-dd")
        if not g_date.isValid():
            return date_str
        j_date = jdatetime.date.fromgregorian(year=g_date.year(), month=g_date.month(), day=g_date.day())
        return j_date.strftime("%Y/%m/%d")
    except Exception:
        return str(date)

def shamsi_to_gregorian(date_str):
    try:
        if not date_str or not isinstance(date_str, str):
            return None
        if not re.match(r"^\d{4}/\d{2}/\d{2}$", date_str):
            return None
        j_year, j_month, j_day = map(int, date_str.replace('/', '-').split('-'))
        jdatetime.date(j_year, j_month, j_day)  # اعتبارسنجی
        g_date = jdatetime.date(j_year, j_month, j_day).togregorian()
        return f"{g_date.year}-{g_date.month:02d}-{g_date.day:02d}"
    except (ValueError, TypeError):
        return None

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
        if text and (text.startswith('-') or text == '0'):
            self.setStyleSheet("background-color: #ffe6e6;")  # رنگ پس‌زمینه قرمز برای خطا
            return
        if text.isdigit():
            formatted = format_number(int(text))
            self.setText(formatted)
            self.setStyleSheet("")  # بازگرداندن استایل پیش‌فرض
            self.setCursorPosition(len(formatted))  # مکان‌نما رو آخر متن می‌بره

    def get_raw_value(self):
        text = self.text().replace(",", "")
        if text.isdigit():
            value = int(text)
            if value <= 0:
                return None  # مقادیر صفر یا منفی نامعتبر هستند
            return value
        return None  # یا مقدار پیش‌فرض دیگر

class FinanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager('finance.db')
        self.app = QApplication(sys.argv)
        self.init_db()
        self.show_login()


    def show_login(self):
        login_dialog = LoginDialog(self.db_manager)
        if login_dialog.exec():
            self.init_app()
        else:
            sys.exit()

    def init_app(self):
        self.setWindowTitle("نرم‌افزار حسابداری شخصی - حرفه‌ای")
        self.setGeometry(100, 100, 1200, 900)
        self.setWindowIcon(QIcon("assets/icon.ico"))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # بارگذاری استایل‌ها
        with open('styles.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

        self.init_db()
        self.init_ui()
        self.load_data()
        
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(86400000)
        self.show()

    def init_db(self):
        try:
            self.db_manager.executescript("""
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
                    due_date TEXT,
                    is_paid INTEGER DEFAULT 0,
                    account_id INTEGER,
                    show_in_dashboard INTEGER DEFAULT 0,
                    is_credit INTEGER DEFAULT 0,
                    description TEXT,
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
                    account_id INTEGER,
                    installments_total INTEGER,
                    installments_paid INTEGER DEFAULT 0,
                    installment_amount REAL,
                    installment_interval INTEGER DEFAULT 30,  -- ستون جدید
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
                CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                dropbox_token TEXT
                );                    
            """)
            self.db_manager.commit()

            # بررسی و به‌روزرسانی ستون dropbox_token
            self.db_manager.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in self.db_manager.fetchall()]
            if "dropbox_token" not in columns:
                self.db_manager.execute("ALTER TABLE users ADD COLUMN dropbox_token TEXT")
                self.db_manager.commit()

            # بررسی و به‌روزرسانی ستون‌های جدول debts
            self.db_manager.execute("PRAGMA table_info(debts)")
            columns = [col[1] for col in self.db_manager.fetchall()]
            if "is_credit" not in columns:
                self.db_manager.execute("ALTER TABLE debts ADD COLUMN is_credit INTEGER DEFAULT 0")
            if "show_in_dashboard" not in columns:
                self.db_manager.execute("ALTER TABLE debts ADD COLUMN show_in_dashboard INTEGER DEFAULT 0")
            if "description" not in columns:
                self.db_manager.execute("ALTER TABLE debts ADD COLUMN description TEXT")

            # به‌روزرسانی جدول loans برای حذف end_date و افزودن installment_amount و installment_interval
            self.db_manager.execute("PRAGMA table_info(loans)")
            loan_columns = [col[1] for col in self.db_manager.fetchall()]
            if "installment_amount" not in loan_columns:
                self.db_manager.execute("ALTER TABLE loans ADD COLUMN installment_amount REAL")
            if "installment_interval" not in loan_columns:
                self.db_manager.execute("ALTER TABLE loans ADD COLUMN installment_interval INTEGER DEFAULT 30")
            if "end_date" in loan_columns:
                self.db_manager.executescript("""
                    CREATE TABLE loans_temp AS 
                    SELECT id, type, bank_name, total_amount, paid_amount, interest_rate, 
                        start_date, account_id, installments_total, installments_paid, 
                        installment_amount, installment_interval 
                    FROM loans;
                    DROP TABLE loans;
                    CREATE TABLE loans (
                        id INTEGER PRIMARY KEY,
                        type TEXT CHECK(type IN ('taken', 'given')),
                        bank_name TEXT,
                        total_amount REAL,
                        paid_amount REAL DEFAULT 0,
                        interest_rate REAL,
                        start_date TEXT,
                        account_id INTEGER,
                        installments_total INTEGER,
                        installments_paid INTEGER DEFAULT 0,
                        installment_amount REAL,
                        installment_interval INTEGER DEFAULT 30,
                        FOREIGN KEY (account_id) REFERENCES accounts(id)
                    );
                    INSERT INTO loans 
                    SELECT * FROM loans_temp;
                    DROP TABLE loans_temp;
                """)
            # تنظیم مقدار پیش‌فرض برای installment_interval در ردیف‌های قدیمی
            self.db_manager.execute(
                "UPDATE loans SET installment_interval = 30 WHERE installment_interval IS NULL"
            )
            # به‌روزرسانی installment_amount برای ردیف‌هایی که NULL هستند
            self.db_manager.execute(
                """
                UPDATE loans 
                SET installment_amount = COALESCE(installment_amount, total_amount / installments_total)
                WHERE installment_amount IS NULL AND installments_total > 0
                """
            )
            self.db_manager.execute(
                "UPDATE loans SET installment_amount = 0 WHERE installment_amount IS NULL"
            )
            self.db_manager.commit()

            # افزودن دسته‌بندی‌های پیش‌فرض
            self.db_manager.execute("SELECT COUNT(*) FROM categories")
            if self.db_manager.fetchone()[0] == 0:
                self.db_manager.executescript("""
                    INSERT OR IGNORE INTO categories (name, type) VALUES
                    ('حقوق', 'income'), ('فروش', 'income'), ('سایر درآمدها', 'income'),
                    ('خوراک', 'expense'), ('حمل‌ونقل', 'expense'), ('مسکن', 'expense'),
                    ('تفریح', 'expense'), ('خرید', 'expense'), ('سلامتی', 'expense'),
                    ('سایر هزینه‌ها', 'expense'),
                    ('انتقال بین حساب‌ها (خروج)', 'expense'), ('انتقال بین حساب‌ها (ورود)', 'income');
                    ('تسویه طلب', 'income'),  -- اضافه شدن این خط
                    ('تسویه بدهی', 'expense'); -- اضافه شدن این خط                                              
                """)
                self.db_manager.commit()
            else: # اگر دسته بندی‌ها از قبل وجود دارند، مطمئن می شویم دسته بندی های جدید اضافه شده باشند
                self.db_manager.executescript("""
                    INSERT OR IGNORE INTO categories (name, type) VALUES
                    ('تسویه طلب', 'income'),
                    ('تسویه بدهی', 'expense');
                """)
                self.db_manager.commit()    

            # افزودن کاربر پیش‌فرض (admin) اگر جدول users خالی باشد
            self.db_manager.execute("SELECT COUNT(*) FROM users")
            if self.db_manager.fetchone()[0] == 0:
                default_username = "admin"
                default_password = "password".encode('utf-8')
                password_hash = bcrypt.hashpw(default_password, bcrypt.gensalt()).decode('utf-8')
                self.db_manager.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                    (default_username, password_hash))
                self.db_manager.commit()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            raise

    def init_ui(self):
        #app.setFont(QFont("Vazir", 10))
        QApplication.setFont(QFont("Vazir", 10))
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
        settings_tab = self.create_settings_tab()

        tabs.addTab(dashboard_tab, "داشبورد")
        tabs.addTab(accounts_tab, "حساب‌ها")
        tabs.addTab(transactions_tab, "تراکنش‌ها")
        tabs.addTab(debts_tab, "بدهی/طلب")
        tabs.addTab(loans_tab, "وام‌ها")
        tabs.addTab(reports_tab, "گزارش‌ها")
        tabs.addTab(persons_tab, "اشخاص")
        tabs.addTab(categories_tab, "دسته‌بندی‌ها")
        tabs.addTab(settings_tab, "تنظیمات")

        tabs.currentChanged.connect(self.on_tab_changed)

        scroll = QScrollArea()
        scroll.setWidget(tabs)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

    def on_tab_changed(self, index):
        if index == 0:  # تب داشبورد
            self.update_dashboard()

    def show_change_password_dialog(self, username):
        dialog = ChangePasswordDialog(self.db_manager, username, self)
        dialog.exec()

    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        header = QWidget()
        header_layout = QHBoxLayout()
        header.setStyleSheet("background-color: #4CAF50; border-radius: 10px; padding: 10px;")
        title_label = QLabel("📊 داشبورد مالی")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.total_balance_label = QLabel("موجودی کل: ۰ ریال")
        self.total_balance_label.setStyleSheet("font-size: 18px; color: white;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.total_balance_label)
        header.setLayout(header_layout)
        layout.addWidget(header)

        # بخش جدید: آمار ماه جاری
        stats_widget = QWidget()
        stats_layout = QHBoxLayout()
        stats_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px; margin-top: 10px;")

        # ستون 1: جمع هزینه‌ها
        expenses_column = QVBoxLayout()
        expenses_label = QLabel("جمع هزینه در ماه جاری")
        expenses_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.expenses_value = QLabel("۰ ریال")
        self.expenses_value.setStyleSheet("font-size: 16px; color: red;")
        expenses_column.addWidget(expenses_label)
        expenses_column.addWidget(self.expenses_value)
        stats_layout.addLayout(expenses_column)

        # ستون 2: جمع درآمد‌ها
        income_column = QVBoxLayout()
        income_label = QLabel("جمع درآمد در ماه جاری")
        income_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.income_value = QLabel("۰ ریال")
        self.income_value.setStyleSheet("font-size: 16px; color: #333;")
        income_column.addWidget(income_label)
        income_column.addWidget(self.income_value)
        stats_layout.addLayout(income_column)

        # ستون 3: اختلاف هزینه و درآمد
        balance_column = QVBoxLayout()
        balance_label = QLabel("اختلاف هزینه و درآمد ماه جاری")
        balance_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.balance_value = QLabel("۰ ریال")
        self.balance_value.setStyleSheet("font-size: 16px; color: #333;")
        balance_column.addWidget(balance_label)
        balance_column.addWidget(self.balance_value)
        stats_layout.addLayout(balance_column)

        # ستون 4: جمع طلب‌ها
        credits_column = QVBoxLayout()
        credits_label = QLabel("جمع طلب‌های ماه جاری")
        credits_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.credits_value = QLabel("۰ ریال")
        self.credits_value.setStyleSheet("font-size: 16px; color: #333;")
        credits_column.addWidget(credits_label)
        credits_column.addWidget(self.credits_value)
        stats_layout.addLayout(credits_column)

        # ستون 5: جمع بدهی‌ها
        debts_column = QVBoxLayout()
        debts_label = QLabel("جمع بدهی‌های ماه جاری")
        debts_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        self.debts_value = QLabel("۰ ریال")
        self.debts_value.setStyleSheet("font-size: 16px; color: red;")
        debts_column.addWidget(debts_label)
        debts_column.addWidget(self.debts_value)
        stats_layout.addLayout(debts_column)

        stats_widget.setLayout(stats_layout)
        layout.addWidget(stats_widget)

        debts_widget = QWidget()
        debts_layout = QVBoxLayout()
        debts_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px; margin-top: 10px;")
        debts_label = QLabel("💸 بدهی‌ها و طلب‌های مهم")
        debts_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        debts_layout.addWidget(debts_label)

        scroll_area_debts = QScrollArea()
        self.important_debts_table = QTableWidget()
        self.important_debts_table.setColumnCount(5)
        self.important_debts_table.setHorizontalHeaderLabels(["شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت"])
        self.important_debts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.important_debts_table.verticalHeader().setDefaultSectionSize(40)
        self.important_debts_table.setColumnWidth(0, 150)
        self.important_debts_table.setColumnWidth(1, 100)
        self.important_debts_table.setColumnWidth(2, 100)
        self.important_debts_table.setColumnWidth(3, 100)
        self.important_debts_table.setColumnWidth(4, 80)
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
        self.accounts_table.setColumnCount(4)  # اضافه کردن ستون اقدامات
        self.accounts_table.setHorizontalHeaderLabels(["شناسه", "نام حساب", "موجودی", "اقدامات"])
        self.accounts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.accounts_table.setColumnWidth(0, 50)   # شناسه
        self.accounts_table.setColumnWidth(1, 200)  # نام حساب
        self.accounts_table.setColumnWidth(2, 150)  # موجودی
        self.accounts_table.setColumnWidth(3, 80)   # اقدامات
        layout.addLayout(form_layout)
        layout.addWidget(self.accounts_table)
        tab.setLayout(layout)
        return tab

    # اصلاح متد create_transactions_tab
    def create_transactions_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # فرم ثبت تراکنشcreate_debts_tab
        transaction_form = QFormLayout()
        self.transaction_account = QComboBox()
        self.transaction_person = QComboBox()
        self.transaction_person.addItem("-", None)
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(["درآمد", "هزینه"])
        self.transaction_category = QComboBox()
        self.transaction_type.currentTextChanged.connect(self.update_categories)
        self.load_categories()
        self.transaction_amount = NumberInput()
        self.transaction_date = QLineEdit()
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
        transaction_form.addRow("توضیحات:", self.transaction_desc)
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

        # فرم جستجو و گزارش‌گیری
        search_form = QFormLayout()
        search_label = QLabel("جستجو و گزارش‌گیری تراکنش‌ها")
        search_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.transaction_search_type = QComboBox()
        self.transaction_search_type.addItems(["همه", "برداشت", "واریز", "انتقال"])
        self.transaction_search_person = QComboBox()
        self.transaction_search_person.addItem("-", None)
        self.load_persons_to_combobox(self.transaction_search_person)
        self.transaction_search_amount = NumberInput()
        self.transaction_search_start_date = QLineEdit()
        self.transaction_search_start_date.setPlaceholderText("1404/02/13")
        self.transaction_search_start_date.setReadOnly(True)
        self.transaction_search_start_date.mousePressEvent = lambda event: self.show_calendar_popup(self.transaction_search_start_date)
        self.transaction_search_end_date = QLineEdit()
        self.transaction_search_end_date.setPlaceholderText("1404/02/13")
        self.transaction_search_end_date.setReadOnly(True)
        self.transaction_search_end_date.mousePressEvent = lambda event: self.show_calendar_popup(self.transaction_search_end_date)
        search_btn = QPushButton("نمایش گزارش")
        search_btn.clicked.connect(self.search_transactions)
        search_form.addRow(search_label)
        search_form.addRow("نوع تراکنش:", self.transaction_search_type)
        search_form.addRow("شخص:", self.transaction_search_person)
        search_form.addRow("مبلغ:", self.transaction_search_amount)
        search_form.addRow("از تاریخ (شمسی):", self.transaction_search_start_date)
        search_form.addRow("تا تاریخ (شمسی):", self.transaction_search_end_date)
        search_form.addRow(search_btn)
        layout.addLayout(search_form)

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

        # صفحه‌بندی
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

    def load_persons_to_combobox(self, combobox):
        try:
            combobox.clear()
            combobox.addItem("-", None)
            self.db_manager.execute("SELECT id, name FROM persons")
            persons = self.db_manager.fetchall()
            for id, name in persons:
                combobox.addItem(name, id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_accounts_to_combobox(self, combobox):
        try:
            combobox.clear()
            combobox.addItem("-", None)
            self.db_manager.execute("SELECT id, name FROM accounts")
            accounts = self.db_manager.fetchall()
            for id, name in accounts:
                combobox.addItem(name, id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def search_transactions(self):
        try:
            trans_type = self.transaction_search_type.currentText()
            person_id = self.transaction_search_person.currentData()
            amount = self.transaction_search_amount.get_raw_value()
            start_date = self.transaction_search_start_date.text()
            end_date = self.transaction_search_end_date.text()

            if not start_date or not end_date:
                QMessageBox.warning(self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
                return
            if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
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
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.verticalHeader().setDefaultSectionSize(40)

        self.transaction_report_current_page = 1
        self.transaction_report_per_page = 50
        self.transaction_report_results = results
        self.transaction_report_total_pages = (len(results) + self.transaction_report_per_page - 1) // self.transaction_report_per_page

        self.update_transaction_report_table(table)

        scroll_area = QScrollArea()
        scroll_area.setWidget(table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        pagination_layout = QHBoxLayout()
        prev_btn = QPushButton("صفحه قبلی")
        next_btn = QPushButton("صفحه بعدی")
        page_label = QLabel(f"صفحه {self.transaction_report_current_page} از {self.transaction_report_total_pages}")
        prev_btn.clicked.connect(lambda: self.prev_transaction_report_page(table, page_label))
        next_btn.clicked.connect(lambda: self.next_transaction_report_page(table, page_label))
        pagination_layout.addWidget(prev_btn)
        pagination_layout.addWidget(page_label)
        pagination_layout.addWidget(next_btn)
        layout.addLayout(pagination_layout)

        export_btn = QPushButton("خروجی (اکسل/CSV/PDF)")
        export_btn.clicked.connect(lambda: self.export_report(results, "transactions"))
        layout.addWidget(export_btn)

        dialog.resize(800, 600)
        dialog.exec()

    def update_transaction_report_table(self, table):
        start = (self.transaction_report_current_page - 1) * self.transaction_report_per_page
        end = start + self.transaction_report_per_page
        page_results = self.transaction_report_results[start:end]
        table.setRowCount(len(page_results))
        for row, (id, date, account, person, category, amount, desc, cat_type) in enumerate(page_results):
            table.setItem(row, 0, QTableWidgetItem(str(id)))
            table.setItem(row, 1, QTableWidgetItem(gregorian_to_shamsi(date)))
            table.setItem(row, 2, QTableWidgetItem(account))
            table.setItem(row, 3, QTableWidgetItem(person or "-"))
            table.setItem(row, 4, QTableWidgetItem(category))
            table.setItem(row, 5, QTableWidgetItem(format_number(amount)))
            table.setItem(row, 6, QTableWidgetItem(desc or "-"))
            table.setItem(row, 7, QTableWidgetItem("درآمد" if cat_type == "income" else "هزینه"))

    def prev_transaction_report_page(self, table, page_label):
        if self.transaction_report_current_page > 1:
            self.transaction_report_current_page -= 1
            self.update_transaction_report_table(table)
            page_label.setText(f"صفحه {self.transaction_report_current_page} از {self.transaction_report_total_pages}")

    def next_transaction_report_page(self, table, page_label):
        if self.transaction_report_current_page < self.transaction_report_total_pages:
            self.transaction_report_current_page += 1
            self.update_transaction_report_table(table)
            page_label.setText(f"صفحه {self.transaction_report_current_page} از {self.transaction_report_total_pages}")

    # اصلاح متد create_debts_tab
    def create_debts_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.debt_person = QComboBox()
        self.debt_amount = NumberInput()
        self.debt_account = QComboBox()
        self.debt_account.setEnabled(False)
        self.debt_due_date = QLineEdit()
        today = datetime.now().date()
        self.debt_due_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.debt_due_date.setPlaceholderText("1404/02/13")
        self.debt_due_date.setReadOnly(True)
        self.debt_due_date.mousePressEvent = lambda event: self.show_calendar_popup(self.debt_due_date)
        self.debt_is_credit = QComboBox()
        self.debt_is_credit.addItems(["بدهی من", "طلب من"])
        self.debt_has_payment = QCheckBox("آیا پولی دریافت/پرداخت شده؟")
        self.debt_has_payment.stateChanged.connect(self.toggle_account_field)
        self.debt_show_in_dashboard = QCheckBox("نمایش در داشبورد")
        self.debt_description = QLineEdit()
        add_debt_btn = QPushButton("ثبت بدهی/طلب")
        add_debt_btn.clicked.connect(self.add_debt)
        form_layout.addRow("شخص:", self.debt_person)
        form_layout.addRow("مبلغ:", self.debt_amount)
        form_layout.addRow("حساب مرتبط:", self.debt_account)
        form_layout.addRow("", self.debt_has_payment)
        form_layout.addRow("تاریخ سررسید (شمسی - اختیاری):", self.debt_due_date)
        form_layout.addRow("نوع:", self.debt_is_credit)
        form_layout.addRow("", self.debt_show_in_dashboard)
        form_layout.addRow("توضیحات:", self.debt_description)
        form_layout.addRow(add_debt_btn)
        layout.addLayout(form_layout)

        # فرم جستجو و گزارش‌گیری
        search_form = QFormLayout()
        search_label = QLabel("جستجو و گزارش‌گیری بدهی/طلب")
        search_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.debt_search_type = QComboBox()
        self.debt_search_type.addItems(["همه", "بدهی", "طلب"])
        self.debt_search_person = QComboBox()
        self.debt_search_person.addItem("-", None)
        self.load_persons_to_combobox(self.debt_search_person)
        self.debt_search_amount = NumberInput()
        self.debt_search_start_date = QLineEdit()
        self.debt_search_start_date.setPlaceholderText("1404/02/13")
        self.debt_search_start_date.setReadOnly(True)
        self.debt_search_start_date.mousePressEvent = lambda event: self.show_calendar_popup(self.debt_search_start_date)
        self.debt_search_end_date = QLineEdit()
        self.debt_search_end_date.setPlaceholderText("1404/02/13")
        self.debt_search_end_date.setReadOnly(True)
        self.debt_search_end_date.mousePressEvent = lambda event: self.show_calendar_popup(self.debt_search_end_date)
        search_btn = QPushButton("نمایش گزارش")
        search_btn.clicked.connect(self.search_debts)
        search_form.addRow(search_label)
        search_form.addRow("نوع:", self.debt_search_type)
        search_form.addRow("شخص:", self.debt_search_person)
        search_form.addRow("مبلغ:", self.debt_search_amount)
        search_form.addRow("از تاریخ (شمسی):", self.debt_search_start_date)
        search_form.addRow("تا تاریخ (شمسی):", self.debt_search_end_date)
        search_form.addRow(search_btn)
        layout.addLayout(search_form)

        # جدول بدهی‌ها با اسکرول
        scroll_area = QScrollArea()
        self.debts_table = QTableWidget()
        self.debts_table.setColumnCount(10)
        self.debts_table.setHorizontalHeaderLabels(["شناسه", "شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت", "حساب", "توضیحات", "ویرایش", "حذف", "تسویه"])
        self.debts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.debts_table.verticalHeader().setDefaultSectionSize(40)
        scroll_area.setWidget(self.debts_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        # صفحه‌بندی
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
        today = datetime.now().date()
        self.loan_start_date.setText(gregorian_to_shamsi(today.strftime("%Y-%m-%d")))
        self.loan_start_date.setPlaceholderText("1404/02/13")
        self.loan_start_date.setReadOnly(True)
        self.loan_start_date.mousePressEvent = lambda event: self.show_calendar_popup(self.loan_start_date)
        self.loan_installments_total = NumberInput()
        self.loan_installments_paid = NumberInput()
        self.loan_installment_amount = NumberInput()
        self.loan_installment_interval = NumberInput()
        self.loan_installment_interval.setPlaceholderText("30")

        # چک‌باکس جدید: آیا مبلغ وام به حساب اضافه شود؟
        self.loan_add_to_account_checkbox = QCheckBox("مبلغ وام به حساب اضافه/کم شود؟")
        self.loan_add_to_account_checkbox.setChecked(True) # به صورت پیش‌فرض فعال

        add_loan_btn = QPushButton("ثبت وام")
        add_loan_btn.clicked.connect(self.add_loan)
        form_layout.addRow("نوع وام:", self.loan_type)
        form_layout.addRow("نام بانک:", self.loan_bank)
        form_layout.addRow("مبلغ کل:", self.loan_amount)
        form_layout.addRow("نرخ سود (%):", self.loan_interest)
        form_layout.addRow("حساب مرتبط:", self.loan_account)
        form_layout.addRow("", self.loan_add_to_account_checkbox) # اضافه کردن چک‌باکس
        form_layout.addRow("تاریخ شروع (شمسی):", self.loan_start_date)
        form_layout.addRow("تعداد اقساط کل:", self.loan_installments_total)
        form_layout.addRow("تعداد اقساط پرداخت‌شده:", self.loan_installments_paid)
        form_layout.addRow("مبلغ هر قسط:", self.loan_installment_amount)
        form_layout.addRow("فاصله اقساط (روز):", self.loan_installment_interval)
        form_layout.addRow(add_loan_btn)
        layout.addLayout(form_layout)

        scroll_area = QScrollArea()
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(12)
        self.loans_table.setHorizontalHeaderLabels([
            "شناسه", "نوع", "بانک", "مبلغ", "پرداخت‌شده", "سود",
            "شروع", "اقساط کل", "اقساط پرداخت", "مبلغ قسط", "ویرایش", "مشاهده اقساط"
        ])
        self.loans_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.loans_table.verticalHeader().setDefaultSectionSize(40)
        self.loans_table.setColumnWidth(0, 50)
        self.loans_table.setColumnWidth(1, 100)
        self.loans_table.setColumnWidth(2, 150)
        self.loans_table.setColumnWidth(3, 120)
        self.loans_table.setColumnWidth(4, 120)
        self.loans_table.setColumnWidth(5, 80)
        self.loans_table.setColumnWidth(6, 100)
        self.loans_table.setColumnWidth(7, 80)
        self.loans_table.setColumnWidth(8, 100)
        self.loans_table.setColumnWidth(9, 100)
        self.loans_table.setColumnWidth(10, 80)
        self.loans_table.setColumnWidth(11, 120)
        scroll_area.setWidget(self.loans_table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

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

    def search_debts(self):
        try:
            debt_type = self.debt_search_type.currentText()
            person_id = self.debt_search_person.currentData()
            amount = self.debt_search_amount.get_raw_value()
            start_date = self.debt_search_start_date.text()
            end_date = self.debt_search_end_date.text()

            if not start_date or not end_date:
                QMessageBox.warning(self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
                return
            if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = shamsi_to_gregorian(start_date)
            end_date_g = shamsi_to_gregorian(end_date)
            if not start_date_g or not end_date_g:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            query = """
                SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, d.is_paid, COALESCE(a.name, '-'), d.is_credit, d.description
                FROM debts d
                JOIN persons p ON d.person_id = p.id
                LEFT JOIN accounts a ON d.account_id = a.id
                WHERE d.due_date BETWEEN ? AND ?
            """
            params = [start_date_g, end_date_g]

            if debt_type == "بدهی":
                query += " AND d.is_credit = 0"
            elif debt_type == "طلب":
                query += " AND d.is_credit = 1"

            if person_id:
                query += " AND d.person_id = ?"
                params.append(person_id)
            if amount:
                query += " AND d.amount = ?"
                params.append(amount)

            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()
            self.show_debt_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def show_debt_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش بدهی/طلب")
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels(["شناسه", "شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت", "حساب", "نوع", "توضیحات"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.verticalHeader().setDefaultSectionSize(40)

        self.debt_report_current_page = 1
        self.debt_report_per_page = 50
        self.debt_report_results = results
        self.debt_report_total_pages = (len(results) + self.debt_report_per_page - 1) // self.debt_report_per_page

        self.update_debt_report_table(table)

        scroll_area = QScrollArea()
        scroll_area.setWidget(table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        pagination_layout = QHBoxLayout()
        prev_btn = QPushButton("صفحه قبلی")
        next_btn = QPushButton("صفحه بعدی")
        page_label = QLabel(f"صفحه {self.debt_report_current_page} از {self.debt_report_total_pages}")
        prev_btn.clicked.connect(lambda: self.prev_debt_report_page(table, page_label))
        next_btn.clicked.connect(lambda: self.next_debt_report_page(table, page_label))
        pagination_layout.addWidget(prev_btn)
        pagination_layout.addWidget(page_label)
        pagination_layout.addWidget(next_btn)
        layout.addLayout(pagination_layout)

        export_btn = QPushButton("خروجی (اکسل/CSV/PDF)")
        export_btn.clicked.connect(lambda: self.export_report(results, "debts"))
        layout.addWidget(export_btn)

        dialog.resize(800, 600)
        dialog.exec()

    def update_debt_report_table(self, table):
        start = (self.debt_report_current_page - 1) * self.debt_report_per_page
        end = start + self.debt_report_per_page
        page_results = self.debt_report_results[start:end]
        table.setRowCount(len(page_results))
        for row, (id, person, amount, paid, due_date, is_paid, account, is_credit, description) in enumerate(page_results):
            table.setItem(row, 0, QTableWidgetItem(str(id)))
            table.setItem(row, 1, QTableWidgetItem(person))
            table.setItem(row, 2, QTableWidgetItem(format_number(amount)))
            table.setItem(row, 3, QTableWidgetItem(format_number(paid)))
            table.setItem(row, 4, QTableWidgetItem(gregorian_to_shamsi(due_date) if due_date else "-"))
            table.setItem(row, 5, QTableWidgetItem("پرداخت شده" if is_paid else "در جریان"))
            table.setItem(row, 6, QTableWidgetItem(account))
            table.setItem(row, 7, QTableWidgetItem("طلب" if is_credit else "بدهی"))
            table.setItem(row, 8, QTableWidgetItem(description))

    def prev_debt_report_page(self, table, page_label):
        if self.debt_report_current_page > 1:
            self.debt_report_current_page -= 1
            self.update_debt_report_table(table)
            page_label.setText(f"صفحه {self.debt_report_current_page} از {self.debt_report_total_pages}")

    def next_debt_report_page(self, table, page_label):
        if self.debt_report_current_page < self.debt_report_total_pages:
            self.debt_report_current_page += 1
            self.update_debt_report_table(table)
            page_label.setText(f"صفحه {self.debt_report_current_page} از {self.debt_report_total_pages}")

    def create_reports_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        # دکمه‌های انواع گزارش با استایل بهبود‌یافته
        buttons_layout = QHBoxLayout()
        general_report_btn = QPushButton("گزارش کلی")
        cost_income_report_btn = QPushButton("گزارش هزینه/درآمد")
        monthly_report_btn = QPushButton("گزارش تفصیلی ماهانه")
        person_report_btn = QPushButton("گزارش اشخاص")
        
        # اعمال استایل به دکمه‌ها
        button_style = """
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        general_report_btn.setStyleSheet(button_style)
        cost_income_report_btn.setStyleSheet(button_style)
        monthly_report_btn.setStyleSheet(button_style)
        person_report_btn.setStyleSheet(button_style)
        
        general_report_btn.clicked.connect(self.show_general_report_form)
        cost_income_report_btn.clicked.connect(self.show_cost_income_report_form)
        monthly_report_btn.clicked.connect(self.show_monthly_report_form)
        person_report_btn.clicked.connect(self.show_person_report_form)
        
        buttons_layout.addWidget(general_report_btn)
        buttons_layout.addWidget(cost_income_report_btn)
        buttons_layout.addWidget(monthly_report_btn)
        buttons_layout.addWidget(person_report_btn)
        layout.addLayout(buttons_layout)

        # فرم فیلترهای گزارش
        form_layout = QFormLayout()
        self.report_type = QComboBox()
        self.report_type.addItems(["تراکنش‌ها", "درآمد", "هزینه", "بدهی/طلب شخص", "بدهی/طلب کل"])
        self.report_person = QComboBox()  # تعریف self.report_person
        self.report_person.addItem("-", None)
        self.load_report_persons()  # بارگذاری اشخاص
        self.report_date_start = QLineEdit()
        self.report_date_start.setPlaceholderText("1404/02/13")
        self.report_date_start.setReadOnly(True)
        self.report_date_start.mousePressEvent = lambda event: self.show_calendar_popup(self.report_date_start)
        self.report_date_end = QLineEdit()
        self.report_date_end.setPlaceholderText("1404/02/13")
        self.report_date_end.setReadOnly(True)
        self.report_date_end.mousePressEvent = lambda event: self.show_calendar_popup(self.report_date_end)
        generate_btn = QPushButton("تولید گزارش")
        generate_btn.setStyleSheet(button_style)
        generate_btn.clicked.connect(self.generate_custom_report)
        form_layout.addRow("نوع گزارش:", self.report_type)
        form_layout.addRow("شخص:", self.report_person)
        form_layout.addRow("از تاریخ (شمسی):", self.report_date_start)
        form_layout.addRow("تا تاریخ (شمسی):", self.report_date_end)
        form_layout.addRow(generate_btn)
        layout.addLayout(form_layout)

        # اضافه کردن فاصله برای جداسازی
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        tab.setLayout(layout)
        return tab

    def show_general_report_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش کلی")
        layout = QFormLayout()
        
        self.general_start_date = QLineEdit()
        self.general_start_date.setPlaceholderText("1404/02/13")
        self.general_start_date.setReadOnly(True)
        self.general_start_date_calendar = PersianCalendarWidget(self.general_start_date)
        
        self.general_end_date = QLineEdit()
        self.general_end_date.setPlaceholderText("1404/02/13")
        self.general_end_date.setReadOnly(True)
        self.general_end_date_calendar = PersianCalendarWidget(self.general_end_date)
        
        generate_btn = QPushButton("نمایش گزارش")
        generate_btn.clicked.connect(lambda: self.generate_general_report(dialog))
        
        layout.addRow("از تاریخ (شمسی):", self.general_start_date)
        layout.addRow(self.general_start_date_calendar)
        layout.addRow("تا تاریخ (شمسی):", self.general_end_date)
        layout.addRow(self.general_end_date_calendar)
        layout.addRow(generate_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def generate_general_report(self, dialog):
        try:
            start_date = self.general_start_date.text()
            end_date = self.general_end_date.text()

            if not start_date or not end_date:
                QMessageBox.warning(self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
                return
            if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = shamsi_to_gregorian(start_date)
            end_date_g = shamsi_to_gregorian(end_date)
            if not start_date_g or not end_date_g:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            results = []
            # مجموع هزینه‌ها
            self.db_manager.execute("""
                SELECT SUM(t.amount)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE c.type = 'expense' AND t.date BETWEEN ? AND ?
            """, (start_date_g, end_date_g))
            total_cost = self.db_manager.fetchone()[0] or 0
            results.append(["مجموع هزینه‌ها", format_number(total_cost)])

            # مجموع درآمدها
            self.db_manager.execute("""
                SELECT SUM(t.amount)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE c.type = 'income' AND t.date BETWEEN ? AND ?
            """, (start_date_g, end_date_g))
            total_income = self.db_manager.fetchone()[0] or 0
            results.append(["مجموع درآمدها", format_number(total_income)])

            # تفاوت
            results.append(["تفاوت (درآمد - هزینه)", format_number(total_income - total_cost)])

            # بستن دیالوگ پارامترها
            dialog.accept()

            # نمایش گزارش
            self.show_general_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def show_general_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش کلی")
        layout = QVBoxLayout()
        
        # بررسی خالی بودن داده‌ها
        if not results:
            QMessageBox.information(self, "بدون نتیجه", "هیچ داده‌ای برای نمایش یافت نشد.")
            dialog.accept()
            return

        # لاگ‌گیری برای دیباگ
        #print(f"تعداد ردیف‌های گزارش کلی: {len(results)}")
        #print(f"داده‌های گزارش: {results}")

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["معیار", "مقدار"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.setRowCount(len(results))
        table.setColumnWidth(0, 200)  # معیار
        table.setColumnWidth(1, 200)  # مقدار
        table.setMinimumHeight(400)
        table.setMinimumWidth(500)

        # پر کردن جدول
        for row_idx, row_data in enumerate(results):
            #print(f"پر کردن ردیف {row_idx}: {row_data}")
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "-")
                table.setItem(row_idx, col_idx, item)
                #print(f"تنظیم آیتم در ردیف {row_idx}، ستون {col_idx}: {item.text()}")

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.update()

        scroll_area = QScrollArea()
        scroll_area.setWidget(table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        export_btn = QPushButton("خروجی (اکسل/CSV/PDF)")
        export_btn.clicked.connect(lambda: self.export_report(results, "general"))
        layout.addWidget(export_btn)

        dialog.setLayout(layout)
        dialog.resize(600, 600)
        dialog.exec()

    def show_cost_income_report_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش هزینه/درآمد")
        layout = QFormLayout()
        
        self.cost_income_account = QComboBox()
        self.load_accounts_to_combobox(self.cost_income_account)
        
        self.cost_income_type = QComboBox()
        self.cost_income_type.addItems(["هزینه", "درآمد"])
        
        self.cost_income_person = QComboBox()
        self.load_persons_to_combobox(self.cost_income_person)
        
        self.cost_income_start_date = QLineEdit()
        self.cost_income_start_date.setPlaceholderText("1404/02/13")
        self.cost_income_start_date.setReadOnly(True)
        self.cost_income_start_date_calendar = PersianCalendarWidget(self.cost_income_start_date)
        
        self.cost_income_end_date = QLineEdit()
        self.cost_income_end_date.setPlaceholderText("1404/02/13")
        self.cost_income_end_date.setReadOnly(True)
        self.cost_income_end_date_calendar = PersianCalendarWidget(self.cost_income_end_date)
        
        generate_btn = QPushButton("نمایش گزارش")
        generate_btn.clicked.connect(lambda: self.generate_cost_income_report(dialog))
        
        layout.addRow("حساب:", self.cost_income_account)
        layout.addRow("نوع:", self.cost_income_type)
        layout.addRow("شخص:", self.cost_income_person)
        layout.addRow("از تاریخ (شمسی):", self.cost_income_start_date)
        layout.addRow(self.cost_income_start_date_calendar)
        layout.addRow("تا تاریخ (شمسی):", self.cost_income_end_date)
        layout.addRow(self.cost_income_end_date_calendar)
        layout.addRow(generate_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def load_accounts_to_combobox(self, combobox):
        try:
            combobox.clear()
            combobox.addItem("-", None)
            self.db_manager.execute("SELECT id, name FROM accounts")
            accounts = self.db_manager.fetchall()
            for id, name in accounts:
                combobox.addItem(name, id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def generate_cost_income_report(self, dialog):
        try:
            account_id = self.cost_income_account.currentData()
            report_type = "expense" if self.cost_income_type.currentText() == "هزینه" else "income"
            person_id = self.cost_income_person.currentData()
            start_date = self.cost_income_start_date.text()
            end_date = self.cost_income_end_date.text()

            if not start_date or not end_date:
                QMessageBox.warning(self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
                return
            if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = shamsi_to_gregorian(start_date)
            end_date_g = shamsi_to_gregorian(end_date)
            if not start_date_g or not end_date_g:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            query = """
                SELECT c.name, t.amount, t.date, a.name, p.name, t.description
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN accounts a ON t.account_id = a.id
                LEFT JOIN persons p ON t.person_id = p.id
                WHERE c.type = ? AND t.date BETWEEN ? AND ?
            """
            params = [report_type, start_date_g, end_date_g]
            
            if account_id:
                query += " AND t.account_id = ?"
                params.append(account_id)
            if person_id:
                query += " AND t.person_id = ?"
                params.append(person_id)

            self.db_manager.execute(query, params)
            results = self.db_manager.fetchall()

            # بستن دیالوگ پارامترها
            dialog.accept()

            # نمایش گزارش
            self.show_cost_income_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def show_cost_income_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش هزینه/درآمد")
        layout = QVBoxLayout()
        
        # بررسی خالی بودن داده‌ها
        if not results:
            QMessageBox.information(self, "بدون نتیجه", "هیچ داده‌ای برای نمایش در این بازه زمانی یافت نشد.")
            dialog.accept()
            return

        # لاگ‌گیری برای دیباگ
        #print(f"تعداد ردیف‌های گزارش هزینه/درآمد: {len(results)}")
        #print(f"داده‌های گزارش: {results}")

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["نوع", "مبلغ", "تاریخ", "حساب", "شخص", "توضیحات"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.setRowCount(len(results))  # تنظیم تعداد ردیف‌ها بر اساس داده‌ها
        table.setColumnWidth(0, 150)  # نوع
        table.setColumnWidth(1, 120)  # مبلغ
        table.setColumnWidth(2, 120)  # تاریخ
        table.setColumnWidth(3, 150)  # حساب
        table.setColumnWidth(4, 150)  # شخص
        table.setColumnWidth(5, 250)  # توضیحات
        table.setMinimumHeight(400)
        table.setMinimumWidth(800)

        # پر کردن جدول
        for row_idx, row_data in enumerate(results):
            #print(f"پر کردن ردیف {row_idx}: {row_data}")
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "-")
                table.setItem(row_idx, col_idx, item)
                #print(f"تنظیم آیتم در ردیف {row_idx}، ستون {col_idx}: {item.text()}")

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.update()

        # استفاده از QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidget(table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        # دکمه خروجی
        export_btn = QPushButton("خروجی (اکسل/CSV/PDF)")
        export_btn.clicked.connect(lambda: self.export_report(results, "cost_income"))
        layout.addWidget(export_btn)

        dialog.setLayout(layout)
        dialog.resize(900, 600)
        dialog.exec() 
        
    def update_cost_income_report_table(self, table):
        start = (self.cost_income_report_current_page - 1) * self.cost_income_report_per_page
        end = start + self.cost_income_report_per_page
        page_results = self.cost_income_report_results[start:end]
        table.setRowCount(len(page_results))
        for row, (category, amount, date, account, person, desc) in enumerate(page_results):
            table.setItem(row, 0, QTableWidgetItem(category))
            table.setItem(row, 1, QTableWidgetItem(format_number(amount)))
            table.setItem(row, 2, QTableWidgetItem(gregorian_to_shamsi(date)))
            table.setItem(row, 3, QTableWidgetItem(account))
            table.setItem(row, 4, QTableWidgetItem(person or "-"))
            table.setItem(row, 5, QTableWidgetItem(desc or "-"))

    def prev_cost_income_report_page(self, table, page_label):
        if self.cost_income_report_current_page > 1:
            self.cost_income_report_current_page -= 1
            self.update_cost_income_report_table(table)
            page_label.setText(f"صفحه {self.cost_income_report_current_page} از {self.cost_income_report_total_pages}")

    def next_cost_income_report_page(self, table, page_label):
        if self.cost_income_report_current_page < self.cost_income_report_total_pages:
            self.cost_income_report_current_page += 1
            self.update_cost_income_report_table(table)
            page_label.setText(f"صفحه {self.cost_income_report_current_page} از {self.cost_income_report_total_pages}")

    def show_monthly_report_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش تفصیلی ماهانه")
        layout = QFormLayout()
        
        self.monthly_year = QLineEdit()
        self.monthly_year.setPlaceholderText("1404")
        self.monthly_year.setValidator(QIntValidator(1300, 1500))
        
        generate_btn = QPushButton("نمایش گزارش")
        generate_btn.clicked.connect(lambda: self.generate_monthly_report(dialog))
        
        layout.addRow("سال (شمسی):", self.monthly_year)
        layout.addRow(generate_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def generate_monthly_report(self, dialog):
        try:
            year = self.monthly_year.text()
            if not year:
                QMessageBox.warning(self, "خطا", "فیلد سال ضروری است!")
                return
            year = int(year)
            if year < 1300 or year > 1500:
                QMessageBox.warning(self, "خطا", "سال باید بین 1300 تا 1500 باشد!")
                return

            results = []
            for month in range(1, 13):
                start_date = f"{year}/{month:02d}/01"
                end_date = f"{year}/{month:02d}/30"  # ساده‌سازی برای تست
                start_date_g = shamsi_to_gregorian(start_date)
                end_date_g = shamsi_to_gregorian(end_date)
                
                query = """
                    SELECT SUM(CASE WHEN c.type = 'expense' THEN t.amount ELSE 0 END) as cost,
                        SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END) as income,
                        SUM(CASE WHEN c.type = 'expense' THEN t.amount ELSE 0 END) -
                        SUM(CASE WHEN c.type = 'income' THEN t.amount ELSE 0 END) as diff
                    FROM transactions t
                    JOIN categories c ON t.category_id = c.id
                    WHERE t.date BETWEEN ? AND ?
                """
                self.db_manager.execute(query, (start_date_g, end_date_g))
                cost, income, diff = self.db_manager.fetchone() or (0, 0, 0)
                results.append([f"{year}/{month:02d}", cost or 0, income or 0, diff or 0])

            # بستن دیالوگ پارامترها
            dialog.accept()

            # نمایش گزارش
            self.show_monthly_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def show_monthly_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش تفصیلی ماهانه")
        layout = QVBoxLayout()
        
        # بررسی خالی بودن داده‌ها
        if not results:
            QMessageBox.information(self, "بدون نتیجه", "هیچ داده‌ای برای نمایش یافت نشد.")
            dialog.accept()
            return

        # لاگ‌گیری برای دیباگ
        #print(f"تعداد ردیف‌های گزارش تفصیلی ماهانه: {len(results)}")
        #print(f"داده‌های گزارش: {results}")

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["ماه", "هزینه", "درآمد", "تفاوت"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.setRowCount(len(results))
        table.setColumnWidth(0, 100)  # ماه
        table.setColumnWidth(1, 120)  # هزینه
        table.setColumnWidth(2, 120)  # درآمد
        table.setColumnWidth(3, 120)  # تفاوت
        table.setMinimumHeight(400)
        table.setMinimumWidth(600)

        # پر کردن جدول
        for row_idx, row_data in enumerate(results):
            #print(f"پر کردن ردیف {row_idx}: {row_data}")
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "-")
                table.setItem(row_idx, col_idx, item)
                #print(f"تنظیم آیتم در ردیف {row_idx}، ستون {col_idx}: {item.text()}")

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.update()

        scroll_area = QScrollArea()
        scroll_area.setWidget(table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        export_btn = QPushButton("خروجی (اکسل/CSV/PDF)")
        export_btn.clicked.connect(lambda: self.export_report(results, "monthly"))
        layout.addWidget(export_btn)

        dialog.setLayout(layout)
        dialog.resize(700, 600)
        dialog.exec()

    def show_person_report_form(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش اشخاص")
        layout = QFormLayout()
        
        self.person_report_person = QComboBox()
        self.load_persons_to_combobox(self.person_report_person)
        
        self.person_report_start_date = QLineEdit()
        self.person_report_start_date.setPlaceholderText("1404/02/13")
        self.person_report_start_date.setReadOnly(True)
        self.person_report_start_date_calendar = PersianCalendarWidget(self.person_report_start_date)
        
        self.person_report_end_date = QLineEdit()
        self.person_report_end_date.setPlaceholderText("1404/02/13")
        self.person_report_end_date.setReadOnly(True)
        self.person_report_end_date_calendar = PersianCalendarWidget(self.person_report_end_date)
        
        generate_btn = QPushButton("نمایش گزارش")
        generate_btn.clicked.connect(lambda: self.generate_person_report(dialog))
        
        layout.addRow("شخص:", self.person_report_person)
        layout.addRow("از تاریخ (شمسی):", self.person_report_start_date)
        layout.addRow(self.person_report_start_date_calendar)
        layout.addRow("تا تاریخ (شمسی):", self.person_report_end_date)
        layout.addRow(self.person_report_end_date_calendar)
        layout.addRow(generate_btn)
        
        dialog.setLayout(layout)
        dialog.exec()

    def generate_person_report(self, dialog):
        try:
            person_id = self.person_report_person.currentData()
            start_date = self.person_report_start_date.text()
            end_date = self.person_report_end_date.text()

            if not person_id:
                QMessageBox.warning(self, "خطا", "لطفاً یک شخص انتخاب کنید!")
                return
            if not start_date or not end_date:
                QMessageBox.warning(self, "خطا", "فیلدهای تاریخ شروع و پایان ضروری هستند!")
                return
            if not is_valid_shamsi_date(start_date) or not is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = shamsi_to_gregorian(start_date)
            end_date_g = shamsi_to_gregorian(end_date)
            if not start_date_g or not end_date_g:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return

            query = """
                SELECT c.name, t.date, a.name, t.amount, t.description
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                JOIN accounts a ON t.account_id = a.id
                WHERE t.person_id = ? AND t.date BETWEEN ? AND ?
            """
            self.db_manager.execute(query, (person_id, start_date_g, end_date_g))
            results = self.db_manager.fetchall()

            # بستن دیالوگ پارامترها
            dialog.accept()

            # نمایش گزارش
            self.show_person_report(results)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def show_person_report(self, results):
        dialog = QDialog(self)
        dialog.setWindowTitle("گزارش اشخاص")
        layout = QVBoxLayout()
        
        # بررسی خالی بودن داده‌ها
        if not results:
            QMessageBox.information(self, "بدون نتیجه", "هیچ داده‌ای برای نمایش یافت نشد.")
            dialog.accept()
            return

        # لاگ‌گیری برای دیباگ
        #print(f"تعداد ردیف‌های گزارش اشخاص: {len(results)}")
        #print(f"داده‌های گزارش: {results}")

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["دسته‌بندی", "تاریخ", "حساب", "مبلغ", "توضیحات"])
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        table.setRowCount(len(results))
        table.setColumnWidth(0, 150)  # دسته‌بندی
        table.setColumnWidth(1, 120)  # تاریخ
        table.setColumnWidth(2, 150)  # حساب
        table.setColumnWidth(3, 120)  # مبلغ
        table.setColumnWidth(4, 250)  # توضیحات
        table.setMinimumHeight(400)
        table.setMinimumWidth(800)

        # پر کردن جدول
        for row_idx, row_data in enumerate(results):
            #print(f"پر کردن ردیف {row_idx}: {row_data}")
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "-")
                table.setItem(row_idx, col_idx, item)
                print(f"تنظیم آیتم در ردیف {row_idx}، ستون {col_idx}: {item.text()}")

        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        table.update()

        scroll_area = QScrollArea()
        scroll_area.setWidget(table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        layout.addWidget(scroll_area)

        export_btn = QPushButton("خروجی (اکسل/CSV/PDF)")
        export_btn.clicked.connect(lambda: self.export_report(results, "person"))
        layout.addWidget(export_btn)

        dialog.setLayout(layout)
        dialog.resize(900, 600)
        dialog.exec()

    def update_person_report_table(self, table):
        start = (self.person_report_current_page - 1) * self.person_report_per_page
        end = start + self.person_report_per_page
        page_results = self.person_report_results[start:end]
        table.setRowCount(len(page_results))
        for row, (typ, date, account, category, amount, desc, status) in enumerate(page_results):
            table.setItem(row, 0, QTableWidgetItem(typ))
            table.setItem(row, 1, QTableWidgetItem(gregorian_to_shamsi(date) if date != "-" else "-"))
            table.setItem(row, 2, QTableWidgetItem(account))
            table.setItem(row, 3, QTableWidgetItem(category))
            table.setItem(row, 4, QTableWidgetItem(format_number(amount) if isinstance(amount, (int, float)) else amount))
            table.setItem(row, 5, QTableWidgetItem(desc))
            table.setItem(row, 6, QTableWidgetItem(status))

    def prev_person_report_page(self, table, page_label):
        if self.person_report_current_page > 1:
            self.person_report_current_page -= 1
            self.update_person_report_table(table)
            page_label.setText(f"صفحه {self.person_report_current_page} از {self.person_report_total_pages}")

    def next_person_report_page(self, table, page_label):
        if self.person_report_current_page < self.person_report_total_pages:
            self.person_report_current_page += 1
            self.update_person_report_table(table)
            page_label.setText(f"صفحه {self.person_report_current_page} از {self.person_report_total_pages}")
    
    def export_report(self, data, report_type):
        dialog = QDialog(self)
        dialog.setWindowTitle("انتخاب نوع خروجی")
        layout = QVBoxLayout()
        excel_btn = QPushButton("خروجی اکسل")
        csv_btn = QPushButton("خروجی CSV")
        pdf_btn = QPushButton("خروجی PDF")
        excel_btn.clicked.connect(lambda: self.generate_export(data, report_type, "excel", dialog))
        csv_btn.clicked.connect(lambda: self.generate_export(data, report_type, "csv", dialog))
        pdf_btn.clicked.connect(lambda: self.generate_export(data, report_type, "pdf", dialog))
        layout.addWidget(excel_btn)
        layout.addWidget(csv_btn)
        layout.addWidget(pdf_btn)
        dialog.setLayout(layout)
        dialog.exec()

    def generate_export(self, data, report_type, format_type, dialog):
        try:
            # تولید نام فایل با تاریخ و زمان
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_prefix = f"{report_type}_report_{timestamp}"

            if report_type == "transactions":
                df = pd.DataFrame(
                    data,
                    columns=["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"]
                )
                df["تاریخ"] = df["تاریخ"].apply(gregorian_to_shamsi)
                df["مبلغ"] = df["مبلغ"].apply(format_number)
            elif report_type == "debts":
                df = pd.DataFrame(
                    data,
                    columns=["شناسه", "شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت", "حساب", "نوع"]
                )
                df["سررسید"] = df["سررسید"].apply(lambda x: gregorian_to_shamsi(x) if x else "-")
                df["مبلغ"] = df["مبلغ"].apply(format_number)
                df["پرداخت شده"] = df["پرداخت شده"].apply(format_number)
            elif report_type == "cost_income":
                df = pd.DataFrame(
                    data,
                    columns=["نوع", "مبلغ", "تاریخ", "حساب", "شخص", "توضیحات"]
                )
                df["تاریخ"] = df["تاریخ"].apply(gregorian_to_shamsi)
                df["مبلغ"] = df["مبلغ"].apply(format_number)
            elif report_type == "monthly":
                df = pd.DataFrame(
                    data,
                    columns=["ماه", "هزینه", "درآمد", "تفاوت", "اقساط پرداختی", "بدهی", "طلب"]
                )
                df[["هزینه", "درآمد", "تفاوت", "اقساط پرداختی", "بدهی", "طلب"]] = df[
                    ["هزینه", "درآمد", "تفاوت", "اقساط پرداختی", "بدهی", "طلب"]
                ].apply(lambda x: x.apply(format_number))
            elif report_type == "person":
                df = pd.DataFrame(
                    data,
                    columns=["نوع", "تاریخ", "حساب", "دسته‌بندی", "مبلغ", "توضیحات", "وضعیت"]
                )
                df["تاریخ"] = df["تاریخ"].apply(lambda x: gregorian_to_shamsi(x) if x != "-" else "-")
                df["مبلغ"] = df["مبلغ"].apply(lambda x: format_number(x) if isinstance(x, (int, float)) else x)
            elif report_type == "general":
                df = pd.DataFrame(data, columns=["معیار", "مقدار"])

            if format_type == "excel":
                output_path = f"{file_prefix}.xlsx"
                df.to_excel(output_path, index=False, engine='openpyxl')
                QMessageBox.information(self, "موفق", f"فایل اکسل در {output_path} ذخیره شد!")
            elif format_type == "csv":
                output_path = f"{file_prefix}.csv"
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "موفق", f"فایل CSV در {output_path} ذخیره شد!")
            elif format_type == "pdf":
                output_path = f"{file_prefix}.pdf"
                pdfmetrics.registerFont(TTFont('Vazir', 'Vazir.ttf'))
                doc = SimpleDocTemplate(output_path, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()
                persian_style = ParagraphStyle(
                    name='Persian',
                    parent=styles['Normal'],
                    fontName='Vazir',
                    fontSize=12,
                    alignment=1,
                    wordWrap='RTL'
                )

                table_data = [df.columns.tolist()] + df.values.tolist()
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('FONT', (0, 0), (-1, -1), 'Vazir'),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ]))
                elements.append(table)
                doc.build(elements)
                QMessageBox.information(self, "موفق", f"فایل PDF در {output_path} ذخیره شد!")

            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تولید خروجی: {e}")

    def create_persons_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.person_name_input = QLineEdit()
        add_person_btn = QPushButton("افزودن شخص")
        add_person_btn.clicked.connect(self.add_person)

        form_layout.addRow("نام شخص:", self.person_name_input)
        form_layout.addRow(add_person_btn)

        # اضافه کردن فیلد جستجو
        self.person_search_input = QLineEdit()
        self.person_search_input.setPlaceholderText("جستجو بر اساس نام شخص")
        self.person_search_input.textChanged.connect(self.filter_persons_table) # اتصال سیگنال به متد فیلتر
        form_layout.addRow("جستجو:", self.person_search_input)

        self.persons_table = QTableWidget()
        self.persons_table.setColumnCount(3)
        self.persons_table.setHorizontalHeaderLabels(["شناسه", "نام", "اقدامات"])
        self.persons_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # تنظیم عرض ستون‌ها برای نمایش بهتر
        self.persons_table.setColumnWidth(0, 50)  # شناسه
        self.persons_table.setColumnWidth(1, 250) # نام
        self.persons_table.setColumnWidth(2, 100) # اقدامات

        layout.addLayout(form_layout)
        layout.addWidget(self.persons_table)
        
        # بارگذاری اولیه اشخاص بعد از ایجاد جدول و فیلد جستجو
        self.load_persons() 

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

        # New: Search input for categories
        self.category_search_input = QLineEdit()
        self.category_search_input.setPlaceholderText("جستجو بر اساس نام دسته‌بندی (حداقل ۲ حرف)")
        # Connect textChanged signal to filter_categories_table method
        self.category_search_input.textChanged.connect(self.filter_categories_table)
        form_layout.addRow("جستجو:", self.category_search_input) # Add the search input to the form layout


        # New: Dropdown filter for category types
        self.category_filter_dropdown = QComboBox()
        self.category_filter_dropdown.addItems(["نمایش همه", "نمایش فقط دسته بندی هزینه ها", "نمایش فقط دسته بندی درامد ها"])
        # Connect the dropdown's currentIndexChanged signal to the new filter method
        self.category_filter_dropdown.currentIndexChanged.connect(self.apply_category_type_filter)
        form_layout.addRow("فیلتر نوع دسته‌بندی:", self.category_filter_dropdown) # Add the dropdown to the form layout


        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(5)
        self.categories_table.setHorizontalHeaderLabels(["شناسه", "نام", "نوع", "ویرایش", "حذف"])
        self.categories_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # Set column widths for better display
        self.categories_table.setColumnWidth(0, 50)  # ID
        self.categories_table.setColumnWidth(1, 300) # Name
        self.categories_table.setColumnWidth(2, 100) # Type
        self.categories_table.setColumnWidth(3, 80)  # Edit button
        self.categories_table.setColumnWidth(4, 80)  # Delete button

        layout.addLayout(form_layout)
        layout.addWidget(self.categories_table)
        self.load_categories_table()  # بارگذاری اولیه جدول
        tab.setLayout(layout)
        return tab
    
    def filter_categories_table(self, search_text):
        # This method now only handles the text search.
        # It calls apply_category_type_filter to also apply the type filter.
        self.apply_category_type_filter()

    def apply_category_type_filter(self):
        try:
            filter_text = self.category_filter_dropdown.currentText()
            search_text = self.category_search_input.text()

            query = "SELECT id, name, type FROM categories "
            params = []
            where_clauses = []

            if filter_text == "نمایش فقط دسته بندی هزینه ها":
                where_clauses.append("type = 'expense'")
            elif filter_text == "نمایش فقط دسته بندی درامد ها":
                where_clauses.append("type = 'income'")
            # If "نمایش همه" is selected, no type filter is added

            if len(search_text) >= 2:
                where_clauses.append("name LIKE ?")
                params.append(f"%{search_text}%")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY name ASC"

            self.db_manager.execute(query, tuple(params))
            filtered_categories = self.db_manager.fetchall()

            self.categories_table.setRowCount(len(filtered_categories))
            for row, (id, name, category_type) in enumerate(filtered_categories):
                self.categories_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.categories_table.setItem(row, 1, QTableWidgetItem(name))
                self.categories_table.setItem(row, 2, QTableWidgetItem("درآمد" if category_type == "income" else "هزینه"))
                
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, cat_id=id: self.edit_category(cat_id))
                self.categories_table.setCellWidget(row, 3, edit_btn)
                
                delete_btn = QPushButton("حذف")
                delete_btn.clicked.connect(lambda checked, cat_id=id: self.delete_category(cat_id))
                self.categories_table.setCellWidget(row, 4, delete_btn)
                
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده هنگام فیلتر دسته‌بندی‌ها: {e}")
    
    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # هدر تب تنظیمات
        header = QLabel("⚙️ تنظیمات")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFF; padding: 10px;")
        layout.addWidget(header)
        
        # دکمه تغییر رمز عبور
        change_password_btn = QPushButton("تغییر رمز عبور")
        change_password_btn.clicked.connect(lambda: self.show_change_password_dialog("admin"))
        change_password_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                max-width: 200px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(change_password_btn)

        # --- اضافه کردن خط جداکننده اول ---
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine) # خط افقی
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setFixedHeight(2) # می‌توانید ارتفاع (ضخامت) خط را تنظیم کنید
        separator1.setStyleSheet("background-color: #c0c0c0;") # رنگ خط
        layout.addWidget(separator1)
        # ---------------------------------
        
        # بخش تنظیم توکن Dropbox
        token_label = QLabel("توکن دسترسی Dropbox:")
        token_label.setStyleSheet("font-family: Vazir, Arial;font-size: 14px; color: #FFF;")
        layout.addWidget(token_label)
        
        self.dropbox_token_input = QLineEdit()
        self.dropbox_token_input.setPlaceholderText("توکن دسترسی Dropbox را وارد کنید")
        self.dropbox_token_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
                max-width: 400px;
            }
        """)
        # بارگذاری توکن فعلی (اگر وجود داشته باشد)
        self.db_manager.execute("SELECT dropbox_token FROM users WHERE username = ?", ("admin",))
        result = self.db_manager.fetchone()
        if result and result[0]:
            self.dropbox_token_input.setText(result[0])
        layout.addWidget(self.dropbox_token_input)
        
        save_token_btn = QPushButton("ذخیره توکن")
        save_token_btn.clicked.connect(self.save_dropbox_token)
        save_token_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                font-family: Vazir, Arial;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                max-width: 200px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(save_token_btn)

        # دکمه بکاپ‌گیری آنلاین به Dropbox
        backup_btn = QPushButton("بکاپ‌گیری آنلاین")
        backup_btn.clicked.connect(self.backup_to_dropbox)
        backup_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                font-family: Vazir, Arial;                                 
                padding: 10px;
                background-color: #FF9800;
                color: white;
                border-radius: 5px;
                max-width: 200px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(backup_btn)

        # --- اضافه کردن خط جداکننده اول ---
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine) # خط افقی
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setFixedHeight(2) # می‌توانید ارتفاع (ضخامت) خط را تنظیم کنید
        separator1.setStyleSheet("background-color: #c0c0c0;") # رنگ خط
        layout.addWidget(separator1)
        # ---------------------------------

        offline_backup_btn = QPushButton("💾 بکاپ‌گیری آفلاین (در پوشه برنامه)") # یا "پشتیبان‌گیری محلی"
        offline_backup_btn.clicked.connect(self.backup_offline)
        offline_backup_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                font-family: Vazir, Arial;
                padding: 10px;
                background-color: #007BFF; /* یک رنگ متفاوت، مثلا آبی */
                color: white;
                border-radius: 5px;
                max-width: 250px; /* ممکن است نیاز به عرض بیشتری داشته باشد */
                margin-top: 10px; /* برای ایجاد کمی فاصله از دکمه بالایی */
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        layout.addWidget(offline_backup_btn)
        
        # فاصله‌گذاری برای ظاهر بهتر
        layout.addStretch()
        
        tab.setLayout(layout)
        return tab
    
    def backup_offline(self):
        db_path = "finance.db" # مسیر فایل دیتابیس اصلی

        # نام و مسیر پوشه بکاپ
        backup_folder_name = "database-backup"
        # مسیر پایه برنامه (جایی که اسکریپت یا فایل اجرایی قرار دارد)
        # استفاده از os.path.dirname(os.path.abspath(sys.argv[0])) برای دقت بیشتر در محیط‌های مختلف
        # یا اگر با PyInstaller کار می‌کنید، باید مسیر مناسب را با توجه به آن تنظیم کنید.
        # برای سادگی، مسیر جاری را در نظر می‌گیریم و یک پوشه در آن می‌سازیم.
        base_path = os.getcwd() # یا مسیر دقیق‌تر مدنظرتان
        backup_dir_path = os.path.join(base_path, backup_folder_name)

        # ایجاد نام فایل بکاپ با تاریخ و زمان
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"finance_backup_offline_{timestamp}.db"

        # مسیر کامل فایل بکاپ درون پوشه database-backup
        backup_filepath = os.path.join(backup_dir_path, backup_filename)

        try:

            # ایجاد پوشه بکاپ اگر وجود ندارد
            # exist_ok=True باعث می‌شود اگر پوشه از قبل وجود داشته باشد، خطایی رخ ندهد.
            os.makedirs(backup_dir_path, exist_ok=True)

            # ابتدا اتصال به دیتابیس اصلی را موقتا می‌بندیم (اگر باز است)
            # یا مطمئن می‌شویم که هیچ تراکنش در حال انجام نیست.
            # ساده‌ترین راه، استفاده از یک اتصال جدید برای VACUUM INTO است.

            # اطمینان از بسته بودن اتصال اصلی دیتابیس منیجر قبل از بکاپ‌گیری
            # این کار برای جلوگیری از قفل شدن دیتابیس مهم است.
            # اگر db_manager شما اتصال را باز نگه می‌دارد، باید آن را ببندید.
            # در کد شما، db_manager اتصال را در صورت نیاز باز می‌کند و می‌بندد،
            # اما VACUUM روی دیتابیس فعال ممکن است مشکل‌ساز باشد.
            # بهتر است db_manager.close() را قبل از بکاپ صدا بزنید و بعد دوباره connect کنید.
            # یا از یک کانکشن مجزا فقط برای بکاپ استفاده کنید.

            # راه حل ساده‌تر: استفاده از یک کانکشن جدید برای عملیات VACUUM
            source_conn = sqlite3.connect(db_path)
            source_conn.execute(f"VACUUM INTO '{backup_filepath}'")
            source_conn.close()

            QMessageBox.information(self, "موفقیت", f"بکاپ آفلاین با موفقیت در مسیر زیر ذخیره شد:\n{backup_filepath}")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا در بکاپ آفلاین", f"خطای پایگاه داده هنگام ایجاد بکاپ: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطا در بکاپ آفلاین", f"یک خطای غیرمنتظره رخ داد: {e}")
    
    def save_dropbox_token(self):
        from PyQt6.QtWidgets import QMessageBox
        
        token = self.dropbox_token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "خطا", "توکن Dropbox نمی‌تواند خالی باشد!")
            return
        
        try:
            self.db_manager.execute("UPDATE users SET dropbox_token = ? WHERE username = ?",
                                (token, "admin"))
            self.db_manager.commit()
            QMessageBox.information(self, "موفق", "توکن Dropbox با موفقیت ذخیره شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def backup_to_dropbox(self):        
        # خواندن توکن از دیتابیس
        try:
            self.db_manager.execute("SELECT dropbox_token FROM users WHERE username = ?", ("admin",))
            result = self.db_manager.fetchone()
            if not result or not result[0]:
                QMessageBox.warning(self, "خطا", "لطفاً ابتدا توکن Dropbox را در تنظیمات وارد کنید!")
                return
            DROPBOX_ACCESS_TOKEN = result[0]
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return
        
        # مسیر دیتابیس و فایل بکاپ موقت
        db_path = "finance.db"
        backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        try:
            # ایجاد بکاپ امن با VACUUM INTO
            conn = sqlite3.connect(db_path)
            conn.execute(f"VACUUM INTO '{backup_path}'")
            conn.close()
            
            # اتصال به Dropbox
            dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
            
            # مسیر فایل در Dropbox
            dropbox_path = f"/backups/{os.path.basename(backup_path)}"
            
            # آپلود فایل بکاپ به Dropbox
            with open(backup_path, "rb") as f:
                dbx.files_upload(f.read(), dropbox_path, mute=True)
            
            # حذف فایل بکاپ محلی
            os.remove(backup_path)
            
            QMessageBox.information(self, "موفق", "بکاپ با موفقیت در Dropbox ذخیره شد!")
            
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای دیتابیس: {e}")
        except ApiError as e:
            QMessageBox.critical(self, "خطا", f"خطای Dropbox: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطای عمومی: {e}")

    def load_data(self):
        self.load_accounts()
        self.load_categories()
        self.load_persons()
        self.load_transactions()
        self.load_debts()
        self.load_loans()
        self.update_dashboard()

    def load_accounts(self):
        try:
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
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
                # اضافه کردن دکمه ویرایش
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, acc_id=id: self.edit_account(acc_id))
                self.accounts_table.setCellWidget(row, 3, edit_btn)
                # پر کردن لیست‌های کشویی
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
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
            self.db_manager.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
            self.db_manager.commit()
            self.account_name_input.clear()
            self.account_balance_input.clear()
            self.load_accounts()
            QMessageBox.information(self, "موفق", "حساب با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_account(self, account_id):
        try:
            self.db_manager.execute("SELECT name FROM accounts WHERE id = ?", (account_id,))
            account = self.db_manager.fetchone()
            if not account:
                QMessageBox.warning(self, "خطا", "حساب یافت نشد!")
                return
            name = account[0]

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش نام حساب")
            layout = QFormLayout()
            edit_name = QLineEdit(name)
            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_account(account_id, edit_name.text(), dialog))
            layout.addRow("نام حساب:", edit_name)
            layout.addRow(save_btn)
            dialog.setLayout(layout)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_account(self, account_id, name, dialog):
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب نمی‌تواند خالی باشد!")
            return
        try:
            # بررسی تکراری نبودن نام حساب
            self.db_manager.execute("SELECT id FROM accounts WHERE name = ? AND id != ?", (name, account_id))
            if self.db_manager.fetchone():
                QMessageBox.warning(self, "خطا", "حسابی با این نام قبلاً وجود دارد!")
                return
            self.db_manager.execute("UPDATE accounts SET name = ? WHERE id = ?", (name, account_id))
            self.db_manager.commit()
            self.load_accounts()
            dialog.accept()
            QMessageBox.information(self, "موفق", "نام حساب با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def update_categories(self):
        """به‌روزرسانی لیست دسته‌بندی‌ها بر اساس نوع تراکنش"""
        category_type = "income" if self.transaction_type.currentText() == "درآمد" else "expense"
        self.transaction_category.clear()
        try:
            self.db_manager.execute("SELECT id, name FROM categories WHERE type = ?", (category_type,))
            categories = self.db_manager.fetchall()
            for cat_id, name in categories:
                self.transaction_category.addItem(name, cat_id)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_categories(self):
        """بارگذاری اولیه دسته‌بندی‌ها"""
        self.update_categories()  # به جای کد قبلی، از متد جدید استفاده می‌کنیم

    def load_categories_table(self):
        # This method is now simplified to call the main filtering method,
        # ensuring all filters are applied when the tab is loaded or categories are reloaded.
        self.apply_category_type_filter()

    def edit_category(self, category_id):
        try:
            self.db_manager.execute("SELECT name, type FROM categories WHERE id = ?", (category_id,))
            category = self.db_manager.fetchone()
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
            self.db_manager.execute("UPDATE categories SET name = ?, type = ? WHERE id = ?", (name, category_type, category_id))
            self.db_manager.commit()
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
            self.db_manager.execute("SELECT id, name FROM persons")
            persons = self.db_manager.fetchall()
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
            self.db_manager.execute("INSERT INTO categories (name, type) VALUES (?, ?)", (name, category_type))
            self.db_manager.commit()
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
        if person_id is None or person_id == "":
            person_id = None  # صریح مشخص کنیم
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
            self.db_manager.execute(
                "INSERT INTO transactions (account_id, person_id, category_id, amount, date, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, person_id, category_id, amount, date, desc)
            )
            if category_type == "income":
                self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            else:
                self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            self.db_manager.commit()
            self.transaction_amount.clear()
            self.transaction_date.clear()
            self.transaction_desc.clear()
            self.load_transactions()
            self.load_accounts()
            self.update_dashboard()
            QMessageBox.information(self, "موفق", "تراکنش با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def delete_category(self, category_id):
        try:
            # بررسی استفاده از دسته‌بندی در تراکنش‌ها
            self.db_manager.execute("SELECT COUNT(*) FROM transactions WHERE category_id = ?", (category_id,))
            if self.db_manager.fetchone()[0] > 0:
                QMessageBox.warning(self, "خطا", "این دسته‌بندی در تراکنش‌ها استفاده شده و نمی‌تواند حذف شود!")
                return

            # ⚠️ تأیید حذف از کاربر حتی اگر دسته در جایی استفاده نشده باشد
            reply = QMessageBox.question(
                self, "تأیید حذف", "آیا مطمئن هستید که می‌خواهید این دسته‌بندی را حذف کنید؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            self.db_manager.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            self.db_manager.commit()
            self.load_categories()
            self.load_categories_table()
            self.load_transactions()
            QMessageBox.information(self, "موفق", "دسته‌بندی با موفقیت حذف شد!")
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
            layout = QFormLayout()
            dialog.setLayout(layout)

            edit_account = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                edit_account.addItem(display_text, acc_id)
            edit_account.setCurrentText([f"{name} (موجودی: {format_number(balance)} ریال)" for acc_id, name, balance in accounts if acc_id == account_id][0])

            edit_person = QComboBox()
            edit_person.addItem("-", None)
            self.db_manager.execute("SELECT id, name FROM persons")
            persons = self.db_manager.fetchall()
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
                self.db_manager.execute("SELECT id, name FROM categories WHERE type = ?", (current_type,))
                categories = self.db_manager.fetchall()
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
            new_category_type = "income" if type_text == "درآمد" else "expense"

            # خنثی کردن اثر تراکنش قدیمی
            if old_category_type == "income":
                self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_amount, old_account_id))
            else:
                self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (old_amount, old_account_id))

            # اعمال اثر تراکنش جدید
            if new_category_type == "income":
                self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
            else:
                self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))

            # بروزرسانی در دیتابیس
            self.db_manager.execute(
                "UPDATE transactions SET account_id = ?, person_id = ?, category_id = ?, amount = ?, date = ?, description = ? WHERE id = ?",
                (account_id, person_id, category_id, amount, date, desc, transaction_id)
            )

            self.db_manager.commit()
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
            QDate.fromString(date, "yyyy-MM-dd")

            # بررسی موجودی حساب مبدأ
            self.db_manager.execute("SELECT balance FROM accounts WHERE id = ?", (from_account_id,))
            balance = self.db_manager.fetchone()
            if not balance or balance[0] < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب مبدأ کافی نیست!")
                return

            # پیدا کردن دسته‌بندی‌های انتقال
            self.db_manager.execute("SELECT id FROM categories WHERE name = 'انتقال بین حساب‌ها (خروج)' AND type = 'expense'")
            expense_category_id = self.db_manager.fetchone()
            if not expense_category_id:
                QMessageBox.critical(self, "خطا", "دسته‌بندی 'انتقال بین حساب‌ها (خروج)' یافت نشد!")
                return
            expense_category_id = expense_category_id[0]

            self.db_manager.execute("SELECT id FROM categories WHERE name = 'انتقال بین حساب‌ها (ورود)' AND type = 'income'")
            income_category_id = self.db_manager.fetchone()
            if not income_category_id:
                QMessageBox.critical(self, "خطا", "دسته‌بندی 'انتقال بین حساب‌ها (ورود)' یافت نشد!")
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
            self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
            self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

            # کامیت تراکنش
            self.db_manager.commit()

            # پاک کردن فرم و به‌روزرسانی UI
            self.transfer_amount.clear()
            self.transfer_date.clear()
            self.load_transactions()
            self.load_accounts()
            self.update_dashboard()
            QMessageBox.information(self, "موفق", "انتقال با موفقیت انجام شد!")

        except sqlite3.Error as e:
            # رول‌بک در صورت خطا
            self.db_manager.rollback()
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def load_transactions(self):
        try:
            self.db_manager.execute("SELECT COUNT(*) FROM transactions")
            total_transactions = self.db_manager.fetchone()[0]
            self.transactions_total_pages = (total_transactions + self.transactions_per_page - 1) // self.transactions_per_page
            self.recent_total_pages = (total_transactions + self.recent_per_page - 1) // self.recent_per_page

            offset = (self.transactions_current_page - 1) * self.transactions_per_page
            self.db_manager.execute(
                "SELECT t.id, t.date, a.name, p.name, c.name, t.amount, t.description, c.type "
                "FROM transactions t "
                "JOIN accounts a ON t.account_id = a.id "
                "LEFT JOIN persons p ON t.person_id = p.id "
                "JOIN categories c ON t.category_id = c.id "
                "ORDER BY t.date DESC LIMIT ? OFFSET ?",
                (self.transactions_per_page, offset)
            )
            transactions = self.db_manager.fetchall()

            offset_recent = (self.recent_current_page - 1) * self.recent_per_page
            self.db_manager.execute(
                "SELECT t.id, t.date, a.name, p.name, c.name, t.amount, t.description, c.type "
                "FROM transactions t "
                "JOIN accounts a ON t.account_id = a.id "
                "LEFT JOIN persons p ON t.person_id = p.id "
                "JOIN categories c ON t.category_id = c.id "
                "ORDER BY t.date DESC LIMIT ? OFFSET ?",
                (self.recent_per_page, offset_recent)
            )
            recent_transactions = self.db_manager.fetchall()
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
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            # معکوس کردن اثر تراکنش روی موجودی حساب
            if category_type == "income":
                # اگر تراکنش درآمد بوده، مبلغ رو از حساب کم می‌کنیم
                self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            else:
                # اگر تراکنش هزینه بوده، مبلغ رو به حساب برمی‌گردونیم
                self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))

            # حذف تراکنش از دیتابیس
            self.db_manager.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            self.db_manager.commit()

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
                QDate.fromString(due_date, "yyyy-MM-dd")
            except ValueError:
                QMessageBox.warning(self, "خطا", "تاریخ نامعتبر است!")
                return

        try:
            # برای طلب من، account_id باید None باشد
            account_id_to_save = account_id if has_payment else None

            self.db_manager.execute(
            "INSERT INTO debts (person_id, amount, due_date, is_paid, account_id, show_in_dashboard, is_credit, description) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (person_id, amount, due_date, 0, account_id_to_save, 1 if show_in_dashboard else 0, 1 if is_credit else 0, description)
            )

            # اگه تیک پرداخت فعال باشه، موجودی حساب رو به‌روزرسانی می‌کنیم
            if has_payment and account_id:
                if is_credit:  # طلب من: من به کسی پول دادم، موجودی کم می‌شه
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                        (amount, account_id)
                    )
                else:  # بدهی من: من از کسی پول گرفتم، موجودی زیاد می‌شه
                    self.db_manager.execute(
                        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                        (amount, account_id)
                    )

            self.db_manager.commit()
            self.debt_amount.clear()
            self.debt_due_date.clear()
            self.debt_has_payment.setChecked(False)
            self.debt_show_in_dashboard.setChecked(False)
            self.debt_description.clear()
            self.load_debts()
            self.load_accounts()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")


    def edit_debt(self, debt_id):
        try:
            self.db_manager.execute(
                "SELECT person_id, amount, account_id, due_date, is_paid, show_in_dashboard, description FROM debts WHERE id = ?",
                (debt_id,)
            )
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            person_id, amount, account_id, due_date, is_paid, show_in_dashboard, description = debt

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش بدهی/طلب")
            layout = QFormLayout()
            dialog.setLayout(layout)

            edit_person = QComboBox()
            self.db_manager.execute("SELECT id, name FROM persons")
            persons = self.db_manager.fetchall()
            for p_id, name in persons:
                edit_person.addItem(name, p_id)
            edit_person.setCurrentText([name for p_id, name in persons if p_id == person_id][0])

            edit_amount = NumberInput()
            edit_amount.setText(str(amount))

            edit_account = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                edit_account.addItem(display_text, acc_id)
            if account_id:
                edit_account.setCurrentText([f"{name} (موجودی: {format_number(balance)} ریال)" for acc_id, name, balance in accounts if acc_id == account_id][0])
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

            edit_description = QLineEdit(description or "")
            edit_description.setPlaceholderText("توضیحات (اختیاری)")
            edit_description.setMaxLength(100)
            edit_description.setToolTip("توضیحات (اختیاری)")    
            edit_description.setStyleSheet("QLineEdit { font-family: 'Vazir'; }")

            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_debt(
                debt_id, edit_person.currentData(), edit_amount.get_raw_value(),
                edit_account.currentData(), edit_due_date.text(),
                edit_is_credit.currentText() == "طلب من",
                edit_has_payment.isChecked(), edit_show_in_dashboard.isChecked(), edit_description.text() or None, dialog
            ))

            layout.addRow("شخص:", edit_person)
            layout.addRow("مبلغ:", edit_amount)
            layout.addRow("حساب مرتبط:", edit_account)
            layout.addRow("", edit_has_payment)
            layout.addRow("تاریخ سررسید (شمسی - اختیاری):", edit_due_date)
            layout.addRow("نوع:", edit_is_credit)
            layout.addRow("", edit_show_in_dashboard)
            layout.addRow("توضیحات", edit_description)
            layout.addRow(save_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_debt(self, debt_id, person_id, amount, account_id, shamsi_due_date, is_credit, has_payment, show_in_dashboard, description, dialog):
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
            # دریافت اطلاعات بدهی قبلی برای حذف اثر آن
            self.db_manager.execute("SELECT amount, account_id FROM debts WHERE id = ?", (debt_id,))
            old_debt = self.db_manager.fetchone()
            if not old_debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            old_amount, old_account_id = old_debt

            # مشخص کردن account_id جدید برای ذخیره
            account_id_to_save = account_id if has_payment else None

            # بررسی موجودی حساب در صورت نیاز
            if has_payment and not is_credit and account_id:
                self.db_manager.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
                balance = self.db_manager.fetchone()[0]
                if balance < amount:
                    QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                    return

            # حذف اثر قبلی از حساب قبلی
            if old_account_id:
                self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_amount, old_account_id))

            # اعمال اثر جدید در صورت نیاز (فقط برای بدهی من)
            if has_payment and not is_credit and account_id:
                self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))

            # ذخیره در دیتابیس
            self.db_manager.execute(
                "UPDATE debts SET person_id = ?, amount = ?, account_id = ?, due_date = ?, is_paid = 0, show_in_dashboard = ?, description = ? WHERE id = ?",
                (person_id, amount, account_id_to_save, due_date, 1 if show_in_dashboard else 0, description, debt_id)
            )
            self.db_manager.commit()
            self.load_debts()
            self.load_accounts()
            dialog.accept()
            QMessageBox.information(self, "موفق", "بدهی/طلب با موفقیت ویرایش شد!")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")


    def load_debts(self):
        try:
            self.db_manager.execute("SELECT COUNT(*) FROM debts")
            total_debts = self.db_manager.fetchone()[0]
            self.debts_total_pages = (total_debts + self.debts_per_page - 1) // self.debts_per_page

            offset = (self.debts_current_page - 1) * self.debts_per_page
            self.db_manager.execute(
                "SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, d.is_paid, COALESCE(a.name, '-'), d.is_credit, d.description "
                "FROM debts d JOIN persons p ON d.person_id = p.id LEFT JOIN accounts a ON d.account_id = a.id "
                "LIMIT ? OFFSET ?",
                (self.debts_per_page, offset)
            )
            debts = self.db_manager.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return
        
         # پاک‌سازی کامل جدول
        self.debts_table.clear()
        self.debts_table.setColumnCount(11)
        self.debts_table.setHorizontalHeaderLabels([
            "شناسه", "نام", "مبلغ کل", "مبلغ پرداختی", "سررسید",
            "وضعیت", "حساب", "توضیحات", "ویرایش", "حذف", "تسویه"
        ])
        self.debts_table.setRowCount(0)
        self.debts_table.setRowCount(min(len(debts), self.debts_per_page))
        # تنظیم عرض ستون‌ها
        self.debts_table.setColumnWidth(0, 50)
        self.debts_table.setColumnWidth(1, 120)
        self.debts_table.setColumnWidth(2, 100)
        self.debts_table.setColumnWidth(3, 100)
        self.debts_table.setColumnWidth(4, 100)
        self.debts_table.setColumnWidth(5, 80)
        self.debts_table.setColumnWidth(6, 120)
        self.debts_table.setColumnWidth(7, 200)
        self.debts_table.setColumnWidth(8, 80)
        self.debts_table.setColumnWidth(9, 80)  # ستون حذف
        self.debts_table.setColumnWidth(10, 80)  # ستون تسویه

        for row, (id, person, amount, paid, due_date, is_paid, account, is_credit, description) in enumerate(debts):
            shamsi_due_date = gregorian_to_shamsi(due_date) if due_date else "-"
            self.debts_table.setItem(row, 0, QTableWidgetItem(str(id)))
            self.debts_table.setItem(row, 1, QTableWidgetItem(person))
            self.debts_table.setItem(row, 2, QTableWidgetItem(format_number(amount)))
            self.debts_table.setItem(row, 3, QTableWidgetItem(format_number(paid)))
            self.debts_table.setItem(row, 4, QTableWidgetItem(shamsi_due_date))
            self.debts_table.setItem(row, 5, QTableWidgetItem("پرداخت شده" if is_paid else "در جریان"))
            self.debts_table.setItem(row, 6, QTableWidgetItem(account))
            self.debts_table.setItem(row, 7, QTableWidgetItem(description or ""))

            # چاپ برای دیباگ
            #print(f"Debt ID: {id}, Amount: {amount}, Paid: {paid}, Is Paid: {is_paid}, Remaining: {amount - paid}")

            # تعیین رنگ ردیف بر اساس is_credit
            if is_credit == 1:  # طلب من
                for col in range(self.debts_table.columnCount()):
                    item = self.debts_table.item(row, col)
                    if item:
                        item.setBackground(QColor(230, 255, 230))  # سبز کم‌رنگ
            else:  # بدهی من
                for col in range(self.debts_table.columnCount()):
                    item = self.debts_table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 230, 230))  # قرمز کم‌رنگ

            # دکمه‌های ویرایش، حذف و تسویه
            if is_paid == 0:  # شرط جدید: فقط اگه مبلغ باقی‌مانده باشه
                #print(f"Debt ID: {id} - Showing buttons (is_paid = 0)")
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, d_id=id: self.edit_debt(d_id))
                self.debts_table.setCellWidget(row, 8, edit_btn)

                delete_btn = QPushButton("حذف")
                delete_btn.clicked.connect(lambda checked, d_id=id: self.delete_debt(d_id))
                self.debts_table.setCellWidget(row, 9, delete_btn)

                settle_btn = QPushButton("تسویه")
                settle_btn.clicked.connect(lambda checked, d_id=id: self.settle_debt(d_id))
                self.debts_table.setCellWidget(row, 10, settle_btn)
            else:
                #print(f"Debt ID: {id} - Showing dashes (is_paid = 1)")
                # پاک کردن ویجت‌های قبلی
                self.debts_table.removeCellWidget(row, 8)
                self.debts_table.removeCellWidget(row, 9)
                self.debts_table.removeCellWidget(row, 10)
                # تنظیم خط تیره
                self.debts_table.setItem(row, 8, QTableWidgetItem("-"))
                self.debts_table.setItem(row, 9, QTableWidgetItem("-"))
                self.debts_table.setItem(row, 10, QTableWidgetItem("-"))

        self.debts_page_label.setText(f"صفحه {self.debts_current_page} از {self.debts_total_pages}")
        self.debts_prev_btn.setEnabled(self.debts_current_page > 1)
        self.debts_next_btn.setEnabled(self.debts_current_page < self.debts_total_pages)

    def settle_debt(self, debt_id):
        try:
            self.db_manager.execute(
                "SELECT d.person_id, d.amount, d.paid_amount, d.account_id, p.name, d.is_credit "
                "FROM debts d JOIN persons p ON d.person_id = p.id WHERE d.id = ?",
                (debt_id,)
            )
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                return
            person_id, amount, paid_amount, account_id, person_name, is_credit = debt
            remaining_amount = amount - paid_amount

            dialog = QDialog(self)
            dialog.setWindowTitle(f"تسویه بدهی/طلب با {person_name}")
            layout = QFormLayout()
            dialog.setLayout(layout)

            # نوع بدهی/طلب
            type_label_text = "طلب من (دریافت پول)" if is_credit else "بدهی من (پرداخت پول)"
            type_label = QLabel(type_label_text)
            layout.addRow("نوع:", type_label)

            # مبلغ باقی‌مانده
            remaining_label = QLabel(format_number(remaining_amount))
            layout.addRow("مبلغ باقی‌مانده:", remaining_label)

            # چک‌باکس جدید
            self.settle_has_payment_checkbox = QCheckBox("انتقال وجه انجام می‌شود؟")
            # به صورت پیش‌فرض، اگر قبلاً حساب مرتبطی برای این بدهی ثبت شده بود، فعال باشد
            self.settle_has_payment_checkbox.setChecked(account_id is not None) 
            layout.addRow("", self.settle_has_payment_checkbox)

            # ورودی برای مبلغ پرداخت‌شده
            self.settle_payment_input = NumberInput()
            self.settle_payment_input.setPlaceholderText("مبلغ پرداخت‌شده (اختیاری)")
            # اگر حالت تسویه جزئی باشد و مبلغ باقی‌مانده مثبت باشد، آن را به عنوان پیش‌فرض قرار دهید.
            # و فقط در صورتی که چک‌باکس فعال بود، این مقدار نمایش داده شود
            if account_id is not None and remaining_amount > 0:
                self.settle_payment_input.setText(str(remaining_amount)) # پیش‌فرض: کل مبلغ باقی‌مانده

            layout.addRow("مبلغ پرداخت‌شده:", self.settle_payment_input)

            # انتخاب حساب
            self.settle_account_combo = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                self.settle_account_combo.addItem(display_text, acc_id)
            if account_id:  # اگه قبلاً حسابی انتخاب شده بود، اون رو پیش‌فرض قرار بده
                for i in range(self.settle_account_combo.count()):
                    if self.settle_account_combo.itemData(i) == account_id:
                        self.settle_account_combo.setCurrentIndex(i)
                        break
            layout.addRow("حساب مرتبط:", self.settle_account_combo)

            # کنترل فعال/غیرفعال بودن فیلدها بر اساس چک‌باکس
            def toggle_settle_fields(state):
                is_checked = (state == Qt.CheckState.Checked.value)
                self.settle_payment_input.setEnabled(is_checked)
                self.settle_account_combo.setEnabled(is_checked)
                
                # اگر غیرفعال شد، مبلغ و حساب را پاک می‌کنیم یا به حالت پیش‌فرض برمی‌گردانیم
                if not is_checked:
                    self.settle_payment_input.clear()
                    self.settle_account_combo.setCurrentIndex(0) # انتخاب آیتم پیش‌فرض (None)
                else:
                    # اگر فعال شد، مبلغ باقی‌مانده را نمایش می‌دهیم
                    self.settle_payment_input.setText(str(remaining_amount))

            self.settle_has_payment_checkbox.stateChanged.connect(toggle_settle_fields)
            # وضعیت اولیه فیلدها را تنظیم کنید
            toggle_settle_fields(self.settle_has_payment_checkbox.checkState().value)


            # دکمه تأیید
            confirm_btn = QPushButton("تأیید تسویه")
            confirm_btn.clicked.connect(lambda: self.confirm_partial_payment(
                debt_id,
                self.settle_payment_input.get_raw_value(),
                self.settle_account_combo.currentData(),
                is_credit,
                self.settle_has_payment_checkbox.isChecked(), # وضعیت چک‌باکس را پاس می‌دهیم
                dialog
            ))
            layout.addRow(confirm_btn)

            dialog.exec()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def confirm_partial_payment(self, debt_id, payment_amount, account_id, is_credit, has_transfer_checked, dialog):
        try:
            self.db_manager.execute("SELECT amount, paid_amount, person_id FROM debts WHERE id = ?", (debt_id,))
            debt = self.db_manager.fetchone()
            if not debt:
                QMessageBox.warning(self, "خطا", "بدهی/طلب یافت نشد!")
                self.db_manager.rollback() # اضافه شده برای اطمینان از rollback
                return
            total_debt_amount, current_paid_amount, person_id = debt
            remaining_amount = total_debt_amount - current_paid_amount

            if has_transfer_checked: # اگر چک‌باکس "انتقال وجه انجام می‌شود" فعال بود
                if payment_amount is None or payment_amount <= 0:
                    QMessageBox.warning(self, "خطا", "مبلغ پرداخت‌شده باید بیشتر از صفر باشد!")
                    self.db_manager.rollback() # اضافه شده برای اطمینان از rollback
                    return
                if not account_id:
                    QMessageBox.warning(self, "خطا", "لطفاً حساب مرتبط را انتخاب کنید!")
                    self.db_manager.rollback() # اضافه شده برای اطمینان از rollback
                    return

                if payment_amount > remaining_amount:
                    QMessageBox.warning(self, "خطا", "مبلغ پرداخت‌شده نمی‌تواند بیشتر از مبلغ باقی‌مانده باشد!")
                    self.db_manager.rollback() # اضافه شده برای اطمینان از rollback
                    return
                
                # بررسی موجودی حساب برای بدهی (اگه بخوایم پول پرداخت کنیم)
                if not is_credit:  # بدهی من: پرداخت پول
                    self.db_manager.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
                    balance = self.db_manager.fetchone()[0]
                    if balance < payment_amount:
                        QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                        self.db_manager.rollback() # اضافه شده برای اطمینان از rollback
                        return

                # به‌روزرسانی paid_amount
                new_paid_amount = current_paid_amount + payment_amount
                
                # به‌روزرسانی موجودی حساب
                if is_credit:  # طلب من: دریافت پول (اضافه کردن به حساب)
                    self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (payment_amount, account_id))
                else:  # بدهی من: پرداخت پول (کم کردن از حساب)
                    self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (payment_amount, account_id))
                
                # ثبت تراکنش مرتبط
                category_name = "تسویه طلب" if is_credit else "تسویه بدهی"
                category_type = "income" if is_credit else "expense"
                self.db_manager.execute("SELECT id FROM categories WHERE name = ? AND type = ?", (category_name, category_type))
                category_id_from_db = self.db_manager.fetchone()
                if not category_id_from_db:
                    QMessageBox.critical(self, "خطا", f"خطای سیستمی: دسته‌بندی '{category_name}' یافت نشد. لطفاً برنامه را مجدداً راه‌اندازی کنید یا با پشتیبانی تماس بگیرید.")
                    self.db_manager.rollback()
                    return 
                category_id_from_db = category_id_from_db[0]

                today_gregorian = datetime.now().strftime("%Y-%m-%d")
                
                self.db_manager.execute('SELECT name FROM persons WHERE id = ?', (person_id,))
                person_name = self.db_manager.fetchone()[0]

                description = f"تسویه {format_number(payment_amount)} از {'طلب' if is_credit else 'بدهی'} با شخص {person_name}"
                self.db_manager.execute(
                    "INSERT INTO transactions (account_id, person_id, category_id, amount, date, description) VALUES (?, ?, ?, ?, ?, ?)",
                    (account_id, person_id, category_id_from_db, payment_amount, today_gregorian, description)
                )

            else:
                payment_amount = remaining_amount 
                new_paid_amount = current_paid_amount + payment_amount
                account_id = None
            
            is_paid = 1 if new_paid_amount >= total_debt_amount else 0

            self.db_manager.execute(
                "UPDATE debts SET paid_amount = ?, is_paid = ?, account_id = ? WHERE id = ?",
                (new_paid_amount, is_paid, account_id, debt_id)
            )

            self.db_manager.commit()
            self.load_debts()
            self.load_accounts()
            self.update_dashboard()
            dialog.accept()
            QMessageBox.information(self, "موفق", f"پرداخت به مبلغ {format_number(payment_amount)} ریال ثبت شد! وضعیت تسویه: {'کامل' if is_paid else 'جزئی'}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback() # اطمینان از rollback در صورت بروز خطا

    
    def confirm_settle_debt(self, debt_id, remaining_amount, account_id, has_payment, is_credit, dialog):
        try:
            # بررسی اینکه برای طلب، حساب مرتبط انتخاب شده باشه
            if is_credit and not has_payment:
                QMessageBox.warning(self, "خطا", "برای تسویه طلب، باید حساب مرتبط برای دریافت پول انتخاب شود!")
                return

            # بررسی موجودی حساب در صورت نیاز
            if has_payment and account_id:
                self.db_manager.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
                balance = self.db_manager.fetchone()[0]
                if is_credit:  # طلب من: دریافت پول (اضافه کردن به حساب)
                    pass  # نیازی به بررسی موجودی نیست چون پول اضافه می‌شه
                else:  # بدهی من: پرداخت پول (کم کردن از حساب)
                    if balance < remaining_amount:
                        QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                        return

            # به‌روزرسانی وضعیت بدهی/طلب
            self.db_manager.execute(
                "UPDATE debts SET is_paid = 1, paid_amount = amount WHERE id = ?",
                (debt_id,)
            )

            # به‌روزرسانی حساب در صورت پرداخت/دریافت
            if has_payment and account_id:
                if is_credit:  # طلب من: پول دریافت می‌شه
                    self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (remaining_amount, account_id))
                else:  # بدهی من: پول پرداخت می‌شه
                    self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (remaining_amount, account_id))

            self.db_manager.commit()
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
            self.db_manager.execute(
                "SELECT d.account_id, d.amount, d.paid_amount FROM debts d WHERE d.id = ?",
                (debt_id,)
            )
            debt = self.db_manager.fetchone()
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
                self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (remaining_amount, account_id))

            # حذف بدهی/طلب از دیتابیس
            self.db_manager.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
            self.db_manager.commit()

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

    def add_loan(self):
        loan_type = "taken" if self.loan_type.currentText() == "وام گرفته‌شده" else "given"
        bank_name = self.loan_bank.text()
        total_amount = self.loan_amount.get_raw_value()
        interest_rate = self.loan_interest.get_raw_value() or 0
        account_id = self.loan_account.currentData()
        start_date = self.loan_start_date.text()
        installments_total = self.loan_installments_total.get_raw_value()
        installments_paid = self.loan_installments_paid.get_raw_value() or 0
        installment_amount = self.loan_installment_amount.get_raw_value()
        installment_interval = self.loan_installment_interval.get_raw_value() or 30
        add_to_account = self.loan_add_to_account_checkbox.isChecked() # دریافت وضعیت چک‌باکس

        if not bank_name:
            QMessageBox.warning(self, "خطا", "نام بانک نمی‌تواند خالی باشد!")
            return
        if not total_amount:
            QMessageBox.warning(self, "خطا", "مبلغ وام نمی‌تواند خالی باشد!")
            return
        if not account_id:
            QMessageBox.warning(self, "خطا", "لطفاً حساب مرتبط را انتخاب کنید!")
            return
        if not installments_total:
            QMessageBox.warning(self, "خطا", "تعداد اقساط نمی‌تواند خالی باشد!")
            return
        if not installment_amount:
            QMessageBox.warning(self, "خطا", "مبلغ قسط نمی‌تواند خالی باشد!")
            return
        if not is_valid_shamsi_date(start_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        if installments_paid > installments_total:
            QMessageBox.warning(self, "خطا", "تعداد اقساط پرداخت‌شده نمی‌تواند بیشتر از کل اقساط باشد!")
            return

        try:
            date = shamsi_to_gregorian(start_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            QDate.fromString(date, "yyyy-MM-dd")

            # به‌روزرسانی موجودی حساب فقط اگر چک‌باکس فعال باشد
            if add_to_account:
                if loan_type == "taken":
                    self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (total_amount, account_id))
                else:  # given
                    self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (total_amount, account_id))

            # ثبت وام با installment_interval
            self.db_manager.execute(
                """
                INSERT INTO loans (type, bank_name, total_amount, paid_amount, interest_rate, start_date,
                                account_id, installments_total, installments_paid, installment_amount,
                                installment_interval)
                VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
                """,
                (loan_type, bank_name, total_amount, interest_rate, date, account_id,
                installments_total, installments_paid, installment_amount, installment_interval)
            )
            loan_id = self.db_manager.cursor.lastrowid

            # تولید اقساط با حفظ روز ثابت
            start_gregorian = datetime.strptime(date, "%Y-%m-%d")
            start_jdate = jdatetime.date.fromgregorian(date=start_gregorian)
            for i in range(installments_total):
                due_jdate = start_jdate + jdatetime.timedelta(days=installment_interval * (i + 1))
                due_date_shamsi = due_jdate.strftime("%Y/%m/%d")
                due_date_gregorian = shamsi_to_gregorian(due_date_shamsi)
                is_paid = 1 if i < installments_paid else 0
                self.db_manager.execute(
                    "INSERT INTO loan_installments (loan_id, amount, due_date, is_paid) VALUES (?, ?, ?, ?)",
                    (loan_id, installment_amount, due_date_gregorian, is_paid)
                )

            self.db_manager.commit()
            self.loan_bank.clear()
            self.loan_amount.clear()
            self.loan_interest.clear()
            self.loan_start_date.clear()
            self.loan_installments_total.clear()
            self.loan_installments_paid.clear()
            self.loan_installment_amount.clear()
            self.loan_installment_interval.clear()
            self.load_loans()
            self.load_accounts()
            QMessageBox.information(self, "موفق", "وام با موفقیت ثبت شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback() # اضافه شده برای اطمینان از rollback


    def edit_loan(self, loan_id):
        try:
            self.db_manager.execute(
                """
                SELECT type, bank_name, total_amount, paid_amount, interest_rate, start_date,
                    account_id, installments_total, installments_paid, installment_amount,
                    installment_interval
                FROM loans WHERE id = ?
                """,
                (loan_id,)
            )
            loan = self.db_manager.fetchone()
            if not loan:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                return
            loan_type, bank_name, total_amount, paid_amount, interest_rate, start_date, account_id, installments_total, installments_paid, installment_amount, installment_interval = loan

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش وام")
            layout = QFormLayout()
            edit_type = QComboBox()
            edit_type.addItems(["وام گرفته‌شده", "وام داده‌شده"])
            edit_type.setCurrentText("وام گرفته‌شده" if loan_type == "taken" else "وام داده‌شده")
            edit_bank = QLineEdit(bank_name)
            edit_amount = NumberInput()
            edit_amount.setText(str(total_amount) if total_amount else "")
            edit_interest = NumberInput()
            edit_interest.setText(str(interest_rate) if interest_rate else "")
            edit_account = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                edit_account.addItem(display_text, acc_id)
            if account_id:
                edit_account.setCurrentText([f"{name} (موجودی: {format_number(balance)} ریال)" for acc_id, name, balance in accounts if acc_id == account_id][0])
            edit_start_date = QLineEdit(gregorian_to_shamsi(start_date) if start_date else "")
            edit_start_date.setReadOnly(True)
            edit_start_date.setPlaceholderText("1404/02/13")
            edit_start_date.mousePressEvent = lambda event: self.show_calendar_popup(edit_start_date)
            edit_installments_total = NumberInput()
            edit_installments_total.setText(str(installments_total) if installments_total else "")
            edit_installments_paid = NumberInput()
            edit_installments_paid.setText(str(installments_paid) if installments_paid else "")
            edit_installment_amount = NumberInput()
            edit_installment_amount.setText(str(installment_amount) if installment_amount else "")
            edit_installment_interval = NumberInput()
            edit_installment_interval.setText(str(installment_interval) if installment_interval else "30")

            # چک‌باکس "مبلغ وام به حساب اضافه شود؟" برای ویرایش
            # وضعیت این چک‌باکس باید بر اساس اینکه آیا در زمان ثبت وام، مبلغ به حساب اضافه شده بود یا نه، تعیین شود.
            # برای این کار، نیاز به یک ستون جدید در جدول loans داریم که این وضعیت را ذخیره کند.
            # فعلاً، به دلیل نبود این ستون، می‌توانیم آن را به‌صورت پیش‌فرض فعال در نظر بگیریم
            # یا اگر logic دیگری برای تعیین آن دارید، اعمال کنید.
            # برای سادگی، فعلاً آن را نمایش نمی‌دهیم یا همیشه فعال در نظر می‌گیریم تا زمانی که ستون مربوطه اضافه شود.
            # اگر می‌خواهید این چک‌باکس در ویرایش نیز قابل تنظیم باشد، باید ستون `is_added_to_account` را به جدول `loans` اضافه کنید.
            # فرض می‌کنیم در اینجا فعلاً نیازی به این کنترل در ویرایش نداریم و موجودی از طریق اقساط مدیریت می‌شود.
            # اگر نیاز به این کنترل در ویرایش بود، باید `ALTER TABLE` برای `loans` در `init_db` اضافه شود.


            save_btn = QPushButton("ذخیره")
            # در save_loan، پارامتر add_to_account را نیز ارسال می‌کنیم.
            # چون در ویرایش این چک‌باکس را اضافه نکردیم (طبق کامنت بالا)، فعلاً مقدار True را به صورت پیش‌فرض ارسال می‌کنیم.
            # اگر چک‌باکس را در edit_loan اضافه کردید، باید مقدار آن را از edit_loan_add_to_account_checkbox.isChecked() بگیرید.
            save_btn.clicked.connect(lambda: self.save_loan(
                loan_id, edit_type.currentText(), edit_bank.text(), edit_amount.get_raw_value(),
                edit_interest.get_raw_value() or 0, edit_account.currentData(), edit_start_date.text(),
                edit_installments_total.get_raw_value(), edit_installments_paid.get_raw_value() or 0,
                edit_installment_amount.get_raw_value(), edit_installment_interval.get_raw_value() or 30, dialog,
                True # فرض می‌کنیم همیشه True است تا زمانی که چک‌باکس در ویرایش اضافه شود.
            ))

            layout.addRow("نوع وام:", edit_type)
            layout.addRow("نام بانک:", edit_bank)
            layout.addRow("مبلغ کل:", edit_amount)
            layout.addRow("نرخ سود (%):", edit_interest)
            layout.addRow("حساب مرتبط:", edit_account)
            layout.addRow("تاریخ شروع (شمسی):", edit_start_date)
            layout.addRow("تعداد اقساط کل:", edit_installments_total)
            layout.addRow("تعداد اقساط پرداخت‌شده:", edit_installments_paid)
            layout.addRow("مبلغ هر قسط:", edit_installment_amount)
            layout.addRow("فاصله اقساط (روز):", edit_installment_interval)
            layout.addRow(save_btn)
            dialog.setLayout(layout)
            dialog.resize(400, 400)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback() # اضافه شده برای اطمینان از rollback

    def save_loan(self, loan_id, type_text, bank_name, total_amount, interest_rate, account_id, start_date,
              installments_total, installments_paid, installment_amount, installment_interval, dialog, add_to_account_on_edit):
        if not bank_name:
            QMessageBox.warning(self, "خطا", "نام بانک نمی‌تواند خالی باشد!")
            return
        if not total_amount:
            QMessageBox.warning(self, "خطا", "مبلغ وام نمی‌تواند خالی باشد!")
            return
        if not account_id:
            QMessageBox.warning(self, "خطا", "لطفاً حساب مرتبط را انتخاب کنید!")
            return
        if not installments_total:
            QMessageBox.warning(self, "خطا", "تعداد اقساط نمی‌تواند خالی باشد!")
            return
        if not installment_amount:
            QMessageBox.warning(self, "خطا", "مبلغ قسط نمی‌تواند خالی باشد!")
            return
        if not is_valid_shamsi_date(start_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        if installments_paid > installments_total:
            QMessageBox.warning(self, "خطا", "تعداد اقساط پرداخت‌شده نمی‌تواند بیشتر از کل اقساط باشد!")
            return

        try:
            date = shamsi_to_gregorian(start_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            loan_type = "taken" if type_text == "وام گرفته‌شده" else "given"

            # دریافت اطلاعات وام قبلی
            self.db_manager.execute("SELECT type, total_amount, account_id FROM loans WHERE id = ?", (loan_id,))
            old_loan = self.db_manager.fetchone()
            if not old_loan:
                QMessageBox.warning(self, "خطا", "وام یافت نشد!")
                self.db_manager.rollback()
                return
            old_type, old_total_amount, old_account_id = old_loan

            # بازگرداندن اثر وام قبلی بر موجودی حساب فقط اگر قبلاً اضافه شده بود
            # در اینجا فرض می‌کنیم که اگر مبلغ وام در ابتدا به حساب اضافه شده باشد، باید در ویرایش هم مدیریت شود.
            # این نیاز به یک ستون جدید در جدول loans دارد تا وضعیت اولیه را ذخیره کند.
            # فعلاً، اگر در زمان ایجاد وام، چک‌باکس فعال بود، فرض می‌کنیم اثرش روی حساب بوده و باید خنثی شود.
            # برای ساده‌سازی فعلی، فرض می‌کنیم هر بار ویرایش، اثر را خنثی و مجددا اعمال می‌کند.
            # اگر نیاز به رفتار دقیق‌تر بود، ستون is_initial_amount_added_to_account INTEGER DEFAULT 1
            # باید به جدول loans اضافه شود و هنگام add_loan مقداردهی شود.
            # سپس در save_loan بر اساس آن ستون عمل شود.

            # فرض: اگر old_account_id وجود داشت، یعنی قبلاً به حساب اضافه شده بود.
            # (این فرض ممکن است در همه سناریوها دقیق نباشد و راه حل بهتر، اضافه کردن یک ستون is_amount_affected_account باشد)
            if old_account_id: # اگر وامی قبلا به حسابی مرتبط بوده است
                 if old_type == "taken": # اگر وام گرفته شده بود، مبلغش اضافه شده بود، حالا کم کن
                     self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (old_total_amount, old_account_id))
                 else: # اگر وام داده شده بود، مبلغش کم شده بود، حالا اضافه کن
                     self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (old_total_amount, old_account_id))


            # اعمال اثر وام جدید فقط اگر add_to_account_on_edit (که از چک‌باکس گرفته می‌شود) فعال باشد.
            # فعلاً add_to_account_on_edit را True در نظر گرفتیم.
            if add_to_account_on_edit:
                if loan_type == "taken":
                    self.db_manager.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (total_amount, account_id))
                else:
                    self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (total_amount, account_id))


            # به‌روزرسانی وام با installment_interval
            self.db_manager.execute(
                """
                UPDATE loans SET type = ?, bank_name = ?, total_amount = ?, interest_rate = ?,
                                start_date = ?, account_id = ?, installments_total = ?,
                                installments_paid = ?, installment_amount = ?, installment_interval = ?
                WHERE id = ?
                """,
                (loan_type, bank_name, total_amount, interest_rate, date, account_id,
                installments_total, installments_paid, installment_amount, installment_interval, loan_id)
            )

            # حذف اقساط قبلی
            self.db_manager.execute("DELETE FROM loan_installments WHERE loan_id = ?", (loan_id,))

            # بازسازی اقساط
            start_gregorian = datetime.strptime(date, "%Y-%m-%d")
            start_jdate = jdatetime.date.fromgregorian(date=start_gregorian)
            for i in range(installments_total):
                due_jdate = start_jdate + jdatetime.timedelta(days=installment_interval * (i + 1))
                due_date_shamsi = due_jdate.strftime("%Y/%m/%d")
                due_date_gregorian = shamsi_to_gregorian(due_date_shamsi)
                is_paid = 1 if i < installments_paid else 0
                self.db_manager.execute(
                    "INSERT INTO loan_installments (loan_id, amount, due_date, is_paid) VALUES (?, ?, ?, ?)",
                    (loan_id, installment_amount, due_date_gregorian, is_paid)
                )

            self.db_manager.commit()
            self.load_loans()
            self.load_accounts()
            dialog.accept()
            QMessageBox.information(self, "موفق", "وام با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            self.db_manager.rollback() # اضافه شده برای اطمینان از rollback

    def load_loans(self):
        try:
            offset = (self.loans_current_page - 1) * self.loans_per_page
            self.db_manager.execute(
                """
                SELECT l.id, l.type, l.bank_name, l.total_amount, l.paid_amount, l.interest_rate, 
                    l.start_date, l.account_id, l.installments_total, l.installments_paid, 
                    l.installment_amount, l.installment_interval
                FROM loans l
                ORDER BY l.start_date DESC
                LIMIT ? OFFSET ?
                """,
                (self.loans_per_page, offset)
            )
            loans = self.db_manager.fetchall()
            self.loans_table.setRowCount(len(loans))
            for row, (id, loan_type, bank_name, total_amount, paid_amount, interest_rate, start_date, 
                    account_id, installments_total, installments_paid, installment_amount, 
                    installment_interval) in enumerate(loans):
                self.loans_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.loans_table.setItem(row, 1, QTableWidgetItem("گرفته‌شده" if loan_type == "taken" else "داده‌شده"))
                self.loans_table.setItem(row, 2, QTableWidgetItem(bank_name))
                self.loans_table.setItem(row, 3, QTableWidgetItem(format_number(total_amount)))
                self.loans_table.setItem(row, 4, QTableWidgetItem(format_number(paid_amount)))
                self.loans_table.setItem(row, 5, QTableWidgetItem(str(interest_rate)))
                self.loans_table.setItem(row, 6, QTableWidgetItem(gregorian_to_shamsi(start_date)))
                self.loans_table.setItem(row, 7, QTableWidgetItem(str(installments_total)))
                self.loans_table.setItem(row, 8, QTableWidgetItem(str(installments_paid)))
                self.loans_table.setItem(row, 9, QTableWidgetItem(format_number(installment_amount) if installment_amount is not None else "0"))
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, l_id=id: self.edit_loan(l_id))
                self.loans_table.setCellWidget(row, 10, edit_btn)
                view_btn = QPushButton("مشاهده اقساط")
                view_btn.clicked.connect(lambda checked, l_id=id: self.view_installments(l_id))
                self.loans_table.setCellWidget(row, 11, view_btn)
            self.loans_page_label.setText(f"صفحه {self.loans_current_page}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def view_installments(self, loan_id):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("اقساط وام")
            layout = QVBoxLayout()
            dialog.setLayout(layout)

            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(["شناسه", "مبلغ", "سررسید", "وضعیت", "ویرایش", "تسویه"])
            table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            table.verticalHeader().setDefaultSectionSize(40)
            table.setColumnWidth(0, 50)
            table.setColumnWidth(1, 120)
            table.setColumnWidth(2, 100)
            table.setColumnWidth(3, 100)
            table.setColumnWidth(4, 80)
            table.setColumnWidth(5, 80)

            self.db_manager.execute(
                "SELECT id, amount, due_date, is_paid FROM loan_installments WHERE loan_id = ? ORDER BY due_date",
                (loan_id,)
            )
            installments = self.db_manager.fetchall()
            table.setRowCount(len(installments))
            for row, (id, amount, due_date, is_paid) in enumerate(installments):
                table.setItem(row, 0, QTableWidgetItem(str(id)))
                table.setItem(row, 1, QTableWidgetItem(format_number(amount)))
                table.setItem(row, 2, QTableWidgetItem(gregorian_to_shamsi(due_date)))
                table.setItem(row, 3, QTableWidgetItem("پرداخت‌شده" if is_paid else "پرداخت‌نشده"))
                if not is_paid:
                    edit_btn = QPushButton("ویرایش")
                    edit_btn.clicked.connect(lambda checked, inst_id=id: self.edit_installment(inst_id, loan_id, dialog))
                    table.setCellWidget(row, 4, edit_btn)
                    settle_btn = QPushButton("تسویه")
                    settle_btn.clicked.connect(lambda checked, inst_id=id: self.settle_installment(inst_id, loan_id, dialog))
                    table.setCellWidget(row, 5, settle_btn)
                else:
                    table.setItem(row, 4, QTableWidgetItem("-"))
                    table.setItem(row, 5, QTableWidgetItem("-"))

            scroll_area = QScrollArea()
            scroll_area.setWidget(table)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMinimumHeight(400)
            layout.addWidget(scroll_area)
            dialog.resize(600, 500)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_installment(self, installment_id, loan_id, parent_dialog):
        try:
            self.db_manager.execute(
                "SELECT amount, due_date FROM loan_installments WHERE id = ?",
                (installment_id,)
            )
            installment = self.db_manager.fetchone()
            if not installment:
                QMessageBox.warning(self, "خطا", "قسط یافت نشد!")
                return
            amount, due_date = installment

            dialog = QDialog(self)
            dialog.setWindowTitle("ویرایش قسط")
            layout = QFormLayout()
            edit_amount = NumberInput()
            edit_amount.setText(str(amount))
            edit_due_date = QLineEdit(gregorian_to_shamsi(due_date))
            edit_due_date.setReadOnly(True)
            edit_due_date.setPlaceholderText("1404/02/13")
            edit_due_date.mousePressEvent = lambda event: self.show_calendar_popup(edit_due_date)
            save_btn = QPushButton("ذخیره")
            save_btn.clicked.connect(lambda: self.save_installment(
                installment_id, loan_id, edit_amount.get_raw_value(), edit_due_date.text(), dialog, parent_dialog
            ))

            layout.addRow("مبلغ قسط:", edit_amount)
            layout.addRow("تاریخ سررسید (شمسی):", edit_due_date)
            layout.addRow(save_btn)
            dialog.setLayout(layout)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_installment(self, installment_id, loan_id, amount, due_date, dialog, parent_dialog):
        if not amount:
            QMessageBox.warning(self, "خطا", "مبلغ قسط نمی‌تواند خالی باشد!")
            return
        if not is_valid_shamsi_date(due_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            date = shamsi_to_gregorian(due_date)
            if not date:
                QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                return
            self.db_manager.execute(
                "UPDATE loan_installments SET amount = ?, due_date = ? WHERE id = ?",
                (amount, date, installment_id)
            )
            self.db_manager.commit()
            self.view_installments(loan_id)  # به‌روزرسانی جدول اقساط
            dialog.accept()
            parent_dialog.accept()  # بستن دیالوگ اصلی و باز کردن مجدد
            self.view_installments(loan_id)  # باز کردن مجدد دیالوگ اقساط
            QMessageBox.information(self, "موفق", "قسط با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def settle_installment(self, installment_id, loan_id, parent_dialog):
        try:
            self.db_manager.execute(
                "SELECT amount, is_paid FROM loan_installments WHERE id = ?",
                (installment_id,)
            )
            installment = self.db_manager.fetchone()
            if not installment:
                QMessageBox.warning(self, "خطا", "قسط یافت نشد!")
                return
            amount, is_paid = installment
            if is_paid:
                QMessageBox.warning(self, "خطا", "این قسط قبلاً تسویه شده است!")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("تسویه قسط")
            layout = QFormLayout()
            account_combo = QComboBox()
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            for acc_id, name, balance in accounts:
                display_text = f"{name} (موجودی: {format_number(balance)} ریال)"
                account_combo.addItem(display_text, acc_id)
            save_btn = QPushButton("تسویه")
            save_btn.clicked.connect(lambda: self.confirm_settle_installment(
                installment_id, loan_id, amount, account_combo.currentData(), dialog, parent_dialog
            ))

            layout.addRow("حساب برای برداشت:", account_combo)
            layout.addRow(save_btn)
            dialog.setLayout(layout)
            dialog.exec()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def confirm_settle_installment(self, installment_id, loan_id, amount, account_id, dialog, parent_dialog):
        try:
            # بررسی موجودی حساب
            self.db_manager.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
            balance = self.db_manager.fetchone()[0]
            if balance < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                return

            # به‌روزرسانی موجودی حساب
            self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            
            # علامت‌گذاری قسط به‌عنوان پرداخت‌شده
            self.db_manager.execute("UPDATE loan_installments SET is_paid = 1 WHERE id = ?", (installment_id,))
            
            # به‌روزرسانی تعداد اقساط پرداخت‌شده و مبلغ پرداخت‌شده وام
            self.db_manager.execute(
                """
                UPDATE loans 
                SET installments_paid = installments_paid + 1, 
                    paid_amount = paid_amount + ?
                WHERE id = ?
                """,
                (amount, loan_id)
            )

            self.db_manager.commit()
            self.load_accounts()
            self.load_loans()
            dialog.accept()  # بستن دیالوگ تسویه
            parent_dialog.accept()  # بستن دیالوگ لیست اقساط
            self.view_installments(loan_id)  # باز کردن مجدد لیست اقساط به‌روزرسانی‌شده
            QMessageBox.information(self, "موفق", "قسط با موفقیت تسویه شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

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
            self.db_manager.execute("SELECT total_amount, installments_total, installments_paid, start_date FROM loans WHERE id = ?", (loan_id,))
            loan = self.db_manager.fetchone()
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
            self.db_manager.execute("SELECT id, amount, due_date, is_paid FROM loan_installments WHERE loan_id = ?", (loan_id,))
            installments = self.db_manager.fetchall()
            if not installments:
                start_date = jdatetime.date.fromgregorian(date=datetime.strptime(start_date, "%Y-%m-%d"))
                for i in range(installments_total):
                    due_date = start_date + jdatetime.timedelta(days=i * 30)
                    due_date_str = due_date.togregorian().strftime("%Y-%m-%d")
                    self.db_manager.execute("INSERT INTO loan_installments (loan_id, amount, due_date, is_paid) VALUES (?, ?, ?, ?)", 
                                    (loan_id, installment_amount, due_date_str, 1 if i < installments_paid else 0))
                    self.db_manager.commit()
                self.db_manager.execute("SELECT id, amount, due_date, is_paid FROM loan_installments WHERE loan_id = ?", (loan_id,))
                installments = self.db_manager.fetchall()
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
            self.db_manager.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
            balance = self.db_manager.fetchone()[0]
            if balance < amount:
                QMessageBox.warning(self, "خطا", "موجودی حساب کافی نیست!")
                return

            self.db_manager.execute("UPDATE loan_installments SET is_paid = 1 WHERE loan_id = ? LIMIT 1 OFFSET ?", (loan_id, row))
            self.db_manager.execute("UPDATE loans SET paid_amount = paid_amount + ?, installments_paid = installments_paid + 1 WHERE id = ?", (amount, loan_id))
            self.db_manager.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, account_id))
            self.db_manager.commit()
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
            self.db_manager.execute("INSERT INTO persons (name) VALUES (?)", (name,))
            self.db_manager.commit()
            self.person_name_input.clear()
            self.load_persons()
            self.load_report_persons()
            QMessageBox.information(self, "موفق", "شخص با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def filter_persons_table(self):
        search_text = self.person_search_input.text().strip()
        try:
            query = "SELECT id, name FROM persons"
            params = []
            
            if search_text:
                query += " WHERE name LIKE ?"
                params.append(f"%{search_text}%")
            
            query += " ORDER BY name ASC" # مرتب‌سازی بر اساس نام

            self.db_manager.execute(query, tuple(params))
            persons = self.db_manager.fetchall()

            self.persons_table.setRowCount(len(persons))
            for row, (id, name) in enumerate(persons):
                self.persons_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.persons_table.setItem(row, 1, QTableWidgetItem(name))
                
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, p_id=id: self.edit_person(p_id))
                self.persons_table.setCellWidget(row, 2, edit_btn)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده هنگام فیلتر اشخاص: {e}")

    def load_persons(self):
        # به جای بارگذاری مستقیم از دیتابیس و پر کردن جدول، متد فیلتر را فراخوانی می‌کنیم
        # این کار تضمین می‌کند که فیلتر اعمال شود و کامبوباکس‌ها نیز به‌روز شوند.
        try:
            self.filter_persons_table() # ابتدا جدول را فیلتر و پر می‌کنیم

            # به‌روزرسانی کامبوباکس‌ها (برای تراکنش‌ها و بدهی‌ها)
            self.transaction_person.clear()
            self.debt_person.clear()
            self.transaction_person.addItem("-", None)
            self.debt_person.addItem("-", None)

            self.db_manager.execute("SELECT id, name FROM persons ORDER BY name ASC")
            all_persons = self.db_manager.fetchall()
            for id, name in all_persons:
                self.transaction_person.addItem(name, id)
                self.debt_person.addItem(name, id)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_person(self, person_id):
        try:
            self.db_manager.execute("SELECT name FROM persons WHERE id = ?", (person_id,))
            person = self.db_manager.fetchone()
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
            self.db_manager.execute("UPDATE persons SET name = ? WHERE id = ?", (name, person_id))
            self.db_manager.commit()
            self.load_persons()
            self.load_report_persons()
            dialog.accept()
            QMessageBox.information(self, "موفق", "نام شخص با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def update_dashboard(self):
        try:
            # به‌روزرسانی موجودی کل
            self.db_manager.execute("SELECT SUM(balance) FROM accounts")
            total_balance = self.db_manager.fetchone()[0] or 0
            self.total_balance_label.setText(f"موجودی کل: {format_number(total_balance)} ریال")

            # بارگذاری بدهی‌ها و طلب‌های مهم
            today = jdatetime.date.today()
            fifteen_days_later = today + jdatetime.timedelta(days=15)
            today_str = today.togregorian().strftime("%Y-%m-%d")
            fifteen_days_later_str = fifteen_days_later.togregorian().strftime("%Y-%m-%d")

            self.db_manager.execute(
                "SELECT d.id, p.name, d.amount, d.paid_amount, d.due_date, d.is_paid, COALESCE(a.name, '-') "
                "FROM debts d JOIN persons p ON d.person_id = p.id LEFT JOIN accounts a ON d.account_id = a.id "
                "WHERE d.show_in_dashboard = 1 AND d.is_paid = 0 AND d.due_date IS NOT NULL "
                "AND (d.due_date <= ? OR (d.due_date >= ? AND d.due_date <= ?))",
                (today_str, today_str, fifteen_days_later_str)
            )
            debts = self.db_manager.fetchall()

            # دیباگ: چاپ نوع و مقدار debts
            #print(f"Type of debts: {type(debts)}, Value: {debts}")
            # مطمئن شدن از اینکه debts یه لیست یا تاپل هست
            if not isinstance(debts, (list, tuple)):
                #print(f"Error: Expected a list for debts, got {type(debts)}")
                debts = []

            self.important_debts_table.setRowCount(len(debts))
            for row, (id, person, amount, paid, due_date, is_paid, account) in enumerate(debts):
                shamsi_due_date = gregorian_to_shamsi(due_date) if due_date else "-"
                self.important_debts_table.setItem(row, 0, QTableWidgetItem(person))
                self.important_debts_table.setItem(row, 1, QTableWidgetItem(format_number(amount)))
                self.important_debts_table.setItem(row, 2, QTableWidgetItem(format_number(paid)))
                self.important_debts_table.setItem(row, 3, QTableWidgetItem(shamsi_due_date))
                self.important_debts_table.setItem(row, 4, QTableWidgetItem("پرداخت شده" if is_paid else "در جریان"))

            # آپدیت آمار ماه جاری
            expenses = self.get_current_month_expenses()
            income = self.get_current_month_income()
            balance = self.get_current_month_balance()
            credits = self.get_current_month_credits()
            debts_value = self.get_current_month_debts()
            
            self.expenses_value.setText(f"{format_number(expenses)} ریال")
            self.income_value.setText(f"{format_number(income)} ریال")
            self.balance_value.setText(f"{format_number(balance)} ریال")
            self.credits_value.setText(f"{format_number(credits)} ریال")
            self.debts_value.setText(f"{format_number(debts_value)} ریال")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def get_current_month_expenses(self):
        today = jdatetime.date.today()
        start_of_month = jdatetime.date(today.year, today.month, 1).togregorian()
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year + 1 if today.month == 12 else today.year
        end_of_month = (jdatetime.date(next_year, next_month, 1) - jdatetime.timedelta(days=1)).togregorian()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0)
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = 'expense' AND t.date BETWEEN ? AND ?
            """,
            (start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"))
        )
        return self.db_manager.fetchone()[0]

    def get_current_month_income(self):
        today = jdatetime.date.today()
        start_of_month = jdatetime.date(today.year, today.month, 1).togregorian()
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year + 1 if today.month == 12 else today.year
        end_of_month = (jdatetime.date(next_year, next_month, 1) - jdatetime.timedelta(days=1)).togregorian()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(t.amount), 0)
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE c.type = 'income' AND t.date BETWEEN ? AND ?
            """,
            (start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"))
        )
        return self.db_manager.fetchone()[0]

    def get_current_month_balance(self):
        income = self.get_current_month_income()
        expenses = self.get_current_month_expenses()
        return income - expenses

    def get_current_month_credits(self):
        today = jdatetime.date.today()
        start_of_month = jdatetime.date(today.year, today.month, 1).togregorian()
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year + 1 if today.month == 12 else today.year
        end_of_month = (jdatetime.date(next_year, next_month, 1) - jdatetime.timedelta(days=1)).togregorian()
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(amount - paid_amount), 0)
            FROM debts
            WHERE is_credit = 1 AND is_paid = 0 AND due_date BETWEEN ? AND ?
            """,
            (start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"))
        )
        return self.db_manager.fetchone()[0]

    def get_current_month_debts(self):
        today = jdatetime.date.today()
        start_of_month = jdatetime.date(today.year, today.month, 1).togregorian()
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year + 1 if today.month == 12 else today.year
        end_of_month = (jdatetime.date(next_year, next_month, 1) - jdatetime.timedelta(days=1)).togregorian()
        
        # دیباگ: چاپ بازه تاریخ
        #print(f"get_current_month_debts: start_of_month = {start_of_month.strftime('%Y-%m-%d')}, end_of_month = {end_of_month.strftime('%Y-%m-%d')}")
        
        # دیباگ: چک کردن تعداد بدهی‌های پرداخت‌نشده
        self.db_manager.execute(
            """
            SELECT COUNT(*)
            FROM debts
            WHERE is_credit = 0 AND is_paid = 0
            """
        )
        debt_count = self.db_manager.fetchone()[0]
        #print(f"get_current_month_debts: Total unpaid debts (is_credit = 0) = {debt_count}")
        
        # دیباگ: چک کردن بدهی‌هایی که due_date در بازه ماه جاری دارن
        self.db_manager.execute(
            """
            SELECT COUNT(*)
            FROM debts
            WHERE is_credit = 0 AND is_paid = 0 AND due_date BETWEEN ? AND ?
            """,
            (start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"))
        )
        matching_debt_count = self.db_manager.fetchone()[0]
        #print(f"get_current_month_debts: Unpaid debts in current month = {matching_debt_count}")
        
        # کوئری اصلی
        self.db_manager.execute(
            """
            SELECT COALESCE(SUM(amount - paid_amount), 0)
            FROM debts
            WHERE is_credit = 0 AND is_paid = 0 AND due_date BETWEEN ? AND ?
            """,
            (start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"))
        )
        result = self.db_manager.fetchone()[0]
        #print(f"get_current_month_debts: Sum of unpaid debts = {result}")
        return result

    def check_reminders(self):
        today = jdatetime.date.today().togregorian().strftime("%Y-%m-%d")
        try:
            self.db_manager.execute("SELECT id, amount, due_date FROM debts WHERE is_paid = 0 AND due_date IS NOT NULL AND due_date <= ?", (today,))
            debts = self.db_manager.fetchall()
            for debt in debts:
                QMessageBox.warning(self, "یادآوری", f"بدهی به مبلغ {format_number(debt[1])} ریال تا {gregorian_to_shamsi(debt[2])} سررسید شده!")
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
                self.db_manager.execute(query, params)
                results = self.db_manager.fetchall()
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
        self.db_manager.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FinanceApp()
    window.show()
    sys.exit(app.exec())