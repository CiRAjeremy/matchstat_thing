# 🏗️ System Architecture

**For future you: This explains how everything works together.**

---

## 🎯 What This System Does

Tracks tennis match predictions from Matchstat.com and calculates if they're profitable:
1. **Scrapes predictions** 5x daily (catches predictions across timezones)
2. **Scrapes results** daily (2 days after match)
3. **Calculates ROI** (simulates 10 KSH bets)
4. **Shows dashboard** (web UI with charts)
5. **(Optional) Sends notifications** (Telegram alerts)

---

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Cloud)                    │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  Predictions     │         │  Results                │  │
│  │  5x daily        │         │  1x daily               │  │
│  │  9AM,1PM,4PM,    │         │  1AM EAT                │  │
│  │  7PM,11PM EAT    │         │                         │  │
│  └────────┬─────────┘         └───────────┬─────────────┘  │
└───────────┼──────────────────────────────┼─────────────────┘
            │                               │
            ▼                               ▼
    ┌───────────────┐               ┌──────────────┐
    │   Matchstat   │               │  FlashScore  │
    │  (Selenium)   │               │  (Requests)  │
    └───────┬───────┘               └──────┬───────┘
            │                              │
            │  Predictions                 │  Results
            ▼                              ▼
       ┌────────────────────────────────────────┐
       │     Neon PostgreSQL (Cloud)            │
       │  - players                             │
       │  - predictions                         │
       │  - odds_snapshots                      │
       │  - scrape_logs                         │
       └────────┬───────────────────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │   Dashboard (Local/Vercel)    │
    │   - Flask API serves data     │
    │   - HTML/JS displays charts   │
    └───────────────────────────────┘
                │
                ▼
           ┌─────────┐
           │ You! 👤 │
           └─────────┘
```

---

## 🔄 Data Flow

### Flow 1: Scraping Predictions

```
1. GitHub Actions triggers (cron schedule)
   ↓
2. src/scrapers/matchstat_selenium.py runs
   ↓
3. Opens Matchstat.com homepage (Selenium browser)
   ↓
4. Finds all matches with H2H links
   ↓
5. For each match:
   - Visit H2H page
   - Look for "Odds indicate [PLAYER] will win (X%)"
   - Extract: players, tournament, surface, odds
   ↓
6. src/database.py saves to PostgreSQL
   - get_or_create_player() → players table
   - save_prediction() → predictions table
   - save_odds_snapshot() → odds_snapshots table
   ↓
7. (Optional) src/notifications.py sends Telegram alert
   ↓
8. Log to scrape_logs table
```

### Flow 2: Scraping Results

```
1. GitHub Actions triggers (10 PM UTC daily)
   ↓
2. src/scrapers/flashscore.py runs
   ↓
3. Query database: predictions from 2 days ago without results
   ↓
4. For each match:
   - Search FlashScore for match
   - Extract: winner, score, status
   ↓
5. src/database.py updates predictions
   - update_match_result() sets actual_winner_id
   - calculate_roi() computes profit/loss
   ↓
6. (Optional) src/notifications.py sends results notification
   ↓
7. Log to scrape_logs table
```

### Flow 3: Viewing Dashboard

```
1. Run: python dashboard/api.py
   ↓
2. Flask server starts on localhost:5000
   ↓
3. User opens browser → http://localhost:5000
   ↓
4. dashboard/index.html loads
   ↓
5. JavaScript calls /api/stats
   ↓
6. dashboard/api.py queries database via src/database.py
   ↓
7. Returns JSON with:
   - Overall stats (win rate, ROI)
   - Performance by surface
   - Daily prediction counts
   - Recent predictions table
   ↓
8. Chart.js renders beautiful graphs
```

---

## 🗄️ Database Schema

### Key Tables

**players**
```sql
- id (PK)
- canonical_name (e.g., "Rafael Nadal")
- alternate_names[] (e.g., ["R. Nadal", "Nadal R."])
- country
```

**predictions**
```sql
- id (PK)
- prediction_date
- player1_id, player2_id (FK → players)
- predicted_winner_id (FK → players)
- actual_winner_id (FK → players) -- NULL until result scraped
- tournament_name, surface, tour_type
- match_datetime
- prediction_correct (boolean, calculated on result)
- roi_prediction_odds (KSH profit/loss)
- matchstat_url (UNIQUE -- prevents duplicates)
```

**odds_snapshots**
```sql
- id (PK)
- prediction_id (FK → predictions)
- bookmaker
- player1_odds, player2_odds
- odds_type ('prediction_time', 'closing', 'live_update')
```

**Key Design Decisions:**
1. **Canonical names** - Handles "Rafael Nadal" vs "R. Nadal"
2. **matchstat_url as UNIQUE** - Prevents duplicate predictions
3. **ON CONFLICT DO NOTHING** - Safe to re-scrape same match
4. **ROI calculated in database** - Single source of truth

---

## ⚙️ Critical Code Paths

### 1. Player Name Matching (`src/database.py`)

**Problem:** "Rafael Nadal" vs "R. Nadal" vs "Nadal R." are same person.

**Solution:**
```python
def get_or_create_player(name):
    canonical = clean_player_name(name)  # "Rafael Nadal"
    
    # Exact match?
    if exists(canonical): return id
    
    # Fuzzy match (same last name)?
    if last_name_match(canonical): 
        add_to_alternates()
        return existing_id
    
    # Create new player
    create(canonical, alternates=[name])
```

### 2. Prediction Scraping (`src/scrapers/matchstat_selenium.py`)

**Challenge:** JavaScript-rendered site (requests returns empty HTML)

**Solution:**
```python
# Use Selenium headless browser
driver = webdriver.Chrome(options=chrome_options)
driver.get(homepage_url)
time.sleep(5)  # Wait for JS to render

# Find match containers
containers = driver.find_elements(By.CSS_SELECTOR, 'div.match-container')

# Extract H2H links
for container in containers:
    h2h_url = container.find_element(...).get_attribute('href')
    
    # Visit detail page
    driver.get(h2h_url)
    
    # Extract prediction: "Odds indicate Nadal will win (55%)"
    text = driver.page_source
    match = re.search(r'Odds indicate (.+?) will win \((.+?)%\)', text)
```

### 3. ROI Calculation (`src/database.py`)

**Logic:**
```python
BET_AMOUNT = 10.0  # KSH per prediction

if predicted_winner == actual_winner:
    # Win: get back (odds × bet)
    roi = (predicted_odds * BET_AMOUNT) - BET_AMOUNT
    # Example: 1.86 odds → (1.86 × 10) - 10 = +8.6 KSH
else:
    # Loss: lose entire bet
    roi = -BET_AMOUNT
    # Example: -10 KSH
```

### 4. Duplicate Prevention

**Multiple scrapes per day = potential duplicates**

**Protection:**
```sql
-- Database constraint
UNIQUE (matchstat_url)

-- Insert statement
INSERT INTO predictions (...)
ON CONFLICT (matchstat_url) DO NOTHING
RETURNING id;

-- Returns NULL if duplicate → scraper logs "already exists"
```

---

## 🕒 Timing Strategy

**Why 5 scrapes per day?**

Tennis is **global** → matches in all timezones:
- 🇦🇺 Australian matches: predictions at 3-6 AM UTC
- 🇪🇺 European matches: predictions at 12-3 PM UTC
- 🇺🇸 American matches: predictions at 8-11 PM UTC

**Schedule (EAT = UTC+3):**
- 9 AM EAT (6 AM UTC) - Catch overnight predictions
- 1 PM EAT (10 AM UTC) - Pre-afternoon sweep
- **4 PM EAT (1 PM UTC)** - **PRIME TIME** (most predictions)
- 7 PM EAT (4 PM UTC) - Evening sweep
- 11 PM EAT (8 PM UTC) - Late night sweep

**Result:** ~85-95% prediction coverage (vs 70-80% with 2x/day)

**Why 2-day delay for results?**
- Day 0: Prediction made
- Day 1: Match happens
- Day 2: Result scraped (safe buffer for late/rescheduled matches)

---

## 💾 GitHub Actions Integration

**Secrets needed:**
```
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
TELEGRAM_BOT_TOKEN=123456:ABC... (optional)
TELEGRAM_CHAT_ID=123456789 (optional)
```

**Workflows:**

**`.github/workflows/scrape_predictions.yml`**
```yaml
schedule:
  - cron: '0 6 * * *'   # 9 AM EAT
  - cron: '0 10 * * *'  # 1 PM EAT
  - cron: '0 13 * * *'  # 4 PM EAT
  - cron: '0 16 * * *'  # 7 PM EAT
  - cron: '0 20 * * *'  # 11 PM EAT

steps:
  - Install Chrome/ChromeDriver (for Selenium)
  - Run: python -m src.scrapers.matchstat_selenium
```

**`.github/workflows/scrape_results.yml`**
```yaml
schedule:
  - cron: '0 22 * * *'  # 1 AM EAT (next day)

steps:
  - Run: python -m src.scrapers.flashscore
```

---

## 🚨 Error Handling Strategy

**Philosophy:** Fail gracefully, log everything, continue on errors

**Pattern used throughout:**
```python
stats = {'found': 0, 'saved': 0, 'failed': 0, 'errors': []}

try:
    # Scrape match
    prediction = scrape_match(url)
    save_prediction(prediction)
    stats['saved'] += 1
except Exception as e:
    logger.error(f"Failed: {e}")
    stats['failed'] += 1
    stats['errors'].append(str(e))
    # Continue to next match (don't crash entire scraper)

# Always log results
log_scrape(stats)
```

**Why this works:**
- 1 failed match ≠ failed scraper
- Logs show exactly what succeeded/failed
- Next run catches missed matches (idempotent)

---

## 🔌 Extension Points

**Want to add features? Hook into these:**

### 1. New Data Source
Create `src/scrapers/new_source.py`:
```python
def scrape_new_source():
    # Your logic
    return predictions

# Use same database functions:
from src.database import save_prediction
```

### 2. New Analysis
Create function in `analysis/roi_calculator.py`:
```python
def my_analysis():
    conn = get_connection()
    # Your SQL query
    return results
```

### 3. New Notification Channel
Add to `src/notifications.py`:
```python
class EmailNotifier:
    def send_message(self, text):
        # Your logic
```

---

## 🎓 Design Principles Used

1. **Idempotency** - Re-running scraper is safe (no duplicates)
2. **Single Responsibility** - Each module has one job
3. **Fail-Safe** - One error doesn't crash everything
4. **Database as Truth** - All logic in database layer
5. **Simple > Clever** - Direct code over abstractions

---

## 🛠️ Local Development

```bash
# Setup
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python setup_database.py

# Run scrapers manually
python -m src.scrapers.matchstat_selenium
python -m src.scrapers.flashscore

# Run dashboard
python dashboard/api.py

# Query database directly
python -c "from src.database import test_connection; test_connection()"
```

---

## 📝 Future Improvements (If Needed)

**Don't add unless you actually need them:**

1. **More scrapers** - Other prediction sites
2. **Closing odds** - Track odds movements
3. **ML predictions** - Compare Matchstat vs your model
4. **Bet tracking** - Track actual bets placed
5. **Multi-bookmaker** - Compare odds across bookmakers

**Remember:** Working > Perfect. Don't over-engineer.

---

**Last Updated:** June 2026  
**Complexity Score:** 🟢 Simple (Can understand after 6 months away)
