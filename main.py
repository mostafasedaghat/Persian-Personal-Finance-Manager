import sys
import locale
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget,
                             QVBoxLayout, QPushButton, QLabel, QLineEdit,
                             QMessageBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QFont
import sqlite3
import jdatetime
from datetime import datetime
import os
import bcrypt
import dropbox
from dropbox.exceptions import ApiError

from database import DatabaseManager
from login_dialog import LoginDialog
from change_password_dialog import ChangePasswordDialog
from core import utils
from core import report_exporter
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.accounts_tab import AccountsTab
from ui.tabs.transactions_tab import TransactionsTab
from ui.tabs.debts_tab import DebtsTab
from ui.tabs.loans_tab import LoansTab
from ui.tabs.persons_tab import PersonsTab
from ui.tabs.categories_tab import CategoriesTab
from ui.tabs.reports_tab import ReportsTab

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
        # ساخت تب گزارش‌ها به صورت ماژول مستقل (مرکز گزارش‌های حرفه‌ای)
        self.reports_tab = ReportsTab(self.db_manager, self)
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
        tabs.addTab(self.reports_tab, "گزارش‌ها")
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

    # ------------------------------------------------------------------ #
    # خروجی گزارش‌ها (پل ارتباطی تب‌ها با موتور مشترک خروجی)
    # ------------------------------------------------------------------ #
    def export_report(self, data, report_type, date_range=None):
        """گرفتن خروجی اکسل/CSV/PDF از نتایج گزارش تب‌های دیگر.

        موتور اصلی در core/report_exporter.py است؛ خروجی‌ها همیشه
        با ردیف «جمع کل» در انتهای گزارش ساخته می‌شوند.
        """
        report_exporter.export_report(self, data, report_type, date_range)

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
            
    def closeEvent(self, event):
        self.db_manager.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FinanceApp()
    window.show()
    sys.exit(app.exec())