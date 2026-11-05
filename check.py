import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.core.database import DB_PATH
import sqlite3
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT service_id, name, api_service_id, price FROM services WHERE name LIKE '%Free%'")
for row in cur.fetchall():
    print(row)
conn.close()