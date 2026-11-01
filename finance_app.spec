# -*- mode: python ; coding: utf-8 -*-
"""
finance_app.spec — فایل ساخت نسخه ویندوز با PyInstaller
=========================================================

ساخت فایل اجرایی تک‌پارچه (یک exe) برای ویندوز:

    pyinstaller --noconfirm finance_app.spec

خروجی در پوشه «dist/FinanceApp/» ساخته می‌شود (به صورت پیش‌فرض
--onefile است، چون EXE همه a.binaries/a.datas را می‌گیرد).

نکته مهم درباره مسیرها:
  - منابع (فونت، استایل، آیکون) داخل فایل exe بسته‌بندی می‌شوند
    و توسط core/paths.py از مسیر موقت استخراج می‌شوند.
  - فایل دیتابیس (finance.db) و پوشه‌های reports و database-backup
    به صورت خودکار «کنار فایل exe» ساخته می‌شوند تا بین اجراها
    حفظ شوند.

نکته مهم درباره excludes (لیست حذف‌شده‌ها):
  برنامه فقط از «PyQt6» استفاده می‌کند؛ اما matplotlib برای پیداکردن
  بایندینگ Qt، هربار PyQt6/PySide6/PyQt5/PySide2 را داخل try/except
  امتحان می‌کند. اگر در پایتونِ سراسری شما PyQt5 یا PySide هم نصب
  باشد، PyInstaller هر دو را جمع می‌کند و این خطا را می‌دهد:

    «attempt to collect multiple Qt bindings packages ...»

  راه‌حل همین لیست excludes است؛ به همین دلیل PyQt5، PySide2 و
  PySide6 صریحاً حذف شده‌اند. پکیج‌های سنگین دیگری (torch، sympy،
  IPython، pytest، scipy و ...) هم حذف شده‌اند که اگر در محیط پایتون
  شما نصب باشند، بی‌جهت وارد فایل exe شوند و حجم آن را چند برابر
  کنند. (توصیه اصلی: ساخت در یک محیط مجازی تمیز — راهنمای کامل
  در README.md)
"""

import os
from PyInstaller.utils.hooks import collect_data_files

# منابع برنامه که باید داخل بسته قرار بگیرند
datas = [
    ('assets/fonts', 'assets/fonts'),        # فونت وزیر
    ('assets/styles', 'assets/styles'),      # استایل سراسری (styles.qss)
    ('assets/icon.ico', 'assets'),           # آیکون برنامه
]

# فایل‌های داده matplotlib (فونت‌ها و تنظیمات داخلی)
datas += collect_data_files('matplotlib', include_py_files=False)

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ---------- بایندینگ‌های دیگر Qt (فقط PyQt6 لازم است) ----------
        # مهم‌ترین بخش: جلوگیری از خطای
        # «multiple Qt bindings packages» وقتی چند کتابخانه Qt نصب است.
        'PyQt5',
        'PyQt5.sip',
        'PySide2',
        'PySide6',
        'tkinter',

        # ---------- پکیج‌های سنگینِ غیرضروری ----------
        # (اگر در محیط پایتون نصب باشند، وارد خروجی نمی‌شوند)
        'torch',
        'sympy',
        'IPython',
        'pytest',
        'scipy',
        'zmq',
        'jupyter',
        'notebook',
        'pygments',
        'jedi',
        'parso',
        'cryptography',
        'urllib3',
        'requests',
        'certifi',
        'charset_normalizer',
        'idna',
        'chardet',
        # شتاب‌دهنده‌ها/ابزارهای «اختیاری» pandas و matplotlib که
        # برنامه از آن‌ها استفاده نمی‌کند ولی اگر نصب باشند جمع می‌شوند:
        'numba',
        'llvmlite',
        'numexpr',
        'bottleneck',
        'bs4',
        'lxml',
        'pyarrow',
        'psutil',
        # ابزارهای بسته‌بندی پایتون (در زمان اجرا لازم نیستند):
        'setuptools',
        'pkg_resources',
        '_distutils_hack',
        'cairo',

        # ---------- زیرماژول‌های بلااستفاده PyQt6 (کاهش حجم) ----------
        'PyQt6.QtNetwork',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtBluetooth',
        'PyQt6.QtNfc',
        'PyQt6.QtPositioning',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtXml',
        'PyQt6.QtMultimedia',
        'PyQt6.QtPdf',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FinanceApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                     # بدون پنجره کنسول
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',            # آیکون فایل اجرایی
)
