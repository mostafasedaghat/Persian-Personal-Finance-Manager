# -*- coding: utf-8 -*-
"""
core/paths.py
=============
تمام مسیرهای برنامه از این ماژول گرفته می‌شوند.

چرا این ماژول وجود دارد؟
  1) ساختار پروژه مرتب شد؛ فونت‌ها در «assets/fonts»، استایل‌ها در
     «assets/styles» و دیتابیس کنار فایل اجرایی قرار دارند.
  2) برنامه هم در حالت اجرا با پایتون (python main.py) و هم در حالت
     بسته‌بندی‌شده با PyInstaller (exe) مسیرها را درست پیدا می‌کند.
  3) ثبت فونت «وزیر» فقط از یک نقطه انجام می‌شود — هم برای رابط
     کاربری Qt و هم برای نمودار matplotlib و هم برای PDF های reportlab.
     (رفع باگ «getRegisteredFontNames is not defined» که پس از ورود
     به برنامه رخ می‌داد.)
"""

import os
import sys

APP_NAME = "نرم‌افزار حسابداری شخصی"
APP_VERSION = "3.0"
APP_RELEASE_NAME = "تقویم سه‌مرحله‌ای و ورودی عددی صحیح"


# ------------------------------------------------------------------ #
# مسیرهای پایه
# ------------------------------------------------------------------ #
def is_frozen() -> bool:
    """True اگر برنامه با PyInstaller بسته‌بندی شده باشد."""
    return getattr(sys, "frozen", False)


def app_root() -> str:
    """پوشه‌ای که برنامه در آن «نصب» شده است.

    - حالت dev:       پوشه ریشه پروژه (جایی که main.py در آن است)
    - حالت PyInstaller: پوشه‌ای که فایل exe در آن قرار دارد
      (مناسب برای فایل‌هایی که باید بین اجراها بمانند: دیتابیس و بکاپ‌ها)
    """
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    # core/paths.py → بالاتر برویم تا ریشه پروژه
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_root() -> str:
    """پوشه منابع بسته‌بندی‌شده.

    - حالت dev:       ریشه پروژه
    - حالت one-file:  پوشه استخراج موقت (sys._MEIPASS)
    - حالت one-folder: پوشه کنار exe
    """
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return app_root()


def resource_path(*parts) -> str:
    """مسیر یک منبع داخلی (فونت، استایل، آیکون و ...)."""
    return os.path.join(resource_root(), *parts)


# ------------------------------------------------------------------ #
# مسیرهای مشخص برنامه
# ------------------------------------------------------------------ #
def font_path() -> str:
    """فایل فونت وزیر."""
    return resource_path("assets", "fonts", "Vazir.ttf")


def stylesheet_path() -> str:
    """فایل استایل سراسری برنامه."""
    return resource_path("assets", "styles", "styles.qss")


def icon_path() -> str:
    """آیکون برنامه."""
    return resource_path("assets", "icon.ico")


def database_path() -> str:
    """فایل دیتابیس — همیشه کنار برنامه (نه در پوشه موقت)."""
    return os.path.join(app_root(), "finance.db")


def backup_dir() -> str:
    """پوشه نسخه‌های پشتیبان."""
    return os.path.join(app_root(), "database-backup")


def reports_dir() -> str:
    """پوشه خروجی گزارش‌ها."""
    return os.path.join(app_root(), "reports")


# ------------------------------------------------------------------ #
# ثبت فونت وزیر (یک بار در طول اجرا)
# ------------------------------------------------------------------ #
def ensure_vazir_font() -> bool:
    """ثبت فونت وزیر برای گزارش‌های PDF (reportlab).

    اگر فونت از قبل ثبت شده باشد یا فایل وجود نداشته باشد، کاری
    نمی‌کند. خروجی: True اگر فونت «Vazir» در دسترس reportlab باشد.
    """
    try:
        from reportlab.pdfbase.pdfmetrics import getRegisteredFontNames, registerFont
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return False

    if "Vazir" in getRegisteredFontNames():
        return True

    path = font_path()
    if not os.path.exists(path):
        return False
    try:
        registerFont(TTFont("Vazir", path))
        return True
    except Exception:
        return False


def register_qt_font() -> str:
    """ثبت فونت وزیر برای رابط کاربری Qt.

    فونت به صورت «application font» اضافه می‌شود؛ یعنی بدون نصب
    در ویندوز هم همه اجزای برنامه با وزیر نمایش داده می‌شوند.
    خروجی: نام خانواده فونت ثبت‌شده (یا رشته خالی در صورت خطا).
    """
    from PyQt6.QtGui import QFontDatabase

    path = font_path()
    if not os.path.exists(path):
        return ""
    try:
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            return ""
        families = QFontDatabase.applicationFontFamilies(font_id)
        return families[0] if families else ""
    except Exception:
        return ""


def register_matplotlib_font() -> bool:
    """ثبت فونت وزیر برای نمودارهای matplotlib (گزارش ماهانه)."""
    try:
        from matplotlib import font_manager, rcParams
    except ImportError:
        return False

    path = font_path()
    if not os.path.exists(path):
        return False
    try:
        font_manager.fontManager.addfont(path)
        rcParams["font.family"] = "Vazir"
        return True
    except Exception:
        return False
