import locale
import re
import jdatetime
from PyQt6.QtCore import QDate

# تنظیمات لوکال برای فرمت‌بندی اعداد (قرار دادن جداکننده هزارگان)
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass # در صورتی که لوکال تنظیم نشد، از پیش‌فرض استفاده می‌شود

def gregorian_to_shamsi(date):
    """تبدیل تاریخ میلادی به شمسی (رشته یا QDate)"""
    if not date:
        return ""
    try:
        if isinstance(date, QDate):
            date_str = date.toString("yyyy-MM-dd")
        else:
            date_str = str(date).split()[0]
            
        y, m, d = map(int, date_str.split('-'))
        jalali_date = jdatetime.date.fromgregorian(day=d, month=m, year=y)
        return jalali_date.strftime("%Y/%m/%d")
    except Exception:
        return str(date)

def shamsi_to_gregorian(date_str):
    """تبدیل تاریخ شمسی (YYYY/MM/DD) به میلادی (YYYY-MM-DD)"""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        parts = date_str.split('/')
        if len(parts) != 3:
            return None
        y, m, d = map(int, parts)
        jalali_date = jdatetime.date(y, m, d)
        gregorian_date = jalali_date.togregorian()
        return gregorian_date.strftime("%Y-%m-%d")
    except Exception:
        return None

def is_valid_shamsi_date(date_str):
    """بررسی صحت فرمت تاریخ شمسی (YYYY/MM/DD)"""
    if not date_str:
        return False
    return bool(re.match(r'^\d{4}/\d{2}/\d{2}$', str(date_str)))

def format_number(number):
    """فرمت‌بندی اعداد با جداکننده هزارگان"""
    if number is None or number == "":
        return "0"
    try:
        return locale.format_string("%d", int(number), grouping=True)
    except (ValueError, TypeError):
        return str(number)
