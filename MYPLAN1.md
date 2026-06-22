\# 🎾 MATCHSTAT TENNIS PREDICTION PROFITABILITY ANALYSIS

\## COMPLETE IMPLEMENTATION PLAN - PART 1 OF 3



\---



\## 📋 PROJECT OVERVIEW



\*\*Goal\*\*: Build an automated system to track Matchstat.com tennis predictions vs actual results over 6 months, measuring profitability using multiple odds strategies.



\*\*Timeline\*\*: 6 months data collection (after 2-week setup)



\*\*Tech Stack\*\*:

\- \*\*Language\*\*: Python 3.11+

\- \*\*Database\*\*: Neon Postgres (free tier)

\- \*\*Automation\*\*: GitHub Actions (2-3 daily cron jobs)

\- \*\*Scraping\*\*: Requests + BeautifulSoup (custom scraper)

\- \*\*Future Enhancement\*\*: Firecrawl API (after initial setup works)



\---



\## 🎯 SUCCESS CRITERIA



After 6 months, the system should have:

\- ✅ 500+ predictions tracked

\- ✅ <5% scrape failure rate

\- ✅ Complete odds data (prediction-time AND closing odds)

\- ✅ Accurate ROI calculations for multiple betting strategies

\- ✅ Breakdown by surface, tournament level, player rankings



\---



\## 📂 PROJECT STRUCTURE



```

matchstat-scraper/

├── .github/

│   └── workflows/

│       ├── scrape\_predictions.yml    # Daily 6 AM UTC

│       ├── scrape\_results.yml        # Daily 10 PM UTC

│       └── scrape\_closing\_odds.yml   # Hourly (optional)

│

├── src/

│   ├── \_\_init\_\_.py

│   ├── config.py                     # Configuration management

│   ├── database.py                   # Database operations

│   ├── utils.py                      # Helper functions

│   │

│   └── scrapers/

│       ├── \_\_init\_\_.py

│       ├── matchstat.py              # Prediction scraper

│       ├── oddsportal.py             # Odds scraper

│       └── flashscore.py             # Results scraper

│

├── sql/

│   └── schema.sql                    # Database schema

│

├── analysis/

│   ├── roi\_calculator.py             # ROI analysis

│   └── generate\_report.py            # PhD report generation

│

├── tests/

│   ├── test\_database.py

│   ├── test\_scrapers.py

│   └── test\_integration.py

│

├── logs/                             # Auto-generated logs

├── backups/                          # CSV exports

│

├── .env.example                      # Environment template

├── .gitignore

├── requirements.txt

├── README.md

└── run\_scraper.py                    # Local testing script

```



\---



\## 🗄️ DATABASE SCHEMA



\### \*\*Table 1: players\*\*

Normalized player data to avoid duplicate names.



```sql

CREATE TABLE IF NOT EXISTS players (

&#x20;   id SERIAL PRIMARY KEY,

&#x20;   canonical\_name VARCHAR(255) UNIQUE NOT NULL,

&#x20;   alternate\_names TEXT\[],

&#x20;   country VARCHAR(10),

&#x20;   created\_at TIMESTAMP DEFAULT NOW(),

&#x20;   updated\_at TIMESTAMP DEFAULT NOW()

);



CREATE INDEX idx\_players\_name ON players(canonical\_name);

CREATE INDEX idx\_players\_country ON players(country);

```



\*\*Purpose\*\*: Stores unique players with their various name formats (e.g., "R. Nadal", "Rafael Nadal", "Nadal R.")



\---



\### \*\*Table 2: predictions\*\*

Main table storing all prediction data.



```sql

CREATE TABLE IF NOT EXISTS predictions (

&#x20;   id SERIAL PRIMARY KEY,

&#x20;   

&#x20;   -- Scraping metadata

&#x20;   prediction\_date DATE NOT NULL,

&#x20;   prediction\_scraped\_at TIMESTAMP DEFAULT NOW(),

&#x20;   

&#x20;   -- Player references

&#x20;   player1\_id INTEGER REFERENCES players(id) ON DELETE CASCADE,

&#x20;   player2\_id INTEGER REFERENCES players(id) ON DELETE CASCADE,

&#x20;   player1\_rank INTEGER,

&#x20;   player2\_rank INTEGER,

&#x20;   

&#x20;   -- Match details

&#x20;   tournament\_name VARCHAR(255),

&#x20;   tournament\_round VARCHAR(50),  -- R1, R2, QF, SF, F

&#x20;   surface VARCHAR(20),           -- Clay, Hard, Grass, Carpet

&#x20;   tour\_type VARCHAR(20),         -- ATP, WTA, Challenger, ITF

&#x20;   match\_datetime TIMESTAMP,

&#x20;   

&#x20;   -- Time until match (auto-calculated)

&#x20;   hours\_before\_match DECIMAL(5,2) GENERATED ALWAYS AS 

&#x20;       (EXTRACT(EPOCH FROM (match\_datetime - prediction\_scraped\_at))/3600) STORED,

&#x20;   

&#x20;   -- Prediction data

&#x20;   predicted\_winner\_id INTEGER REFERENCES players(id),

&#x20;   matchstat\_url TEXT UNIQUE NOT NULL,

&#x20;   raw\_prediction\_text TEXT,

&#x20;   prediction\_summary JSONB,

&#x20;   

&#x20;   -- Match status

&#x20;   match\_status VARCHAR(20) DEFAULT 'scheduled',

&#x20;   

&#x20;   -- Results (filled by results scraper)

&#x20;   actual\_winner\_id INTEGER REFERENCES players(id),

&#x20;   match\_score VARCHAR(100),

&#x20;   result\_scraped\_at TIMESTAMP,

&#x20;   

&#x20;   -- Analysis

&#x20;   prediction\_correct BOOLEAN,

&#x20;   

&#x20;   -- Multiple ROI calculations

&#x20;   roi\_prediction\_odds DECIMAL(10,2),  -- Using odds at prediction time

&#x20;   roi\_closing\_odds DECIMAL(10,2),     -- Using odds just before match

&#x20;   roi\_best\_odds DECIMAL(10,2),        -- Using best available odds

&#x20;   

&#x20;   -- Timestamps

&#x20;   created\_at TIMESTAMP DEFAULT NOW(),

&#x20;   updated\_at TIMESTAMP DEFAULT NOW(),

&#x20;   

&#x20;   -- Constraints

&#x20;   CONSTRAINT valid\_players CHECK (player1\_id != player2\_id),

&#x20;   CONSTRAINT valid\_winner CHECK (

&#x20;       predicted\_winner\_id IN (player1\_id, player2\_id)

&#x20;   ),

&#x20;   CONSTRAINT valid\_actual\_winner CHECK (

&#x20;       actual\_winner\_id IS NULL OR 

&#x20;       actual\_winner\_id IN (player1\_id, player2\_id)

&#x20;   )

);



\-- Indexes for fast queries

CREATE INDEX idx\_prediction\_date ON predictions(prediction\_date);

CREATE INDEX idx\_match\_datetime ON predictions(match\_datetime);

CREATE INDEX idx\_tournament ON predictions(tournament\_name);

CREATE INDEX idx\_surface ON predictions(surface);

CREATE INDEX idx\_tour\_type ON predictions(tour\_type);

CREATE INDEX idx\_match\_status ON predictions(match\_status);

CREATE INDEX idx\_player1 ON predictions(player1\_id);

CREATE INDEX idx\_player2 ON predictions(player2\_id);

```



\*\*Key Features\*\*:

\- Auto-calculates `hours\_before\_match` using PostgreSQL generated column

\- Stores multiple ROI values to compare betting strategies

\- Uses foreign keys to `players` table for data integrity



\---



\### \*\*Table 3: odds\_snapshots\*\*

Tracks odds at different points in time.



```sql

CREATE TABLE IF NOT EXISTS odds\_snapshots (

&#x20;   id SERIAL PRIMARY KEY,

&#x20;   prediction\_id INTEGER REFERENCES predictions(id) ON DELETE CASCADE,

&#x20;   

&#x20;   bookmaker VARCHAR(100) NOT NULL,

&#x20;   player1\_odds DECIMAL(5,2) NOT NULL,

&#x20;   player2\_odds DECIMAL(5,2) NOT NULL,

&#x20;   

&#x20;   -- When were these odds captured?

&#x20;   odds\_type VARCHAR(50) NOT NULL,  -- 'prediction\_time', 'closing', 'live\_update'

&#x20;   captured\_at TIMESTAMP DEFAULT NOW(),

&#x20;   

&#x20;   -- How long before match?

&#x20;   hours\_before\_match DECIMAL(5,2),

&#x20;   

&#x20;   -- Prevent duplicate odds

&#x20;   CONSTRAINT unique\_odds UNIQUE (prediction\_id, bookmaker, odds\_type),

&#x20;   

&#x20;   -- Validate odds are reasonable

&#x20;   CONSTRAINT valid\_odds CHECK (

&#x20;       player1\_odds > 1.0 AND 

&#x20;       player2\_odds > 1.0

&#x20;   )

);



CREATE INDEX idx\_odds\_prediction ON odds\_snapshots(prediction\_id);

CREATE INDEX idx\_odds\_type ON odds\_snapshots(odds\_type);

CREATE INDEX idx\_odds\_bookmaker ON odds\_snapshots(bookmaker);

```



\*\*Odds Types Explained\*\*:

\- `prediction\_time`: Odds when prediction was scraped (YOUR PRIMARY METHOD)

\- `closing`: Odds just before match starts (industry standard)

\- `live\_update`: Intermediate updates (optional)



\---



\### \*\*Table 4: scrape\_logs\*\*

Monitoring and debugging table.



```sql

CREATE TABLE IF NOT EXISTS scrape\_logs (

&#x20;   id SERIAL PRIMARY KEY,

&#x20;   scrape\_type VARCHAR(50) NOT NULL,  -- 'predictions', 'results', 'closing\_odds'

&#x20;   scrape\_timestamp TIMESTAMP DEFAULT NOW(),

&#x20;   

&#x20;   matches\_found INTEGER DEFAULT 0,

&#x20;   matches\_saved INTEGER DEFAULT 0,

&#x20;   matches\_failed INTEGER DEFAULT 0,

&#x20;   

&#x20;   errors TEXT,

&#x20;   status VARCHAR(20) NOT NULL,  -- 'success', 'partial', 'failed'

&#x20;   execution\_time\_seconds DECIMAL(10,2),

&#x20;   

&#x20;   pages\_scraped INTEGER DEFAULT 0,

&#x20;   firecrawl\_credits\_used INTEGER DEFAULT 0

);



CREATE INDEX idx\_scrape\_type ON scrape\_logs(scrape\_type);

CREATE INDEX idx\_scrape\_timestamp ON scrape\_logs(scrape\_timestamp);

```



\*\*Purpose\*\*: Track scraper health, identify issues, monitor resource usage.



\---



\### \*\*Helper Views\*\*



```sql

\-- View: Get predictions with player names (easier querying)

CREATE OR REPLACE VIEW predictions\_view AS

SELECT 

&#x20;   p.id,

&#x20;   p.prediction\_date,

&#x20;   p1.canonical\_name AS player1\_name,

&#x20;   p2.canonical\_name AS player2\_name,

&#x20;   pw.canonical\_name AS predicted\_winner,

&#x20;   aw.canonical\_name AS actual\_winner,

&#x20;   p.tournament\_name,

&#x20;   p.surface,

&#x20;   p.tour\_type,

&#x20;   p.match\_datetime,

&#x20;   p.hours\_before\_match,

&#x20;   p.prediction\_correct,

&#x20;   p.roi\_prediction\_odds,

&#x20;   p.roi\_closing\_odds,

&#x20;   p.match\_status,

&#x20;   p.matchstat\_url

FROM predictions p

LEFT JOIN players p1 ON p.player1\_id = p1.id

LEFT JOIN players p2 ON p.player2\_id = p2.id

LEFT JOIN players pw ON p.predicted\_winner\_id = pw.id

LEFT JOIN players aw ON p.actual\_winner\_id = aw.id;



\-- View: Get latest odds for each prediction

CREATE OR REPLACE VIEW latest\_odds AS

SELECT DISTINCT ON (prediction\_id, odds\_type)

&#x20;   prediction\_id,

&#x20;   odds\_type,

&#x20;   bookmaker,

&#x20;   player1\_odds,

&#x20;   player2\_odds,

&#x20;   captured\_at,

&#x20;   hours\_before\_match

FROM odds\_snapshots

ORDER BY prediction\_id, odds\_type, captured\_at DESC;

```



\---



\### \*\*Database Functions\*\*



```sql

\-- Auto-update updated\_at timestamp

CREATE OR REPLACE FUNCTION update\_updated\_at\_column()

RETURNS TRIGGER AS $$

BEGIN

&#x20;   NEW.updated\_at = NOW();

&#x20;   RETURN NEW;

END;

$$ language 'plpgsql';



CREATE TRIGGER update\_players\_updated\_at BEFORE UPDATE ON players

&#x20;   FOR EACH ROW EXECUTE FUNCTION update\_updated\_at\_column();



CREATE TRIGGER update\_predictions\_updated\_at BEFORE UPDATE ON predictions

&#x20;   FOR EACH ROW EXECUTE FUNCTION update\_updated\_at\_column();

```



\---



\## 🔧 CORE MODULES SPECIFICATION



\### \*\*Module 1: src/config.py\*\*



\*\*Purpose\*\*: Centralized configuration management.



\*\*Required Functionality\*\*:

```python

\# Load from .env file

DATABASE\_URL: str

LOG\_LEVEL: str (default: INFO)

USER\_AGENT: str

REQUEST\_TIMEOUT: int (default: 10 seconds)

MIN\_DELAY: float (default: 2.0 seconds)

MAX\_DELAY: float (default: 5.0 seconds)

FIRECRAWL\_API\_KEY: str (optional, for future use)



\# Configuration validation

\- Ensure DATABASE\_URL is valid PostgreSQL connection string

\- Ensure delays are positive numbers

\- Provide sensible defaults for all values

```



\*\*Implementation Notes\*\*:

\- Use `python-dotenv` to load `.env` file

\- Raise clear errors if critical config missing

\- Support environment variable overrides



\---



\### \*\*Module 2: src/utils.py\*\*



\*\*Purpose\*\*: Reusable helper functions.



\*\*Required Functions\*\*:



\#### \*\*Scraping Utilities\*\*

```python

get\_headers() -> dict

&#x20;   """Return randomized headers to avoid detection"""

&#x20;   - Rotate between 3-5 different User-Agent strings

&#x20;   - Include Accept, Accept-Language, Accept-Encoding

&#x20;   - Add DNT, Connection, Upgrade-Insecure-Requests headers



smart\_delay(min\_seconds=2, max\_seconds=5) -> None

&#x20;   """Random delay between requests"""

&#x20;   - Use random.uniform() for natural variation

&#x20;   - Log delay duration at DEBUG level



check\_robots\_txt(url: str) -> bool

&#x20;   """Verify site allows scraping"""

&#x20;   - Parse robots.txt using urllib.robotparser

&#x20;   - Return True if allowed, False otherwise

&#x20;   - Log warning if disallowed

&#x20;   - Return True if robots.txt unreachable (fail open)

```



\#### \*\*Text Processing\*\*

```python

clean\_player\_name(raw\_name: str) -> str

&#x20;   """Remove rankings, badges from player names"""

&#x20;   - Remove trailing numbers (e.g., "Nadal 2" -> "Nadal")

&#x20;   - Remove badges: WC, Q, ALT, LL, PR, SE

&#x20;   - Strip extra whitespace

&#x20;   - Return cleaned name



parse\_rank(text: str) -> Optional\[int]

&#x20;   """Extract ranking number from text"""

&#x20;   - Use regex to find first number in string

&#x20;   - Return as integer or None



fuzzy\_match\_player(name1: str, name2: str) -> bool

&#x20;   """Check if two player names refer to same person"""

&#x20;   - Compare last names (case-insensitive)

&#x20;   - Handle initials (R. Nadal matches Rafael Nadal)

&#x20;   - Return True if match, False otherwise

```



\#### \*\*Date/Time Utilities\*\*

```python

parse\_match\_date(date\_string: str) -> datetime

&#x20;   """Parse various date formats"""

&#x20;   - Support: '05 Jan 2024', '2024-01-05', '05.01.2024', '05/01/2024'

&#x20;   - Try multiple formats in sequence

&#x20;   - Raise ValueError if no format matches



calculate\_hours\_until(target\_datetime: datetime) -> float

&#x20;   """Calculate hours from now until target"""

&#x20;   - Return positive float (hours remaining)

&#x20;   - Round to 2 decimal places

```



\#### \*\*Validation\*\*

```python

validate\_odds(odds: float) -> bool

&#x20;   """Check if odds value is reasonable"""

&#x20;   - Must be > 1.01 (no free money)

&#x20;   - Must be < 100 (suspiciously high)

&#x20;   - Return True if valid, False otherwise



validate\_prediction\_data(data: dict) -> bool

&#x20;   """Validate scraped data before database insert"""

&#x20;   - Check required fields exist: player1\_name, player2\_name, 

&#x20;     predicted\_winner, match\_datetime, matchstat\_url

&#x20;   - Verify players are different

&#x20;   - Verify predicted\_winner is one of the two players

&#x20;   - Log specific errors for debugging

&#x20;   - Return True if valid, False otherwise

```



\#### \*\*Logging Setup\*\*

```python

setup\_logging(log\_file='logs/scraper.log', level=INFO) -> Logger

&#x20;   """Configure application logging"""

&#x20;   - Create logs/ directory if missing

&#x20;   - Setup file handler (append mode)

&#x20;   - Setup console handler with colors (if colorlog available)

&#x20;   - Format: timestamp - module - level - message

&#x20;   - Return configured logger

```



\---



\### \*\*Module 3: src/database.py\*\*



\*\*Purpose\*\*: All database operations with connection pooling.



\*\*Required Functionality\*\*:



\#### \*\*Connection Management\*\*

```python

\# Use psycopg2 connection pool (1-10 connections)

get\_connection() -> connection

&#x20;   """Get connection from pool"""



release\_connection(conn: connection) -> None

&#x20;   """Return connection to pool"""

```



\#### \*\*Player Operations\*\*

```python

get\_or\_create\_player(name: str, country: str = None) -> int

&#x20;   """Get player ID, creating if doesn't exist"""

&#x20;   Input:

&#x20;       - name: Player name (will be auto-cleaned)

&#x20;       - country: ISO country code (optional)

&#x20;   

&#x20;   Process:

&#x20;       1. Clean name using utils.clean\_player\_name()

&#x20;       2. Check if player exists (exact match OR in alternate\_names array)

&#x20;       3. If exists: return player\_id

&#x20;       4. If not: INSERT new player, return new player\_id

&#x20;   

&#x20;   Return: player\_id (integer)

&#x20;   

&#x20;   Error Handling:

&#x20;       - Rollback transaction on error

&#x20;       - Log error with player name

&#x20;       - Re-raise exception



clean\_player\_name(name: str) -> str

&#x20;   """Normalize player name for canonical storage"""

&#x20;   - Remove ranks, badges

&#x20;   - Standardize whitespace

&#x20;   - Return cleaned name

```



\#### \*\*Prediction Operations\*\*

```python

save\_prediction(

&#x20;   player1\_name: str,

&#x20;   player2\_name: str,

&#x20;   predicted\_winner\_name: str,

&#x20;   tournament\_name: str,

&#x20;   match\_datetime: datetime,

&#x20;   matchstat\_url: str,

&#x20;   player1\_country: str = None,

&#x20;   player2\_country: str = None,

&#x20;   player1\_rank: int = None,

&#x20;   player2\_rank: int = None,

&#x20;   tournament\_round: str = None,

&#x20;   surface: str = None,

&#x20;   tour\_type: str = None,

&#x20;   raw\_prediction\_text: str = None,

&#x20;   prediction\_summary: dict = None

) -> Optional\[int]

&#x20;   """Save prediction to database"""

&#x20;   

&#x20;   Process:

&#x20;       1. Get/create player IDs for all 3 players (p1, p2, winner)

&#x20;       2. INSERT prediction with ON CONFLICT DO NOTHING (matchstat\_url unique)

&#x20;       3. If inserted: return prediction\_id

&#x20;       4. If duplicate: log and return None

&#x20;   

&#x20;   Return: prediction\_id or None

&#x20;   

&#x20;   Notes:

&#x20;       - Uses Json() wrapper for prediction\_summary JSONB field

&#x20;       - Sets prediction\_date to CURRENT\_DATE automatically

```



\#### \*\*Odds Operations\*\*

```python

save\_odds\_snapshot(

&#x20;   prediction\_id: int,

&#x20;   bookmaker: str,

&#x20;   player1\_odds: float,

&#x20;   player2\_odds: float,

&#x20;   odds\_type: str = 'prediction\_time',

&#x20;   hours\_before\_match: float = None

) -> None

&#x20;   """Save odds snapshot for a prediction"""

&#x20;   

&#x20;   Parameters:

&#x20;       - odds\_type: 'prediction\_time', 'closing', or 'live\_update'

&#x20;   

&#x20;   Process:

&#x20;       1. INSERT odds with ON CONFLICT UPDATE

&#x20;          (allows updating odds if scraped multiple times)

&#x20;       2. Log success with odds\_type and prediction\_id

&#x20;   

&#x20;   Error Handling:

&#x20;       - Rollback on error

&#x20;       - Log error details

&#x20;       - Re-raise exception

```



\#### \*\*Results Operations\*\*

```python

get\_matches\_needing\_results(days\_ago: int = 2) -> List\[dict]

&#x20;   """Get matches from N days ago that need results"""

&#x20;   

&#x20;   Query:

&#x20;       SELECT predictions from (CURRENT\_DATE - days\_ago)

&#x20;       WHERE actual\_winner\_id IS NULL

&#x20;       AND match\_status = 'scheduled'

&#x20;       JOIN with players to get names

&#x20;   

&#x20;   Return: List of dicts with:

&#x20;       - id

&#x20;       - player1\_name

&#x20;       - player2\_name

&#x20;       - match\_datetime

&#x20;       - matchstat\_url



update\_match\_result(

&#x20;   prediction\_id: int,

&#x20;   actual\_winner\_name: str,

&#x20;   match\_score: str,

&#x20;   match\_status: str = 'completed'

) -> None

&#x20;   """Update prediction with result and calculate ROI"""

&#x20;   

&#x20;   Process:

&#x20;       1. Get prediction details (predicted\_winner\_id, player IDs)

&#x20;       2. Get/create actual\_winner\_id

&#x20;       3. Determine if prediction\_correct (bool)

&#x20;       4. Calculate roi\_prediction\_odds (using prediction\_time odds)

&#x20;       5. Calculate roi\_closing\_odds (using closing odds, if available)

&#x20;       6. UPDATE prediction with all results

&#x20;       7. Log result with ROI

&#x20;   

&#x20;   Notes:

&#x20;       - match\_status can be: 'completed', 'walkover', 'retired'

&#x20;       - If walkover/retired, still counts as win/loss



calculate\_roi(

&#x20;   prediction\_id: int,

&#x20;   predicted\_winner\_id: int,

&#x20;   actual\_winner\_id: int,

&#x20;   odds\_type: str = 'prediction\_time'

) -> Optional\[float]

&#x20;   """Calculate ROI for a prediction"""

&#x20;   

&#x20;   Parameters:

&#x20;       - odds\_type: 'prediction\_time' or 'closing'

&#x20;   

&#x20;   Process:

&#x20;       1. Get odds from odds\_snapshots (latest for given odds\_type)

&#x20;       2. Get player1\_id, player2\_id from prediction

&#x20;       3. Determine which odds to use (player1 or player2)

&#x20;       4. Calculate ROI:

&#x20;          - If correct: (odds \* 10 KSH) - 10 KSH = profit

&#x20;          - If wrong: -10 KSH = loss

&#x20;       5. Return ROI rounded to 2 decimals

&#x20;   

&#x20;   Return: ROI in KSH or None if no odds found

```



\#### \*\*Logging Operations\*\*

```python

log\_scrape(

&#x20;   scrape\_type: str,

&#x20;   matches\_found: int = 0,

&#x20;   matches\_saved: int = 0,

&#x20;   matches\_failed: int = 0,

&#x20;   errors: str = None,

&#x20;   status: str = 'success',

&#x20;   execution\_time: float = None,

&#x20;   pages\_scraped: int = 0

) -> None

&#x20;   """Log scrape execution to database"""

&#x20;   

&#x20;   Parameters:

&#x20;       - scrape\_type: 'predictions', 'results', 'closing\_odds'

&#x20;       - status: 'success', 'partial', 'failed'

&#x20;   

&#x20;   Process:

&#x20;       1. INSERT into scrape\_logs

&#x20;       2. Commit immediately (even if scrape failed)

```



\#### \*\*Utility Functions\*\*

```python

test\_connection() -> bool

&#x20;   """Test database connection and return status"""

&#x20;   

&#x20;   Process:

&#x20;       1. Get connection from pool

&#x20;       2. Execute simple query: SELECT COUNT(\*) FROM predictions

&#x20;       3. Print count and success message

&#x20;       4. Return True if successful, False if error

```



\---



\## 🕷️ SCRAPER SPECIFICATIONS



\### \*\*Module 4: src/scrapers/matchstat.py\*\*



\*\*Purpose\*\*: Scrape tennis predictions from Matchstat.com



\*\*Main Function\*\*:

```python

scrape\_matchstat\_predictions() -> List\[dict]

&#x20;   """Scrape today's tennis predictions from Matchstat homepage"""

&#x20;   

&#x20;   URL: https://matchstat.com/

&#x20;   

&#x20;   Process:

&#x20;       1. Send GET request with headers from utils.get\_headers()

&#x20;       2. Parse HTML with BeautifulSoup

&#x20;       3. Find all prediction cards (look for tennis matches only)

&#x20;       4. For each card:

&#x20;          a. Extract player names (from links with '/tennis/player/')

&#x20;          b. Extract player countries (from flag images)

&#x20;          c. Extract player rankings (parse from text)

&#x20;          d. Extract odds from homepage (from odds divs)

&#x20;          e. Get H2H URL (link containing '/tennis/h2h-odds-bets/')

&#x20;          f. Skip if "Prediction Ready Soon" in card

&#x20;       5. smart\_delay() between requests

&#x20;   

&#x20;   Return: List of dicts, each containing:

&#x20;       {

&#x20;           'player1': {

&#x20;               'name': str,

&#x20;               'country': str,

&#x20;               'rank': int

&#x20;           },

&#x20;           'player2': {

&#x20;               'name': str,

&#x20;               'country': str,

&#x20;               'rank': int

&#x20;           },

&#x20;           'homepage\_odds': {

&#x20;               'player1': float,

&#x20;               'player2': float

&#x20;           },

&#x20;           'h2h\_url': str (full URL)

&#x20;       }

&#x20;   

&#x20;   Error Handling:

&#x20;       - Catch requests.RequestException

&#x20;       - Log parsing errors with card HTML snippet

&#x20;       - Skip malformed cards, continue with rest

&#x20;       - Return empty list if complete failure



scrape\_prediction\_details(h2h\_url: str) -> Optional\[dict]

&#x20;   """Scrape full prediction analysis from H2H page"""

&#x20;   

&#x20;   Process:

&#x20;       1. Send GET request to h2h\_url

&#x20;       2. Parse page with BeautifulSoup

&#x20;       3. Extract from <h1>:

&#x20;          - Match date (e.g., "05 Jan 2024")

&#x20;          - Tournament name

&#x20;          - Tournament round

&#x20;       4. Extract surface (look for "Clay court", "Hard court", etc.)

&#x20;       5. Determine tour\_type (ATP/WTA/Challenger/ITF from tournament name)

&#x20;       6. Extract predicted\_winner (first player name in h1)

&#x20;       7. Extract full prediction text (from .prose div)

&#x20;       8. Extract detailed odds (from "Best Odds" section)

&#x20;       9. smart\_delay()

&#x20;   

&#x20;   Return: Dict containing:

&#x20;       {

&#x20;           'predicted\_winner': str,

&#x20;           'match\_datetime': datetime,

&#x20;           'tournament\_name': str,

&#x20;           'tournament\_round': str,

&#x20;           'surface': str,

&#x20;           'tour\_type': str,

&#x20;           'prediction\_text': str,

&#x20;           'detail\_odds': {

&#x20;               'player1': float,

&#x20;               'player2': float

&#x20;           }

&#x20;       }

&#x20;       OR None if parsing failed

&#x20;   

&#x20;   Error Handling:

&#x20;       - Return None if cannot parse h1

&#x20;       - Log warnings for missing optional fields

&#x20;       - Continue with partial data if possible



main() -> None

&#x20;   """Main execution function"""

&#x20;   

&#x20;   Process:

&#x20;       1. Start timer

&#x20;       2. Call scrape\_matchstat\_predictions()

&#x20;       3. For each prediction:

&#x20;          a. Call scrape\_prediction\_details(h2h\_url)

&#x20;          b. Merge homepage and detail data

&#x20;          c. Use detail odds if available, else homepage odds

&#x20;          d. Validate data with utils.validate\_prediction\_data()

&#x20;          e. Call database.save\_prediction()

&#x20;          f. Call database.save\_odds\_snapshot() (odds\_type='prediction\_time')

&#x20;          g. Track successes/failures

&#x20;       4. Call database.log\_scrape() with statistics

&#x20;       5. Print summary

&#x20;   

&#x20;   Logging:

&#x20;       - INFO: Each successful save

&#x20;       - WARNING: Each failed prediction (with reason)

&#x20;       - ERROR: Complete scrape failure

```



\*\*HTML Selectors\*\* (as of Jan 2024 - may need updates):

```python

\# Homepage prediction cards

PREDICTION\_CARDS = 'div.flex.w-full.justify-between.items-center'

PLAYER\_LINKS = 'a\[href\*="/tennis/player/"]'

H2H\_LINK = 'a\[href\*="/tennis/h2h-odds-bets/"]'

ODDS\_DIVS = 'div.text-center.bg-gray-100.rounded-md'



\# H2H page

MATCH\_HEADING = 'h1'

PREDICTION\_TEXT = 'div.prose'

SURFACE\_LINKS = 'a\[href\*="court"]'

```



\---



\### \*\*Module 5: src/scrapers/oddsportal.py\*\*



\*\*Purpose\*\*: Scrape betting odds from Oddsportal.com (backup/supplement)



\*\*Main Function\*\*:

```python

scrape\_oddsportal\_match(player1: str, player2: str, match\_date: datetime) -> Optional\[dict]

&#x20;   """Scrape odds for specific match from Oddsportal"""

&#x20;   

&#x20;   URL Pattern: https://www.oddsportal.com/tennis/

&#x20;   

&#x20;   Challenge: Oddsportal uses heavy JavaScript

&#x20;   

&#x20;   Strategy:

&#x20;       1. Try requests first (may get cached/static version)

&#x20;       2. If no data, fallback to Selenium (for now)

&#x20;       3. Search for match using player last names

&#x20;       4. Extract odds from multiple bookmakers

&#x20;   

&#x20;   Process:

&#x20;       1. Build search URL (filter by date if possible)

&#x20;       2. Send request with headers

&#x20;       3. Parse HTML for match row

&#x20;       4. Extract odds for multiple bookmakers:

&#x20;          - Pinnacle (priority)

&#x20;          - Bet365

&#x20;          - 1xBet

&#x20;          - Average odds

&#x20;       5. smart\_delay()

&#x20;   

&#x20;   Return: Dict containing:

&#x20;       {

&#x20;           'bookmakers': {

&#x20;               'Pinnacle': {'player1': float, 'player2': float},

&#x20;               'Bet365': {'player1': float, 'player2': float},

&#x20;               'Average': {'player1': float, 'player2': float}

&#x20;           }

&#x20;       }

&#x20;       OR None if match not found

&#x20;   

&#x20;   Error Handling:

&#x20;       - Return None if match not found (not an error)

&#x20;       - Log warning if site structure changed

&#x20;       - Implement retry logic (up to 3 attempts)



\# FOR FUTURE (Phase 2): Replace with Firecrawl

scrape\_oddsportal\_with\_firecrawl(player1: str, player2: str) -> Optional\[dict]

&#x20;   """Use Firecrawl API to handle JavaScript rendering"""

&#x20;   # Implementation after initial setup works

```



\*\*Note\*\*: Oddsportal scraping is complex. Initial version can:

\- Use odds from Matchstat only

\- Add Oddsportal later as enhancement

\- Prioritize getting prediction scraper working first



\---



\### \*\*Module 6: src/scrapers/flashscore.py\*\*



\*\*Purpose\*\*: Scrape match results from FlashScore.com



\*\*Main Function\*\*:

```python

scrape\_flashscore\_result(player1: str, player2: str, match\_date: datetime) -> Optional\[tuple]

&#x20;   """Scrape match result from FlashScore"""

&#x20;   

&#x20;   URL: https://www.flashscore.com/tennis/

&#x20;   

&#x20;   Process:

&#x20;       1. Navigate to tennis results page

&#x20;       2. Filter by date (match\_date)

&#x20;       3. Search for match using player last names

&#x20;       4. Extract winner and score

&#x20;   

&#x20;   Challenge: FlashScore is heavily JavaScript-based

&#x20;   

&#x20;   Strategy for Phase 1:

&#x20;       1. Use requests to get initial page

&#x20;       2. Look for match in static HTML

&#x20;       3. If not found, use Selenium as fallback

&#x20;   

&#x20;   Process (Detailed):

&#x20;       1. Build results URL with date parameter

&#x20;       2. Send GET request

&#x20;       3. Parse HTML for match events

&#x20;       4. For each match:

&#x20;          a. Extract home/away player names

&#x20;          b. Use fuzzy\_match\_player() to find our match

&#x20;          c. Extract score

&#x20;          d. Determine winner (player with more sets won)

&#x20;       5. smart\_delay()

&#x20;   

&#x20;   Return: Tuple of (actual\_winner\_name, match\_score)

&#x20;       Example: ("Rafael Nadal", "6-4, 6-3")

&#x20;       OR (None, None) if not found

&#x20;   

&#x20;   Error Handling:

&#x20;       - Return (None, None) if match not found (not an error - maybe not played yet)

&#x20;       - Log warning if found multiple potential matches

&#x20;       - Try alternate date (±1 day) if exact date fails



main() -> None

&#x20;   """Main execution function"""

&#x20;   

&#x20;   Process:

&#x20;       1. Call database.get\_matches\_needing\_results(days\_ago=2)

&#x20;       2. For each match:

&#x20;          a. Call scrape\_flashscore\_result()

&#x20;          b. If found:

&#x20;             - Call database.update\_match\_result()

&#x20;             - Increment success counter

&#x20;          c. If not found:

&#x20;             - Log warning (match may not have been played)

&#x20;       3. Call database.log\_scrape() with statistics

&#x20;       4. Print summary

```



\*\*HTML Selectors\*\* (approximate - will need testing):

```python

\# FlashScore uses dynamic IDs, look for:

MATCH\_EVENTS = 'div.event\_\_match'  # or similar

PARTICIPANT\_HOME = 'div.event\_\_participant--home'

PARTICIPANT\_AWAY = 'div.event\_\_participant--away'

SCORE = 'div.event\_\_score'

```



\---



\## 🤖 AUTOMATION SPECIFICATIONS



\### \*\*Workflow 1: .github/workflows/scrape\_predictions.yml\*\*



\*\*Purpose\*\*: Daily scraping of new predictions and odds



```yaml

name: Scrape Predictions \& Odds



on:

&#x20; schedule:

&#x20;   - cron: '0 6 \* \* \*'  # 6:00 AM UTC daily (adjust for tournament schedules)

&#x20; workflow\_dispatch:     # Allow manual triggering



jobs:

&#x20; scrape-predictions:

&#x20;   runs-on: ubuntu-latest

&#x20;   timeout-minutes: 15  # Prevent runaway jobs

&#x20;   

&#x20;   steps:

&#x20;     - name: Checkout code

&#x20;       uses: actions/checkout@v3

&#x20;     

&#x20;     - name: Setup Python 3.11

&#x20;       uses: actions/setup-python@v4

&#x20;       with:

&#x20;         python-version: '3.11'

&#x20;         cache: 'pip'

&#x20;     

&#x20;     - name: Install dependencies

&#x20;       run: |

&#x20;         pip install --upgrade pip

&#x20;         pip install -r requirements.txt

&#x20;     

&#x20;     - name: Run prediction scraper

&#x20;       env:

&#x20;         NEON\_DATABASE\_URL: ${{ secrets.NEON\_DATABASE\_URL }}

&#x20;         LOG\_LEVEL: INFO

&#x20;       run: |

&#x20;         python -m src.scrapers.matchstat

&#x20;     

&#x20;     - name: Upload logs (on failure)

&#x20;       if: failure()

&#x20;       uses: actions/upload-artifact@v3

&#x20;       with:

&#x20;         name: scraper-logs

&#x20;         path: logs/

&#x20;         retention-days: 7

```



\*\*Secrets Required\*\* (add to GitHub repo settings):

\- `NEON\_DATABASE\_URL`: PostgreSQL connection string



\---



\### \*\*Workflow 2: .github/workflows/scrape\_results.yml\*\*



\*\*Purpose\*\*: Daily scraping of match results



```yaml

name: Scrape Match Results



on:

&#x20; schedule:

&#x20;   - cron: '0 22 \* \* \*'  # 10:00 PM UTC daily (after most matches finish)

&#x20; workflow\_dispatch:



jobs:

&#x20; scrape-results:

&#x20;   runs-on: ubuntu-latest

&#x20;   timeout-minutes: 15

&#x20;   

&#x20;   steps:

&#x20;     - name: Checkout code

&#x20;       uses: actions/checkout@v3

&#x20;     

&#x20;     - name: Setup Python 3.11

&#x20;       uses: actions/setup-python@v4

&#x20;       with:

&#x20;         python-version: '3.11'

&#x20;         cache: 'pip'

&#x20;     

&#x20;     - name: Install dependencies

&#x20;       run: |

&#x20;         pip install --upgrade pip

&#x20;         pip install -r requirements.txt

&#x20;     

&#x20;     - name: Run results scraper

&#x20;       env:

&#x20;         NEON\_DATABASE\_URL: ${{ secrets.NEON\_DATABASE\_URL }}

&#x20;         LOG\_LEVEL: INFO

&#x20;       run: |

&#x20;         python -m src.scrapers.flashscore

&#x20;     

&#x20;     - name: Upload logs (on failure)

&#x20;       if: failure()

&#x20;       uses: actions/upload-artifact@v3

&#x20;       with:

&#x20;         name: results-logs

&#x20;         path: logs/

&#x20;         retention-days: 7

```



\---



\### \*\*Workflow 3: .github/workflows/scrape\_closing\_odds.yml\*\* (Optional)



\*\*Purpose\*\*: Hourly odds updates to capture closing lines



```yaml

name: Capture Closing Odds



on:

&#x20; schedule:

&#x20;   - cron: '0 \* \* \* \*'  # Every hour

&#x20; workflow\_dispatch:



jobs:

&#x20; closing-odds:

&#x20;   runs-on: ubuntu-latest

&#x20;   timeout-minutes: 10

&#x20;   

&#x20;   steps:

&#x20;     - name: Checkout code

&#x20;       uses: actions/checkout@v3

&#x20;     

&#x20;     - name: Setup Python 3.11

&#x20;       uses: actions/setup-python@v4

&#x20;       with:

&#x20;         python-version: '3.11'

&#x20;         cache: 'pip'

&#x20;     

&#x20;     - name: Install dependencies

&#x20;       run: |

&#x20;         pip install --upgrade pip

&#x20;         pip install -r requirements.txt

&#x20;     

&#x20;     - name: Capture closing odds

&#x20;       env:

&#x20;         NEON\_DATABASE\_URL: ${{ secrets.NEON\_DATABASE\_URL }}

&#x20;       run: |

&#x20;         python -m src.scrapers.closing\_odds

```



\*\*Note\*\*: This workflow is optional for Phase 1. Implement after prediction/results scrapers work.



\---



\## 📊 ANALYSIS MODULE SPECIFICATIONS



\### \*\*Module 7: analysis/roi\_calculator.py\*\*



\*\*Purpose\*\*: Calculate and display ROI statistics



\*\*Required Functions\*\*:



```python

overall\_performance() -> None

&#x20;   """Display overall prediction accuracy and ROI"""

&#x20;   

&#x20;   Query:

&#x20;       SELECT COUNT(\*) as total,

&#x20;              SUM(prediction\_correct) as correct,

&#x20;              AVG(prediction\_correct) \* 100 as win\_rate,

&#x20;              SUM(roi\_prediction\_odds) as total\_roi\_prediction,

&#x20;              SUM(roi\_closing\_odds) as total\_roi\_closing,

&#x20;              AVG(roi\_prediction\_odds) as avg\_roi\_prediction,

&#x20;              AVG(roi\_closing\_odds) as avg\_roi\_closing

&#x20;       FROM predictions

&#x20;       WHERE actual\_winner\_id IS NOT NULL

&#x20;   

&#x20;   Display:

&#x20;       ═══════════════════════════════════════════

&#x20;       📊 OVERALL PERFORMANCE

&#x20;       ═══════════════════════════════════════════

&#x20;       Total Predictions: 487

&#x20;       Correct: 276

&#x20;       Win Rate: 56.67%

&#x20;       

&#x20;       ROI (Prediction-Time Odds):

&#x20;         Total: +234.50 KSH

&#x20;         Per Bet: +0.48 KSH

&#x20;         ROI %: +4.8%

&#x20;       

&#x20;       ROI (Closing Odds):

&#x20;         Total: +156.20 KSH

&#x20;         Per Bet: +0.32 KSH

&#x20;         ROI %: +3.2%

&#x20;       ═══════════════════════════════════════════



performance\_by\_surface() -> None

&#x20;   """Break down performance by court surface"""

&#x20;   

&#x20;   Query:

&#x20;       SELECT surface,

&#x20;              COUNT(\*) as predictions,

&#x20;              SUM(prediction\_correct) as correct,

&#x20;              AVG(prediction\_correct) \* 100 as win\_rate,

&#x20;              SUM(roi\_prediction\_odds) as total\_roi

&#x20;       FROM predictions

&#x20;       WHERE actual\_winner\_id IS NOT NULL

&#x20;         AND surface IS NOT NULL

&#x20;       GROUP BY surface

&#x20;       ORDER BY total\_roi DESC

&#x20;   

&#x20;   Display: Table using tabulate library



performance\_by\_tour\_type() -> None

&#x20;   """Break down by ATP/WTA/Challenger"""

&#x20;   (Similar to performance\_by\_surface)



performance\_by\_ranking\_tier() -> None

&#x20;   """Break down by player ranking tiers"""

&#x20;   

&#x20;   Tiers:

&#x20;       - Top 10 vs Top 10

&#x20;       - Top 10 vs 11-50

&#x20;       - Top 50 vs Top 50

&#x20;       - Others



best\_worst\_predictions() -> None

&#x20;   """Show 10 best and 10 worst ROI predictions"""

&#x20;   

&#x20;   Query for best:

&#x20;       SELECT player1\_name, player2\_name, predicted\_winner,

&#x20;              actual\_winner, roi\_prediction\_odds, tournament\_name

&#x20;       FROM predictions\_view

&#x20;       WHERE actual\_winner IS NOT NULL

&#x20;       ORDER BY roi\_prediction\_odds DESC

&#x20;       LIMIT 10



odds\_value\_analysis() -> None

&#x20;   """Analyze if better value at certain odds ranges"""

&#x20;   

&#x20;   Bins: <1.5, 1.5-2.0, 2.0-3.0, 3.0-5.0, >5.0

&#x20;   

&#x20;   For each bin:

&#x20;       - Count predictions

&#x20;       - Win rate

&#x20;       - Average ROI



monthly\_trend() -> None

&#x20;   """Show performance trend over time"""

&#x20;   

&#x20;   Query:

&#x20;       SELECT DATE\_TRUNC('month', prediction\_date) as month,

&#x20;              COUNT(\*) as predictions,

&#x20;              AVG(prediction\_correct) as win\_rate,

&#x20;              SUM(roi\_prediction\_odds) as monthly\_roi

&#x20;       FROM predictions

&#x20;       WHERE actual\_winner\_id IS NOT NULL

&#x20;       GROUP BY month

&#x20;       ORDER BY month



main() -> None

&#x20;   """Run all analysis functions"""

&#x20;   

&#x20;   Execution:

&#x20;       1. overall\_performance()

&#x20;       2. performance\_by\_surface()

&#x20;       3. performance\_by\_tour\_type()

&#x20;       4. performance\_by\_ranking\_tier()

&#x20;       5. odds\_value\_analysis()

&#x20;       6. monthly\_trend()

&#x20;       7. best\_worst\_predictions()

&#x20;   

&#x20;   Usage:

&#x20;       python analysis/roi\_calculator.py

```



\---



\## 📝 CONFIGURATION FILES



\### \*\*File: .env.example\*\*



```bash

\# Database

NEON\_DATABASE\_URL=postgresql://username:password@ep-xxx.neon.tech/matchstat?sslmode=require



\# Logging

LOG\_LEVEL=INFO



\# Scraping Configuration

USER\_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

REQUEST\_TIMEOUT=10

MIN\_DELAY=2.0

MAX\_DELAY=5.0



\# Future Enhancement (Phase 2)

FIRECRAWL\_API\_KEY=fc-xxxxx

```



\### \*\*File: .gitignore\*\*



```

\# Python

\_\_pycache\_\_/

\*.py\[cod]

\*$py.class

\*.so

.Python

env/

venv/

ENV/

\*.egg-info/

dist/

build/



\# Environment

.env

\*.log



\# IDE

.vscode/

.idea/

\*.swp

\*.swo



\# Data

backups/\*.csv

logs/\*.log



\# OS

.DS\_Store

Thumbs.db



\# Testing

.pytest\_cache/

htmlcov/

.coverage

```



\### \*\*File: requirements.txt\*\*



```

\# Core dependencies

requests==2.31.0

beautifulsoup4==4.12.2

lxml==5.1.0



\# Database

psycopg2-binary==2.9.9



\# Configuration

python-dotenv==1.0.0



\# Utilities

tenacity==8.2.3



\# Analysis

pandas==2.1.4

tabulate==0.9.0



\# Logging

colorlog==6.8.0



\# Testing

pytest==7.4.3



\# Selenium (fallback only - keep lightweight for now)

selenium==4.15.2

webdriver-manager==4.0.1



\# Future: Firecrawl (Phase 2)

\# firecrawl-py==0.0.5

```



\---



\## 🧪 TESTING SPECIFICATIONS



\### \*\*File: tests/test\_database.py\*\*



\*\*Purpose\*\*: Verify all database operations work correctly



```python

Test Functions Required:



test\_connection()

&#x20;   """Test database connectivity"""

&#x20;   - Call database.test\_connection()

&#x20;   - Assert returns True



test\_player\_creation()

&#x20;   """Test player CRUD operations"""

&#x20;   - Create player: "Rafael Nadal", "ESP"

&#x20;   - Assert returns player\_id (integer)

&#x20;   - Create same player again

&#x20;   - Assert returns same player\_id (no duplicate)

&#x20;   - Create player with alternate name: "R. Nadal"

&#x20;   - Assert returns same player\_id (fuzzy match)



test\_prediction\_save()

&#x20;   """Test prediction insertion"""

&#x20;   - Save complete prediction

&#x20;   - Assert returns prediction\_id

&#x20;   - Try saving same URL again

&#x20;   - Assert returns None (duplicate prevented)



test\_odds\_snapshot()

&#x20;   """Test odds storage"""

&#x20;   - Save odds with odds\_type='prediction\_time'

&#x20;   - Assert no error

&#x20;   - Save odds with odds\_type='closing'

&#x20;   - Assert both snapshots exist



test\_result\_update()

&#x20;   """Test result recording and ROI calculation"""

&#x20;   - Create prediction with odds

&#x20;   - Update with result (correct prediction)

&#x20;   - Query prediction

&#x20;   - Assert prediction\_correct = True

&#x20;   - Assert roi\_prediction\_odds > 0

&#x20;   - Update different prediction (wrong prediction)

&#x20;   - Assert roi\_prediction\_odds = -10.0



test\_get\_matches\_needing\_results()

&#x20;   """Test result query"""

&#x20;   - Create predictions with various dates

&#x20;   - Call get\_matches\_needing\_results(days\_ago=2)

&#x20;   - Assert returns only matches from 2 days ago without results



test\_scrape\_logging()

&#x20;   """Test log insertion"""

&#x20;   - Call log\_scrape() with test data

&#x20;   - Query scrape\_logs

&#x20;   - Assert log entry exists



Run Tests:

&#x20;   pytest tests/test\_database.py -v

```



\### \*\*File: tests/test\_scrapers.py\*\*



\*\*Purpose\*\*: Test scraper functions in isolation



```python

Test Functions Required:



test\_matchstat\_homepage\_parsing()

&#x20;   """Test parsing Matchstat homepage"""

&#x20;   - Load saved HTML fixture (tests/fixtures/matchstat\_homepage.html)

&#x20;   - Parse with BeautifulSoup

&#x20;   - Extract prediction cards

&#x20;   - Assert finds expected number of tennis matches

&#x20;   - Assert extracts player names correctly



test\_matchstat\_h2h\_parsing()

&#x20;   """Test parsing H2H detail page"""

&#x20;   - Load saved HTML fixture

&#x20;   - Parse prediction details

&#x20;   - Assert extracts: winner, date, tournament, surface, odds



test\_flashscore\_result\_parsing()

&#x20;   """Test parsing FlashScore results"""

&#x20;   - Load saved HTML fixture

&#x20;   - Extract match winner and score

&#x20;   - Assert correct winner identified



test\_player\_name\_cleaning()

&#x20;   """Test name normalization"""

&#x20;   - Input: "Rafael Nadal 2"

&#x20;   - Assert output: "Rafael Nadal"

&#x20;   - Input: "R. Nadal WC"

&#x20;   - Assert output: "R. Nadal"



test\_fuzzy\_player\_matching()

&#x20;   """Test player name matching"""

&#x20;   - Assert fuzzy\_match\_player("Rafael Nadal", "R. Nadal") == True

&#x20;   - Assert fuzzy\_match\_player("Nadal", "Federer") == False



test\_odds\_validation()

&#x20;   """Test odds validation"""

&#x20;   - Assert validate\_odds(1.5) == True

&#x20;   - Assert validate\_odds(0.5) == False (too low)

&#x20;   - Assert validate\_odds(150) == False (too high)



Run Tests:

&#x20;   pytest tests/test\_scrapers.py -v

```



\---



\## 📚 README.md SPECIFICATION



\*\*Required Sections\*\*:



1\. \*\*Project Overview\*\*

&#x20;  - Brief description

&#x20;  - Goal statement

&#x20;  - Timeline (6 months)



2\. \*\*Setup Instructions\*\*

&#x20;  - Prerequisites (Python 3.11+, Neon account)

&#x20;  - Step-by-step installation

&#x20;  - Environment configuration



3\. \*\*Usage\*\*

&#x20;  - How to run scrapers locally

&#x20;  - How to run analysis

&#x20;  - How to check logs



4\. \*\*Architecture\*\*

&#x20;  - Database schema diagram (link to schema.sql)

&#x20;  - Scraping workflow diagram

&#x20;  - Module descriptions



5\. \*\*Monitoring\*\*

&#x20;  - How to check scrape logs

&#x20;  - How to verify data quality

&#x20;  - Common issues and solutions



6\. \*\*Analysis\*\*

&#x20;  - How to run ROI calculations

&#x20;  - How to generate reports

&#x20;  - Example queries



7\. \*\*Development\*\*

&#x20;  - How to run tests

&#x20;  - How to add new scrapers

&#x20;  - Code style guidelines



8\. \*\*Troubleshooting\*\*

&#x20;  - Common errors

&#x20;  - Debugging tips



\---



\## 🚦 IMPLEMENTATION CHECKLIST



\### \*\*Phase 0: Setup (Day 1)\*\*

\- \[ ] Create project directory structure

\- \[ ] Initialize git repository

\- \[ ] Create virtual environment

\- \[ ] Install dependencies (pip install -r requirements.txt)

\- \[ ] Create .env file with Neon DATABASE\_URL

\- \[ ] Test database connection



\### \*\*Phase 1: Database (Day 2)\*\*

\- \[ ] Create Neon database account

\- \[ ] Run schema.sql to create tables

\- \[ ] Implement src/database.py

\- \[ ] Implement src/utils.py

\- \[ ] Run tests/test\_database.py

\- \[ ] Verify all tests pass



\### \*\*Phase 2: Prediction Scraper (Days 3-5)\*\*

\- \[ ] Implement src/scrapers/matchstat.py

\- \[ ] Test scraping homepage manually

\- \[ ] Test scraping H2H pages manually

\- \[ ] Save HTML fixtures for testing

\- \[ ] Implement tests/test\_scrapers.py

\- \[ ] Run full scraper locally (save 5-10 predictions)

\- \[ ] Verify data in database



\### \*\*Phase 3: Results Scraper (Days 6-7)\*\*

\- \[ ] Implement src/scrapers/flashscore.py

\- \[ ] Test manually with recent matches

\- \[ ] Verify results update correctly

\- \[ ] Verify ROI calculations are correct



\### \*\*Phase 4: Automation (Days 8-9)\*\*

\- \[ ] Create GitHub repository

\- \[ ] Add secrets (NEON\_DATABASE\_URL)

\- \[ ] Create .github/workflows/scrape\_predictions.yml

\- \[ ] Create .github/workflows/scrape\_results.yml

\- \[ ] Test workflows with manual trigger

\- \[ ] Verify cron schedules work



\### \*\*Phase 5: Testing \& Validation (Day 10)\*\*

\- \[ ] Run all tests: pytest tests/ -v

\- \[ ] Check logs for errors

\- \[ ] Manually verify 10 predictions in database

\- \[ ] Check odds data accuracy

\- \[ ] Verify ROI calculations



\### \*\*Phase 6: Deploy \& Monitor (Day 11)\*\*

\- \[ ] Enable automated workflows

\- \[ ] Monitor first 3 days of scraping

\- \[ ] Fix any scraping errors

\- \[ ] Document any HTML selector changes needed



\### \*\*Phase 7: First Analysis (Week 2)\*\*

\- \[ ] Implement analysis/roi\_calculator.py

\- \[ ] Wait for 30+ predictions

\- \[ ] Run first ROI analysis

\- \[ ] Generate initial report



\---



\## 🎯 PHASE 2 ENHANCEMENTS (AFTER 1 MONTH)



Once Phase 1 is stable and collecting data:



1\. \*\*Add Firecrawl Integration\*\*

&#x20;  - Replace Selenium with Firecrawl API

&#x20;  - Implement hybrid approach (requests first, Firecrawl fallback)

&#x20;  - Track Firecrawl credit usage



2\. \*\*Add Closing Odds Scraper\*\*

&#x20;  - Implement hourly odds collection

&#x20;  - Calculate roi\_closing\_odds

&#x20;  - Compare prediction-time vs closing odds performance



3\. \*\*Add Notifications\*\*

&#x20;  - Email alerts on scrape failures

&#x20;  - Daily summary emails

&#x20;  - Telegram bot (optional)



4\. \*\*Enhanced Analysis\*\*

&#x20;  - Generate PDF reports

&#x20;  - Create charts/visualizations

&#x20;  - Statistical significance testing

&#x20;  - Confidence intervals



5\. \*\*Dashboard\*\* (Optional)

&#x20;  - Streamlit app

&#x20;  - Live ROI tracking

&#x20;  - Prediction accuracy charts

&#x20;  - Deploy to Streamlit Cloud (free)



\---



\## ⚠️ IMPORTANT NOTES FOR AI CODING AGENT



\### \*\*Critical Implementation Points\*\*:



1\. \*\*Error Handling\*\*

&#x20;  - ALWAYS use try/except blocks in scrapers

&#x20;  - Log errors with full context (URL, error message, traceback)

&#x20;  - Continue processing other items if one fails

&#x20;  - Never let one failed prediction crash entire scrape



2\. \*\*Rate Limiting\*\*

&#x20;  - ALWAYS call smart\_delay() between requests

&#x20;  - Minimum 2 seconds between requests

&#x20;  - Randomize delays to appear human



3\. \*\*Data Validation\*\*

&#x20;  - ALWAYS validate data before database insert

&#x20;  - Check required fields exist

&#x20;  - Verify odds are reasonable (> 1.0)

&#x20;  - Verify predicted\_winner is one of the two players



4\. \*\*Logging\*\*

&#x20;  - Use Python logging module (not print statements)

&#x20;  - Log at appropriate levels:

&#x20;    - DEBUG: Detailed scraping steps

&#x20;    - INFO: Successful operations

&#x20;    - WARNING: Missing optional data

&#x20;    - ERROR: Failed operations

&#x20;  - Include context (player names, URLs) in log messages



5\. \*\*Database Operations\*\*

&#x20;  - ALWAYS use connection pooling (provided in database.py)

&#x20;  - ALWAYS release connections after use

&#x20;  - Use ON CONFLICT for idempotent inserts

&#x20;  - Commit transactions explicitly



6\. \*\*HTML Parsing\*\*

&#x20;  - Expect HTML structure to change

&#x20;  - Use multiple fallback selectors

&#x20;  - Log warnings when selectors fail

&#x20;  - Include sample HTML in error logs



7\. \*\*Date/Time Handling\*\*

&#x20;  - Store all times in UTC

&#x20;  - Use timezone-aware datetimes

&#x20;  - Parse multiple date formats



8\. \*\*Testing\*\*

&#x20;  - Save HTML fixtures for tests (don't hit live sites in tests)

&#x20;  - Test edge cases (missing data, malformed HTML)

&#x20;  - Test database rollback on errors



\---



\## 📖 GLOSSARY OF TENNIS TERMS



For accurate data extraction:



\- \*\*R1, R2, R3\*\*: Round 1, Round 2, Round 3

\- \*\*QF\*\*: Quarter Final

\- \*\*SF\*\*: Semi Final

\- \*\*F\*\*: Final

\- \*\*WC\*\*: Wild Card (player given special entry)

\- \*\*Q\*\*: Qualifier (won qualifying rounds)

\- \*\*LL\*\*: Lucky Loser (lost in qualifying but got main draw spot)

\- \*\*PR\*\*: Protected Ranking

\- \*\*SE\*\*: Special Exempt

\- \*\*ALT\*\*: Alternate

\- \*\*W/O\*\*: Walkover (one player couldn't play)

\- \*\*RET\*\*: Retired (player quit mid-match)



\*\*Score Format\*\*: "6-4, 7-6(3), 6-3"

\- First number = games won by player 1

\- Second number = games won by player 2

\- (3) in tiebreak = tiebreak score



\---



\*\*END OF PART 1\*\*



\---



This plan contains:

\- Complete database schema with all tables, indexes, and constraints

\- Specifications for all core modules (config, utils, database)

\- Detailed scraper specifications (Matchstat, Oddsportal, FlashScore)

\- GitHub Actions workflow specifications

\- Analysis module specifications

\- Testing requirements

\- Implementation checklist




