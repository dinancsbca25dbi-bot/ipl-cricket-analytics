import pandas as pd
import sqlite3

# Database path
db_path = r"C:\Users\dbila\IPL_cricket_analytics\data\raw\ipl.db"

# CSV files
files = {
    "matches": r"C:\Users\dbila\IPL_cricket_analytics\data\raw\tables\matches.csv",
    "deliveries": r"C:\Users\dbila\IPL_cricket_analytics\data\raw\tables\deliveries.csv",
    "players": r"C:\Users\dbila\IPL_cricket_analytics\data\raw\tables\players.csv",
    "teams": r"C:\Users\dbila\IPL_cricket_analytics\data\raw\tables\teams.csv",
    "venues": r"C:\Users\dbila\IPL_cricket_analytics\data\raw\tables\venues.csv"
}

# Connect to SQLite database
conn = sqlite3.connect(db_path)

# Load each CSV into SQLite
for table_name, file_path in files.items():
    df = pd.read_csv(file_path)

    df.to_sql(
        table_name,
        conn,
        if_exists="replace",
        index=False
    )

    print(f"{table_name} table loaded: {len(df)} rows")

conn.close()

print("All IPL data loaded successfully!")