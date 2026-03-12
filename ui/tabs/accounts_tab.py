import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QMessageBox, QDialog
)
from PyQt6.QtCore import Qt

from ui.components.custom_widgets import NumberInput
from core.utils import format_number

class AccountsTab(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent # ارجاع به کلاس اصلی برای ارتباط با سایر تب‌ها

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # --- فرم افزودن حساب ---
        form_layout = QFormLayout()
        self.account_name_input = QLineEdit()
        self.account_balance_input = NumberInput()
        
        add_account_btn = QPushButton("افزودن حساب")
        add_account_btn.clicked.connect(self.add_account)
        
        form_layout.addRow("نام حساب:", self.account_name_input)
        form_layout.addRow("موجودی اولیه:", self.account_balance_input)
        form_layout.addRow(add_account_btn)
        
        # --- جدول نمایش حساب‌ها ---
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(4)
        self.accounts_table.setHorizontalHeaderLabels(["شناسه", "نام حساب", "موجودی", "اقدامات"])
        self.accounts_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.accounts_table.setColumnWidth(0, 50)
        self.accounts_table.setColumnWidth(1, 200)
        self.accounts_table.setColumnWidth(2, 150)
        self.accounts_table.setColumnWidth(3, 80)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.accounts_table)

    def load_accounts_table(self):
        """فقط جدول حساب‌ها را به‌روز می‌کند (توسط main.py فراخوانی می‌شود)"""
        try:
            self.db_manager.execute("SELECT id, name, balance FROM accounts")
            accounts = self.db_manager.fetchall()
            self.accounts_table.setRowCount(len(accounts))
            
            for row, (id, name, balance) in enumerate(accounts):
                self.accounts_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.accounts_table.setItem(row, 1, QTableWidgetItem(name))
                self.accounts_table.setItem(row, 2, QTableWidgetItem(format_number(balance)))
                
                edit_btn = QPushButton("ویرایش")
                edit_btn.clicked.connect(lambda checked, acc_id=id: self.edit_account(acc_id))
                self.accounts_table.setCellWidget(row, 3, edit_btn)
                
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def add_account(self):
        """افزودن حساب جدید به دیتابیس"""
        name = self.account_name_input.text().strip()
        balance = self.account_balance_input.get_raw_value() if self.account_balance_input.text() else 0
        
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب نمی‌تواند خالی باشد!")
            return
            
        try:
            self.db_manager.execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (name, balance))
            self.db_manager.commit()
            
            self.account_name_input.clear()
            self.account_balance_input.clear()
            
            # فراخوانی تابع اصلی برای آپدیت همزمان جدول تب فعلی و کامبوباکس‌های سایر تب‌ها
            if hasattr(self.parent_window, 'load_accounts'):
                self.parent_window.load_accounts()
                
            QMessageBox.information(self, "موفق", "حساب با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_account(self, account_id):
        """باز کردن دیالوگ ویرایش نام حساب"""
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
            save_btn.clicked.connect(lambda: self.save_account(account_id, edit_name.text().strip(), dialog))
            
            layout.addRow("نام حساب:", edit_name)
            layout.addRow(save_btn)
            dialog.setLayout(layout)
            dialog.exec()
            
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def save_account(self, account_id, name, dialog):
        """ذخیره تغییرات نام حساب"""
        if not name:
            QMessageBox.warning(self, "خطا", "نام حساب نمی‌تواند خالی باشد!")
            return
            
        try:
            self.db_manager.execute("SELECT id FROM accounts WHERE name = ? AND id != ?", (name, account_id))
            if self.db_manager.fetchone():
                QMessageBox.warning(self, "خطا", "حسابی با این نام قبلاً وجود دارد!")
                return
                
            self.db_manager.execute("UPDATE accounts SET name = ? WHERE id = ?", (name, account_id))
            self.db_manager.commit()
            
            # فراخوانی آپدیت سراسری
            if hasattr(self.parent_window, 'load_accounts'):
                self.parent_window.load_accounts()
                
            dialog.accept()
            QMessageBox.information(self, "موفق", "نام حساب با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
