import sys
import locale
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
                             QTableWidgetItem, QLabel, QLineEdit, QComboBox,
                             QMessageBox, QFormLayout, QGridLayout, QScrollArea, 
                             QDialog, QCheckBox, QCalendarWidget,QSpacerItem, QSizePolicy, QFrame,
                             QHeaderView)
from PyQt6.QtCore import QDate, Qt, QTimer, QLocale  # اضافه کردن QLocale
from PyQt6.QtGui import QIcon, QFont, QColor, QIntValidator
import sqlite3
import jdatetime
from datetime import datetime, timedelta
import pandas as pd
import reportlab.lib.pagesizes as pagesizes 
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFont, getRegisteredFontNames
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import matplotlib.pyplot as plt
from io import BytesIO
import os
import bcrypt
import dropbox
from dropbox.exceptions import ApiError
from bidi.algorithm import get_display 
from arabic_reshaper import reshape

from database import DatabaseManager
from login_dialog import LoginDialog
from change_password_dialog import ChangePasswordDialog
from ui.components.custom_widgets import NumberInput, PersianCalendarPopup, PersianCalendarWidget
from core import utils
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.accounts_tab import AccountsTab
from ui.tabs.transactions_tab import TransactionsTab
from ui.tabs.debts_tab import DebtsTab
from ui.tabs.loans_tab import LoansTab
from ui.tabs.persons_tab import PersonsTab
from ui.tabs.categories_tab import CategoriesTab

# تنظیم locale برای جداکننده اعداد
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

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
        QApplication.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        try:
            # فقط یک بار فونت را ثبت کنید
            if 'Vazir' not in getRegisteredFontNames(): # استفاده از getRegisteredFontNames
                font_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'Vazir.ttf') 
                if not os.path.exists(font_path):
                    font_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'assets', 'Vazir.ttf')
                
                if os.path.exists(font_path):
                    registerFont(TTFont('Vazir', font_path)) # استفاده از registerFont
                else:
                    QMessageBox.critical(self, "خطا", "فایل فونت Vazir.ttf یافت نشد! لطفا آن را در کنار فایل اجرایی یا پوشه assets قرار دهید.")

        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری فونت: {e}")
        
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
                    ('انتقال بین حساب‌ها (خروج)', 'expense'), ('انتقال بین حساب‌ها (ورود)', 'income'),
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

        self.dashboard_tab = DashboardTab(self.db_manager)
        # استفاده از کلاس جدید برای ساخت تب حساب‌ها و پاس دادن db_manager و self
        self.accounts_tab_widget = AccountsTab(self.db_manager, self)
        
        # ساخت تب تراکنش‌ها به صورت ماژول مستقل + اتصال سیگنال تغییر داده
        self.transactions_tab = TransactionsTab(self.db_manager, self)
        self.transactions_tab.data_changed.connect(self.on_transactions_data_changed)
        # ساخت تب بدهی/طلب به صورت ماژول مستقل + اتصال سیگنال تغییر داده
        self.debts_tab = DebtsTab(self.db_manager, self)
        self.debts_tab.data_changed.connect(self.on_debts_data_changed)
        # ساخت تب وام‌ها به صورت ماژول مستقل + اتصال سیگنال تغییر داده
        self.loans_tab = LoansTab(self.db_manager, self)
        self.loans_tab.data_changed.connect(self.on_loans_data_changed)
        reports_tab = self.create_reports_tab()
        # ساخت تب اشخاص و دسته‌بندی‌ها به صورت ماژول‌های مستقل
        self.persons_tab = PersonsTab(self.db_manager, self)
        self.persons_tab.data_changed.connect(self.on_persons_data_changed)
        self.categories_tab = CategoriesTab(self.db_manager, self)
        self.categories_tab.data_changed.connect(self.on_categories_data_changed)
        settings_tab = self.create_settings_tab()

        tabs.addTab(self.dashboard_tab, "داشبورد")
        tabs.addTab(self.accounts_tab_widget, "حساب‌ها") # افزودن تب مستقل
        tabs.addTab(self.transactions_tab, "تراکنش‌ها")
        tabs.addTab(self.debts_tab, "بدهی/طلب")
        tabs.addTab(self.loans_tab, "وام‌ها")
        tabs.addTab(reports_tab, "گزارش‌ها")
        tabs.addTab(self.persons_tab, "اشخاص")
        tabs.addTab(self.categories_tab, "دسته بندی‌ها")
        tabs.addTab(settings_tab, "تنظیمات")

        tabs.currentChanged.connect(self.on_tab_changed)

        scroll = QScrollArea()
        scroll.setWidget(tabs)
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

    def on_tab_changed(self, index):
        if index == 0:  # تب داشبورد
            self.dashboard_tab.update_dashboard()

    def on_transactions_data_changed(self):
        """پس از هر تغییر در تراکنش‌ها: به‌روزرسانی موجودی حساب‌ها و داشبورد"""
        self.load_accounts()
        self.dashboard_tab.update_dashboard()

    def on_debts_data_changed(self):
        """پس از هر تغییر در بدهی/طلب: به‌روزرسانی حساب‌ها، تراکنش‌ها و داشبورد"""
        self.load_accounts()
        self.transactions_tab.refresh()
        self.dashboard_tab.update_dashboard()

    def on_loans_data_changed(self):
        """پس از هر تغییر در وام‌ها (ثبت/ویرایش/تسویه قسط): به‌روزرسانی حساب‌ها و داشبورد"""
        self.load_accounts()
        self.dashboard_tab.update_dashboard()

    def on_persons_data_changed(self):
        """پس از هر تغییر در اشخاص: به‌روزرسانی کامبوباکس‌های سایر تب‌ها"""
        self.load_persons()

    def on_categories_data_changed(self):
        """پس از هر تغییر در دسته‌بندی‌ها: به‌روزرسانی فرم و لیست تراکنش‌ها"""
        self.load_categories()
        self.load_transactions()

    def show_change_password_dialog(self, username):
        dialog = ChangePasswordDialog(self.db_manager, username, self)
        dialog.exec()

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
            if not utils.is_valid_shamsi_date(start_date) or not utils.is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = utils.shamsi_to_gregorian(start_date)
            end_date_g = utils.shamsi_to_gregorian(end_date)
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
            results.append(["مجموع هزینه‌ها", utils.format_number(total_cost)])

            # مجموع درآمدها
            self.db_manager.execute("""
                SELECT SUM(t.amount)
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE c.type = 'income' AND t.date BETWEEN ? AND ?
            """, (start_date_g, end_date_g))
            total_income = self.db_manager.fetchone()[0] or 0
            results.append(["مجموع درآمدها", utils.format_number(total_income)])

            # تفاوت
            results.append(["تفاوت (درآمد - هزینه)", utils.format_number(total_income - total_cost)])

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
            if not utils.is_valid_shamsi_date(start_date) or not utils.is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = utils.shamsi_to_gregorian(start_date)
            end_date_g = utils.shamsi_to_gregorian(end_date)
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
            table.setItem(row, 1, QTableWidgetItem(utils.format_number(amount)))
            table.setItem(row, 2, QTableWidgetItem(utils.gregorian_to_shamsi(date)))
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
                start_date_g = utils.shamsi_to_gregorian(start_date)
                end_date_g = utils.shamsi_to_gregorian(end_date)
                
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
            if not utils.is_valid_shamsi_date(start_date) or not utils.is_valid_shamsi_date(end_date):
                QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
                return

            start_date_g = utils.shamsi_to_gregorian(start_date)
            end_date_g = utils.shamsi_to_gregorian(end_date)
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
            table.setItem(row, 1, QTableWidgetItem(utils.gregorian_to_shamsi(date) if date != "-" else "-"))
            table.setItem(row, 2, QTableWidgetItem(account))
            table.setItem(row, 3, QTableWidgetItem(category))
            table.setItem(row, 4, QTableWidgetItem(utils.format_number(amount) if isinstance(amount, (int, float)) else amount))
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
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
            reports_folder = os.path.join(base_path, "reports")
            os.makedirs(reports_folder, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_prefix = f"{report_type}_report_{timestamp}"

            output_extension = ""
            if format_type == "excel":
                output_extension = "xlsx"
            elif format_type == "csv":
                output_extension = "csv"
            elif format_type == "pdf":
                output_extension = "pdf"
            else:
                QMessageBox.warning(self, "خطا", "فرمت خروجی نامعتبر است.")
                return

            output_filename = f"{file_prefix}.{output_extension}"
            output_path = os.path.join(reports_folder, output_filename)

            # ... بخش تولید DataFrame (بدون تغییر عمده در این مرحله)
            df = pd.DataFrame() # تعریف اولیه برای جلوگیری از خطای UnboundLocalError
            if report_type == "transactions":
                df = pd.DataFrame(
                    data,
                    columns=["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"]
                )
                df["تاریخ"] = df["تاریخ"].apply(utils.gregorian_to_shamsi)
                df["مبلغ"] = df["مبلغ"].apply(utils.format_number)
                
            elif report_type == "debts":
                processed_data = []
                for row_data in data:
                    processed_row = list(row_data)
                    
                    is_paid_val = processed_row[5]
                    processed_row[5] = "پرداخت شده" if is_paid_val == 1 else "در جریان"

                    is_credit_val = processed_row[7]
                    processed_row[7] = "طلب" if is_credit_val == 1 else "بدهی"
                    
                    processed_data.append(processed_row)

                df = pd.DataFrame(
                    processed_data,
                    columns=["شناسه", "شخص", "مبلغ", "پرداخت شده", "سررسید", "وضعیت", "حساب", "نوع", "توضیحات"]
                )
                df["سررسید"] = df["سررسید"].apply(lambda x: utils.gregorian_to_shamsi(x) if x else "-")
                df["مبلغ"] = df["مبلغ"].apply(utils.format_number)
                df["پرداخت شده"] = df["پرداخت شده"].apply(utils.format_number)

            elif report_type == "cost_income":
                df = pd.DataFrame(
                    data,
                    columns=["نوع", "مبلغ", "تاریخ", "حساب", "شخص", "توضیحات"]
                )
                df["تاریخ"] = df["تاریخ"].apply(utils.gregorian_to_shamsi)
                df["مبلغ"] = df["مبلغ"].apply(utils.format_number)
            elif report_type == "monthly":
                df = pd.DataFrame(
                    data,
                    columns=["ماه", "هزینه", "درآمد", "تفاوت"]
                )
                for col in ["هزینه", "درآمد", "تفاوت"]:
                    df[col] = df[col].apply(utils.format_number)

            elif report_type == "person":
                df = pd.DataFrame(
                    data,
                    columns=["دسته‌بندی", "تاریخ", "حساب", "مبلغ", "توضیحات"]
                )
                df["تاریخ"] = df["تاریخ"].apply(lambda x: utils.gregorian_to_shamsi(x) if x != "-" else "-")
                df["مبلغ"] = df["مبلغ"].apply(lambda x: utils.format_number(x) if isinstance(x, (int, float)) else x)

            elif report_type == "general":
                df = pd.DataFrame(data, columns=["معیار", "مقدار"])
            elif report_type == "loan_installments_report": # اضافه کردن این نوع گزارش جدید [cite: 1]
                df = pd.DataFrame(
                    data,
                    columns=["شناسه قسط", "مبلغ قسط", "سررسید", "وضعیت"] # [cite: 1]
                )
                # در اینجا نیازی به utils.gregorian_to_shamsi یا utils.format_number نیست
                # چون data قبلا در export_single_loan_report فرمت شده است. [cite: 1]
                
            else: # در صورت عدم تطابق نوع گزارش
                QMessageBox.warning(self, "خطا", "نوع گزارش نامعتبر برای تولید خروجی!")
                if dialog: dialog.accept()
                return

            if format_type == "excel":
                df.to_excel(output_path, index=False, engine='openpyxl')
                QMessageBox.information(self, "موفق", f"فایل اکسل با موفقیت در {output_path} ذخیره شد!")
            elif format_type == "csv":
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "موفق", f"فایل CSV با موفقیت در {output_path} ذخیره شد!")
            elif format_type == "pdf":
                doc = SimpleDocTemplate(output_path, pagesize=pagesizes.A4)
                elements = []
                styles = getSampleStyleSheet()

                persian_style = ParagraphStyle(
                    name='PersianTableStyle',
                    parent=styles['Normal'],
                    fontName='Vazir',
                    fontSize=10, # سایز فونت مناسب برای جداول
                    alignment=4, # ALIGN_RIGHT for RTL text
                    wordWrap='RTL',
                )
                
                table_data = []
                header_row = [Paragraph(get_display(reshape(str(col))), persian_style) for col in df.columns.tolist()]
                table_data.append(header_row)

                for row_idx, row_data in df.iterrows():
                    new_row = []
                    for item in row_data.values:
                        text_content = str(item) if item is not None else "-"
                        reshaped_text = reshape(text_content)
                        displayed_text = get_display(reshaped_text)
                        new_row.append(Paragraph(displayed_text, persian_style))
                    table_data.append(new_row)

                table = Table(table_data)
                
                # --- تنظیم عرض ستون‌ها بر اساس نوع گزارش ---
                # A4_WIDTH = 595.27 points
                # Left/Right margin default to 1 inch (72 points each), so usable width = 595.27 - 2*72 = 451.27
                page_width = pagesizes.A4[0]
                margin = 72
                usable_width = page_width - (2 * margin)

                col_widths = []
                if report_type == "transactions":
                    # شناسه، تاریخ، حساب، شخص، دسته‌بندی، مبلغ، توضیحات، نوع
                    # مبلغ و توضیحات نیاز به فضای بیشتر دارند
                    col_widths = [
                        usable_width * 0.12, # شناسه (5%)
                        usable_width * 0.15, # تاریخ (12%)
                        usable_width * 0.15, # حساب (15%)
                        usable_width * 0.12, # شخص (12%)
                        usable_width * 0.15, # دسته‌بندی (15%)
                        usable_width * 0.15, # مبلغ (15%) - افزایش پهنا
                        usable_width * 0.20, # توضیحات (20%) - افزایش پهنا
                        usable_width * 0.12  # نوع (6%)
                    ]
                elif report_type == "debts":
                    # شناسه، شخص، مبلغ، پرداخت شده، سررسید، وضعیت، حساب، نوع، توضیحات
                    col_widths = [
                        usable_width * 0.12,  # شناسه
                        usable_width * 0.12,  # شخص
                        usable_width * 0.15,  # مبلغ (افزایش بیشتر)
                        usable_width * 0.15,  # پرداخت شده (افزایش بیشتر)
                        usable_width * 0.15,  # سررسید
                        usable_width * 0.12,  # وضعیت
                        usable_width * 0.12,  # حساب
                        usable_width * 0.08,  # نوع
                        usable_width * 0.15   # توضیحات (باز هم بررسی کنید که این نسبت‌ها جمعشان 1.0 شود)
                    ]
                elif report_type == "cost_income":
                    # نوع، مبلغ، تاریخ، حساب، شخص، توضیحات
                    col_widths = [
                        usable_width * 0.15, # نوع
                        usable_width * 0.15, # مبلغ (افزایش)
                        usable_width * 0.12, # تاریخ
                        usable_width * 0.15, # حساب
                        usable_width * 0.15, # شخص
                        usable_width * 0.28  # توضیحات (افزایش)
                    ]
                elif report_type == "monthly":
                    # ماه، هزینه، درآمد، تفاوت
                    col_widths = [
                        usable_width * 0.15, # ماه
                        usable_width * 0.28, # هزینه (افزایش)
                        usable_width * 0.28, # درآمد (افزایش)
                        usable_width * 0.29  # تفاوت (افزایش)
                    ]
                elif report_type == "person":
                    # دسته‌بندی، تاریخ، حساب، مبلغ، توضیحات
                    col_widths = [
                        usable_width * 0.18, # دسته‌بندی
                        usable_width * 0.12, # تاریخ
                        usable_width * 0.18, # حساب
                        usable_width * 0.15, # مبلغ (افزایش)
                        usable_width * 0.37  # توضیحات (افزایش)
                    ]
                elif report_type == "general":
                    # معیار، مقدار
                    col_widths = [
                        usable_width * 0.40, # معیار
                        usable_width * 0.60  # مقدار (افزایش)
                    ]
                elif report_type == "loan_installments_report": # عرض ستون‌ها برای گزارش اقساط وام [cite: 1]
                    col_widths = [
                        usable_width * 0.15, # شناسه قسط [cite: 1]
                        usable_width * 0.30, # مبلغ قسط (بیشترین پهنا) [cite: 1]
                        usable_width * 0.25, # سررسید [cite: 1]
                        usable_width * 0.30  # وضعیت (بیشترین پهنا) [cite: 1]
                    ]
                else:
                    # به عنوان بازگشت، عرض مساوی
                    num_columns = len(df.columns)
                    col_widths = [usable_width / num_columns] * num_columns

                table._argW = col_widths 
                # --- پایان تنظیم عرض ستون‌ها ---

                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Vazir'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Vazir'),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), # تراز کلی سلول‌ها به راست
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CCCCCC')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ]))
                
                elements.append(table)
                doc.build(elements)
                QMessageBox.information(self, "موفق", f"فایل PDF با موفقیت در {output_path} ذخیره شد!")

            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تولید خروجی: {e}")

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
        self.debts_tab.refresh()
        self.loans_tab.refresh()
        self.dashboard_tab.update_dashboard()

    def load_accounts(self):
        """نسخه جدید: پر کردن کامبوباکس‌ها و دستور آپدیت به تب حساب‌ها"""
        try:
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()

            # به‌روزرسانی کامبوباکس‌های تب تراکنش‌ها (فرم ثبت، انتقال و فیلتر لیست)
            self.transactions_tab.reload_accounts(accounts)

            # به‌روزرسانی کامبوباکس حساب تب بدهی/طلب
            self.debts_tab.reload_accounts(accounts)

            # به‌روزرسانی کامبوباکس حساب فرم ثبت وام
            if hasattr(self, 'loans_tab'):
                self.loans_tab.reload_accounts()

            # آپدیت کردن جدول داخل فایل جداگانه حساب‌ها
            if hasattr(self, 'accounts_tab_widget'):
                self.accounts_tab_widget.load_accounts_table()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده در بارگذاری حساب‌ها: {e}")

    def load_categories(self):
        """بارگذاری دسته‌بندی‌های فرم تراکنش (واگذاری به تب تراکنش‌ها)"""
        self.transactions_tab.reload_categories()

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

    def load_transactions(self):
        """به‌روزرسانی لیست تراکنش‌ها (واگذاری به تب تراکنش‌ها)"""
        self.transactions_tab.refresh()

    def load_persons(self):
        """به‌روزرسانی کامبوباکس‌های اشخاص در تب تراکنش‌ها، بدهی/طلب و گزارش‌ها
        (جدول اشخاص توسط PersonsTab خودش مدیریت می‌شود)"""
        try:
            self.db_manager.execute("SELECT id, name FROM persons ORDER BY name ASC")
            all_persons = self.db_manager.fetchall()

            # به‌روزرسانی کامبوباکس‌های تب تراکنش‌ها (فرم ثبت و جستجو)
            self.transactions_tab.reload_persons(all_persons)

            # به‌روزرسانی کامبوباکس‌های تب بدهی/طلب (فرم ثبت، جستجو و فیلتر)
            self.debts_tab.reload_persons(all_persons)

            # به‌روزرسانی کامبوباکس شخص در بخش گزارش‌ها
            self.load_report_persons()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def check_reminders(self):
        today = jdatetime.date.today().togregorian().strftime("%Y-%m-%d")
        try:
            self.db_manager.execute("SELECT id, amount, due_date FROM debts WHERE is_paid = 0 AND due_date IS NOT NULL AND due_date <= ?", (today,))
            debts = self.db_manager.fetchall()
            for debt in debts:
                QMessageBox.warning(self, "یادآوری", f"بدهی به مبلغ {utils.format_number(debt[1])} ریال تا {utils.gregorian_to_shamsi(debt[2])} سررسید شده!")
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
        if not utils.is_valid_shamsi_date(start_date) or not utils.is_valid_shamsi_date(end_date):
            QMessageBox.warning(self, "خطا", "فرمت تاریخ باید به صورت 1404/02/19 باشد!")
            return
        try:
            start_date_g = utils.shamsi_to_gregorian(start_date)
            if not start_date_g:
                    QMessageBox.warning(self, "خطا", "تاریخ شمسی نامعتبر است!")
                    return
            end_date_g = utils.shamsi_to_gregorian(end_date)
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
                        shamsi_date = utils.gregorian_to_shamsi(result[0])
                        report_table.setItem(row, 0, QTableWidgetItem(shamsi_date))
                        report_table.setItem(row, 1, QTableWidgetItem(result[1] or "-"))
                        if column_count == 6:
                            report_table.setItem(row, 2, QTableWidgetItem(result[2] or "-"))
                            report_table.setItem(row, 3, QTableWidgetItem(result[3]))
                            report_table.setItem(row, 4, QTableWidgetItem(utils.format_number(result[4])))
                            report_table.setItem(row, 5, QTableWidgetItem(result[5] or "-"))
                        else:
                            report_table.setItem(row, 2, QTableWidgetItem(result[2]))
                            report_table.setItem(row, 3, QTableWidgetItem(utils.format_number(result[3])))
                            report_table.setItem(row, 4, QTableWidgetItem(result[4] or "-"))
                else:
                    report_table.setColumnCount(5)
                    report_table.setHorizontalHeaderLabels(["تاریخ", "شخص", "مبلغ کل", "مبلغ پرداخت‌شده", "وضعیت"])
                    report_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                    report_table.setRowCount(len(results))
                    for row, result in enumerate(results):
                        shamsi_date = utils.gregorian_to_shamsi(result[0])
                        report_table.setItem(row, 0, QTableWidgetItem(shamsi_date))
                        report_table.setItem(row, 1, QTableWidgetItem(result[1]))
                        report_table.setItem(row, 2, QTableWidgetItem(utils.format_number(result[2])))
                        report_table.setItem(row, 3, QTableWidgetItem(utils.format_number(result[3])))
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