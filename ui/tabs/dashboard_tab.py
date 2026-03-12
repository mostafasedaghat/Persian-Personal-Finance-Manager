import sqlite3
import jdatetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QScrollArea, 
                             QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

# فرض بر این است که توابع کمکی در مرحله قبل به این مسیر منتقل شده‌اند
# اگر مسیر فایل توابع شما متفاوت است، این ایمپورت را اصلاح کنید
from core.utils import format_number, gregorian_to_shamsi

class DashboardTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # متغیرهای صفحه‌بندی تراکنش‌های اخیر
        self.recent_current_page = 1
        self.recent_per_page = 50
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- 1. هدر (موجودی کل) ---
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

        # --- 2. آمار ماه جاری ---
        stats_widget = QWidget()
        stats_layout = QHBoxLayout()
        stats_widget.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px; margin-top: 10px;")

        self.expenses_value = self._create_stat_column(stats_layout, "جمع هزینه در ماه جاری", "red")
        self.income_value = self._create_stat_column(stats_layout, "جمع درآمد در ماه جاری", "#333")
        self.balance_value = self._create_stat_column(stats_layout, "اختلاف هزینه و درآمد ماه جاری", "#333")
        self.credits_value = self._create_stat_column(stats_layout, "جمع طلب‌های ماه جاری", "#333")
        self.debts_value = self._create_stat_column(stats_layout, "جمع بدهی‌های ماه جاری", "red")
        
        stats_widget.setLayout(stats_layout)
        layout.addWidget(stats_widget)

        # --- 3. بدهی‌ها و طلب‌های مهم ---
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

        # --- 4. تراکنش‌های اخیر ---
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
        
        # دکمه‌های صفحه‌بندی (متصل به توابعی که اضافه خواهید کرد)
        pagination_layout = QHBoxLayout()
        self.btn_next_recent = QPushButton("صفحه بعد >")
        self.btn_prev_recent = QPushButton("< صفحه قبل")
        self.page_label = QLabel(f"صفحه {self.recent_current_page}")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # self.btn_next_recent.clicked.connect(self.next_recent_page)
        # self.btn_prev_recent.clicked.connect(self.prev_recent_page)
        
        pagination_layout.addWidget(self.btn_next_recent)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.btn_prev_recent)
        recent_layout.addLayout(pagination_layout)

        recent_widget.setLayout(recent_layout)
        layout.addWidget(recent_widget)

    def _create_stat_column(self, parent_layout, title, color):
        """متد کمکی برای ساخت ستون‌های آمار ماهانه"""
        column = QVBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        value_label = QLabel("۰ ریال")
        value_label.setStyleSheet(f"font-size: 16px; color: {color};")
        column.addWidget(label)
        column.addWidget(value_label)
        parent_layout.addLayout(column)
        return value_label

    def update_dashboard(self):
        try:
            # 1. به‌روزرسانی موجودی کل
            self.db_manager.execute("SELECT SUM(balance) FROM accounts")
            total_balance = self.db_manager.fetchone()[0] or 0
            self.total_balance_label.setText(f"موجودی کل: {format_number(total_balance)} ریال")

            # 2. بارگذاری بدهی‌ها و طلب‌های مهم
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

            if not isinstance(debts, (list, tuple)):
                debts = []

            self.important_debts_table.setRowCount(len(debts))
            for row, (id, person, amount, paid, due_date, is_paid, account) in enumerate(debts):
                shamsi_due_date = gregorian_to_shamsi(due_date) if due_date else "-"
                self.important_debts_table.setItem(row, 0, QTableWidgetItem(person))
                self.important_debts_table.setItem(row, 1, QTableWidgetItem(format_number(amount)))
                self.important_debts_table.setItem(row, 2, QTableWidgetItem(format_number(paid)))
                self.important_debts_table.setItem(row, 3, QTableWidgetItem(shamsi_due_date))
                self.important_debts_table.setItem(row, 4, QTableWidgetItem("پرداخت شده" if is_paid else "در جریان"))

            # 3. آپدیت آمار ماه جاری
            self.expenses_value.setText(f"{format_number(self.get_current_month_expenses())} ریال")
            self.income_value.setText(f"{format_number(self.get_current_month_income())} ریال")
            self.balance_value.setText(f"{format_number(self.get_current_month_balance())} ریال")
            self.credits_value.setText(f"{format_number(self.get_current_month_credits())} ریال")
            self.debts_value.setText(f"{format_number(self.get_current_month_debts())} ریال")

            # 4. آپدیت تراکنش‌های اخیر
            self.load_recent_transactions()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    # ==========================================
    # توابعی که باید از main.py به اینجا منتقل کنید:
    # ==========================================
    
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
        
    def load_recent_transactions(self):
        try:
            # ۱. محاسبه تعداد کل تراکنش‌ها برای صفحه‌بندی
            self.db_manager.execute("SELECT COUNT(*) FROM transactions")
            total_transactions = self.db_manager.fetchone()[0]
            self.recent_total_pages = (total_transactions + self.recent_per_page - 1) // self.recent_per_page
            
            if self.recent_total_pages == 0:
                self.recent_total_pages = 1

            # ۲. واکشی اطلاعات فقط برای صفحه فعلی
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

            # ۳. پر کردن جدول تراکنش‌های اخیر داشبورد
            self.recent_transactions_table.setRowCount(min(len(recent_transactions), self.recent_per_page))
            for row, (id, date, account, person, category, amount, desc, category_type) in enumerate(recent_transactions):
                shamsi_date = gregorian_to_shamsi(date) if date else "-"
                self.recent_transactions_table.setItem(row, 0, QTableWidgetItem(shamsi_date))
                self.recent_transactions_table.setItem(row, 1, QTableWidgetItem(account or "-"))
                self.recent_transactions_table.setItem(row, 2, QTableWidgetItem(category or "-"))
                self.recent_transactions_table.setItem(row, 3, QTableWidgetItem(format_number(amount)))
                self.recent_transactions_table.setItem(row, 4, QTableWidgetItem(desc or ""))
                self.recent_transactions_table.setItem(row, 5, QTableWidgetItem("درآمد" if category_type == "income" else "هزینه"))

            # ۴. آپدیت وضعیت دکمه‌های صفحه‌بندی
            self.page_label.setText(f"صفحه {self.recent_current_page} از {self.recent_total_pages}")
            self.btn_prev_recent.setEnabled(self.recent_current_page > 1)
            self.btn_next_recent.setEnabled(self.recent_current_page < self.recent_total_pages)

        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده در تراکنش‌های اخیر: {e}")
        
    def next_recent_page(self):
        if self.recent_current_page < getattr(self, 'recent_total_pages', 1):
            self.recent_current_page += 1
            self.load_recent_transactions()
        
    def prev_recent_page(self):
        if self.recent_current_page > 1:
            self.recent_current_page -= 1
            self.load_recent_transactions()
