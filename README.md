# مدیریت مالی شخصی / Personal Finance Manager

## درباره برنامه / About the Program

**فارسی**  
این برنامه یک ابزار مدیریت مالی شخصی است که با استفاده از PyQt6 برای رابط کاربری گرافیکی و SQLite برای پایگاه داده طراحی شده است. این برنامه به کاربران امکان مدیریت حساب‌ها، تراکنش‌ها، بدهی‌ها و طلب‌ها، وام‌ها، و تولید گزارش‌های مالی حرفه‌ای را می‌دهد. رابط کاربری به زبان فارسی و با پشتیبانی از تقویم شمسی طراحی شده و از ویژگی‌هایی مانند خروجی گزارش به فرمت‌های اکسل، CSV، و PDF (همراه با ردیف جمع کل خودکار) و پشتیبان‌گیری آفلاین پشتیبانی می‌کند.

**English**  
This is a personal finance management application built using PyQt6 for the graphical user interface and SQLite for the database. It allows users to manage accounts, transactions, debts and credits, loans, and generate professional financial reports. The interface is designed in Persian with support for the Persian (Shamsi) calendar and includes features such as exporting reports to Excel, CSV, and PDF formats (with an automatic grand-total row) and offline backups.

---

## ویژگی‌ها / Features

**فارسی**  
- **مدیریت حساب‌ها**: ایجاد، ویرایش و حذف حساب‌های بانکی با نمایش موجودی.  
- **تراکنش‌ها**: ثبت، ویرایش و جستجوی تراکنش‌های درآمدی و هزینه‌ای با دسته‌بندی.  
- **بدهی و طلب**: مدیریت بدهی‌ها و طلب‌ها با امکان ثبت تاریخ سررسید، پرداخت جزئی، و توضیحات.  
- **وام‌ها**: ثبت و مدیریت وام‌های گرفته‌شده یا داده‌شده با جزئیات اقساط.  
- **گزارش‌گیری حرفه‌ای**: مرکز گزارش‌ها با ۹ گزارش کامل (وضعیت مالی، هزینه/درآمد، ماهانه با نمودار، اشخاص، تراکنش‌ها، بدهی/طلب، دسته‌بندی‌ها، حساب‌ها، وام‌ها) با خروجی اکسل، CSV، و PDF — همه با ردیف «جمع کل» خودکار.  
- **تقویم شمسی**: پشتیبانی از تاریخ شمسی برای ثبت و نمایش تاریخ‌ها.  
- **امنیت**: رمزنگاری رمزهای عبور با استفاده از bcrypt.  
- **پشتیبان‌گیری آفلاین**: ایجاد نسخه پشتیبان فشرده از پایگاه داده با یک کلیک، همراه با فهرست نسخه‌های پشتیبان.  
- **رابط کاربری راست‌به‌چپ**: طراحی مناسب برای کاربران فارسی‌زبان.  
- **داشبورد**: نمایش خلاصه وضعیت مالی شامل موجودی حساب‌ها و بدهی‌های سررسیدشده.

**English**  
- **Account Management**: Create, edit, and delete bank accounts with balance tracking.  
- **Transactions**: Record, edit, and search income and expense transactions with categorization.  
- **Debts and Credits**: Manage debts and credits with due dates, partial payments, and descriptions.  
- **Loans**: Record and manage taken or given loans with installment details.  
- **Professional Reporting**: A report center with 9 complete reports (financial overview, income/expense, monthly with charts, persons, transactions, debts/credits, categories, accounts, loans) with Excel, CSV, and PDF export — all with an automatic grand-total row.  
- **Persian Calendar**: Support for Shamsi (Persian) dates for recording and displaying dates.  
- **Security**: Password encryption using bcrypt.  
- **Offline Backups**: One-click compressed database backups with a list of previous backups.  
- **RTL Interface**: Right-to-left design tailored for Persian-speaking users.  
- **Dashboard**: Overview of financial status, including account balances and overdue debts.

---

## ساختار پروژه / Project Structure

```text
├── main.py                        # نقطه ورود برنامه (سبک و خوانا)
├── requirements.txt               # کتابخانه‌های مورد نیاز
├── finance_app.spec               # فایل ساخت نسخه ویندوز (PyInstaller)
│
├── core/                          # منطق اصلی برنامه
│   ├── database.py                # لایه دسترسی به داده (SQLite)
│   ├── paths.py                   # مسیرهای منابع + ثبت فونت وزیر
│   ├── utils.py                   # ابزارهای مشترک (تاریخ شمسی، فرمت عدد)
│   └── report_exporter.py         # موتور خروجی اکسل/CSV/PDF
│
├── ui/
│   ├── dialogs/                   # پنجره‌های محاوره‌ای
│   │   ├── login_dialog.py        # پنجره ورود
│   │   └── change_password_dialog.py  # پنجره تغییر رمز عبور
│   ├── components/
│   │   └── custom_widgets.py      # ویجت‌های سفارشی (تقویم شمسی و ...)
│   └── tabs/                      # تب‌های اصلی برنامه (هر کدام یک کلاس مستقل)
│       ├── dashboard_tab.py       # داشبورد
│       ├── accounts_tab.py        # حساب‌ها
│       ├── transactions_tab.py    # تراکنش‌ها
│       ├── debts_tab.py           # بدهی/طلب
│       ├── loans_tab.py           # وام‌ها
│       ├── reports_tab.py         # گزارش‌ها (مرکز گزارش‌ها)
│       ├── persons_tab.py         # اشخاص
│       ├── categories_tab.py      # دسته‌بندی‌ها
│       └── settings_tab.py        # تنظیمات
│
└── assets/                        # منابع برنامه
    ├── fonts/Vazir.ttf            # فونت فارسی
    ├── styles/styles.qss          # استایل سراسری
    ├── icon.ico                   # آیکون برنامه
    └── icon.png
```

فایل‌های داده که به صورت خودکار کنار برنامه ساخته می‌شوند:
`finance.db` (پایگاه داده)، `reports/` (خروجی گزارش‌ها)، `database-backup/` (نسخه‌های پشتیبان).

---

## پیش‌نیازها / Prerequisites

**فارسی**  
برای اجرای برنامه، پایتون (نسخه 3.12 یا بالاتر) و کتابخانه‌های زیر لازم است:

```bash
pip install -r requirements.txt
```

**English**  
You need Python (version 3.12 or higher) and the following libraries:

```bash
pip install -r requirements.txt
```

---

## نحوه اجرا / How to Run

**فارسی**  
1. مخزن را کلون کنید یا فایل‌ها را دانلود کنید.  
2. پیش‌نیازها را نصب کنید (دستور بالا).  
3. در ترمینال یا خط فرمان، به پوشه پروژه بروید و دستور زیر را اجرا کنید:  
   ```bash
   python main.py
   ```

**English**  
1. Clone the repository or download the files.  
2. Install the prerequisites (command above).  
3. In a terminal or command prompt, navigate to the project directory and run:  
   ```bash
   python main.py
   ```

---

## نام کاربری و رمز عبور پیش‌فرض / Default Username and Password

**فارسی**  
برای ورود به برنامه در اولین اجرا، از اطلاعات زیر استفاده کنید:  
- **نام کاربری**: `admin`  
- **رمز عبور**: `password`  
*توصیه می‌شود پس از ورود، رمز عبور را از تب «تنظیمات» تغییر دهید.*

**English**  
To log in to the application for the first time, use the following credentials:  
- **Username**: `admin`  
- **Password**: `password`  
*It is recommended to change the password after logging in (from the Settings tab).*

---

## ساخت خروجی برای ویندوز / Building Executable for Windows

**فارسی**  
برای ساخت فایل اجرایی مستقل (EXE) در ویندوز، از PyInstaller استفاده کنید:

1. نصب PyInstaller (در کنار سایر کتابخانه‌ها):
   ```bash
   pip install pyinstaller
   ```

2. **روش پیشنهادی — با فایل آماده spec** (همه تنظیمات از قبل انجام شده است):
   ```bash
   pyinstaller --noconfirm finance_app.spec
   ```

3. **روش جایگزین — دستور مستقیم**:
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --add-data "assets;assets" --exclude-module tkinter main.py
   ```

4. فایل اجرایی `FinanceApp.exe` در پوشه `dist` ساخته می‌شود.

**نکات مهم:**
- کل پوشه `dist/FinanceApp` را (یا فقط فایل exe در حالت one-file) هر جا می‌خواهید کپی کنید؛ برنامه کاملاً مستقل است.
- فایل دیتابیس (`finance.db`) و پوشه‌های `reports` و `database-backup` به صورت خودکار **کنار فایل exe** ساخته می‌شوند؛ پس برای دسترسی راست به آن‌ها، exe را در یک پوشه با دسترسی نوشتن قرار دهید (نه داخل `Program Files`).
- اگر آنتی‌ویروس هشدار داد (هشدار رایج PyInstaller)، پوشه برنامه را در استثناهای آنتی‌ویروس قرار دهید.

**English**  
To build a standalone executable (EXE) for Windows, use PyInstaller:

1. Install PyInstaller (alongside the other libraries):
   ```bash
   pip install pyinstaller
   ```

2. **Recommended — using the ready spec file** (all settings are preconfigured):
   ```bash
   pyinstaller --noconfirm finance_app.spec
   ```

3. **Alternative — direct command**:
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --add-data "assets;assets" --exclude-module tkinter main.py
   ```

4. The executable `FinanceApp.exe` is created in the `dist` folder.

**Important notes:**
- Copy the whole `dist/FinanceApp` folder (or just the exe in one-file mode) anywhere you like; it is fully self-contained.
- The database file (`finance.db`) and the `reports` / `database-backup` folders are created automatically **next to the exe**; place the exe in a writable folder (not inside `Program Files`).
- If your antivirus flags the file (a common PyInstaller false positive), add the program folder to your antivirus exclusions.

---

## لایسنس / License

**فارسی**  
این پروژه تحت **لایسنس MIT** منتشر شده است.  
لایسنس MIT یک لایسنس متن‌باز است که به کاربران اجازه می‌دهد کد را آزادانه استفاده، کپی، تغییر، ادغام، انتشار، توزیع، و حتی فروش کنند، به شرطی که اعلان کپی‌رایت و متن لایسنس در تمام کپی‌ها یا بخش‌های قابل‌توجه کد حفظ شود. این لایسنس هیچ ضمانتی برای عملکرد برنامه ارائه نمی‌دهد و مسئولیت استفاده از کد بر عهده کاربر است.  
متن کامل لایسنس در فایل `LICENSE` در مخزن پروژه موجود است.

**English**  
This project is licensed under the **MIT License**.  
The MIT License is a permissive open-source license that allows users to freely use, copy, modify, merge, publish, distribute, and even sell the code, provided that the copyright notice and license text are included in all copies or substantial portions of the code. The license provides no warranty for the software’s performance, and the user assumes all responsibility for its use.  
The full license text is available in the `LICENSE` file in the project repository.

---

## توسعه‌دهندگان / Developers

**فارسی**  
این پروژه به‌عنوان یک ابزار مدیریت مالی شخصی توسعه داده شده است. برای همکاری یا گزارش اشکال، لطفاً از طریق مخزن پروژه اقدام کنید.

**English**  
This project was developed as a personal finance management tool. For contributions or bug reports, please use the project repository.
