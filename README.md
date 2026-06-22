# 🎾 Tennis Prediction Tracker

Automated system to track tennis predictions from Matchstat.com and calculate profitability.

**Status:** ✅ Fully operational - scraping 5x/day, dashboard working, notifications ready

---

## ⚡ Quick Start (5 Minutes)

### 1. Setup

```bash
git clone https://github.com/YOUR_USERNAME/matchstat_thing.git
cd matchstat_thing
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database

1. Create free database at [Neon.tech](https://neon.tech)
2. Copy `.env.example` to `.env`
3. Add your connection string:
   ```
   DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require
   ```

### 3. Initialize & Test

```bash
python setup_database.py
python -c "from src.database import test_connection; test_connection()"
python -m src.scrapers.matchstat_selenium  # Test scraper
```

---

## 🚀 Usage

### Run Dashboard Locally

```bash
.\venv\Scripts\activate
pip install flask flask-cors  # First time only
python dashboard/api.py
```

Open: **http://localhost:5000**

### Manual Scraping

```bash
# Scrape predictions
python -m src.scrapers.matchstat_selenium

# Scrape results
python -m src.scrapers.flashscore
```

### Analysis

```bash
# Overall performance
python -c "from analysis.roi_calculator import overall_performance; overall_performance()"

# By surface (Hard/Clay/Grass)
python -c "from analysis.roi_calculator import performance_by_surface; performance_by_surface()"

# Monthly trend
python -c "from analysis.roi_calculator import monthly_trend; monthly_trend()"
```

---

## 🤖 GitHub Actions Setup

### Add Database Secret

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `DATABASE_URL`
4. Value: Your full connection string from `.env` (including `?sslmode=require`)

### Automated Schedule

- **Predictions:** 5x/day (9 AM, 1 PM, 4 PM, 7 PM, 11 PM EAT)
- **Results:** 1x/day (1 AM EAT)
- **Manual trigger:** Actions tab → Select workflow → "Run workflow"

---

## 📱 Telegram Notifications (Optional)

### Setup (10 minutes)

1. **Create bot:** Search `@BotFather` in Telegram → `/newbot`
2. **Get chat ID:** Search `@userinfobot` → `/start`
3. **Add to `.env`:**
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
4. **Test:**
   ```bash
   python -c "from src.notifications import get_notifier; get_notifier().test_connection()"
   ```

### Add to GitHub Actions

Add two more secrets:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 🐛 Troubleshooting

### "No predictions found"
**Normal!** Predictions post 3-24 hours before matches (afternoon/evening EAT). Try again later.

### "Database connection failed"
```bash
# Check .env has correct DATABASE_URL with ?sslmode=require
python -c "from src.database import test_connection; test_connection()"
```

### "Password authentication failed" (GitHub Actions)
1. Go to Settings → Secrets → Actions
2. Check `DATABASE_URL` exists and matches your `.env` file exactly
3. Must include `?sslmode=require` at the end

### Dashboard shows "Error loading data"
```bash
# Make sure API is running
python dashboard/api.py
```

---

## 📊 How It Works

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for detailed system design.

**TL;DR:**
1. GitHub Actions runs scrapers automatically
2. Selenium scrapes Matchstat for predictions (5x/day)
3. Requests scrapes FlashScore for results (1x/day)
4. PostgreSQL stores everything
5. Dashboard shows stats & charts
6. (Optional) Telegram sends notifications

---

## 📁 Project Structure

```
matchstat_thing/
├── src/
│   ├── scrapers/
│   │   ├── matchstat_selenium.py  # Prediction scraper
│   │   └── flashscore.py          # Results scraper
│   ├── database.py                # All database operations
│   ├── config.py                  # Configuration
│   ├── notifications.py           # Telegram notifications
│   └── utils.py                   # Helper functions
├── analysis/
│   └── roi_calculator.py          # Performance analysis
├── dashboard/
│   ├── index.html                 # Dashboard UI
│   └── api.py                     # API server
├── .github/workflows/             # GitHub Actions automation
├── sql/schema.sql                 # Database schema
├── README.md                      # This file
├── ARCHITECTURE.md                # System design docs
└── .kiro/rules.md                 # LLM instructions
```

---

## 💰 Cost

**$0/month** - Everything uses free tiers:
- Neon PostgreSQL: Free tier
- GitHub Actions: Unlimited for public repos
- Dashboard: Free (local) or Vercel free tier
- Telegram: Free

---

## 📞 Common Commands

```bash
# Activate environment
.\venv\Scripts\activate

# Test database
python -c "from src.database import test_connection; test_connection()"

# Count predictions today
python -c "from src.database import get_connection, release_connection; conn = get_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM predictions WHERE prediction_date = CURRENT_DATE'); print(f'Today: {cur.fetchone()[0]}'); cur.close(); release_connection(conn)"

# Run dashboard
python dashboard/api.py

# Overall stats
python -c "from analysis.roi_calculator import overall_performance; overall_performance()"
```

---

## 📚 Documentation

- **README.md** (this file) - Quick start & usage
- **ARCHITECTURE.md** - How the system works (for future you)
- **.kiro/rules.md** - Instructions for LLMs working on this project

---

## 🙏 Data Sources

- **Predictions:** [Matchstat.com](https://matchstat.com)
- **Results:** [FlashScore](https://www.flashscore.com)
- **Database:** [Neon.tech](https://neon.tech)
- **Automation:** GitHub Actions

---

**Built to determine if tennis predictions are profitable** 🎾📊
