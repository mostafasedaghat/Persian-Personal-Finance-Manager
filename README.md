# مدیریت مالی شخصی / Personal Finance Manager

## درباره برنامه / About the Program

**فارسی**  
این برنامه یک ابزار مدیریت مالی شخصی است که با استفاده از PyQt6 برای رابط کاربری گرافیکی و SQLite برای پایگاه داده طراحی شده است. این برنامه به کاربران امکان مدیریت حساب‌ها، تراکنش‌ها، بدهی‌ها و طلب‌ها، وام‌ها، و تولید گزارش‌های مالی را می‌دهد. رابط کاربری به زبان فارسی و با پشتیبانی از تقویم شمسی طراحی شده و از ویژگی‌هایی مانند خروجی گزارش به فرمت‌های اکسل، CSV، و PDF و ادغام با دراپ‌باکس پشتیبانی می‌کند.

**English**  
This is a personal finance management application built using PyQt6 for the graphical user interface and SQLite for the database. It allows users to manage accounts, transactions, debts and credits, loans, and generate financial reports. The interface is designed in Persian with support for the Persian (Shamsi) calendar and includes features such as exporting reports to Excel, CSV, and PDF formats and integration with Dropbox.

---

## ویژگی‌ها / Features

**فارسی**  
- **مدیریت حساب‌ها**: ایجاد، ویرایش و حذف حساب‌های بانکی با نمایش موجودی.  
- **تراکنش‌ها**: ثبت، ویرایش و جستجوی تراکنش‌های درآمدی و هزینه‌ای با دسته‌بندی.  
- **بدهی و طلب**: مدیریت بدهی‌ها و طلب‌ها با امکان ثبت تاریخ سررسید، پرداخت جزئی، و توضیحات.  
- **وام‌ها**: ثبت و مدیریت وام‌های گرفته‌شده یا داده‌شده با جزئیات اقساط.  
- **گزارش‌گیری**: تولید گزارش‌های مالی (تراکنش‌ها، بدهی/طلب، درآمد/هزینه) با خروجی اکسل، CSV، و PDF.  
- **تقویم شمسی**: پشتیبانی از تاریخ شمسی برای ثبت و نمایش تاریخ‌ها.  
- **امنیت**: رمزنگاری رمزهای عبور با استفاده از bcrypt.  
- **ادغام با دراپ‌باکس**: پشتیبان‌گیری و بازیابی پایگاه داده از طریق دراپ‌باکس.  
- **رابط کاربری راست‌به‌چپ**: طراحی مناسب برای کاربران فارسی‌زبان.  
- **داشبورد**: نمایش خلاصه وضعیت مالی شامل موجودی حساب‌ها و بدهی‌های سررسیدشده.

**English**  
- **Account Management**: Create, edit, and delete bank accounts with balance tracking.  
- **Transactions**: Record, edit, and search income and expense transactions with categorization.  
- **Debts and Credits**: Manage debts and credits with due dates, partial payments, and descriptions.  
- **Loans**: Record and manage taken or given loans with installment details.  
- **Reporting**: Generate financial reports (transactions, debts/credits, income/expenses) with Excel, CSV, and PDF export.  
- **Persian Calendar**: Support for Shamsi (Persian) dates for recording and displaying dates.  
- **Security**: Password encryption using bcrypt.  
- **Dropbox Integration**: Backup and restore the database via Dropbox.  
- **RTL Interface**: Right-to-left design tailored for Persian-speaking users.  
- **Dashboard**: Overview of financial status, including account balances and overdue debts.

---

## پیش‌نیازها / Prerequisites

**فارسی**  
برای اجرای برنامه، باید پایتون و کتابخانه‌های زیر نصب شوند:

- **پایتون**: نسخه 3.12.4  
- **کتابخانه‌ها**:  
  ```bash
  pip install PyQt6 pandas openpyxl reportlab matplotlib jdatetime bcrypt dropbox
  ```

**English**  
To run the program, you need Python and the following libraries installed:

- **Python**: Version 3.12.4  
- **Libraries**:  
  ```bash
  pip install PyQt6 pandas openpyxl reportlab matplotlib jdatetime bcrypt dropbox
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
*توصیه می‌شود پس از ورود، رمز عبور را تغییر دهید.*

**English**  
To log in to the application for the first time, use the following credentials:  
- **Username**: `admin`  
- **Password**: `password`  
*It is recommended to change the password after logging in.*

---

## ساخت خروجی برای ویندوز / Building Executable for Windows

**فارسی**  
برای ساخت فایل اجرایی مستقل (EXE) در ویندوز، از PyInstaller استفاده کنید:  
1. مطمئن شوید PyInstaller نصب شده است:  
   ```bash
   pip install pyinstaller
   ```  
2. در پوشه پروژه، دستور زیر را اجرا کنید:  
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;." main.py
   ```  
3. فایل اجرایی در پوشه `dist` ایجاد می‌شود.

**English**  
To build a standalone executable (EXE) for Windows, use PyInstaller:  
1. Ensure PyInstaller is installed:  
   ```bash
   pip install pyinstaller
   ```  
2. In the project directory, run the following command:  
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon=assets/icon.ico --add-data "assets/icon.ico;." main.py
   ```  
3. The executable file will be created in the `dist` folder.

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
