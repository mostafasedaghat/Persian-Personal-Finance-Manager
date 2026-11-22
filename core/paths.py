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
APP_VERSION = "3.2"
APP_RELEASE_NAME = "فونت وزیرمتن و مستندات تصویری"


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
    """فایل فونت اصلی (وزن معمولی Vazirmatn)."""
    return resource_path("assets", "fonts", "Vazirmatn-Regular.ttf")


def font_paths() -> list:
    """همهٔ فایل‌های فونت برنامه (معمولی، متوسط، ضخیم).

    فونت‌ها از خانوادهٔ «وزیرمتن» (Vazirmatn) هستند — نسخهٔ تکامل‌
    یافتهٔ فونت وزیر با حروف و فاصله‌گذاری بهتر. وجود وزن Bold واقعی
    باعث می‌شود متن‌های ضخیم برنامه با «بولد مصنوعی» (کشیده‌شده و
    بدشکل) رندر نشوند.
    """
    names = ("Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf",
             "Vazirmatn-Bold.ttf")
    paths = [resource_path("assets", "fonts", n) for n in names]
    return [p for p in paths if os.path.exists(p)]


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
# ثبت فونت وزیرمتن (یک بار در طول اجرا)
# ------------------------------------------------------------------ #
def ensure_vazir_font() -> bool:
    """ثبت فونت وزیرمتن برای گزارش‌های PDF (reportlab).

    هر سه وزن ثبت می‌شوند و با registerFontFamily به هم وصل می‌گردند
    تا <b> در متن و Font(bold=True) به وزن ضخیمِ واقعی مپ شوند.
    خروجی: True اگر فونت «Vazirmatn» در دسترس reportlab باشد.
    """
    try:
        from reportlab.pdfbase.pdfmetrics import (
            getRegisteredFontNames, registerFont, registerFontFamily,
        )
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return False

    if "Vazirmatn" in getRegisteredFontNames():
        return True

    regular = font_path()
    bold = resource_path("assets", "fonts", "Vazirmatn-Bold.ttf")
    medium = resource_path("assets", "fonts", "Vazirmatn-Medium.ttf")
    if not os.path.exists(regular):
        return False
    try:
        registerFont(TTFont("Vazirmatn", regular))
        if os.path.exists(bold):
            registerFont(TTFont("Vazirmatn-Bold", bold))
        else:
            registerFont(TTFont("Vazirmatn-Bold", regular))
        if os.path.exists(medium):
            registerFont(TTFont("Vazirmatn-Medium", medium))
        # اتصال وزن‌ها به خانواده تا bold واقعی استفاده شود
        registerFontFamily(
            "Vazirmatn",
            normal="Vazirmatn",
            bold="Vazirmatn-Bold",
            italic="Vazirmatn",
            boldItalic="Vazirmatn-Bold",
        )
        return True
    except Exception:
        return False


def register_qt_font() -> str:
    """ثبت فونت وزیرمتن برای رابط کاربری Qt.

    هر سه وزن (معمولی/متوسط/ضخیم) به‌صورت «application font» اضافه
    می‌شوند؛ یعنی بدون نصب فونت در ویندوز هم همهٔ اجزای برنامه با
    وزیرمتن نمایش داده می‌شوند و متن‌های ضخیم از وزن Bold واقعی
    استفاده می‌کنند (نه بولد مصنوعی کشیده‌شده).
    خروجی: نام خانوادهٔ فونت ثبت‌شده (یا رشتهٔ خالی در صورت خطا).
    """
    from PyQt6.QtGui import QFontDatabase

    paths = font_paths()
    if not paths:
        return ""
    family = ""
    for path in paths:
        try:
            font_id = QFontDatabase.addApplicationFont(path)
            if font_id == -1:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families and not family:
                family = families[0]
        except Exception:
            continue
    return family


def register_matplotlib_font() -> bool:
    """ثبت فونت وزیرمتن برای نمودارهای matplotlib (گزارش ماهانه)."""
    try:
        from matplotlib import font_manager, rcParams
    except ImportError:
        return False

    paths = font_paths()
    if not paths:
        return False
    try:
        for path in paths:
            font_manager.fontManager.addfont(path)
        rcParams["font.family"] = "Vazirmatn"
        return True
    except Exception:
        return False
