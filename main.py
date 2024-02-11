import requests
import sqlite3


def dutch_bet(odds, total_stake):
    # Calculate implied probabilities
    implied_probs = [1 / odd for odd in odds]

    # Sum the implied probabilities
    total_implied_prob = sum(implied_probs)

    # Calculate the percentage for each selection
    percentages = [prob / total_implied_prob for prob in implied_probs]

    # Calculate stake for each selection
    stakes = [percent * total_stake for percent in percentages]

    # Calculate potential payouts
    payouts = [odd * stake for odd, stake in zip(odds, stakes)]

    # Check if the total payout exceeds the total stake
    total_payout = sum(payouts)
    total_profit = total_payout - total_stake

    return stakes, total_profit


# API Key and other parameters
API_KEY = '2a7e14e76d9b86166d3df44be2f18c75'
SPORT = 'soccer_epl'
REGIONS = 'eu'
MARKETS = 'h2h'
ODDS_FORMAT = 'decimal'
DATE_FORMAT = 'iso'

# Establish a connection to the SQLite database (create one if it doesn't exist)
conn = sqlite3.connect('odds_database.db')
cursor = conn.cursor()

try:
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

    # Fetch sports data
    sports_response = requests.get('https://api.the-odds-api.com/v4/sports',
                                   params={'api_key': API_KEY})
    sports_response.raise_for_status()  # Raise an exception for HTTP errors
    sports_data = sports_response.json()

    # Fetch odds data
    odds_response = requests.get(
        f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
        params={
            'api_key': API_KEY,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT,
            'dateFormat': DATE_FORMAT,
        })
    odds_response.raise_for_status()  # Raise an exception for HTTP errors
    odds_json = odds_response.json()

    open('Matches.txt', 'w').close()

    # Insert matches
    for match in odds_json:
        home_team = match['home_team']
        away_team = match['away_team']
        commence_time = match['commence_time']
        cursor.execute(
            'INSERT INTO Matches (home_team, away_team, commence_time) VALUES (?, ?, ?)',
            (home_team, away_team, commence_time))
        match_id = cursor.lastrowid  # Get the ID of the inserted match

        # Insert outcomes
        for bookmaker in match['bookmakers']:
            bookmaker_title = bookmaker['title']
            bookmaker_id = cursor.execute(
                'SELECT bookmaker_id FROM Bookmakers WHERE title = ?',
                (bookmaker_title,)).fetchone()
            if bookmaker_id is None:
                cursor.execute('INSERT INTO Bookmakers (title) VALUES (?)',
                               (bookmaker_title,))
                bookmaker_id = cursor.lastrowid
            else:
                bookmaker_id = bookmaker_id[0]

            for market in bookmaker['markets']:
                market_name = market['key']
                market_id = cursor.execute(
                    'SELECT market_id FROM Markets WHERE name = ?',
                    (market_name,)).fetchone()
                if market_id is None:
                    cursor.execute('INSERT INTO Markets (name) VALUES (?)',
                                   (market_name,))
                    market_id = cursor.lastrowid
                else:
                    market_id = market_id[0]

                for outcome in market['outcomes']:
                    outcome_name = outcome['name']
                    price = outcome['price']
                    cursor.execute(
                        'INSERT INTO Outcomes (match_id, bookmaker_id, market_id, outcome_name, price) VALUES (?, ?, ?, ?, ?)',
                        (match_id, bookmaker_id, market_id, outcome_name, price))

    # Retrieve matches along with the maximum price for each outcome
    cursor.execute('''
            SELECT 
                Matches.home_team,
                Matches.away_team,
                (SELECT Bookmakers.title 
                 FROM Bookmakers 
                 JOIN Outcomes ON Bookmakers.bookmaker_id = Outcomes.bookmaker_id 
                 WHERE Outcomes.match_id = Matches.match_id AND Outcomes.outcome_name = Matches.home_team 
                 AND Outcomes.market_id != 3 -- Exclude outcomes with market_id = 3
                 ORDER BY Outcomes.price DESC LIMIT 1) AS home_bookmaker,
                (SELECT MAX(price) 
                 FROM Outcomes 
                 WHERE Outcomes.match_id = Matches.match_id AND Outcomes.outcome_name = Matches.home_team 
                 AND Outcomes.market_id != 3) AS max_home_price,  -- Exclude outcomes with market_id = 3
                (SELECT Bookmakers.title 
                 FROM Bookmakers 
                 JOIN Outcomes ON Bookmakers.bookmaker_id = Outcomes.bookmaker_id 
                 WHERE Outcomes.match_id = Matches.match_id AND Outcomes.outcome_name = Matches.away_team 
                 AND Outcomes.market_id != 3 -- Exclude outcomes with market_id = 3
                 ORDER BY Outcomes.price DESC LIMIT 1) AS away_bookmaker,
                (SELECT MAX(price) 
                 FROM Outcomes 
                 WHERE Outcomes.match_id = Matches.match_id AND Outcomes.outcome_name = Matches.away_team 
                 AND Outcomes.market_id != 3) AS max_away_price,  -- Exclude outcomes with market_id = 3
                (SELECT Bookmakers.title 
                 FROM Bookmakers 
                 JOIN Outcomes ON Bookmakers.bookmaker_id = Outcomes.bookmaker_id 
                 WHERE Outcomes.match_id = Matches.match_id AND Outcomes.outcome_name = 'Draw' 
                 AND Outcomes.market_id != 3 -- Exclude outcomes with market_id = 3
                 ORDER BY Outcomes.price DESC LIMIT 1) AS draw_bookmaker,
                (SELECT MAX(price) 
                 FROM Outcomes 
                 WHERE Outcomes.match_id = Matches.match_id AND Outcomes.outcome_name = 'Draw' 
                 AND Outcomes.market_id != 3) AS max_draw_price  -- Exclude outcomes with market_id = 3
            FROM Matches
        ''')

    # Fetch the results and print them
    for row in cursor.fetchall():
        home_team, away_team, home_bookmaker, max_home_price, away_bookmaker, max_away_price, draw_bookmaker, max_draw_price = row
        with open('Matches.txt', 'a', encoding="utf-8") as ff:
            ff.write(f"{home_team} - {away_team} \n"
                     f"Max Home Price: {max_home_price} (Bookmaker: {home_bookmaker}), "
                     f"Max Draw Price: {max_draw_price} (Bookmaker: {draw_bookmaker}), "
                     f"Max Away Price: {max_away_price} (Bookmaker: {away_bookmaker})\n")
            # Example usage
            odds = [max_home_price, max_away_price, max_draw_price]
            total_stake = 100
            stakes, total_profit = dutch_bet(odds, total_stake)
            ff.write("Stakes:\n")
            for i, stake in enumerate(stakes):
                ff.write(f"Stake for Odd {i + 1}: ${stake:.2f}\n")

            if total_profit > 0:
                ff.write(f"The Dutch bet is profitable. Total profit: ${total_profit:.2f}\n")
            elif total_profit <= 0:
                ff.write(
                    f"The Dutch bet is not profitable. Total loss: ${abs(total_profit):.2f}\n"
                )
            ff.write('\n')

finally:
    # Close the connection
    conn.close()
print('finnished')
