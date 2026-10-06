import sqlite3

conn = sqlite3.connect(r"C:\Users\dbila\IPL_cricket_analytics\data\raw\ipl.db")

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Tables in database:")
print(tables)

conn.close()