# -*- coding: utf-8 -*-
"""tools/capture_screenshots.py — گرفتن اسکرین‌شات تمام صفحات برنامه.

کاربرد (لینوکس، بدون نیاز به نمایشگر):
    QT_QPA_PLATFORM=offscreen python tools/capture_screenshots.py

خروجی: تصاویر PNG تمام‌صفحه در «docs/screenshots/» برای README.

نکته‌ها:
- دیالوگ ورود به‌صورت جداگانه رندر و ذخیره می‌شود (بدون لاگین واقعی).
- برای عبور از پنجرهٔ ورودِ modal، exec موقتاً replace می‌شود.
- از دیتابیس نمونهٔ تولیدشده توسط tools/generate_demo_data.py استفاده
  کنید تا هیچ دادهٔ واقعی در تصاویر نیاید.
- پیش از هر grab، رویدادهای DeferredDelete پردازش می‌شوند؛ در غیر این
  صورت ویجت‌های تازه‌جایگزین‌شدهٔ جدول‌ها (دکمه‌های عملیات) که هنوز
  deleteLater آن‌ها پردازش نشده، به‌صورت «شبح» کنار نسخهٔ اصلی رندر
  می‌شوند (باگ دیده‌شده در تصویر تب وام‌ها). حلقهٔ رویداد واقعی این
  ویجت‌ها را به‌موقع حذف می‌کند و این فقط حالت آفلاین را گرفتار می‌کند.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

OUT_DIR = os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT_DIR, exist_ok=True)

from PyQt6.QtWidgets import QApplication, QDialog  # noqa: E402
from PyQt6.QtCore import Qt, QEvent  # noqa: E402

import main as app_main  # noqa: E402
from core.database import DatabaseManager  # noqa: E402
from core.paths import database_path  # noqa: E402
from ui.dialogs.login_dialog import LoginDialog  # noqa: E402

app = QApplication(sys.argv)


def flush_pending_deletes():
    """پردازش deleteLaterهای معوق پیش از رندر.

    QWidget.grab() ویجت‌هایی را که deleteLater شده‌اند ولی هنوز حذف
    نشده‌اند هم رندر می‌کند؛ processEvents رویداد DeferredDelete را
    پردازش نمی‌کند و تنها sendPostedEvents یا بازگشت به حلقهٔ رویداد
    واقعی این ویجت‌ها را حذف می‌کند.
    """
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

# ---------------------------------------------------------------------------
# ۱) اسکرین‌شات پنجرهٔ ورود (قبل از ساخت پنجرهٔ اصلی)
# ---------------------------------------------------------------------------
db = DatabaseManager(database_path())
login = LoginDialog(db)
login.username_input.setText("admin")
login.password_input.setText("password")
login.show()
app.processEvents()
flush_pending_deletes()
login.grab().save(os.path.join(OUT_DIR, "01-login.png"))
print("saved 01-login.png")
login.close()

# ---------------------------------------------------------------------------
# ۲) عبور از ورود و ساخت پنجرهٔ اصلی
# ---------------------------------------------------------------------------
LoginDialog.exec = lambda self: QDialog.DialogCode.Accepted.value

win = app_main.FinanceApp()
win.resize(1360, 860)
app.processEvents()

TABS = [
    ("02-dashboard", "داشبورد"),
    ("03-accounts", "حساب‌ها"),
    ("04-transactions", "تراکنش‌ها"),
    ("05-debts", "بدهی-طلب"),
    ("06-loans", "وام‌ها"),
    ("07-reports", "گزارش‌ها"),
    ("08-persons", "اشخاص"),
    ("09-categories", "دسته‌بندی‌ها"),
    ("10-settings", "تنظیمات"),
]

tabs = win.tabs_widget
assert tabs.count() == len(TABS), (
    f"تعداد تب‌ها ({tabs.count()}) با فهرست انتظاری ({len(TABS)}) یکی نیست")

for i, (slug, _title) in enumerate(TABS):
    tabs.setCurrentIndex(i)
    # دو نوبت پردازش رویداد برای چیدمان، داده و رندر پایدار
    app.processEvents()
    app.processEvents()
    # حذف ویجت‌های معوق (مثل دکمه‌های عملیات جایگزین‌شدهٔ ردیف‌ها)
    flush_pending_deletes()
    out = os.path.join(OUT_DIR, f"{slug}.png")
    win.grab().save(out)
    print(f"saved {slug}.png")

win.close()
db.close()
print("\nهمهٔ اسکرین‌شات‌ها در docs/screenshots ذخیره شدند.")
