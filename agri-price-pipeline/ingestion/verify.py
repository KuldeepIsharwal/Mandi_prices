import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mandi_prices.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT commodity, market, COUNT(*), MIN(date), MAX(date) FROM mandi_prices GROUP BY commodity, market")
rows = cursor.fetchall()

for commodity, market, count, min_date, max_date in rows:
    print(f"{commodity:10s} | {market:10s} | rows={count:6d} | {min_date} to {max_date}")

cursor.execute("SELECT COUNT(*) FROM mandi_prices")
print(f"\nTotal rows in DB: {cursor.fetchone()[0]}")

conn.close()