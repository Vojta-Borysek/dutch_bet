import sqlite3

# Establish a connection to the SQLite database (create one if it doesn't exist)
conn = sqlite3.connect('odds_database.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS Matches (
    match_id INTEGER PRIMARY KEY,
    home_team TEXT,
    away_team TEXT,
    commence_time TIMESTAMP
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Bookmakers (
    bookmaker_id INTEGER PRIMARY KEY,
    title TEXT
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Markets (
    market_id INTEGER PRIMARY KEY,
    name TEXT
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Outcomes (
    outcome_id INTEGER PRIMARY KEY,
    match_id INTEGER,
    bookmaker_id INTEGER,
    market_id INTEGER,
    outcome_name TEXT,
    price REAL,
    FOREIGN KEY (match_id) REFERENCES Matches(match_id),
    FOREIGN KEY (bookmaker_id) REFERENCES Bookmakers(bookmaker_id),
    FOREIGN KEY (market_id) REFERENCES Markets(market_id)
);
''')

# Commit the changes to the database
conn.commit()

# Close the connection
conn.close()
