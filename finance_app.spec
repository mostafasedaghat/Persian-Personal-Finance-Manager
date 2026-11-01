# -*- mode: python ; coding: utf-8 -*-
"""
finance_app.spec — فایل ساخت نسخه ویندوز با PyInstaller
=========================================================

ساخت فایل اجرایی تک‌پارچه (یک exe) برای ویندوز:

    pyinstaller finance_app.spec

خروجی در پوشه «dist/FinanceApp/» ساخته می‌شود.

نکته مهم درباره مسیرها:
  - منابع (فونت، استایل، آیکون) داخل فایل exe بسته‌بندی می‌شوند
    و توسط core/paths.py از مسیر موقت استخراج می‌شوند.
  - فایل دیتابیس (finance.db) و پوشه‌های reports و database-backup
    به صورت خودکار «کنار فایل exe» ساخته می‌شوند تا بین اجراها
    حفظ شوند.
"""

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

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
        # حذف کتابخانه‌های سنگین غیرضروری برای کاهش حجم خروجی
        'tkinter',
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
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
