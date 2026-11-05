import sqlite3
from bot.core.database import DB_PATH

def init_full_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            first_name TEXT,
            balance_lira REAL DEFAULT 0,
            balance_dollar REAL DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            source_price REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            product_name TEXT,
            player_id TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            first_name TEXT,
            amount REAL,
            method TEXT,
            currency TEXT,
            transaction_num TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    default_settings = [
        ('profit_ff_gems', '1.02'),
        ('profit_pubg_uc', '1.04'),
        ('profit_ff_subs', '1.07'),
        ('exchange_rate', '135'),
        ('bot_status', 'on'),
    ]
    cursor.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)

    conn.commit()
    conn.close()
    print("Database seeded successfully!")

if __name__ == "__main__":
    init_full_database()
