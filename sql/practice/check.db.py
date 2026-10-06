import sqlite3

conn = sqlite3.connect(r"C:\Users\dinan\ipl_cricket_analytics\ipl-cricket-analytics\notebooks\ipl.db")

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Tables in database:")
print(tables)

conn.close()