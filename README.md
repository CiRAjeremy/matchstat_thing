# 🎾 Tennis Prediction Tracker

Automated system to track tennis predictions from Matchstat.com and calculate profitability.

**Status:** ✅ Fully operational - Groq AI scraping (5x/day), dashboard working, notifications ready

**Scraping Method:** 🤖 Groq API with built-in web browsing (no manual scraping, no servers needed)

---

## ⚡ Quick Start (5 Minutes)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/matchstat_thing.git
cd matchstat_thing
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get Groq API Key (FREE)

1. Sign up at **[console.groq.com](https://console.groq.com)**
2. Go to **[API Keys](https://console.groq.com/keys)**
3. Click "Create API Key"
4. Copy the key (starts with `gsk_`)

### 3. Setup Database

1. Create free database at **[neon.tech](https://neon.tech)**
2. Copy connection string

### 4. Configure Environment

Copy `.env.example` to `.env` and add your credentials:

```env
DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require
GROK_API_KEY=gsk_your_groq_api_key_here

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 5. Initialize & Test

```bash
# Create database tables
python setup_database.py

# Test Groq API connection
python test_grok_api.py

# Test scraper
python run_scraper.py
```

---

## 🤖 Why Groq API?

**Previous Issues:**
- ❌ Selenium scrapers blocked by Cloudflare
- ❌ Required running Chrome headless
- ❌ Needed expensive server/VM
- ❌ Complex setup with browser drivers

**Groq Solution:**
- ✅ Built-in `visit_website` tool bypasses Cloudflare
- ✅ No browser, no headless mode, no server
- ✅ Runs in GitHub Actions for free
- ✅ Uses `groq/compound` model with web browsing
- ✅ Generous free tier

---

## 🚀 Usage

### Run Scraper

```bash
python run_scraper.py
```

This uses **Groq AI** to:
1. Visit matchstat.com automatically
2. Extract today's tennis predictions
3. Parse structured data with AI
4. Save to database

### Run Dashboard

```bash
python dashboard/api.py
```

Open: **http://localhost:5000**

### Analysis Commands

```bash
# Overall performance
python -c "from analysis.roi_calculator import overall_performance; overall_performance()"

# By surface (Hard/Clay/Grass)
python -c "from analysis.roi_calculator import performance_by_surface; performance_by_surface()"

# Monthly trend
python -c "from analysis.roi_calculator import monthly_trend; monthly_trend()"
```

---

## 🤖 GitHub Actions Setup (Automated Scraping)

### Add Secrets

1. Go to repository **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:
   - `DATABASE_URL` - Your Neon.tech connection string
   - `GROK_API_KEY` - Your Groq API key (starts with `gsk_`)
   - `TELEGRAM_BOT_TOKEN` - (Optional) For notifications
   - `TELEGRAM_CHAT_ID` - (Optional) For notifications

### Automated Schedule

**Predictions scraping:** 5x/day
- 6:00 AM UTC (9:00 AM EAT)
- 10:00 AM UTC (1:00 PM EAT)
- 1:00 PM UTC (4:00 PM EAT)
- 4:00 PM UTC (7:00 PM EAT)
- 8:00 PM UTC (11:00 PM EAT)

**Manual trigger:** 
- Go to Actions tab → "Scrape Predictions & Odds" → "Run workflow"

---

## 📱 Telegram Notifications (Optional)

### Setup

1. **Create bot:** 
   - Open Telegram, search `@BotFather`
   - Send `/newbot` and follow instructions
   - Copy the bot token

2. **Get your chat ID:**
   - Search `@userinfobot` in Telegram
   - Send `/start`
   - Copy your chat ID (the number)

3. **Add to `.env`:**
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   TELEGRAM_CHAT_ID=123456789
   ```

4. **Test:**
   ```bash
   python -c "from src.notifications import get_notifier; get_notifier().test_connection()"
   ```

---

## 🐛 Troubleshooting

### "No API key found"
```bash
# Check .env file has GROK_API_KEY (starts with gsk_)
python test_grok_api.py
```

### "Model not found: grok-2-latest"
✅ **Already fixed!** Now using correct model names:
- `groq/compound` (primary)
- `groq/compound-mini` (fallback)

### "No predictions found"
**This is normal!** Matchstat posts predictions 3-24 hours before matches. Best times to check:
- Afternoon (1-4 PM EAT)
- Evening (7-11 PM EAT)

### "Database connection failed"
```bash
# Test connection
python -c "from src.database import test_connection; test_connection()"

# Make sure DATABASE_URL ends with ?sslmode=require
```

### GitHub Actions failing
1. Check all secrets are added correctly
2. Check `GROK_API_KEY` starts with `gsk_` (not `xai-`)
3. View logs in Actions tab for specific error

---

## 📊 How It Works

**Simple workflow:**

1. **GitHub Actions** triggers 5x/day
2. **Groq AI** visits matchstat.com using built-in `visit_website` tool
3. **AI extracts** match predictions with probability percentages
4. **Parser validates** and structures the data
5. **Database** stores predictions
6. **Telegram** sends notification (optional)
7. **Dashboard** displays stats and ROI analysis

**Key advantage:** No manual scraping! Groq's `groq/compound` model has built-in web browsing that bypasses Cloudflare automatically.

---

## 📁 Project Structure

```
matchstat_thing/
├── src/
│   ├── scrapers/
│   │   ├── matchstat_grok.py      # 🤖 Groq AI scraper (ACTIVE)
│   │   ├── matchstat_selenium.py  # ⚠️ Legacy (Cloudflare blocked)
│   │   └── flashscore.py          # Results scraper (future)
│   ├── database.py                # All database operations
│   ├── config.py                  # Configuration
│   ├── notifications.py           # Telegram notifications
│   └── utils.py                   # Helper functions
├── analysis/
│   └── roi_calculator.py          # Performance analysis
├── dashboard/
│   ├── index.html                 # Dashboard UI
│   └── api.py                     # API server
├── .github/workflows/
│   └── scrape_predictions.yml     # Automated scraping
├── test_grok_api.py               # Test Groq connection
├── run_scraper.py                 # Main entry point
└── README.md                      # This file
```

---

## 💰 Cost

**$0/month** - Everything uses free tiers:
- ✅ Groq API: Generous free tier
- ✅ Neon PostgreSQL: Free tier (0.5GB storage)
- ✅ GitHub Actions: Unlimited for public repos
- ✅ Telegram: Free
- ✅ Dashboard: Free (local hosting)

---

## 📞 Common Commands

```bash
# Activate environment
.\venv\Scripts\activate

# Test Groq API
python test_grok_api.py

# Run scraper once
python run_scraper.py

# Test database
python -c "from src.database import test_connection; test_connection()"

# Run dashboard
python dashboard/api.py

# Check today's predictions
python check_data.py

# Overall stats
python -c "from analysis.roi_calculator import overall_performance; overall_performance()"
```

---

## 🔧 Technical Details

### Groq Models Used
- **Primary:** `groq/compound` - Full-featured with web browsing
- **Fallback:** `groq/compound-mini` - Lower latency, same tools

### Built-in Tools
- `visit_website` - Visits URLs and extracts content
- `web_search` - Searches the web (not currently used)

### API Endpoint
```
https://api.groq.com/openai/v1/chat/completions
```

---

## 📚 Documentation

- **README.md** - This file (quick start & usage)
- **ARCHITECTURE.md** - System design details
- **GROK_SETUP.md** - Groq API specific setup
- **test_grok_api.py** - API connection testing

---

## 🙏 Credits

- **AI:** Groq (groq/compound model)
- **Data Source:** [Matchstat.com](https://matchstat.com)
- **Database:** [Neon.tech](https://neon.tech)
- **Automation:** GitHub Actions

---

**Built to determine if tennis predictions are profitable - now fully automated with AI** 🎾🤖📊
