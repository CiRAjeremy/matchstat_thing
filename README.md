# 🎾 Matchstat Tennis Prediction Profitability Analysis

Automated system to track and analyze Matchstat.com tennis predictions over 6 months, measuring profitability using multiple betting strategies.

## 📊 Project Overview

- **Goal**: Determine if Matchstat predictions are profitable for betting
- **Timeline**: 6 months of data collection
- **Method**: Track predictions vs actual results, calculate ROI using odds at prediction time and closing odds
- **Use Case**: PhD research on sports prediction accuracy

## 🏗️ Architecture

```
Matchstat.com → Scraper → Neon Postgres → Analysis → Reports
     ↓              ↓            ↓             ↓          ↓
 Predictions   Odds Data    Normalized    ROI Calc   Charts
                             Storage
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.11+
- Neon PostgreSQL account (free tier) - already configured
- GitHub account (for automation)

### Installation

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Initialize database schema**
```bash
# Run the setup script
python setup_database.py
```

3. **Test database connection**
```bash
python -c "from src.database import test_connection; test_connection()"
```

## 🎮 Usage

### Run Scrapers Locally

```bash
# Scrape predictions
python -m src.scrapers.matchstat

# Scrape results (after 2 days)
python -m src.scrapers.flashscore

# Run analysis
python analysis/roi_calculator.py
```

### Deploy to GitHub Actions

1. **Push to GitHub** (if not already done)
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

2. **Add secrets to GitHub**
   - Go to repository Settings → Secrets → Actions
   - Add `DATABASE_URL` with your Neon connection string

3. **Enable workflows**
   - Workflows are in `.github/workflows/`
   - They run automatically on schedule
   - Can also trigger manually from Actions tab

## 📊 Analysis

Run analysis after collecting data:

```bash
python analysis/roi_calculator.py
```

Sample output:
```
📊 OVERALL PERFORMANCE
═══════════════════════════════════════════
Total Predictions: 487
Correct: 276
Win Rate: 56.67%

ROI (Prediction-Time Odds):
  Total: +234.50 KSH
  Per Bet: +0.48 KSH
  ROI %: +4.8%
```

## 🗂️ Project Structure

```
matchstat-scraper/
├── src/
│   ├── config.py              # Configuration
│   ├── database.py            # DB operations
│   ├── utils.py               # Helper functions
│   └── scrapers/
│       ├── matchstat.py       # Prediction scraper
│       └── flashscore.py      # Results scraper
├── analysis/
│   └── roi_calculator.py      # ROI analysis
├── sql/
│   └── schema.sql             # Database schema
├── .github/workflows/         # Automation
├── tests/                     # Unit tests
├── .env                       # Environment variables (configured)
└── requirements.txt           # Dependencies
```

## 🔍 Monitoring

Check scrape logs:
```sql
SELECT * FROM scrape_logs ORDER BY scrape_timestamp DESC LIMIT 20;
```

Check latest predictions:
```sql
SELECT * FROM predictions_view ORDER BY prediction_date DESC LIMIT 10;
```

Database statistics:
```python
from src.database import get_statistics
print(get_statistics())
```

## 🐛 Troubleshooting

### Scraper fails
- Check logs in `logs/scraper.log`
- Verify website HTML hasn't changed
- Check rate limiting

### Database connection fails
- Verify `DATABASE_URL` in `.env` is correct
- Check Neon dashboard for connection limits
- Ensure database schema is initialized

### No predictions found
- Matchstat may not have predictions for today
- Check if site structure changed
- Verify robots.txt still allows scraping

## 📝 Database Setup

The database connection string is already configured in your `.env` file. Run the setup script to initialize the schema:

```bash
python setup_database.py
```

This will create all necessary tables, indexes, views, and functions.

## 🧪 Testing

Run tests to verify everything works:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_database.py -v
```

## 📈 Next Steps

1. **Initialize Database** - Run `python setup_database.py`
2. **Test Locally** - Run `python -m src.scrapers.matchstat` to test prediction scraping
3. **Deploy to GitHub** - Push code and set up GitHub Actions secrets
4. **Monitor** - Check logs daily for first week
5. **Analyze** - After 30+ predictions, run ROI analysis

## 📄 License

MIT License

## 🙏 Acknowledgments

- Matchstat.com for predictions
- Neon for database hosting
- GitHub Actions for automation
