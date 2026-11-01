# -*- coding: utf-8 -*-
"""تب اشخاص — ماژول مستقل (جدا شده از main.py)

ساختار صفحه (راست‌به‌چپ):
    ┌────────────────┬───────────────────────────────────┐
    │  ستون راست      │  ستون چپ                          │
    │  ┌────────────┐ │  ┌─────────────────────────────┐  │
    │  │ افزودن شخص │ │  │ خلاصه (۳ کارت)               │  │
    │  └────────────┘ │  ├─────────────────────────────┤  │
    │                │  │ جستجو                        │  │
    │                │  ├─────────────────────────────┤  │
    │                │  │ لیست اشخاص + وضعیت هر شخص    │  │
    │                │  └─────────────────────────────┘  │
    └────────────────┴───────────────────────────────────┘
    جداکننده دو ستون با QSplitter قابل درگ است.

- برای هر شخص، خالص وضعیت بدهی/طلب (بدهی‌ها و طلب‌های باز)
  و تعداد تراکنش‌های او نمایش داده می‌شود.
- پس از هر افزودن/ویرایش، سیگنال data_changed منتشر می‌شود تا
  main.py کامبوباکس‌های اشخاص در سایر تب‌ها را تازه‌سازی کند.
"""

import sqlite3

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QFrame,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QScrollArea, QSplitter, QHeaderView,
    QAbstractItemView, QGraphicsDropShadowEffect,
)

from core.utils import format_amount

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


class PersonsTab(QWidget):
    """تب اشخاص: افزودن، جستجو، ویرایش و مشاهده وضعیت هر شخص."""

    # پس از هر افزودن/ویرایش شخص منتشر می‌شود
    data_changed = pyqtSignal()

    # ------------------------------------------------------------------ #
    # استایل کلی تب
    # ------------------------------------------------------------------ #
    STYLESHEET = f"""
    PersonsTab {{
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
    QLineEdit {{
        background-color: #ffffff;
        border: 1px solid #d3dce6;
        border-radius: 9px;
        padding: 7px 10px;
        font-size: 13px;
        color: {TEXT_DARK};
    }}
    QLineEdit:focus {{
        border: 2px solid {GREEN};
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

    /* ---------- جدول ---------- */
    QTableWidget#personsTable {{
        background-color: #ffffff;
        alternate-background-color: #f8fafc;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dcfce7;
        selection-color: #14532d;
        font-size: 13px;
    }}
    QTableWidget#personsTable QHeaderView::section {{
        background-color: #f1f5f9;
        color: #334155;
        font-weight: bold;
        font-size: 12px;
        padding: 7px 6px;
        border: none;
        border-bottom: 2px solid #e2e8f0;
    }}

    /* ---------- کارت‌های خلاصه ---------- */
    QFrame#summaryChip {{
        border-radius: 12px;
        border: 1px solid {CARD_BORDER};
    }}
    QLabel#summaryTitle {{
        color: {TEXT_MUTED};
        font-size: 11px;
        font-weight: bold;
    }}
    QLabel#summaryValue {{
        font-size: 14px;
        font-weight: bold;
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
        QLineEdit {{
            background-color: #ffffff;
            border: 1px solid #d3dce6;
            border-radius: 9px;
            padding: 7px 10px;
            font-size: 13px;
            color: {TEXT_DARK};
        }}
        QLineEdit:focus {{
            border: 2px solid {GREEN};
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
        self.load_persons()

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
    # پنل راست: فرم افزودن شخص
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
        """کارت افزودن شخص جدید"""
        card = QFrame()
        card.setObjectName("panelCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon = QLabel("👤")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("افزودن شخص جدید")
        title.setObjectName("panelTitle")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        lay.addLayout(header_row)

        form = QFormLayout()
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.person_name_input = QLineEdit()
        self.person_name_input.setPlaceholderText(
            "نام شخص (مثلاً: علی رضایی)")
        self.person_name_input.returnPressed.connect(self.add_person)
        form.addRow("نام شخص:", self.person_name_input)
        lay.addLayout(form)

        add_person_btn = QPushButton("✅ افزودن شخص")
        add_person_btn.setObjectName("primaryBtn")
        add_person_btn.setMinimumHeight(42)
        add_person_btn.clicked.connect(self.add_person)
        lay.addWidget(add_person_btn)

        hint = QLabel(
            "اشخاص افزوده‌شده در فرم‌های تراکنش و بدهی/طلب "
            "قابل انتخاب خواهند بود.")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; font-weight: normal;")
        lay.addWidget(hint)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    # ------------------------------------------------------------------ #
    # پنل چپ: خلاصه + جستجو + لیست اشخاص
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
        icon = QLabel("👥")
        icon.setObjectName("panelIcon")
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"background-color: {SOFT_GREEN}; font-size: 15px;")
        title = QLabel("لیست اشخاص")
        title.setObjectName("panelTitle")
        self.persons_count_chip = QLabel("0 مورد")
        self.persons_count_chip.setObjectName("chip")
        self.persons_count_chip.setStyleSheet(
            f"background-color: {SOFT_SLATE}; color: {SLATE};")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.persons_count_chip)
        lay.addLayout(header_row)

        # ---- خلاصه وضعیت کلی ----
        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        summary_row.addWidget(self._build_summary_chip(
            "👥", "تعداد کل اشخاص", SOFT_SLATE, SLATE, "summary_total"), 1)
        summary_row.addWidget(self._build_summary_chip(
            "🧾", "دارای تراکنش", SOFT_GREEN, GREEN,
            "summary_with_tx"), 1)
        summary_row.addWidget(self._build_summary_chip(
            "💳", "دارای بدهی/طلب باز", SOFT_RED, RED,
            "summary_with_debt"), 1)
        lay.addLayout(summary_row)

        # ---- جستجو ----
        search_card = QFrame()
        search_card.setStyleSheet(
            f"QFrame {{ background-color: {SOFT_SLATE};"
            f" border-radius: 10px; }}")
        search_lay = QHBoxLayout(search_card)
        search_lay.setContentsMargins(12, 10, 12, 10)
        search_lay.setSpacing(8)

        search_icon = QLabel("🔍")
        self.person_search_input = QLineEdit()
        self.person_search_input.setPlaceholderText(
            "جستجو بر اساس نام شخص...")
        self.person_search_input.textChanged.connect(
            self.filter_persons_table)
        clear_search_btn = QPushButton("✕")
        clear_search_btn.setObjectName("rowBtn")
        clear_search_btn.setToolTip("پاک کردن جستجو")
        clear_search_btn.clicked.connect(self.person_search_input.clear)

        search_lay.addWidget(search_icon)
        search_lay.addWidget(self.person_search_input, 1)
        search_lay.addWidget(clear_search_btn)
        lay.addWidget(search_card)

        # ---- جدول اشخاص ----
        # نکته RTL: ستون «عملیات» عمداً اولین ستون (سمت راست) است.
        self.persons_table = QTableWidget()
        self.persons_table.setObjectName("personsTable")
        self.persons_table.setColumnCount(5)
        self.persons_table.setHorizontalHeaderLabels(
            ["عملیات", "نام شخص", "وضعیت بدهی/طلب", "تراکنش‌ها", "شناسه"])
        self._style_table(self.persons_table, stretch_column=1)
        self.persons_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed)
        self.persons_table.setColumnWidth(0, 96)
        lay.addWidget(self.persons_table, 1)

        # حالت خالی
        self.persons_empty_label = QLabel(
            "👤 شخصی برای نمایش وجود ندارد")
        self.persons_empty_label.setObjectName("emptyLabel")
        self.persons_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.persons_empty_label.setVisible(False)
        lay.addWidget(self.persons_empty_label, 1)

        self._apply_shadow(card, blur=20, alpha=30, dy=4)
        return card

    def _build_summary_chip(self, icon_text, title, soft_bg, value_color,
                            attr_prefix):
        """ساخت یک کارت خلاصه کوچک (آیکون + عنوان + مقدار)."""
        chip = QFrame()
        chip.setObjectName("summaryChip")
        chip.setStyleSheet(
            f"QFrame#summaryChip {{ background-color: {soft_bg}; }}")

        row = QHBoxLayout(chip)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        icon = QLabel(icon_text)
        icon.setFixedSize(30, 30)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "background-color: rgba(255,255,255,0.65);"
            f"border-radius: 9px; font-size: 14px;")

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")
        value_label = QLabel("0")
        value_label.setObjectName("summaryValue")
        value_label.setStyleSheet(f"color: {value_color};")
        text_box.addWidget(title_label)
        text_box.addWidget(value_label)

        row.addWidget(icon)
        row.addLayout(text_box, 1)

        setattr(self, f"{attr_prefix}_value", value_label)
        return chip

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
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(blur)
        effect.setColor(QColor(15, 40, 30, alpha))
        effect.setOffset(0, dy)
        widget.setGraphicsEffect(effect)

    def refresh(self):
        """تازه‌سازی لیست اشخاص."""
        self.load_persons()

    # ------------------------------------------------------------------ #
    # بارگذاری و فیلتر لیست
    # ------------------------------------------------------------------ #
    def filter_persons_table(self):
        """بارگذاری جدول اشخاص با جستجوی فعال."""
        search_text = self.person_search_input.text().strip()
        try:
            query = """
                SELECT p.id, p.name,
                    (SELECT COUNT(*)
                     FROM transactions t
                     WHERE t.person_id = p.id),
                    COALESCE((SELECT SUM(d.amount - d.paid_amount)
                              FROM debts d
                              WHERE d.person_id = p.id
                                AND d.is_paid = 0
                                AND d.is_credit = 0), 0)
                  - COALESCE((SELECT SUM(d.amount - d.paid_amount)
                              FROM debts d
                              WHERE d.person_id = p.id
                                AND d.is_paid = 0
                                AND d.is_credit = 1), 0)
                FROM persons p
            """
            params = []
            if search_text:
                query += " WHERE p.name LIKE ?"
                params.append(f"%{search_text}%")
            query += " ORDER BY p.name ASC"

            self.db_manager.execute(query, tuple(params))
            persons = self.db_manager.fetchall()
        except sqlite3.Error as e:
            QMessageBox.critical(
                self, "خطا", f"خطای پایگاه داده هنگام فیلتر اشخاص: {e}")
            return

        # حالت خالی
        if not persons:
            self.persons_table.setRowCount(0)
            self.persons_table.setVisible(False)
            self.persons_empty_label.setVisible(True)
        else:
            self.persons_table.setVisible(True)
            self.persons_empty_label.setVisible(False)

            self.persons_table.setRowCount(len(persons))
            for row, (p_id, name, tx_count, net_debt) in \
                    enumerate(persons):
                # ---- عملیات (ویرایش) ----
                actions = QWidget()
                actions_layout = QHBoxLayout(actions)
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)
                edit_btn = QPushButton("ویرایش")
                edit_btn.setObjectName("rowBtn")
                edit_btn.clicked.connect(
                    lambda checked, person_id=p_id:
                        self.edit_person(person_id))
                actions_layout.addWidget(edit_btn)
                self.persons_table.setCellWidget(row, 0, actions)

                # ---- نام ----
                name_item = QTableWidgetItem(name)
                name_font = name_item.font()
                name_font.setBold(True)
                name_item.setFont(name_font)
                name_item.setForeground(QColor(TEXT_DARK))
                self.persons_table.setItem(row, 1, name_item)

                # ---- وضعیت بدهی/طلب ----
                if net_debt > 0:
                    status_text = f"بدهی من: {format_amount(net_debt)} ریال"
                    status_color = QColor(RED)
                elif net_debt < 0:
                    status_text = \
                        f"طلب من: {format_amount(-net_debt)} ریال"
                    status_color = QColor(GREEN)
                else:
                    status_text = "تسویه"
                    status_color = QColor(TEXT_MUTED)
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setForeground(status_color)
                self.persons_table.setItem(row, 2, status_item)

                # ---- تعداد تراکنش‌ها ----
                tx_item = QTableWidgetItem(
                    f"{tx_count} تراکنش" if tx_count else "—")
                tx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                tx_item.setForeground(QColor(TEXT_MUTED))
                self.persons_table.setItem(row, 3, tx_item)

                # ---- شناسه ----
                id_item = QTableWidgetItem(str(p_id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setForeground(QColor(TEXT_MUTED))
                self.persons_table.setItem(row, 4, id_item)

    def load_persons(self):
        """بارگذاری جدول + به‌روزرسانی کارت‌های خلاصه."""
        self.filter_persons_table()
        self._update_summary()

    def _update_summary(self):
        """به‌روزرسانی کارت‌های خلاصه."""
        try:
            self.db_manager.execute("SELECT COUNT(*) FROM persons")
            total = self.db_manager.fetchone()[0]

            self.db_manager.execute(
                "SELECT COUNT(DISTINCT person_id) FROM transactions "
                "WHERE person_id IS NOT NULL")
            with_tx = self.db_manager.fetchone()[0]

            self.db_manager.execute(
                "SELECT COUNT(DISTINCT person_id) FROM debts "
                "WHERE person_id IS NOT NULL AND is_paid = 0")
            with_debt = self.db_manager.fetchone()[0]
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        self.summary_total_value.setText(f"{total} نفر")
        self.summary_with_tx_value.setText(f"{with_tx} نفر")
        self.summary_with_debt_value.setText(f"{with_debt} نفر")
        self.persons_count_chip.setText(f"{total} مورد")

    # ------------------------------------------------------------------ #
    # افزودن / ویرایش شخص
    # ------------------------------------------------------------------ #
    def add_person(self):
        name = self.person_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام شخص نمی‌تواند خالی باشد!")
            return
        try:
            self.db_manager.execute(
                "INSERT INTO persons (name) VALUES (?)", (name,))
            self.db_manager.commit()
            self.person_name_input.clear()
            self.load_persons()
            self.data_changed.emit()
            QMessageBox.information(self, "موفق", "شخص با موفقیت افزوده شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")

    def edit_person(self, person_id):
        try:
            self.db_manager.execute(
                "SELECT name FROM persons WHERE id = ?", (person_id,))
            person = self.db_manager.fetchone()
            if not person:
                QMessageBox.warning(self, "خطا", "شخص یافت نشد!")
                return
            name = person[0]
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("ویرایش شخص")
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dialog.setStyleSheet(self.DIALOG_STYLE)

        layout = QFormLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)

        edit_name = QLineEdit(name)

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(42)
        save_btn.clicked.connect(
            lambda: self.save_person(person_id, edit_name.text(), dialog))

        layout.addRow("نام شخص:", edit_name)
        layout.addRow(save_btn)
        dialog.exec()

    def save_person(self, person_id, name, dialog):
        if not name.strip():
            QMessageBox.warning(
                dialog, "خطا", "نام شخص نمی‌تواند خالی باشد!")
            return
        try:
            self.db_manager.execute(
                "UPDATE persons SET name = ? WHERE id = ?",
                (name.strip(), person_id))
            self.db_manager.commit()
            self.load_persons()
            self.data_changed.emit()
            dialog.accept()
            QMessageBox.information(
                self, "موفق", "نام شخص با موفقیت ویرایش شد!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "خطا", f"خطای پایگاه داده: {e}")
