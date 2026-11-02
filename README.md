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
- **بدهی و طلب**: مدیریت بدهی‌ها و طلب‌ها با امکان ثبت تاریخ سررسید، پرداخت جزئی، توضیحات و **تاریخ تسویه واقعی** (اگر پرداخت در روزی غیر از روز ثبت انجام شده باشد، تاریخ واقعی انتخاب می‌شود و تراکنش مرتبط نیز با همان تاریخ ثبت می‌گردد).  
- **وام‌ها**: ثبت و مدیریت وام‌های گرفته‌شده یا داده‌شده با جزئیات اقساط و **تاریخ پرداخت واقعی هر قسط**.  
- **گزارش‌گیری حرفه‌ای**: مرکز گزارش‌ها با ۹ گزارش کامل (وضعیت مالی، هزینه/درآمد، ماهانه با نمودار، اشخاص، تراکنش‌ها، بدهی/طلب، دسته‌بندی‌ها، حساب‌ها، وام‌ها) با خروجی اکسل، CSV، و PDF — همه با ردیف «جمع کل» خودکار.  
- **تقویم شمسی**: پشتیبانی از تاریخ شمسی برای ثبت و نمایش تاریخ‌ها.  
- **امنیت**: رمزنگاری رمزهای عبور با استفاده از bcrypt.  
- **پشتیبان‌گیری آفلاین**: ایجاد نسخه پشتیبان فشرده از پایگاه داده با یک کلیک، همراه با فهرست نسخه‌های پشتیبان.  
- **رابط کاربری راست‌به‌چپ**: طراحی مناسب برای کاربران فارسی‌زبان.  
- **داشبورد**: نمایش خلاصه وضعیت مالی شامل موجودی حساب‌ها و بدهی‌های سررسیدشده.

**English**  
- **Account Management**: Create, edit, and delete bank accounts with balance tracking.  
- **Transactions**: Record, edit, and search income and expense transactions with categorization.  
- **Debts and Credits**: Manage debts and credits with due dates, partial payments, descriptions, and a **real settlement date** (if the payment happened on a different day than the registration day, pick the actual date — the linked transaction is recorded with that date too).  
- **Loans**: Record and manage taken or given loans with installment details and the **actual paid date of each installment**.  
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
برای ساخت فایل اجرایی مستقل (EXE) در ویندوز، از PyInstaller استفاده کنید.

### ⭐ روش پیشنهادی — محیط مجازی تمیز (venv)

اگر در پایتون سراسری خود پکیج‌های زیادی نصب کرده‌اید (مثلاً PyQt5،
torch، IPython و...)، حتماً در یک محیط مجازی تمیز بیلد بگیرید؛ هم از
خطاهای تداخل جلوگیری می‌کند و هم حجم فایل exe را به‌شدت کم می‌کند:

```bat
cd /d E:\MyProject\Python_personal_accounting

:: ۱) ساخت محیط مجازی تمیز
python -m venv build-env

:: ۲) فعال‌سازی آن
build-env\Scripts\activate

:: ۳) نصب فقط وابستگی‌های برنامه + PyInstaller
pip install -r requirements.txt pyinstaller

:: ۴) ساخت
pyinstaller --noconfirm finance_app.spec

:: ۵) (اختیاری) خارج شدن از محیط مجازی
deactivate
```

### روش دوم — بیلد در پایتون سراسری

فایل `finance_app.spec` لیست `excludes` کاملی دارد (PyQt5، PySide،
torch، scipy، IPython و...) تا حتی در محیط شلوغ هم بیلد موفق و سبک
باشد؛ اما روش venv بالا همیشه تمیزترین نتیجه را می‌دهد:

```bash
pip install pyinstaller
pyinstaller --noconfirm finance_app.spec
```

فایل اجرایی `FinanceApp.exe` در پوشه `dist` ساخته می‌شود.

### 🔧 رفع خطاهای رایج بیلد

**خطای «attempt to collect multiple Qt bindings packages»**  
یعنی در پایتون شما هم PyQt5/PySide نصب است هم PyQt6؛ در حالی که
برنامه فقط PyQt6 لازم دارد. دو راه‌حل:
1. با روش venv بالا در محیط تمیز بیلد بگیرید (بهترین راه).
2. یا از آخرین نسخه `finance_app.spec` استفاده کنید که PyQt5/PySide2/PySide6 را در `excludes` حذف کرده است.

```text
ERROR: Aborting build process due to attempt to collect multiple Qt
bindings packages: attempting to run hook for 'PyQt5', while hook for
'PyQt6' has already been run!
```

**حجم خیلی بزرگ فایل exe**  
نشانه آن است که در محیط شلوغ بیلد گرفته‌اید و پکیج‌های اضافی
(torch/scipy/numba و...) داخل بسته آمده‌اند. با روش venv بیلد بگیرید
یا مطمئن شوید از آخرین نسخه `finance_app.spec` استفاده می‌کنید.

**نکات مهم:**
- کل پوشه `dist/FinanceApp` را (یا فقط فایل exe در حالت one-file) هر جا می‌خواهید کپی کنید؛ برنامه کاملاً مستقل است.
- فایل دیتابیس (`finance.db`) و پوشه‌های `reports` و `database-backup` به صورت خودکار **کنار فایل exe** ساخته می‌شوند؛ پس برای دسترسی راست به آن‌ها، exe را در یک پوشه با دسترسی نوشتن قرار دهید (نه داخل `Program Files`).
- اگر آنتی‌ویروس هشدار داد (هشدار رایج PyInstaller)، پوشه برنامه را در استثناهای آنتی‌ویروس قرار دهید.

**English**  
To build a standalone executable (EXE) for Windows, use PyInstaller.

### ⭐ Recommended — clean virtual environment (venv)

If your global Python has many packages installed (e.g. PyQt5, torch,
IPython...), always build inside a clean virtual environment. This avoids
binding conflicts and greatly reduces the EXE size:

```bat
cd /d E:\MyProject\Python_personal_accounting

:: 1) Create a clean virtual environment
python -m venv build-env

:: 2) Activate it
build-env\Scripts\activate

:: 3) Install only the app dependencies + PyInstaller
pip install -r requirements.txt pyinstaller

:: 4) Build
pyinstaller --noconfirm finance_app.spec

:: 5) (Optional) Leave the virtual environment
deactivate
```

### Alternative — building in the global Python

`finance_app.spec` ships with a comprehensive `excludes` list (PyQt5,
PySide, torch, scipy, IPython, ...) so the build succeeds and stays lean
even in a crowded environment; but the venv method above always gives
the cleanest result:

```bash
pip install pyinstaller
pyinstaller --noconfirm finance_app.spec
```

The executable `FinanceApp.exe` is created in the `dist` folder.

### 🔧 Troubleshooting common build errors

**Error: "attempt to collect multiple Qt bindings packages"**  
This means both PyQt5/PySide and PyQt6 are installed in your Python,
while the app only needs PyQt6. Two fixes:
1. Build inside a clean venv (best practice — see above).
2. Or use the latest `finance_app.spec`, which lists PyQt5/PySide2/PySide6 in `excludes`.

```text
ERROR: Aborting build process due to attempt to collect multiple Qt
bindings packages: attempting to run hook for 'PyQt5', while hook for
'PyQt6' has already been run!
```

**Very large EXE file**  
This means extra packages (torch/scipy/numba/...) leaked into the bundle
from a crowded environment. Build via the venv method, or make sure you
are using the latest `finance_app.spec`.

**Important notes:**
- Copy the whole `dist/FinanceApp` folder (or just the exe in one-file mode) anywhere you like; it is fully self-contained.
- The database file (`finance.db`) and the `reports` / `database-backup` folders are created automatically **next to the exe**; place the exe in a writable folder (not inside `Program Files`).
- If your antivirus flags the file (a common PyInstaller false positive), add the program folder to your antivirus exclusions.

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
