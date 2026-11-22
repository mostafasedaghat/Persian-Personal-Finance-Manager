# -*- coding: utf-8 -*-
"""tools/generate_demo_data.py — ساخت پایگاه دادهٔ نمونه با دادهٔ کاملاً الکی.

کاربرد:
    python tools/generate_demo_data.py

فایل «finance.db» کنار برنامه را از نو می‌سازد و با دادهٔ نمایشی
(حساب‌ها، اشخاص، تراکنش‌ها، بدهی/طلب، وام و اقساط) پر می‌کند تا
بتوان برنامه را بدون دادهٔ واقعی اجرا، تست و از آن اسکرین‌شات گرفت.

نام کاربری/رمز ورود همان پیش‌فرض مستند در README است:
    admin / password

همهٔ مبالغ «ریال» و همهٔ نام‌ها و شرح‌ها ساختگی هستند.
"""

import bcrypt
import jdatetime
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "finance.db")

TODAY = date(2026, 11, 22)          # ۱۴۰۵/۰۹/۰۱
random.seed(14050901)               # خروجی تکرارپذیر


def g(y, m, d):
    """تاریخ میلادی از مختصات شمسی."""
    return jdatetime.date(y, m, d).togregorian()


def iso(d):
    return d.strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# ۱) ساخت دیتابیس تازه
# ----------------------------------------------------------------------------
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.executescript("""
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY, name TEXT, balance REAL DEFAULT 0);
CREATE TABLE categories (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE,
    type TEXT CHECK(type IN ('income', 'expense')));
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY, account_id INTEGER, person_id INTEGER,
    category_id INTEGER, amount REAL, date TEXT, description TEXT,
    debt_id INTEGER, is_transfer INTEGER DEFAULT 0);
CREATE TABLE debts (
    id INTEGER PRIMARY KEY, person_id INTEGER, amount REAL,
    paid_amount REAL DEFAULT 0, due_date TEXT, is_paid INTEGER DEFAULT 0,
    account_id INTEGER, show_in_dashboard INTEGER DEFAULT 0,
    is_credit INTEGER DEFAULT 0, description TEXT, settled_date TEXT,
    payment_date TEXT, reg_transaction_id INTEGER);
CREATE TABLE loans (
    id INTEGER PRIMARY KEY, type TEXT CHECK(type IN ('taken', 'given')),
    bank_name TEXT, total_amount REAL, paid_amount REAL DEFAULT 0,
    interest_rate REAL, start_date TEXT, account_id INTEGER,
    installments_total INTEGER, installments_paid INTEGER DEFAULT 0,
    installment_amount REAL, installment_interval INTEGER DEFAULT 30);
CREATE TABLE loan_installments (
    id INTEGER PRIMARY KEY, loan_id INTEGER, amount REAL, due_date TEXT,
    is_paid INTEGER DEFAULT 0, paid_date TEXT);
CREATE TABLE persons (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
CREATE TABLE users (
    id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, dropbox_token TEXT);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date, id);
CREATE INDEX IF NOT EXISTS idx_debts_due_date ON debts(due_date);
""")

# ----------------------------------------------------------------------------
# ۲) دسته‌بندی‌ها (پیش‌فرض برنامه + چند دستهٔ سفارشی)
# ----------------------------------------------------------------------------
c.executescript("""
INSERT INTO categories (name, type) VALUES
    ('حقوق', 'income'), ('فروش', 'income'), ('سایر درآمدها', 'income'),
    ('خوراک', 'expense'), ('حمل‌ونقل', 'expense'), ('مسکن', 'expense'),
    ('تفریح', 'expense'), ('خرید', 'expense'), ('سلامتی', 'expense'),
    ('سایر هزینه‌ها', 'expense'),
    ('انتقال بین حساب‌ها (خروج)', 'expense'),
    ('انتقال بین حساب‌ها (ورود)', 'income'),
    ('تسویه طلب', 'income'),
    ('تسویه بدهی', 'expense'),
    ('پرداخت قسط وام', 'expense'),
    ('دریافت قسط وام', 'income'),
    ('قرض دادن', 'expense'),
    ('قرض گرفتن', 'income'),
    ('آموزش', 'expense'), ('پوشاک', 'expense'), ('هدیه', 'income');
""")
CAT = {name: cid for cid, name in c.execute("SELECT id, name FROM categories")}

# ----------------------------------------------------------------------------
# ۳) اشخاص (نام‌های کاملاً الکی)
# ----------------------------------------------------------------------------
persons = ["علی رضایی", "مریم احمدی", "حسین کریمی", "زهرا موسوی",
           "رضا قاسمی", "فاطمه نادری", "مهدی شریفی", "نرگس رستمی"]
for name in persons:
    c.execute("INSERT INTO persons (name) VALUES (?)", (name,))
P = {name: pid for pid, name in c.execute("SELECT id, name FROM persons")}

# ----------------------------------------------------------------------------
# ۴) حساب‌ها (موجودی در پایان از تراکنش‌ها محاسبه می‌شود)
# ----------------------------------------------------------------------------
c.executescript("""
INSERT INTO accounts (name, balance) VALUES
    ('حساب جاری — بانک ملت', 0),
    ('حساب پس‌انداز — بانک صادرات', 0),
    ('کیف پول نقدی', 0),
    ('کارت بانک ملی', 0);
""")

# موجودی آغازین هر حساب (پولی که قبل از شروع دیتای نمونه موجود بوده)
OPENING = {1: 150_000_000, 2: 420_000_000, 3: 12_500_000, 4: 8_000_000}

txns = []  # (account_id, person_id, category_id, amount, date_iso, desc, debt_id, is_transfer)


def add_tx(acc, cat, amount, day, desc=None, person=None, debt_id=None,
           is_transfer=0):
    txns.append((acc, P.get(person), CAT[cat], amount, iso(day),
                 desc, debt_id, is_transfer))


# ----------------------------------------------------------------------------
# ۵) تراکنش‌های ۹ ماه اخیر (اسفند ۱۴۰۴ تا آذر ۱۴۰۵)
# ----------------------------------------------------------------------------
months = [(1404, 12), (1405, 1), (1405, 2), (1405, 3), (1405, 4),
          (1405, 5), (1405, 6), (1405, 7), (1405, 8)]

grocery_shops = ["های‌پر مارکت النصر", "فروشگاه زنجیره‌ای رفاه",
                 "میوه‌فروشی خیابان لاله", "نانوایی و لبنیات اتحاد"]
transport_desc = ["اسنپ", "تاکسی خط ۴", "کارت شهری مترو", "بنزین پمپ پارس"]
fun_desc = ["سینما کوروش", "کافه رستوران دریا", "استخر شوروری",
            "بلیت تئاتر شهر"]
health_desc = ["داروخانه دکتر قاضی", "کلینیک دندان‌پزشکی مهر",
               "آزمایشگاه پاتوبیولوژی"]
shop_desc = ["خرید آنلاین دیجی‌استایل", "لوازم خانگی امید",
             "کتاب‌فروشی نیلوفر", "کفش‌فروشی آریا"]

for (y, m) in months:
    # حقوق ماهانه (روز ۱ هر ماه)
    add_tx(1, "حقوق", 950_000_000, g(y, m, 1), "حقوق ماهانه")
    # اجاره خانه (روز ۵)
    add_tx(1, "مسکن", 250_000_000, g(y, m, 5), "اجارهٔ آپارتمان")
    # شارژ ساختمان
    add_tx(1, "مسکن", 18_500_000, g(y, m, 6), "شارژ ماهانهٔ ساختمان")
    # خرید خوارک — ۴ تا ۶ بار در ماه
    for d in sorted(random.sample(range(2, 29), random.randint(4, 6))):
        add_tx(random.choice([1, 4]), "خوراک",
               random.randrange(2_800_000, 9_500_000, 100_000),
               g(y, m, d), random.choice(grocery_shops))
    # حمل‌ونقل
    for d in sorted(random.sample(range(1, 29), random.randint(3, 5))):
        add_tx(4, "حمل‌ونقل", random.randrange(180_000, 900_000, 10_000),
               g(y, m, d), random.choice(transport_desc))
    # تفریح
    for d in sorted(random.sample(range(3, 28), random.randint(1, 3))):
        add_tx(random.choice([1, 4]), "تفریح",
               random.randrange(1_200_000, 6_000_000, 50_000),
               g(y, m, d), random.choice(fun_desc))
    # سلامتی
    if random.random() < 0.7:
        add_tx(1, "سلامتی", random.randrange(3_000_000, 25_000_000, 500_000),
               g(y, m, random.randint(4, 26)), random.choice(health_desc))
    # خرید
    if random.random() < 0.8:
        add_tx(random.choice([1, 2]), "خرید",
               random.randrange(5_000_000, 40_000_000, 500_000),
               g(y, m, random.randint(6, 27)), random.choice(shop_desc))
    # پوشاک و آموزش بعضی ماه‌ها
    if random.random() < 0.4:
        add_tx(2, "پوشاک", random.randrange(6_000_000, 30_000_000, 500_000),
               g(y, m, random.randint(8, 25)), "پوشاک فروشگاه آریا")
    if random.random() < 0.35:
        add_tx(1, "آموزش", random.randrange(8_000_000, 20_000_000, 1_000_000),
               g(y, m, random.randint(10, 24)), "شهریهٔ دورهٔ آموزشی")
    # فروش شخصی/سایر درآمد
    if random.random() < 0.5:
        add_tx(1, "فروش", random.randrange(15_000_000, 70_000_000, 1_000_000),
               g(y, m, random.randint(7, 27)), "فروش آنلاین")
    if random.random() < 0.3:
        add_tx(2, "سایر درآمدها", random.randrange(2_000_000, 9_000_000, 500_000),
               g(y, m, random.randint(12, 26)), "هدیهٔ سالگرد")
    # انتقال ماهانه بین جاری و پس‌انداز (جفت خروج/ورود)
    d = random.randint(9, 22)
    tr_amount = random.randrange(30_000_000, 90_000_000, 5_000_000)
    add_tx(1, "انتقال بین حساب‌ها (خروج)", tr_amount, g(y, m, d),
           "انتقال به پس‌انداز", is_transfer=1)
    add_tx(2, "انتقال بین حساب‌ها (ورود)", tr_amount, g(y, m, d),
           "انتقال از جاری", is_transfer=1)
    # شارژ ماهانهٔ کارت بانک ملی برای هزینه‌های روزمره
    add_tx(1, "انتقال بین حساب‌ها (خروج)", 35_000_000, g(y, m, 7),
           "شارژ کارت بانک ملی", is_transfer=1)
    add_tx(4, "انتقال بین حساب‌ها (ورود)", 35_000_000, g(y, m, 7),
           "دریافت از جاری", is_transfer=1)

# هزینه‌های بزرگ نامنظم
d = g(1405, 5, 14)   # سفر تابستانی
add_tx(1, "تفریح", 185_000_000, d, "سفر شمال — اقامت و رفت‌وآمد")
d = g(1405, 6, 9)    # گوشی نو
add_tx(1, "خرید", 98_000_000, d, "خرید گوشی همراه جدید")
d = g(1405, 1, 18)   # بیمهٔ خودرو
add_tx(1, "سایر هزینه‌ها", 43_500_000, d, "بیمهٔ شخص ثالث و بدنهٔ خودرو")
d = g(1405, 8, 11)   # تعمیر خودرو
add_tx(1, "سایر هزینه‌ها", 27_000_000, d, "تعمیر گیربکس خودرو")

# ----------------------------------------------------------------------------
# ۶) بدهی/طلب‌های نمونه + تراکنش‌های مرتبط
# ----------------------------------------------------------------------------
# (۱) طلب ۵۰م از علی رضایی — پول موقع ثبت از جاری خارج شده (قرض دادن)
add_tx(1, "قرض دادن", 50_000_000, g(1405, 6, 12),
       "قرض‌دادن به علی رضایی", person="علی رضایی", debt_id=1)
c.execute("""INSERT INTO debts (id, person_id, amount, paid_amount, due_date,
             is_paid, account_id, show_in_dashboard, is_credit, description,
             payment_date, reg_transaction_id)
             VALUES (1, ?, 50000000, 0, ?, 0, 1, 1, 1,
             'قرض برای تعمیر خودرو', ?, 1)""",
          (P["علی رضایی"], iso(g(1405, 10, 15)), iso(g(1405, 6, 12))))
# تسویهٔ جزئی ۲۰م با انتقال وجه (واریز به جاری)
add_tx(1, "تسویه طلب", 20_000_000, g(1405, 8, 3),
       "تسویه طلب از علی رضایی", person="علی رضایی", debt_id=1)
c.execute("UPDATE debts SET paid_amount = 20000000 WHERE id = 1")

# (۲) بدهی ۸۰م به حسین کریمی — پول موقع ثبت به جاری آمده (قرض گرفتن)
add_tx(1, "قرض گرفتن", 80_000_000, g(1405, 4, 20),
       "قرض‌گرفتن از حسین کریمی", person="حسین کریمی", debt_id=2)
c.execute("""INSERT INTO debts (id, person_id, amount, paid_amount, due_date,
             is_paid, account_id, show_in_dashboard, is_credit, description,
             payment_date, reg_transaction_id)
             VALUES (2, ?, 80000000, 0, ?, 0, 1, 1, 0,
             'کمک برای پیش‌خرید خانه', ?, 2)""",
          (P["حسین کریمی"], iso(g(1405, 7, 30)), iso(g(1405, 4, 20))))
# بازپرداخت ۳۰م با انتقال (کم از جاری) — سررسید گذشته = نمایش سررسیدشده
add_tx(1, "تسویه بدهی", 30_000_000, g(1405, 7, 28),
       "بازپرداخت بخشی از قرض حسین کریمی", person="حسین کریمی", debt_id=2)
c.execute("UPDATE debts SET paid_amount = 30000000 WHERE id = 2")

# (۳) طلب ۱۲م از زهرا موسوی — تسویهٔ کامل شده
add_tx(1, "قرض دادن", 12_000_000, g(1405, 3, 8),
       "قرض‌دادن به زهرا موسوی", person="زهرا موسوی", debt_id=3)
add_tx(4, "تسویه طلب", 12_000_000, g(1405, 5, 19),
       "تسویهٔ کامل طلب زهرا موسوی", person="زهرا موسوی", debt_id=3)
c.execute("""INSERT INTO debts (id, person_id, amount, paid_amount, due_date,
             is_paid, account_id, show_in_dashboard, is_credit, description,
             settled_date, payment_date, reg_transaction_id)
             VALUES (3, ?, 12000000, 12000000, ?, 1, 1, 0, 1,
             'قرض کوتاه‌مدت', ?, ?, 3)""",
          (P["زهرا موسوی"], iso(g(1405, 5, 1)), iso(g(1405, 5, 19)),
           iso(g(1405, 3, 8))))

# (۴) طلب ۱۰م از رضا قاسمی — کسر جزئی «بدون انتقال وجه» (تهاتر بابت کار)
c.execute("""INSERT INTO debts (id, person_id, amount, paid_amount, due_date,
             is_paid, account_id, show_in_dashboard, is_credit, description)
             VALUES (4, ?, 10000000, 5000000, ?, 0, NULL, 1, 1,
             'طلب بابت طراحی سایت')""",
          (P["رضا قاسمی"], iso(g(1405, 11, 20))))

# (۵) بدهی ۲۵م به مریم احمدی — بدون جابه‌جایی پول، سررسید آینده
c.execute("""INSERT INTO debts (id, person_id, amount, paid_amount, due_date,
             is_paid, account_id, show_in_dashboard, is_credit, description)
             VALUES (5, ?, 25000000, 0, ?, 0, NULL, 1, 0,
             'بدهی خرید لپ‌تاپ دست دوم')""",
          (P["مریم احمدی"], iso(g(1406, 1, 10))))

# (۶) طلب ۳۵م از مهدی شریفی — بدون حساب، نمایش در داشبورد
c.execute("""INSERT INTO debts (id, person_id, amount, paid_amount, due_date,
             is_paid, account_id, show_in_dashboard, is_credit, description)
             VALUES (6, ?, 35000000, 0, ?, 0, NULL, 1, 1,
             'سهم سرمایه‌گذاری مشترک')""",
          (P["مهدی شریفی"], iso(g(1405, 10, 2))))

# ----------------------------------------------------------------------------
# ۷) وام‌ها + اقساط + تراکنش‌های تسویهٔ اقساط
# ----------------------------------------------------------------------------
# (۱) وام گرفتن ۱.۲ میلیارد از بانک ملی — ۱۲ قسط ۱۰۵م، ۵ قسط پرداخت‌شده
c.execute("""INSERT INTO loans (id, type, bank_name, total_amount, paid_amount,
             interest_rate, start_date, account_id, installments_total,
             installments_paid, installment_amount, installment_interval)
             VALUES (1, 'taken', 'بانک ملی', 1200000000, 0, 23,
             ?, 1, 12, 0, 105000000, 30)""", (iso(g(1405, 2, 10)),))
loan1_start = g(1405, 2, 10)
for i in range(12):
    due = loan1_start + timedelta(days=30 * i)
    paid_flag = 1 if i < 5 else 0
    paid_day = due + timedelta(days=random.randint(0, 4)) if paid_flag else None
    c.execute("""INSERT INTO loan_installments (loan_id, amount, due_date,
                 is_paid, paid_date) VALUES (1, 105000000, ?, ?, ?)""",
              (iso(due), paid_flag, iso(paid_day) if paid_day else None))
    if paid_flag:
        add_tx(1, "پرداخت قسط وام", 105_000_000, paid_day,
               f"پرداخت قسط {i + 1} از وام «بانک ملی»")

# (۲) وام دادن ۳۰۰م به فاطمه نادری — ۱۰ قسط ۳۳م، ۳ قسط دریافت‌شده
c.execute("""INSERT INTO loans (id, type, bank_name, total_amount, paid_amount,
             interest_rate, start_date, account_id, installments_total,
             installments_paid, installment_amount, installment_interval)
             VALUES (2, 'given', 'قرض‌التالیه فاطمه نادری', 300000000, 0,
             0, ?, 2, 10, 0, 33000000, 30)""", (iso(g(1405, 4, 5)),))
loan2_start = g(1405, 4, 5)
for i in range(10):
    due = loan2_start + timedelta(days=30 * i)
    paid_flag = 1 if i < 3 else 0
    paid_day = due + timedelta(days=random.randint(0, 3)) if paid_flag else None
    c.execute("""INSERT INTO loan_installments (loan_id, amount, due_date,
                 is_paid, paid_date) VALUES (2, 33000000, ?, ?, ?)""",
              (iso(due), paid_flag, iso(paid_day) if paid_day else None))
    if paid_flag:
        add_tx(2, "دریافت قسط وام", 33_000_000, paid_day,
               f"دریافت قسط {i + 1} از وام به فاطمه نادری")

# همگام‌سازی paid_amount وام‌ها با اقساط (منطق نسخهٔ ۲.۷ برنامه)
c.execute("""UPDATE loans SET
    paid_amount = COALESCE((SELECT SUM(li.amount) FROM loan_installments li
                            WHERE li.loan_id = loans.id AND li.is_paid = 1), 0),
    installments_paid = COALESCE((SELECT COUNT(*) FROM loan_installments li
                            WHERE li.loan_id = loans.id AND li.is_paid = 1), 0)""")

# ----------------------------------------------------------------------------
# ۸) تراکنش‌های امروز (۱۴۰۵/۰۹/۰۱) برای پرمحتوا شدن داشبوردِ ماه جاری
# ----------------------------------------------------------------------------
today = g(1405, 9, 1)
add_tx(1, "حقوق", 950_000_000, today, "حقوق ماه آذر")
add_tx(1, "مسکن", 250_000_000, today, "اجارهٔ آپارتمان")
add_tx(4, "خوراک", 4_650_000, today, "های‌پر مارکت النصر")
add_tx(4, "خوراک", 1_980_000, today, "نانوایی و لبنیات اتحاد")
add_tx(4, "حمل‌ونقل", 320_000, today, "اسنپ")
add_tx(1, "تفریح", 2_400_000, today, "کافه رستوران دریا")
add_tx(1, "فروش", 36_000_000, today, "فروش آنلاین")
add_tx(3, "خوراک", 850_000, today, "میوه‌فروشی خیابان لاله")

# ----------------------------------------------------------------------------
# ۹) درج تراکنش‌ها + محاسبهٔ موجودی نهایی حساب‌ها
# ----------------------------------------------------------------------------
for t in txns:
    c.execute("""INSERT INTO transactions (account_id, person_id, category_id,
                 amount, date, description, debt_id, is_transfer)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", t)

# شناسهٔ تراکنش‌های «ثبتِ» بدهی‌ها را به رکورد بدهی وصل کن
for debt_id, desc_match in [(1, "قرض‌دادن به علی رضایی"),
                            (2, "قرض‌گرفتن از حسین کریمی"),
                            (3, "قرض‌دادن به زهرا موسوی")]:
    c.execute("SELECT id FROM transactions WHERE description = ?",
              (desc_match,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE debts SET reg_transaction_id = ? WHERE id = ?",
                  (row[0], debt_id))

for acc_id in OPENING:
    c.execute("""SELECT COALESCE(SUM(CASE
                 WHEN cat.type = 'income' THEN t.amount ELSE -t.amount END), 0)
                 FROM transactions t JOIN categories cat
                 ON t.category_id = cat.id WHERE t.account_id = ?""",
              (acc_id,))
    delta = c.fetchone()[0]
    c.execute("UPDATE accounts SET balance = ? WHERE id = ?",
              (OPENING[acc_id] + delta, acc_id))

# ----------------------------------------------------------------------------
# ۱۰) کاربر پیش‌فرض (admin / password) — مطابق README
# ----------------------------------------------------------------------------
pw_hash = bcrypt.hashpw("password".encode("utf-8"), bcrypt.gensalt()).decode()
c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
          ("admin", pw_hash))

conn.commit()

# ----------------------------------------------------------------------------
# گزارش خلاصه
# ----------------------------------------------------------------------------
print("پایگاه دادهٔ نمونه ساخته شد:", DB_PATH)
for tbl in ["accounts", "persons", "categories", "transactions",
            "debts", "loans", "loan_installments", "users"]:
    n = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"  {tbl:20s} {n:4d} ردیف")
print("\nموجودی حساب‌ها:")
for aid, name, bal in c.execute("SELECT id, name, balance FROM accounts"):
    print(f"  {name:35s} {bal:>15,.0f} ریال")
conn.close()
