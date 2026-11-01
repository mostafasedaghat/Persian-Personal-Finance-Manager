# -*- coding: utf-8 -*-
"""تب دسته‌بندی‌ها — ماژول مستقل (جدا شده از main.py)

ساختار صفحه (راست‌به‌چپ):
    ┌────────────────┬───────────────────────────────────┐
    │  ستون راست      │  ستون چپ                          │
    │  ┌────────────┐ │  ┌─────────────────────────────┐  │
    │  │ افزودن     │ │  │ فیلترها (جستجو + نوع)        │  │
    │  │ دسته‌بندی  │ │  ├─────────────────────────────┤  │
    │  └────────────┘ │  │ لیست دسته‌بندی‌ها            │  │
    │                │  │ + تعداد استفاده هر دسته      │  │
    │                │  └─────────────────────────────┘  │
    └────────────────┴───────────────────────────────────┘
    جداکننده دو ستون با QSplitter قابل درگ است.

- حذف دسته‌بندی فقط در صورت عدم استفاده در تراکنش‌ها ممکن است
  (همان منطق قبلی، بدون تغییر).
- پس از هر افزودن/ویرایش/حذف، سیگنال data_changed منتشر می‌شود تا
  main.py فرم و لیست تراکنش‌ها را تازه‌سازی کند.
"""

import sqlite3

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QFrame,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QScrollArea, QSplitter, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect,
)

# ----------------------------------------------------------------------------
# پالت رنگی (هماهنگ با سایر تب‌ها)
# ----------------------------------------------------------------------------
PAGE_BG = "#eef1f6"
CARD_BORDER = "#e5eaf1"
TEXT_DARK = "#1e293b"
TEXT_MUTED = "#64748b"
GREEN = "#16a34a"
RED = "#dc2626"
SLATE = "#475569"
SOFT_GREEN = "#dcfce7"
SOFT_RED = "#fee2e2"
SOFT_SLATE = "#f1f5f9"


class CategoriesTab(QWidget):
    """تب دسته‌بندی‌ها: افزودن، فیلتر، ویرایش و حذف."""

    # پس از هر افزودن/ویرایش/حذف منتشر می‌شود
    data_changed = pyqtSignal()

    # ------------------------------------------------------------------ #
    # استایل کلی تب
    # ------------------------------------------------------------------ #
    STYLESHEET = f"""
    CategoriesTab {{
        background-color: {PAGE_BG};
        font-family: 'Vazir', 'Arial';
    }}

    /* ---------- جداکننده قابل درگ ---------- */
    QSplitter::handle {{
        background-color: #d9e0e9;
    }}
    QSplitter::handle:horizontal {{
        width: 7px;
        border-radius: 3px;
    }}
    QSplitter::handle:horizontal:hover {{
        background-color: {GREEN};
    }}

    /* ---------- کارت‌ها ---------- */
    /* رنگ پایه برای همه لیبل‌ها؛ در ویندوز با تم تاریک، پالت سیستم
       متن لیبل‌های بی‌رنگ را سفید می‌کند — این قانون صریح از آن
       جلوگیری می‌کند. */
    QLabel {{
        color: {TEXT_DARK};
    }}
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

    /* ---------- فرم‌ها ---------- */
    QLineEdit, QComboBox {{
        background-color: #ffffff;
        border: 1px solid #d3dce6;
        border-radius: 9px;
        padding: 7px 10px;
        font-size: 13px;
        color: {TEXT_DARK};
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 2px solid {GREEN};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #ffffff;
        color: {TEXT_DARK};
        selection-background-color: {SOFT_GREEN};
        selection-color: #14532d;
        border: 1px solid #d3dce6;
    }}

    /* ---------- دکمه‌ها ---------- */
    QPushButton#primaryBtn {{
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #16a34a, stop:1 #15803d);
        color: white;
        border: none;
        border-radius: 9px;
        padding: 9px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#primaryBtn:hover {{
        background-color: #15803d;
    }}
    QPushButton#primaryBtn:pressed {{
        background-color: #166534;
    }}
    QPushButton#rowBtn {{
        background-color: #ffffff;
        color: {SLATE};
        border: 1px solid #cbd5e1;
        border-radius: 7px;
        padding: 5px 12px;
        font-size: 11px;
        font-weight: bold;
    }}
    QPushButton#rowBtn:hover {{
        background-color: {SOFT_SLATE};
        border-color: {SLATE};
    }}
    QPushButton#rowBtnRed {{
        background-color: {SOFT_RED};
        color: #991b1b;
        border: 1px solid #fca5a5;
        border-radius: 7px;
        padding: 5px 12px;
        font-size: 11px;
        font-weight: bold;
    }}
    QPushButton#rowBtnRed:hover {{
        background-color: #fecaca;
        border-color: {RED};
    }}

    /* ---------- جدول ---------- */
    QTableWidget#categoriesTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#categoriesTable QHeaderView::section {{
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

    # استایل مشترک دیالوگ‌ها (رنگ صریح برای همه ویجت‌های متنی)
    DIALOG_STYLE = f"""
        QDialog {{
            background-color: {PAGE_BG};
            font-family: 'Vazir', 'Arial';
        }}
        QLabel {{
            color: {TEXT_DARK};
            font-size: 13px;
            font-weight: bold;
        }}
        QLineEdit, QComboBox {{
            background-color: #ffffff;
            border: 1px solid #d3dce6;
            border-radius: 9px;
            padding: 7px 10px;
            font-size: 13px;
            color: {TEXT_DARK};
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 2px solid {GREEN};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 26px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #ffffff;
            color: {TEXT_DARK};
            selection-background-color: {SOFT_GREEN};
            selection-color: #14532d;
            border: 1px solid #d3dce6;
        }}
        QPushButton#primaryBtn {{
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
            color: white;
            border: none;
            border-radius: 9px;
            padding: 9px 20px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#primaryBtn:hover {{
            background-color: #15803d;
        }}
    """

    # ================================================================== #
    # ساختار کلی
    # ================================================================== #
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(self.STYLESHEET)

        self.setup_ui()
        self.load_categories_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(0)

        # در RTL ویجت اول سمت «راست» قرار می‌گیرد
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(7)
        splitter.addWidget(self._build_forms_panel())   # سمت راست
        splitter.addWidget(self._build_list_panel())    # سمت چپ
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 820])

        layout.addWidget(splitter)

    # ------------------------------------------------------------------ #
    # پنل راست: فرم افزودن دسته‌بندی
    # ------------------------------------------------------------------ #
    def _build_forms_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(300)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QWidget#formsContainer { background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; }"
            "QScrollBar::handle:vertical { background: #cbd5e1;"
            " border-radius: 4px; min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        container = QWidget()
        container.setObjectName("formsContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(16)

        container_layout.addWidget(self._build_entry_card())
        container_layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    def _build_entry_card(self):
        """کارت افزودن دسته‌بندی جدید"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🏷️")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("افزودن دسته‌بندی جدید")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.category_name_input = QLineEdit()
        self.category_name_input.setPlaceholderText(
            "نام دسته‌بندی (مثلاً: خوار و بار)")
        self.category_type = QComboBox()
        self.category_type.addItems(["درآمد", "هزینه"])

        form.addRow("نام دسته‌بندی:", self.category_name_input)
        form.addRow("نوع:", self.category_type)
        lay.addLayout(form)

        add_category_btn = QPushButton("✅ افزودن دسته‌بندی")
        add_category_btn.setObjectName("primaryBtn")
        add_category_btn.setMinimumHeight(42)
        add_category_btn.clicked.connect(self.add_category)
        lay.addWidget(add_category_btn)

        hint = QLabel(
            "دسته‌بندی‌های افزوده‌شده در فرم ثبت تراکنش قابل "
            "انتخاب خواهند بود. حذف دسته‌بندیِ استفاده‌شده در "
            "تراکنش‌ها ممکن نیست.")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; font-weight: normal;")
        lay.addWidget(hint)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # پنل چپ: فیلترها + لیست دسته‌بندی‌ها
    # ------------------------------------------------------------------ #
    def _build_list_panel(self):
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # سربرگ
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("🗂️")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("لیست دسته‌بندی‌ها")
        title.setObjectName("panelTitle")
        self.categories_count_chip = QLabel("0 مورد")
        self.categories_count_chip.setObjectName("chip")
        self.categories_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.categories_count_chip)
        lay.addLayout(header_row)

        # ---- نوار فیلترها ----
        filters_card = QFrame()
        filters_card.setStyleSheet(
            f"QFrame {{ background-color: {SOFT_SLATE};"
            f" border-radius: 10px; }}")
        filters_lay = QHBoxLayout(filters_card)
        filters_lay.setContentsMargins(12, 10, 12, 10)
        filters_lay.setSpacing(10)

        search_icon = QLabel("🔍")
        self.category_search_input = QLineEdit()
        self.category_search_input.setPlaceholderText(
            "جستجو بر اساس نام دسته‌بندی (حداقل ۲ حرف)")
        self.category_search_input.textChanged.connect(
            self.filter_categories_table)

        self.category_filter_dropdown = QComboBox()
        self.category_filter_dropdown.addItem("نمایش همه", "all")
        self.category_filter_dropdown.addItem(
            "فقط دسته‌بندی هزینه‌ها", "expense")
        self.category_filter_dropdown.addItem(
            "فقط دسته‌بندی درآمدها", "income")
        self.category_filter_dropdown.currentIndexChanged.connect(
            lambda _: self.apply_category_type_filter())

        clear_btn = QPushButton("✕")
        clear_btn.setObjectName("rowBtn")
        clear_btn.setToolTip("پاک کردن فیلترها")
        clear_btn.clicked.connect(self.clear_filters)

        filters_lay.addWidget(search_icon)
        filters_lay.addWidget(self.category_search_input, 3)
        filters_lay.addWidget(self.category_filter_dropdown, 2)
        filters_lay.addWidget(clear_btn)
        lay.addWidget(filters_card)

        # ---- جدول دسته‌بندی‌ها ----
        # نکته RTL: ستون «عملیات» عمداً اولین ستون (سمت راست) است.
        self.categories_table = QTableWidget()
        self.categories_table.setObjectName("categoriesTable")
        self.categories_table.setColumnCount(5)
        self.categories_table.setHorizontalHeaderLabels(
            ["عملیات", "نوع", "نام دسته‌بندی", "تعداد استفاده", "شناسه"])
        self._style_table(self.categories_table, stretch_column=2)
        self.categories_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)
        self.categories_table.setColumnWidth(0, 176)
        lay.addWidget(self.categories_table, 1)

        # حالت خالی
        self.categories_empty_label = QLabel(
            "🏷️ دسته‌بندی‌ای برای نمایش وجود ندارد")
        self.categories_empty_label.setObjectName("emptyLabel")
        self.categories_empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter)
        self.categories_empty_label.setVisible(False)
        lay.addWidget(self.categories_empty_label, 1)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # ابزارهای مشترک
    # ------------------------------------------------------------------ #
    def _style_table(self, table, stretch_column):
        """تنظیمات ظاهری و رفتاری مشترک جدول‌ها."""
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

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

        horizontal_header = table.horizontalHeader()
        horizontal_header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        horizontal_header.setSectionResizeMode(
            stretch_column, QHeaderView.ResizeMode.Stretch)
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setMinimumSectionSize(56)
        horizontal_header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter)

    def _apply_shadow(self, widget, blur=18, alpha=28, dy=3):
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(15, 40, 30, alpha))
        effect.setOffset(0, dy)
        widget.setGraphicsEffect(effect)

    def refresh(self):
        """تازه‌سازی لیست دسته‌بندی‌ها."""
        self.load_categories_table()

    def clear_filters(self):
        self.category_search_input.clear()
        self.category_filter_dropdown.setCurrentIndex(0)
        self.apply_category_type_filter()

    # ------------------------------------------------------------------ #
    # بارگذاری و فیلتر لیست
    # ------------------------------------------------------------------ #
    def filter_categories_table(self, _search_text=None):
        # جستجوی متنی + اعمال فیلتر نوع به‌صورت هم‌زمان
        self.apply_category_type_filter()

    def apply_category_type_filter(self):
        """بارگذاری جدول دسته‌بندی‌ها با فیلترهای فعال."""
        try:
            filter_type = self.category_filter_dropdown.currentData()
            search_text = self.category_search_input.text().strip()

            query = """
                SELECT c.id, c.name, c.type,
                    (SELECT COUNT(*) FROM transactions t
                     WHERE t.category_id = c.id)
                FROM categories c
            """
            params = []
            where_clauses = []

            if filter_type == "expense":
                where_clauses.append("c.type = 'expense'")
            elif filter_type == "income":
                where_clauses.append("c.type = 'income'")

            if len(search_text) >= 2:
                where_clauses.append("c.name LIKE ?")
                params.append(f"%{search_text}%")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += " ORDER BY c.name ASC"

            self.db_manager.execute(query, tuple(params))
            filtered_categories = self.db_manager.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(
                self, "خطا",
                f"خطای پایگاه داده هنگام فیلتر دسته‌بندی‌ها: {e}")
            return

        # تعداد کل (برای چیپ سربرگ) — بدون فیلتر
        try:
            self.db_manager.execute("SELECT COUNT(*) FROM categories")
            total = self.db_manager.fetchone()[0]
        except sqlite3.Error:
            total = len(filtered_categories)
        self.categories_count_chip.setText(f"{total} مورد")

        # حالت خالی
        if not filtered_categories:
            self.categories_table.setRowCount(0)
            self.categories_table.setVisible(False)
            self.categories_empty_label.setVisible(True)
        else:
            self.categories_table.setVisible(True)
            self.categories_empty_label.setVisible(False)

            self.categories_table.setRowCount(len(filtered_categories))
            for row, (cat_id, name, category_type, usage_count) in \
                    enumerate(filtered_categories):
                is_income = (category_type == "income")

                # ---- عملیات (ویرایش + حذف) ----
                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                edit_btn = QPushButton("ویرایش")
                edit_btn.setObjectName("rowBtn")
                edit_btn.clicked.connect(
                    lambda checked, c_id=cat_id: self.edit_category(c_id))

                delete_btn = QPushButton("حذف")
                delete_btn.setObjectName("rowBtnRed")
                delete_btn.clicked.connect(
                    lambda checked, c_id=cat_id: self.delete_category(c_id))

                actions_layout.addWidget(edit_btn)
                actions_layout.addWidget(delete_btn)
                self.categories_table.setCellWidget(row, 0, actions)

                # ---- نوع ----
                type_item = QTableWidgetItem(
                    "درآمد" if is_income else "هزینه")
                type_font = type_item.font()
                type_font.setBold(True)
                type_item.setFont(type_font)
                type_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter)
                type_item.setForeground(
                    QColor(GREEN if is_income else RED))
                self.categories_table.setItem(row, 1, type_item)

                # ---- نام ----
                name_item = QTableWidgetItem(name)
                name_font = name_item.font()
                name_font.setBold(True)
                name_item.setFont(name_font)
                name_item.setForeground(QColor(TEXT_DARK))
                self.categories_table.setItem(row, 2, name_item)

                # ---- تعداد استفاده ----
                if usage_count:
                    usage_text = f"{usage_count} تراکنش"
                    usage_color = QColor(SLATE)
                else:
                    usage_text = "بدون استفاده"
                    usage_color = QColor(TEXT_MUTED)
                usage_item = QTableWidgetItem(usage_text)
                usage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                usage_item.setForeground(usage_color)
                self.categories_table.setItem(row, 3, usage_item)

                # ---- شناسه ----
                id_item = QTableWidgetItem(str(cat_id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setForeground(QColor(TEXT_MUTED))
                self.categories_table.setItem(row, 4, id_item)

    def load_categories_table(self):
        """بارگذاری جدول با فیلترهای فعال (نقطه ورود اصلی)."""
        self.apply_category_type_filter()

    # ------------------------------------------------------------------ #
    # افزودن / ویرایش / حذف
    # ------------------------------------------------------------------ #
    def add_category(self):
        name = self.category_name_input.text().strip()
        category_type = \
            "income" if self.category_type.currentText() == "درآمد" \
            else "expense"
        if not name:
            QMessageBox.warning(
                self, "خطا", "نام دسته‌بندی نمی‌تواند خالی باشد!")
            return
        try:
            self.db_manager.execute(
                "INSERT INTO categories (name, type) VALUES (?, ?)",
                (name, category_type))
            self.db_manager.commit()
            self.category_name_input.clear()
            self.load_categories_table()
            self.data_changed.emit()
            QMessageBox.information(
                self, "موفق", "دسته‌بندی با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_category(self, category_id):
        try:
            self.db_manager.execute(
                "SELECT name, type FROM categories WHERE id = ?",
                (category_id,))
            category = self.db_manager.fetchone()
            if not category:
                QMessageBox.warning(self, "خطا", "دسته‌بندی یافت نشد!")
                return
            name, category_type = category
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش دسته‌بندی")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setStyleSheet(self.DIALOG_STYLE)

        layout = QFormLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)

        edit_name = QLineEdit(name)
        edit_type = QComboBox()
        edit_type.addItems(["درآمد", "هزینه"])
        edit_type.setCurrentText(
            "درآمد" if category_type == "income" else "هزینه")

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(42)
        save_btn.clicked.connect(
            lambda: self.save_category(
                category_id, edit_name.text(),
                edit_type.currentText(), dialog))

        layout.addRow("نام دسته‌بندی:", edit_name)
        layout.addRow("نوع:", edit_type)
        layout.addRow(save_btn)
        dialog.exec()

    def save_category(self, category_id, name, type_text, dialog):
        if not name.strip():
            QMessageBox.warning(
                dialog, "خطا", "نام دسته‌بندی نمی‌تواند خالی باشد!")
            return
        category_type = "income" if type_text == "درآمد" else "expense"
        try:
            self.db_manager.execute(
                "UPDATE categories SET name = ?, type = ? WHERE id = ?",
                (name.strip(), category_type, category_id))
            self.db_manager.commit()
            self.load_categories_table()
            self.data_changed.emit()
            dialog.accept()
            QMessageBox.information(
                self, "موفق", "دسته‌بندی با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def delete_category(self, category_id):
        try:
            # بررسی استفاده از دسته‌بندی در تراکنش‌ها
            self.db_manager.execute(
                "SELECT COUNT(*) FROM transactions "
                "WHERE category_id = ?", (category_id,))
            if self.db_manager.fetchone()[0] > 0:
                QMessageBox.warning(
                    self, "خطا",
                    "این دسته‌بندی در تراکنش‌ها استفاده شده و "
                    "نمی‌تواند حذف شود!")
                return

            # تأیید حذف از کاربر
            reply = QMessageBox.question(
                self, "تأیید حذف",
                "آیا مطمئن هستید که می‌خواهید این دسته‌بندی را "
                "حذف کنید؟",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

            self.db_manager.execute(
                "DELETE FROM categories WHERE id = ?", (category_id,))
            self.db_manager.commit()
            self.load_categories_table()
            self.data_changed.emit()
            QMessageBox.information(
                self, "موفق", "دسته‌بندی با موفقیت حذف شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
