import sqlite3
import os
from datetime import datetime
from bot.config import USD_TO_LIRA_RATE, PROFIT_MARGIN_FF_GEMS, PROFIT_MARGIN_PUBG_UC, PROFIT_MARGIN_FF_SUBS, PROFIT_MARGIN

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance_lira REAL DEFAULT 0.0,
            balance_dollar REAL DEFAULT 0.0,
            join_date TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id TEXT UNIQUE,
            name TEXT,
            category TEXT,
            price REAL,
            original_price REAL,
            api_service_id TEXT,
            is_active BOOLEAN DEFAULT 1,
            min_qty REAL DEFAULT 1,
            max_qty REAL DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            service_id TEXT,
            service_name TEXT,
            player_id TEXT,
            quantity INTEGER,
            total_price REAL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_orders (
            order_uuid TEXT PRIMARY KEY,
            api_product_id TEXT,
            qty REAL,
            player_id TEXT,
            status TEXT DEFAULT 'pending',
            raw_response TEXT,
            chat_id INTEGER,
            product_name TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            first_name TEXT,
            amount REAL,
            currency TEXT DEFAULT 'SYP',
            payment_method TEXT,
            transaction_id TEXT,
            screenshot_file_id TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (chat_id) REFERENCES users(chat_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT
        )
    ''')

    default_settings = [
        ('exchange_rate', str(USD_TO_LIRA_RATE), 'USD to SYP rate'),
        ('profit_ff_gems', str(PROFIT_MARGIN_FF_GEMS), 'Free Fire gems profit margin'),
        ('profit_pubg_uc', str(PROFIT_MARGIN_PUBG_UC), 'PUBG UC profit margin'),
        ('profit_ff_subs', str(PROFIT_MARGIN_FF_SUBS), 'Free Fire subs profit margin'),
        ('bot_status', 'on', 'Bot status (on/off)')
    ]

    for key, value, description in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value, description) 
            VALUES (?, ?, ?)
        ''', (key, value, description))

    try:
        cursor.execute("ALTER TABLE api_orders ADD COLUMN product_name TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("Database initialized successfully")

def get_user_balance(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT balance_lira, balance_dollar 
        FROM users 
        WHERE chat_id = ?
    ''', (chat_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        lira, dollar = result
        exchange_rate = float(get_setting_value('exchange_rate') or 1)
        return lira + (dollar * exchange_rate)
    return 0.0

def deduct_user_balance(chat_id, amount_lira):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT balance_lira, balance_dollar 
        FROM users 
        WHERE chat_id = ?
    ''', (chat_id,))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return False

    lira, dollar = result
    exchange_rate = float(get_setting_value('exchange_rate') or 1)
    total_balance = lira + (dollar * exchange_rate)

    if total_balance < amount_lira:
        conn.close()
        return False

    if lira >= amount_lira:
        new_lira = lira - amount_lira
        new_dollar = dollar
    else:
        remaining = amount_lira - lira
        dollar_deduction = remaining / exchange_rate
        new_lira = 0
        new_dollar = dollar - dollar_deduction

    cursor.execute('''
        UPDATE users 
        SET balance_lira = ?, balance_dollar = ? 
        WHERE chat_id = ?
    ''', (new_lira, new_dollar, chat_id))

    conn.commit()
    conn.close()
    return True

def add_user_balance(chat_id, amount_lira):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users 
        SET balance_lira = balance_lira + ? 
        WHERE chat_id = ?
    ''', (amount_lira, chat_id))

    conn.commit()
    conn.close()

def get_setting_value(key):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def update_setting_value(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
    conn.commit()
    conn.close()

def add_or_update_user(chat_id, username=None, first_name=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT chat_id FROM users WHERE chat_id = ?', (chat_id,))
    if not cursor.fetchone():
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO users (chat_id, username, first_name, balance_lira, balance_dollar, join_date)
            VALUES (?, ?, ?, 0, 0, ?)
        ''', (chat_id, username, first_name, join_date))
    else:
        cursor.execute('''
            UPDATE users 
            SET username = ?, first_name = ? 
            WHERE chat_id = ?
        ''', (username, first_name, chat_id))

    conn.commit()
    conn.close()

# ─── Deposit CRUD ────────────────────────────────────────────────────────────

def create_deposit(chat_id, first_name, amount, payment_method, transaction_id, screenshot_file_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO deposits (chat_id, first_name, amount, payment_method, transaction_id, screenshot_file_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
    ''', (chat_id, first_name, amount, payment_method, transaction_id, screenshot_file_id, now, now))
    conn.commit()
    dep_id = cursor.lastrowid
    conn.close()
    return dep_id

def get_deposits(status=None, limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if status:
        cursor.execute('''
            SELECT id, chat_id, first_name, amount, payment_method, transaction_id, screenshot_file_id, status, created_at
            FROM deposits WHERE status = ? ORDER BY created_at DESC LIMIT ?
        ''', (status, limit))
    else:
        cursor.execute('''
            SELECT id, chat_id, first_name, amount, payment_method, transaction_id, screenshot_file_id, status, created_at
            FROM deposits ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0], "chat_id": r[1], "first_name": r[2], "amount": r[3],
            "payment_method": r[4], "transaction_id": r[5],
            "screenshot_file_id": r[6], "status": r[7], "created_at": r[8],
        }
        for r in rows
    ]

def approve_deposit(deposit_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, amount FROM deposits WHERE id = ? AND status = 'pending'", (deposit_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    chat_id, amount = row
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE deposits SET status = 'approved', updated_at = ? WHERE id = ?", (now, deposit_id))
    cursor.execute('''
        INSERT INTO users (chat_id, balance_lira, join_date) VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET balance_lira = balance_lira + ?
    ''', (chat_id, amount, now, amount))
    conn.commit()
    conn.close()
    return chat_id

def reject_deposit(deposit_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM deposits WHERE id = ? AND status = 'pending'", (deposit_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    chat_id = row[0]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE deposits SET status = 'rejected', updated_at = ? WHERE id = ?", (now, deposit_id))
    conn.commit()
    conn.close()
    return chat_id

if __name__ == "__main__":
    init_db()
