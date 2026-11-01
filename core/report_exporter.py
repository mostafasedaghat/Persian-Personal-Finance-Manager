# -*- coding: utf-8 -*-
"""
core/report_exporter.py
=======================
موتور مشترک خروجی گزارش‌ها (اکسل / CSV / PDF)

هدف‌ها:
    1) «ردیف جمع کل» خودکار: در انتهای همه گزارش‌های عددی، آخرین
       ردیف فایل‌های xlsx/csv/pdf جمع ستون‌های مبلغ را نشان می‌دهد
       تا کاربر مجبور به جمع‌زدن دستی در فایل خروجی نباشد.
    2) استایل حرفه‌ای:
         * اکسل: سربرگ سبز پررنگ، فریز ردیف عنوان، عرض ستون هوشمند،
           فرمت عددی #,##0 برای ستون‌های مبلغ، ردیف جمع کل هایلایت‌شده
           و راست‌به‌چپ بودن شیت.
         * PDF: عنوان گزارش + بازه گزارش + زمان تولید بالای جدول،
           سربرگ تکرارشونده در هر صفحه، ردیف‌های یک‌درمیان و ردیف
           جمع کل متمایز.
         * CSV: با BOM (utf-8-sig) برای باز شدن درست در اکسل.
    3) یک نقطه مرکزی: هم تب گزارش‌ها و هم خروجی تب تراکنش‌ها/
       بدهی‌ها/وام‌ها از همین موتور استفاده می‌کنند.

هر «نوع گزارش» در دیکشنری SPECS تعریف می‌شود:
    title        عنوان فارسی گزارش (برای PDF)
    file_prefix  پیشوند نام فایل خروجی
    columns      عناوین ستون‌ها
    numeric_idx  اندیس ستون‌های مبلغ (برای فرمت اعداد در اکسل)
    build        تبدیل ردیف‌های خام دیتابیس به ردیف نمایشی
                 (سلول‌های مبلغ به‌صورت عدد خام باقی می‌مانند)
    total        ساخت ردیف «جمع کل» از ردیف‌های خام (یا None)
    widths       نسبت عرض ستون‌ها برای PDF (جمعشان = ۱)
"""

import os
import sys
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import getRegisteredFontNames, registerFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout

from core.utils import format_amount, gregorian_to_shamsi

TOTAL_LABEL = "جمع کل"
HEADER_GREEN = "16A34A"
TOTAL_FILL = "DCFCE7"
ZEBRA_FILL = "F8FAFC"
GRID_COLOR = "D3DCE6"
TEXT_DARK = "#1e293b"
PAGE_BG = "#eef1f6"
CARD_BORDER = "#e5eaf1"
GREEN = "#16a34a"


# ------------------------------------------------------------------ #
# ابزارهای کمکی
# ------------------------------------------------------------------ #
def _num(value):
    """تبدیل امن مقدار به عدد (برای سلول‌های عددی اکسل)."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _parse_formatted(text):
    """تبدیل «1,234,567» به 1234567 (برای داده‌های از پیش فرمت‌شده)."""
    try:
        return int(str(text).replace(",", "").replace("٫", "").strip())
    except (TypeError, ValueError):
        return 0


def _app_base_path():
    """مسیر پایه برنامه (مثل کدهای موجود؛ سازگار با نسخه بسته‌بندی‌شده)."""
    return os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()


def _ensure_vazir():
    """ثبت فونت وزیر برای PDF در صورت نبود."""
    if "Vazir" in getRegisteredFontNames():
        return
    base = _app_base_path()
    for candidate in (
        os.path.join(base, "Vazir.ttf"),
        os.path.join(base, "assets", "Vazir.ttf"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Vazir.ttf"),
    ):
        if os.path.exists(candidate):
            try:
                registerFont(TTFont("Vazir", candidate))
            except Exception:
                pass
            return


# ------------------------------------------------------------------ #
# سازنده‌های ردیف (خام → نمایشی) و ردیف جمع کل، برای هر نوع گزارش
# ------------------------------------------------------------------ #
def _b_transactions(raw):
    rows = []
    for (tid, date, account, person, category, amount, desc, cat_type) in raw:
        rows.append([
            str(tid), gregorian_to_shamsi(date), account or "-", person or "-",
            category or "-", _num(amount), desc or "-",
            "درآمد" if cat_type == "income" else "هزینه",
        ])
    return rows


def _t_transactions(raw):
    income = sum(_num(r[5]) for r in raw if r[7] == "income")
    expense = sum(_num(r[5]) for r in raw if r[7] != "income")
    return [
        "", TOTAL_LABEL, "", "", "", _num(income - expense),
        f"جمع درآمد: {format_amount(income)} | جمع هزینه: {format_amount(expense)}",
        "خالص",
    ]


def _b_debts(raw):
    rows = []
    for (tid, person, amount, paid, due, is_paid, account, is_credit, desc) in raw:
        rows.append([
            str(tid), person or "-", _num(amount), _num(paid),
            gregorian_to_shamsi(due) if due else "-",
            "تسویه‌شده" if is_paid else "در جریان",
            account or "-",
            "طلب" if (is_credit == 1 or is_credit is True) else "بدهی",
            desc or "-",
        ])
    return rows


def _t_debts(raw):
    total_amount = sum(_num(r[2]) for r in raw)
    total_paid = sum(_num(r[3]) for r in raw)
    return [
        "", TOTAL_LABEL, _num(total_amount), _num(total_paid), "",
        f"{len(raw)} مورد", "", "",
        f"باقی‌مانده: {format_amount(total_amount - total_paid)}",
    ]


def _b_cost_income(raw):
    rows = []
    for (category, amount, date, account, person, desc) in raw:
        rows.append([
            category or "-", _num(amount), gregorian_to_shamsi(date),
            account or "-", person or "-", desc or "-",
        ])
    return rows


def _t_cost_income(raw):
    return [TOTAL_LABEL, _num(sum(_num(r[1]) for r in raw)), "", "", "",
            f"{len(raw)} تراکنش"]


def _b_monthly(raw):
    """ردیف‌های خام ماهانه: (برچسب ماه، تعداد، هزینه، درآمد، مانده)"""
    return [[str(r[0]), _num(r[1]), _num(r[2]), _num(r[3]), _num(r[4])] for r in raw]


def _t_monthly(raw):
    return [
        TOTAL_LABEL,
        _num(sum(_num(r[1]) for r in raw)),
        _num(sum(_num(r[2]) for r in raw)),
        _num(sum(_num(r[3]) for r in raw)),
        _num(sum(_num(r[4]) for r in raw)),
    ]


def _b_person(raw):
    rows = []
    for (category, date, account, amount, desc) in raw:
        rows.append([
            category or "-", gregorian_to_shamsi(date) if date else "-",
            account or "-", _num(amount), desc or "-",
        ])
    return rows


def _t_person(raw):
    return [TOTAL_LABEL, "", "", _num(sum(_num(r[3]) for r in raw)),
            f"{len(raw)} تراکنش"]


def _b_person_grouped(raw):
    """خلاصه به تفکیک شخص: (شخص، تعداد، جمع هزینه، جمع درآمد، مانده)"""
    return [
        [str(r[0]), _num(r[1]), _num(r[2]), _num(r[3]), _num(r[4])] for r in raw
    ]


def _t_person_grouped(raw):
    return [
        TOTAL_LABEL,
        _num(sum(_num(r[1]) for r in raw)),
        _num(sum(_num(r[2]) for r in raw)),
        _num(sum(_num(r[3]) for r in raw)),
        _num(sum(_num(r[4]) for r in raw)),
    ]


def _b_general(raw):
    """گزارش کلی از قبل فرمت‌شده است: (معیار، مقدار)"""
    return [[str(r[0]), str(r[1])] for r in raw]


def _b_loan_installments(raw):
    """داده از پیش فرمت‌شده: (شناسه، مبلغ فرمت‌شده، سررسید شمسی، وضعیت)"""
    return [list(r) for r in raw]


def _t_loan_installments(raw):
    total = sum(_parse_formatted(r[1]) for r in raw)
    paid = sum(1 for r in raw if "پرداخت" in str(r[3]) and "نشده" not in str(r[3]))
    return [TOTAL_LABEL, format_amount(total), "",
            f"{paid} پرداخت‌شده از {len(raw)}"]


def _b_category(raw):
    """گزارش دسته‌بندی: (دسته، تعداد، جمع مبلغ، درصد سهم)"""
    return [[str(r[0]), _num(r[1]), _num(r[2]), f"{float(r[3] or 0):.1f}%"] for r in raw]


def _t_category(raw):
    return [
        TOTAL_LABEL,
        _num(sum(_num(r[1]) for r in raw)),
        _num(sum(_num(r[2]) for r in raw)),
        "100%",
    ]


def _b_accounts(raw):
    """گزارش حساب‌ها: (حساب، تعداد تراکنش، جمع واریز، جمع برداشت، مانده)"""
    return [[str(r[0]), _num(r[1]), _num(r[2]), _num(r[3]), _num(r[4])] for r in raw]


def _t_accounts(raw):
    return [
        TOTAL_LABEL,
        _num(sum(_num(r[1]) for r in raw)),
        _num(sum(_num(r[2]) for r in raw)),
        _num(sum(_num(r[3]) for r in raw)),
        _num(sum(_num(r[4]) for r in raw)),
    ]


def _b_loans(raw):
    """خلاصه وام‌ها: (نوع، عنوان، مبلغ کل، پرداخت‌شده، باقی‌مانده، پیشرفت اقساط)"""
    return [[str(r[0]), str(r[1]), _num(r[2]), _num(r[3]), _num(r[4]), str(r[5])] for r in raw]


def _t_loans(raw):
    return [
        "", TOTAL_LABEL,
        _num(sum(_num(r[2]) for r in raw)),
        _num(sum(_num(r[3]) for r in raw)),
        _num(sum(_num(r[4]) for r in raw)),
        f"{len(raw)} وام",
    ]


# ------------------------------------------------------------------ #
# تعریف انواع گزارش
# ------------------------------------------------------------------ #
SPECS = {
    "transactions": {
        "title": "گزارش تراکنش‌ها",
        "file_prefix": "transactions_report",
        "columns": ["شناسه", "تاریخ", "حساب", "شخص", "دسته‌بندی", "مبلغ", "توضیحات", "نوع"],
        "numeric_idx": {5},
        "build": _b_transactions,
        "total": _t_transactions,
        "widths": [0.10, 0.13, 0.13, 0.12, 0.14, 0.14, 0.16, 0.08],
    },
    "debts": {
        "title": "گزارش بدهی/طلب",
        "file_prefix": "debts_report",
        "columns": ["شناسه", "شخص", "مبلغ", "پرداخت‌شده", "سررسید", "وضعیت", "حساب", "نوع", "توضیحات"],
        "numeric_idx": {2, 3},
        "build": _b_debts,
        "total": _t_debts,
        "widths": [0.08, 0.12, 0.13, 0.13, 0.12, 0.10, 0.12, 0.08, 0.12],
    },
    "cost_income": {
        "title": "گزارش هزینه/درآمد",
        "file_prefix": "cost_income_report",
        "columns": ["نوع", "مبلغ", "تاریخ", "حساب", "شخص", "توضیحات"],
        "numeric_idx": {1},
        "build": _b_cost_income,
        "total": _t_cost_income,
        "widths": [0.15, 0.15, 0.12, 0.15, 0.15, 0.28],
    },
    "monthly": {
        "title": "گزارش تفصیلی ماهانه",
        "file_prefix": "monthly_report",
        "columns": ["ماه", "تعداد تراکنش", "هزینه", "درآمد", "مانده (درآمد − هزینه)"],
        "numeric_idx": {1, 2, 3, 4},
        "build": _b_monthly,
        "total": _t_monthly,
        "widths": [0.24, 0.14, 0.21, 0.21, 0.20],
    },
    "person": {
        "title": "گزارش تراکنش‌های شخص",
        "file_prefix": "person_report",
        "columns": ["دسته‌بندی", "تاریخ", "حساب", "مبلغ", "توضیحات"],
        "numeric_idx": {3},
        "build": _b_person,
        "total": _t_person,
        "widths": [0.18, 0.12, 0.18, 0.15, 0.37],
    },
    "person_grouped": {
        "title": "گزارش خلاصه اشخاص",
        "file_prefix": "person_summary_report",
        "columns": ["شخص", "تعداد تراکنش", "جمع هزینه", "جمع درآمد", "مانده"],
        "numeric_idx": {1, 2, 3, 4},
        "build": _b_person_grouped,
        "total": _t_person_grouped,
        "widths": [0.24, 0.14, 0.21, 0.21, 0.20],
    },
    "general": {
        "title": "گزارش کلی وضعیت مالی",
        "file_prefix": "general_report",
        "columns": ["معیار", "مقدار"],
        "numeric_idx": set(),
        "build": _b_general,
        "total": None,  # خود گزارش، مجموع‌ها را نشان می‌دهد
        "widths": [0.45, 0.55],
    },
    "loan_installments_report": {
        "title": "گزارش اقساط وام",
        "file_prefix": "loan_installments_report",
        "columns": ["شناسه قسط", "مبلغ قسط", "سررسید", "وضعیت"],
        "numeric_idx": set(),
        "build": _b_loan_installments,
        "total": _t_loan_installments,
        "widths": [0.20, 0.30, 0.25, 0.25],
    },
    "category": {
        "title": "گزارش دسته‌بندی‌ها",
        "file_prefix": "category_report",
        "columns": ["دسته‌بندی", "تعداد تراکنش", "جمع مبلغ", "سهم از کل"],
        "numeric_idx": {1, 2},
        "build": _b_category,
        "total": _t_category,
        "widths": [0.34, 0.16, 0.25, 0.25],
    },
    "accounts": {
        "title": "گزارش حساب‌ها",
        "file_prefix": "accounts_report",
        "columns": ["حساب", "تعداد تراکنش", "جمع واریز", "جمع برداشت", "مانده"],
        "numeric_idx": {1, 2, 3, 4},
        "build": _b_accounts,
        "total": _t_accounts,
        "widths": [0.24, 0.14, 0.21, 0.21, 0.20],
    },
    "loans": {
        "title": "گزارش وام‌ها",
        "file_prefix": "loans_report",
        "columns": ["نوع", "عنوان", "مبلغ کل", "پرداخت‌شده", "باقی‌مانده", "پیشرفت اقساط"],
        "numeric_idx": {2, 3, 4},
        "build": _b_loans,
        "total": _t_loans,
        "widths": [0.12, 0.24, 0.17, 0.17, 0.17, 0.13],
    },
}


# ------------------------------------------------------------------ #
# ساخت جدول‌های نمایشی/عددی
# ------------------------------------------------------------------ #
def _build_dataframes(spec, raw_data):
    """خروجی: (df_numeric برای اکسل، df_text برای CSV/PDF، has_total)"""
    body = spec["build"](raw_data or [])

    has_total = bool(body) and spec.get("total") is not None
    total_row = spec["total"](raw_data) if has_total else None

    columns = spec["columns"]
    numeric_idx = spec.get("numeric_idx") or set()

    # جدول عددی (اکسل): مبالغ به‌صورت عدد خام می‌مانند
    numeric_rows = [list(r) for r in body]
    if has_total:
        numeric_rows.append(list(total_row))
    df_numeric = pd.DataFrame(numeric_rows, columns=columns)

    # جدول متنی (CSV/PDF): مبالغ با جداکننده هزارگان
    def _fmt_row(row):
        out = []
        for i, v in enumerate(row):
            if i in numeric_idx and v is not None and v != "":
                out.append(format_amount(v))
            else:
                out.append(str(v) if v is not None else "-")
        return out

    text_rows = [_fmt_row(r) for r in body]
    if has_total:
        text_rows.append(_fmt_row(total_row))
    df_text = pd.DataFrame(text_rows, columns=columns)

    return df_numeric, df_text, has_total


def _report_paths(report_type, extension):
    spec = SPECS[report_type]
    reports_folder = os.path.join(_app_base_path(), "reports")
    os.makedirs(reports_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{spec['file_prefix']}_{timestamp}.{extension}"
    return os.path.join(reports_folder, filename), reports_folder


# ------------------------------------------------------------------ #
# تولیدکنندگان فایل
# ------------------------------------------------------------------ #
def _write_excel(spec, raw_data, output_path):
    df, _, has_total = _build_dataframes(spec, raw_data)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="گزارش")
        ws = writer.sheets["گزارش"]
        ws.sheet_view.rightToLeft = True          # شیت راست‌به‌چپ
        ws.freeze_panes = "A2"                     # فریز ردیف سربرگ

        n_rows, n_cols = df.shape

        # --- سربرگ ---
        header_fill = PatternFill("solid", fgColor=HEADER_GREEN)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF", name="Vazir", size=11)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # --- عرض ستون هوشمند ---
        for col_idx in range(1, n_cols + 1):
            values = [str(df.columns[col_idx - 1])]
            values += ["" if v is None else str(v) for v in df.iloc[:, col_idx - 1]]
            width = min(max(max(len(v) for v in values) + 4, 10), 55)
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # --- فرمت اعداد ستون‌های مبلغ ---
        for col_idx in sorted(spec.get("numeric_idx") or set()):
            for r in range(2, n_rows + 2):
                cell = ws.cell(row=r, column=col_idx + 1)
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "#,##0"

        # --- ردیف جمع کل ---
        if has_total:
            r = n_rows + 1
            top_side = Side(style="medium", color=HEADER_GREEN)
            for c in range(1, n_cols + 1):
                cell = ws.cell(row=r, column=c)
                cell.font = Font(bold=True, name="Vazir", size=11)
                cell.fill = PatternFill("solid", fgColor=TOTAL_FILL)
                cell.border = Border(top=top_side)
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "#,##0"


def _write_csv(spec, raw_data, output_path):
    _, df_text, _ = _build_dataframes(spec, raw_data)
    df_text.to_csv(output_path, index=False, encoding="utf-8-sig")


def _write_pdf(spec, raw_data, output_path, date_range=None):
    _, df_text, has_total = _build_dataframes(spec, raw_data)

    _ensure_vazir()
    font = "Vazir" if "Vazir" in getRegisteredFontNames() else "Helvetica"

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36,
        title=spec["title"])

    title_style = ParagraphStyle(
        "RTitle", fontName=font, fontSize=15, alignment=1,
        textColor=colors.HexColor("#14532d"), spaceAfter=4)
    sub_style = ParagraphStyle(
        "RSub", fontName=font, fontSize=9, alignment=1,
        textColor=colors.HexColor("#64748b"))
    cell_style = ParagraphStyle(
        "RCell", fontName=font, fontSize=9, alignment=2,
        wordWrap="RTL", leading=12)
    head_style = ParagraphStyle(
        "RHead", parent=cell_style, textColor=colors.white)

    elements = [
        Paragraph(get_display(reshape(spec["title"])), title_style),
    ]

    sub_parts = []
    if date_range:
        sub_parts.append(f"بازه گزارش: {date_range}")
    sub_parts.append(f"تاریخ تولید: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    elements.append(Paragraph(get_display(reshape(" | ".join(sub_parts))), sub_style))
    elements.append(Spacer(1, 12))

    table_data = [[
        Paragraph(get_display(reshape(str(c))), head_style)
        for c in df_text.columns
    ]]
    for _, row in df_text.iterrows():
        table_data.append([
            Paragraph(get_display(reshape(str(v) if v is not None else "-")), cell_style)
            for v in row
        ])

    page_width = A4[0]
    usable_width = page_width - 72
    ratios = spec.get("widths")
    if not ratios or len(ratios) != len(df_text.columns):
        ratios = [1.0 / len(df_text.columns)] * len(df_text.columns)
    col_widths = [usable_width * w for w in ratios]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    style = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + HEADER_GREEN)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#" + GRID_COLOR)),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]

    if has_total:
        # ردیف‌های یک‌درمیان برای بدنه (بدون جمع کل)
        style.append((
            "ROWBACKGROUNDS", (0, 1), (-1, -2),
            [colors.white, colors.HexColor("#" + ZEBRA_FILL)]))
        # ردیف جمع کل: متمایز و پررنگ
        style += [
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#" + TOTAL_FILL)),
            ("LINEABOVE", (0, -1), (-1, -1), 1.4, colors.HexColor("#" + HEADER_GREEN)),
            ("FONTSIZE", (0, -1), (-1, -1), 9.5),
        ]
    else:
        style.append((
            "ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#" + ZEBRA_FILL)]))

    table.setStyle(TableStyle(style))
    elements.append(table)
    doc.build(elements)


# ------------------------------------------------------------------ #
# API عمومی
# ------------------------------------------------------------------ #
def export_report_as(parent, raw_data, report_type, format_type,
                     date_range=None):
    """تولید مستقیم فایل خروجی با فرمت مشخص (excel/csv/pdf).

    خروجی: مسیر فایل تولیدشده یا None در صورت خطا.
    """
    spec = SPECS.get(report_type)
    if spec is None:
        QMessageBox.warning(parent, "خطا", "نوع گزارش نامعتبر برای تولید خروجی!")
        return None

    try:
        if format_type == "excel":
            output_path, reports_folder = _report_paths(report_type, "xlsx")
            _write_excel(spec, raw_data, output_path)
        elif format_type == "csv":
            output_path, reports_folder = _report_paths(report_type, "csv")
            _write_csv(spec, raw_data, output_path)
        elif format_type == "pdf":
            output_path, reports_folder = _report_paths(report_type, "pdf")
            _write_pdf(spec, raw_data, output_path, date_range)
        else:
            QMessageBox.warning(parent, "خطا", "فرمت خروجی نامعتبر است.")
            return None

        _success_box(parent, output_path, reports_folder)
        return output_path
    except Exception as e:  # noqa: BLE001 - نمایش خطا به کاربر
        QMessageBox.critical(parent, "خطا", f"خطا در تولید خروجی: {e}")
        return None


def _success_box(parent, output_path, reports_folder):
    """جعبه پیام موفقیت + دکمه باز کردن پوشه گزارش‌ها."""
    box = QMessageBox(parent)
    box.setWindowTitle("موفق")
    box.setText(
        f"فایل با موفقیت در مسیر زیر ذخیره شد:\n{output_path}")
    box.setIcon(QMessageBox.Icon.Information)
    open_btn = box.addButton("📂 باز کردن پوشه گزارش‌ها",
                             QMessageBox.ButtonRole.ActionRole)
    box.addButton("باشه", QMessageBox.ButtonRole.AcceptRole)
    box.exec()
    if box.clickedButton() is open_btn:
        QDesktopServices.openUrl(QUrl.fromLocalFile(reports_folder))


def export_report(parent, raw_data, report_type, date_range=None):
    """پنجره انتخاب نوع خروجی (اکسل/CSV/PDF) و تولید فایل.

    این همان نقطه ورودی قبلی main.export_report است؛ تب‌های
    تراکنش‌ها، بدهی/طلب و وام‌ها از طریق پنجره اصلی به اینجا می‌رسند.
    """
    if report_type not in SPECS:
        QMessageBox.warning(parent, "خطا", "نوع گزارش نامعتبر برای تولید خروجی!")
        return

    dialog = QDialog(parent)
    dialog.setWindowTitle("انتخاب نوع خروجی")
    dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    dialog.setMinimumWidth(320)
    dialog.setStyleSheet(f"""
        QDialog {{ background-color: {PAGE_BG};
                  font-family: 'Vazir', 'Arial'; }}
        QLabel {{ color: {TEXT_DARK}; font-size: 13px; }}
        QPushButton {{ text-align: center; }}
    """)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(10)
    dialog.setLayout(layout)

    hint = QLabel("فرمت فایل خروجی گزارش را انتخاب کنید:")
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(hint)

    buttons = [
        ("📊 خروجی اکسل (xlsx)", "excel"),
        ("🧾 خروجی CSV", "csv"),
        ("📄 خروجی PDF", "pdf"),
    ]
    for text, fmt in buttons:
        btn = QPushButton(text)
        btn.setObjectName("primaryBtn")
        btn.setMinimumHeight(42)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a34a, stop:1 #15803d);
                color: white; border: none; border-radius: 9px;
                padding: 9px 20px; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #15803d; }}
        """)
        btn.clicked.connect(
            lambda _=False, f=fmt: export_report_as(
                parent, raw_data, report_type, f, date_range))
        layout.addWidget(btn)

    dialog.exec()
