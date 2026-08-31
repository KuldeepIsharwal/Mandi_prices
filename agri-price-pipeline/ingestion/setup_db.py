import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "mandi_prices.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS mandi_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    market TEXT NOT NULL,
    commodity TEXT NOT NULL,
    variety TEXT,
    grade TEXT,
    min_price REAL,
    max_price REAL,
    modal_price REAL,
    UNIQUE(date, market, commodity, variety)
);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database ready at: {os.path.abspath(DB_PATH)}")

if __name__ == "__main__":
    main()