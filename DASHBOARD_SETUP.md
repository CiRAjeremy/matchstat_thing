# 📊 Dashboard & Notifications Setup

## 🎯 What You're Getting

1. **📈 Live Dashboard** - Beautiful web interface showing:
   - Total predictions, win rate, ROI
   - Performance by surface (Hard/Clay/Grass)
   - Daily prediction trends
   - Recent predictions table
   
2. **📱 Telegram Notifications** - Get instant alerts on your phone:
   - New predictions scraped
   - Match results updated
   - Daily performance summary

**Cost: $0** (100% free!)

---

## Part 1: Dashboard Setup (5 minutes)

### Step 1: Install Dependencies

```bash
.\venv\Scripts\activate
pip install flask flask-cors
```

### Step 2: Run Dashboard Locally

```bash
python dashboard/api.py
```

You should see:
```
🎾 Starting dashboard server...
📊 Dashboard: http://localhost:5000
🔌 API: http://localhost:5000/api/stats
```

### Step 3: Open Dashboard

Open your browser and go to: **http://localhost:5000**

You'll see your live dashboard with all your predictions and stats!

---

## Part 2: Telegram Notifications (10 minutes)

### Step 1: Create a Telegram Bot

1. Open Telegram on your phone
2. Search for **@BotFather**
3. Send: `/start`
4. Send: `/newbot`
5. Enter a name: `Tennis Tracker` (or whatever you want)
6. Enter a username: `your_tennis_tracker_bot` (must end with `_bot`)
7. **Copy the bot token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Search for **@userinfobot** in Telegram
2. Send: `/start`
3. **Copy your Chat ID** (looks like: `123456789`)

### Step 3: Add to .env File

Open your `.env` file and add these lines at the end:

```env
# Telegram Notifications
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE
```

Replace with your actual values!

### Step 4: Test Notifications

```bash
.\venv\Scripts\activate
python -c "from src.notifications import get_notifier; notifier = get_notifier(); notifier.test_connection()"
```

You should get a message on Telegram: **"🎾 Tennis Tracker Connected!"**

✅ If you got the message, notifications are working!

---

## Part 3: Enable Auto-Notifications in GitHub Actions

Now let's make GitHub Actions send you notifications automatically!

### Option A: Manually Update Scraper Files (I'll do this for you)

I need to update the scraper files to send notifications after each run.

**Would you like me to do this now?** Just say "yes continue"

### Option B: You Add Telegram Secrets to GitHub

1. Go to your repository on GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. Add two new secrets:
   - Name: `TELEGRAM_BOT_TOKEN`, Value: (your bot token)
   - Name: `TELEGRAM_CHAT_ID`, Value: (your chat ID)

---

## 🚀 What Notifications You'll Get

### When Predictions Are Scraped:
```
🎾 3 New Predictions

1. Nadal vs Djokovic
   📍 Australian Open (Hard)
   🎯 Predicted: Nadal (55%)

2. Federer vs Murray
   📍 Wimbledon (Grass)
   🎯 Predicted: Federer (62%)

... and 1 more

⏰ 4:00 PM
```

### When Results Come In:
```
📊 Results Update

✅ Correct: 2/3 (66.7%)
💰 ROI: +12.5 KSH ✅

✅ Nadal vs Djokovic
   Predicted: Nadal
   Winner: Nadal
   ROI: +8.6 KSH

❌ Federer vs Murray
   Predicted: Federer
   Winner: Murray
   ROI: -10 KSH

⏰ 11:00 PM
```

---

## 📱 Dashboard on Mobile

The dashboard works on mobile! Just:

1. Make sure dashboard is running: `python dashboard/api.py`
2. Find your computer's local IP:
   - Windows: `ipconfig` (look for IPv4 Address like 192.168.x.x)
3. On your phone's browser, go to: `http://YOUR_IP:5000`

**Even better:** Deploy to Vercel (completely free, always accessible)

---

## 🌐 Deploy Dashboard to Vercel (Free Forever)

### Why Vercel?
- ✅ Free hosting
- ✅ Always online (24/7)
- ✅ Fast global CDN
- ✅ HTTPS included
- ✅ Access from anywhere

### Quick Deploy Steps:

I'll create a Vercel-ready version that connects directly to your database (no need for the Python API server).

**Want me to set this up?** Just say "setup vercel"

---

## 🔍 Testing Everything

### Test Dashboard:
```bash
python dashboard/api.py
# Open http://localhost:5000
```

### Test Telegram:
```bash
python -c "from src.notifications import get_notifier; n = get_notifier(); n.send_message('Test from Python!')"
```

### Test Full Flow:
```bash
# Run scraper (should send Telegram notification if configured)
python -m src.scrapers.matchstat_selenium
```

---

## 🆘 Troubleshooting

### Dashboard shows "Error loading data"
- ✅ Make sure API server is running: `python dashboard/api.py`
- ✅ Check database connection works

### No Telegram notifications
- ✅ Check `.env` has correct bot token and chat ID
- ✅ Test with: `python -c "from src.notifications import get_notifier; get_notifier().test_connection()"`
- ✅ Make sure bot token and chat ID are correct (no extra spaces)

### "Module flask not found"
```bash
.\venv\Scripts\activate
pip install flask flask-cors
```

---

## 🎯 What's Next?

1. ✅ Install Flask dependencies
2. ✅ Run dashboard locally
3. ✅ Setup Telegram bot
4. ✅ Test notifications
5. ⏳ (Optional) Deploy to Vercel for 24/7 access
6. ⏳ Add GitHub Actions integration for auto-notifications

**Ready to continue? Let me know!** 🎾
