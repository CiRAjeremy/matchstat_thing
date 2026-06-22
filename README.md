# 🎾 Tennis Prediction Tracker

Automated system to scrape tennis match predictions from Matchstat.com, track results from FlashScore, and calculate ROI to determine if predictions are profitable.

---

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/YOUR_USERNAME/matchstat_thing.git
cd matchstat_thing
```

### 2. Create Virtual Environment
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Configure Database
1. Create a free PostgreSQL database at [Neon.tech](https://neon.tech)
2. Copy `.env.example` to `.env`
3. Update `DATABASE_URL` with your connection string:
   ```
   DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require
   ```

### 4. Initialize Database
```bash
python setup_database.py
```

### 5. Test Locally
```bash
# Test database connection
python -c "from src.database import test_connection; test_connection()"

# Run prediction scraper
python -m src.scrapers.matchstat_selenium

# Check predictions saved
python -c "from src.database import get_connection, release_connection; conn = get_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM predictions'); print(f'Predictions: {cur.fetchone()[0]}'); cur.close(); release_connection(conn)"
```

---

## 🤖 GitHub Actions Setup

### Configure Secrets
1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add secret:
   - **Name:** `DATABASE_URL`
   - **Value:** Your full connection string from `.env` file
   - Example: `postgresql://user:password@ep-xxx.neon.tech/matchstat?sslmode=require`

### Automated Schedule
- **Predictions:** 5 times/day (9 AM, 1 PM, 4 PM, 7 PM, 11 PM EAT)
- **Results:** Once daily at 1 AM EAT
- **Manual trigger:** Go to Actions tab → Select workflow → "Run workflow"

---

## 📊 How It Works

### 1. Prediction Scraping (`matchstat_selenium.py`)
- Scrapes Matchstat.com homepage for today's matches
- Visits each match's H2H page
- Extracts prediction: "Odds indicate [PLAYER] will win (X% probability)"
- Saves to database with odds and match details
- **Runs:** 5x daily to catch predictions across all timezones

### 2. Results Scraping (`flashscore.py`)
- Checks predictions from 2 days ago
- Scrapes FlashScore for match outcomes
- Updates database with actual winner and score
- Calculates ROI (10 KSH bet per prediction)
- **Runs:** Once daily

### 3. Analysis (`roi_calculator.py`)
- Calculates overall win rate and total ROI
- Performance by surface (Hard/Clay/Grass)
- Performance by tour type (ATP/WTA/Challenger)
- Monthly trends

---

## 📈 Analyzing Performance

### Overall Performance
```bash
python -c "from analysis.roi_calculator import overall_performance; overall_performance()"
```

### By Surface
```bash
python -c "from analysis.roi_calculator import performance_by_surface; performance_by_surface()"
```

### By Tour Type
```bash
python -c "from analysis.roi_calculator import performance_by_tour_type; performance_by_tour_type()"
```

### Monthly Trend
```bash
python -c "from analysis.roi_calculator import monthly_trend; monthly_trend()"
```

---

## 📁 Project Structure

```
matchstat_thing/
├── .github/workflows/       # GitHub Actions automation
│   ├── scrape_predictions.yml  # Runs 5x daily
│   └── scrape_results.yml      # Runs 1x daily
├── src/
│   ├── scrapers/
│   │   ├── matchstat_selenium.py  # Prediction scraper (Selenium)
│   │   └── flashscore.py          # Results scraper
│   ├── database.py          # All database operations
│   ├── config.py            # Configuration from .env
│   └── utils.py             # Helper functions
├── analysis/
│   └── roi_calculator.py    # Performance analysis tools
├── sql/
│   └── schema.sql           # Database schema
├── logs/
│   └── scraper.log          # Execution logs
├── .env                     # Your configuration (not in git)
├── .env.example             # Template
├── requirements.txt         # Python dependencies
├── setup_database.py        # Database initialization
├── verify_setup.py          # Test everything works
└── README.md                # This file
```

---

## 🗄️ Database Schema

### Tables
- **players** - Player names and metadata
- **predictions** - Match predictions with odds
- **odds_snapshots** - Historical odds data
- **scrape_logs** - Scraping execution logs

### Views
- **predictions_view** - Easy-to-query joined data
- **roi_summary** - Performance metrics

---

## 🐛 Troubleshooting

### "No predictions found"
**Normal!** Predictions are posted 3-24 hours before matches, typically in afternoon/evening (3-6 PM EAT). Run again later.

### "Database connection failed" (Locally)
1. Check `.env` file exists and has correct `DATABASE_URL`
2. Verify connection string includes `?sslmode=require`
3. Test: `python -c "from src.database import test_connection; test_connection()"`

### "Password authentication failed" (GitHub Actions)
1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Check `DATABASE_URL` secret exists
3. Verify it matches your `.env` file exactly (including `?sslmode=require`)
4. Update secret if needed, then re-run workflow

### GitHub Actions workflow fails
1. Go to **Actions** tab
2. Click failed workflow
3. Click **scrape-predictions** or **scrape-results** job
4. Expand steps to see error logs
5. Download artifacts for full logs

---

## 💰 Cost Analysis

### Free Tier Usage
- **Database:** Neon.tech free tier (512 MB storage, 0.5 GB data transfer)
- **GitHub Actions:** Unlimited for public repos, 2,000 min/month for private
- **Current usage:** ~300 minutes/month (15% of private repo limit)
- **Total cost:** $0/month ✅

---

## 📚 Additional Documentation

- **STATUS.md** - System status and detailed usage guide
- **SCRAPING_STRATEGY.md** - Why we scrape 5x/day (optimization analysis)
- **QUICK_SUMMARY.md** - At-a-glance reference

---

## 🎯 Expected Timeline

### Week 1
- Collect 20-25 predictions
- Results start coming in after 2 days
- Initial accuracy calculated

### Week 2-4
- 60-100 predictions collected
- ROI trends become visible
- Can identify profitable patterns (surface, tour type)

### Month 2+
- Statistical confidence improves
- Identify best bet types
- Optimize prediction selection strategy

---

## 🛠️ Development

### Run Tests
```bash
python -c "from src.database import test_connection; test_connection()"
python verify_setup.py
```

### Manual Scraping
```bash
# Predictions
python -m src.scrapers.matchstat_selenium

# Results
python -m src.scrapers.flashscore
```

### View Logs
```bash
# Windows
type logs\scraper.log

# Or open in editor
code logs\scraper.log
```

---

## 📞 Quick Commands Reference

```bash
# Activate environment
.\venv\Scripts\activate

# Test database
python -c "from src.database import test_connection; test_connection()"

# Count predictions
python -c "from src.database import get_connection, release_connection; conn = get_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM predictions'); print(f'Total: {cur.fetchone()[0]}'); cur.close(); release_connection(conn)"

# Today's predictions
python -c "from src.database import get_connection, release_connection; conn = get_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM predictions WHERE prediction_date = CURRENT_DATE'); print(f'Today: {cur.fetchone()[0]}'); cur.close(); release_connection(conn)"

# Overall performance
python -c "from analysis.roi_calculator import overall_performance; overall_performance()"

# Run scraper
python -m src.scrapers.matchstat_selenium
```

---

## 🤝 Contributing

This is a personal project, but feel free to fork and adapt for your own use!

---

## 📄 License

MIT License - Use freely!

---

## 🙏 Credits

- **Matchstat.com** - Prediction data source
- **FlashScore** - Match results data source
- **Neon.tech** - Free PostgreSQL hosting
- **GitHub Actions** - Free automation

---

**Built to track and analyze tennis prediction profitability** 🎾📊
