# 🚀 Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Initialize Database

Your Neon database connection is already configured in `.env`. Run the setup script:

```bash
python setup_database.py
```

You should see:
```
✅ Connected successfully!
✅ Schema created successfully!
📊 Created tables:
  - odds_snapshots
  - players
  - predictions
  - scrape_logs
✨ Database setup complete!
```

## Step 3: Test Database Connection

```bash
python -c "from src.database import test_connection; test_connection()"
```

Expected output:
```
✅ Database connected!
PostgreSQL version: PostgreSQL 16.x...
Total predictions in database: 0
```

## Step 4: Run Your First Scrape

```bash
python -m src.scrapers.matchstat
```

This will:
- Visit Matchstat.com homepage
- Find today's tennis predictions
- Scrape detailed prediction pages
- Save predictions and odds to database

Expected output:
```
STARTING MATCHSTAT PREDICTION SCRAPER
Found 8 tennis predictions from homepage
Processing prediction 1/8...
✓ Saved prediction 1: Player1 vs Player2 → Player1
...
SCRAPE COMPLETE
Saved: 8
Status: SUCCESS
```

## Step 5: Check Your Data

Query the database to see your predictions:

```sql
SELECT * FROM predictions_view ORDER BY prediction_date DESC LIMIT 5;
```

Or using Python:
```python
from src.database import get_statistics
stats = get_statistics()
print(f"Total predictions: {stats['total_predictions']}")
```

## Step 6: Wait for Results

After 2 days, scrape match results:

```bash
python -m src.scrapers.flashscore
```

## Step 7: Run Analysis

Once you have results for some matches:

```bash
python analysis/roi_calculator.py
```

## 📊 Quick Commands Reference

```bash
# Check database status
python -c "from src.database import get_statistics; print(get_statistics())"

# Scrape predictions
python -m src.scrapers.matchstat

# Scrape results
python -m src.scrapers.flashscore

# Run analysis
python analysis/roi_calculator.py

# Run tests
pytest tests/ -v
```

## 🔧 GitHub Actions Setup

1. Push your code to GitHub
2. Go to Settings → Secrets → Actions
3. Add secret: `DATABASE_URL` (copy from your `.env` file)
4. Go to Actions tab
5. Manually trigger "Scrape Predictions" to test

## 🎯 What's Next?

1. **Monitor Daily** - Check logs for first week
2. **Wait for Data** - Need 30+ predictions with results
3. **Run Analysis** - See if Matchstat predictions are profitable!
4. **Iterate** - Adjust scrapers if site structure changes

## 🆘 Need Help?

- Check logs in `logs/scraper.log`
- Run tests: `pytest tests/ -v`
- Review README.md for detailed documentation
- Check database schema in `sql/schema.sql`

## 📝 Important Notes

- Scraper respects robots.txt and rate limits (2-5s delays)
- Database uses connection pooling for efficiency
- All timestamps stored in UTC
- ROI calculated with 10 KSH flat bet
- Duplicate predictions automatically handled (URL uniqueness)

Happy scraping! 🎾
