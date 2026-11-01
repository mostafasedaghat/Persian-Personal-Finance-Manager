# -*- coding: utf-8 -*-
"""
main.py — نرم‌افزار حسابداری شخصی (نسخه حرفه‌ای)
==================================================
نقطه ورود برنامه. این فایل عمداً سبک نگه داشته شده است؛
منطق هر تب در ماژول مستقل خودش در پوشه «ui/tabs» است:

    ui/tabs/dashboard_tab.py      داشبورد
    ui/tabs/accounts_tab.py       حساب‌ها
    ui/tabs/transactions_tab.py   تراکنش‌ها
    ui/tabs/debts_tab.py          بدهی/طلب
    ui/tabs/loans_tab.py          وام‌ها
    ui/tabs/reports_tab.py        گزارش‌ها (مرکز گزارش‌ها)
    ui/tabs/persons_tab.py        اشخاص
    ui/tabs/categories_tab.py     دسته‌بندی‌ها
    ui/tabs/settings_tab.py       تنظیمات

پایگاه داده و مسیرها:
    core/database.py              لایه دسترسی به داده (SQLite)
    core/paths.py                 مسیرهای منابع + ثبت فونت وزیر
    core/utils.py                 ابزارهای مشترک (تاریخ/فرمت عدد)
    core/report_exporter.py       موتور خروجی اکسل/CSV/PDF

دیالوگ‌ها:
    ui/dialogs/login_dialog.py            پنجره ورود
    ui/dialogs/change_password_dialog.py  پنجره تغییر رمز عبور

منابع (فونت/استایل/آیکون):
    assets/fonts/Vazir.ttf
    assets/styles/styles.qss
    assets/icon.ico
"""

import sys

import bcrypt
import jdatetime
import sqlite3
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QScrollArea, QTabWidget,
)

from core import report_exporter, utils
from core.database import DatabaseManager
from core.paths import (
    database_path, ensure_vazir_font, font_path,
    icon_path, register_qt_font, stylesheet_path,
)
from ui.dialogs.login_dialog import LoginDialog
from ui.tabs.accounts_tab import AccountsTab
from ui.tabs.categories_tab import CategoriesTab
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.debts_tab import DebtsTab
from ui.tabs.loans_tab import LoansTab
from ui.tabs.persons_tab import PersonsTab
from ui.tabs.reports_tab import ReportsTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.transactions_tab import TransactionsTab


class FinanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager(database_path())
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
        self.setWindowIcon(QIcon(icon_path()))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        QApplication.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # بارگذاری فونت وزیر (برای Qt و reportlab — از core/paths)
        self._load_fonts()

        # بارگذاری استایل سراسری
        try:
            with open(stylesheet_path(), 'r', encoding='utf-8') as f:
                QApplication.instance().setStyleSheet(f.read())
        except OSError as e:
            QMessageBox.warning(self, "اخطار", f"بارگذاری فایل استایل ممکن نشد: {e}")

        self.init_ui()
        self.load_data()

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_reminders)
        self.reminder_timer.start(86400000)
        self.show()

    def _load_fonts(self):
        """ثبت فونت وزیر برای همه بخش‌های برنامه.

        - Qt (رابط کاربری): بدون نیاز به نصب فونت در ویندوز
        - reportlab (خروجی PDF): رفع باگ «getRegisteredFontNames is not defined»
        """
        # ثبت برای رابط کاربری
        family = register_qt_font()
        if family:
            QApplication.setFont(QFont(family, 10))
        elif not font_path():
            QMessageBox.warning(
                self, "اخطار",
                "فایل فونت Vazir.ttf یافت نشد؛ از فونت پیش‌فرض سیستم استفاده می‌شود.\n"
                "مسیر مورد انتظار: assets/fonts/Vazir.ttf"
            )

        # ثبت برای گزارش‌های PDF (reportlab)
        ensure_vazir_font()

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
                    installment_interval INTEGER DEFAULT 30,
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
                -- شاخص‌های کارایی: مرتب‌سازی بر اساس تاریخ و جستجوهای بازه‌ای
                -- در دیتابیس‌های بزرگ (ده‌ها هزار تراکنش) سرعت داشبورد و
                -- تب تراکنش‌ها را به‌شدت افزایش می‌دهند.
                CREATE INDEX IF NOT EXISTS idx_transactions_date
                    ON transactions(date, id);
                CREATE INDEX IF NOT EXISTS idx_debts_due_date
                    ON debts(due_date);
            """)
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
                    ('تسویه طلب', 'income'),
                    ('تسویه بدهی', 'expense');                                               
                """)
                self.db_manager.commit()
            else:
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
        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.dashboard_tab = DashboardTab(self.db_manager)
        # ساخت تب حساب‌ها (ماژول مستقل)
        self.accounts_tab_widget = AccountsTab(self.db_manager, self)

        # ساخت تب تراکنش‌ها + اتصال سیگنال تغییر داده
        self.transactions_tab = TransactionsTab(self.db_manager, self)
        self.transactions_tab.data_changed.connect(self.on_transactions_data_changed)
        # ساخت تب بدهی/طلب + اتصال سیگنال تغییر داده
        self.debts_tab = DebtsTab(self.db_manager, self)
        self.debts_tab.data_changed.connect(self.on_debts_data_changed)
        # ساخت تب وام‌ها + اتصال سیگنال تغییر داده
        self.loans_tab = LoansTab(self.db_manager, self)
        self.loans_tab.data_changed.connect(self.on_loans_data_changed)
        # ساخت تب گزارش‌ها (مرکز گزارش‌های حرفه‌ای)
        self.reports_tab = ReportsTab(self.db_manager, self)
        # ساخت تب اشخاص و دسته‌بندی‌ها
        self.persons_tab = PersonsTab(self.db_manager, self)
        self.persons_tab.data_changed.connect(self.on_persons_data_changed)
        self.categories_tab = CategoriesTab(self.db_manager, self)
        self.categories_tab.data_changed.connect(self.on_categories_data_changed)
        # ساخت تب تنظیمات (ماژول مستقل — بدون بکاپ Dropbox)
        self.settings_tab = SettingsTab(self.db_manager, self)

        tabs.addTab(self.dashboard_tab, "داشبورد")
        tabs.addTab(self.accounts_tab_widget, "حساب‌ها")
        tabs.addTab(self.transactions_tab, "تراکنش‌ها")
        tabs.addTab(self.debts_tab, "بدهی/طلب")
        tabs.addTab(self.loans_tab, "وام‌ها")
        tabs.addTab(self.reports_tab, "گزارش‌ها")
        tabs.addTab(self.persons_tab, "اشخاص")
        tabs.addTab(self.categories_tab, "دسته بندی‌ها")
        tabs.addTab(self.settings_tab, "تنظیمات")

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

    # ------------------------------------------------------------------ #
    # خروجی گزارش‌ها (پل ارتباطی تب‌ها با موتور مشترک خروجی)
    # ------------------------------------------------------------------ #
    def export_report(self, data, report_type, date_range=None):
        """گرفتن خروجی اکسل/CSV/PDF از نتایج گزارش تب‌های دیگر.

        موتور اصلی در core/report_exporter.py است؛ خروجی‌ها همیشه
        با ردیف «جمع کل» در انتهای گزارش ساخته می‌شوند.
        """
        report_exporter.export_report(self, data, report_type, date_range)

    def load_data(self):
        self.load_accounts()
        self.load_categories()
        self.load_persons()
        self.load_transactions()
        self.debts_tab.refresh()
        self.loans_tab.refresh()
        self.dashboard_tab.update_dashboard()

    def load_accounts(self):
        """پر کردن کامبوباکس‌ها و دستور آپدیت به تب حساب‌ها"""
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
        """به‌روزرسانی کامبوباکس‌های اشخاص در تب تراکنش‌ها و بدهی/طلب
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


def main():
    app = QApplication(sys.argv)
    window = FinanceApp()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
