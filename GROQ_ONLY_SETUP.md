# 🤖 Groq API Only - Complete Setup Guide

This project is now **Groq API exclusive**. No Selenium, no manual scraping, no servers.

---

## ✅ What's Working

- ✅ Fixed model names (`groq/compound`, `groq/compound-mini`)
- ✅ Simplified prompts to avoid 413 errors
- ✅ Test script working (`test_grok_api.py`)
- ✅ Verification script (`verify_groq_setup.py`)
- ✅ GitHub Actions configured for automated scraping

---

## 🚀 Quick Setup

### 1. Get Groq API Key

1. Go to **[console.groq.com/keys](https://console.groq.com/keys)**
2. Sign up (free)
3. Click "Create API Key"
4. Copy the key (starts with `gsk_`)

**Important:** Not xAI's Grok! This is **Groq** (different company).

### 2. Configure Environment

Add to `.env`:

```env
DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require
GROK_API_KEY=gsk_your_groq_api_key_here
```

### 3. Verify Setup

```bash
# Activate environment
.\venv\Scripts\activate

# Check configuration
python verify_groq_setup.py

# Test API connection
python test_grok_api.py

# Run scraper
python run_scraper.py
```

---

## 💰 Groq Free Tier Limits

**Free tier includes:**
- 14,400 requests/day (10 requests/minute)
- Different limits per model
- Generous token limits

**Your usage:**
- 5 runs/day (scheduled)
- ~2-3 API calls per run
- **Well within free tier** ✅

**Rate limits:**
- If you hit rate limits during testing, wait a few minutes
- The free tier resets every minute
- Production usage (5x/day) will never hit limits

---

## 🔧 How It Works

### 1. Groq Models

- **Primary:** `groq/compound`
  - Full-featured model with built-in tools
  - Includes `visit_website`, `web_search`, `code_interpreter`
  - Best for complex scraping

- **Fallback:** `groq/compound-mini`
  - Lower latency, same tools
  - Used if primary is rate-limited

### 2. Built-in Tools

Groq's `groq/compound` model has **server-side tools**:

- `visit_website` - Visits URLs and extracts content (bypasses Cloudflare)
- `web_search` - Searches the web
- `code_interpreter` - Executes Python code

**No configuration needed** - just use the model and it automatically uses tools when needed!

### 3. How Scraping Works

```
1. Your script calls Groq API with: "Visit https://matchstat.com/tennis/"
2. Groq's visit_website tool fetches the page (bypasses Cloudflare)
3. AI extracts predictions from HTML
4. Returns structured JSON data
5. Script saves to database
```

---

## 📝 Files Modified for Groq-Only

### Updated Files:

1. **run_scraper.py** - Now Groq-only, no Selenium fallback
2. **src/scrapers/matchstat_grok.py** - Fixed model names, simplified prompt
3. **test_grok_api.py** - Fixed model names
4. **README.md** - Updated with Groq-only documentation
5. **.github/workflows/scrape_predictions.yml** - Already uses Groq

### New Files:

1. **verify_groq_setup.py** - Pre-flight checks
2. **GROQ_ONLY_SETUP.md** - This file

### Deprecated (Not Deleted):

- `src/scrapers/matchstat_selenium.py` - Legacy
- `src/scrapers/matchstat_selenium_v2.py` - Legacy
- `test_cloudflare_bypass.py` - No longer needed

---

## 🐛 Troubleshooting

### "Rate limited (429)"

**Cause:** You've hit the free tier limit (10 requests/minute)

**Solution:**
- Wait 1-2 minutes between test runs
- For production (GitHub Actions 5x/day), this won't happen
- The script automatically retries with backoff

### "Request Entity Too Large (413)"

**Cause:** Prompt was too long

**Status:** ✅ Fixed! Simplified prompt from 1500 to 400 characters

### "Unable to access website"

**Possible causes:**
1. `groq/compound-mini` doesn't always work - use `groq/compound`
2. Matchstat may be temporarily down
3. Rate limits exhausted

**Solution:**
- Check `logs/grok_response.txt` for details
- Try again in a few minutes
- Verify site is accessible: https://matchstat.com/tennis/

### "No predictions found"

**This is normal!** Matchstat posts predictions hours before matches.

**Best times to check:**
- Afternoon (1-4 PM EAT / 10am-1pm UTC)
- Evening (7-11 PM EAT / 4-8pm UTC)

---

## 🤖 GitHub Actions Setup

### Add Secrets

1. Go to repo **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these:

| Name | Value | Required |
|------|-------|----------|
| `DATABASE_URL` | Your Neon.tech connection string | ✅ Yes |
| `GROK_API_KEY` | Your Groq API key (starts with `gsk_`) | ✅ Yes |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | ⭕ Optional |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | ⭕ Optional |

### Schedule

The workflow runs **5 times per day**:
- 6:00 AM UTC (9:00 AM EAT)
- 10:00 AM UTC (1:00 PM EAT)
- 1:00 PM UTC (4:00 PM EAT)
- 4:00 PM UTC (7:00 PM EAT)
- 8:00 PM UTC (11:00 PM EAT)

### Manual Trigger

- Go to **Actions** tab
- Select "Scrape Predictions & Odds"
- Click "Run workflow"

---

## 📊 Expected Output

### Successful Run:

```
============================================================
MATCHSTAT SCRAPER - GROQ API
============================================================
[OK] API Key found: gsk_xxxxxx...xxxx
[*] Starting Groq AI scraper...
============================================================
INFO - Using Grok AI to extract predictions from Matchstat
INFO - Trying model: groq/compound
INFO - Sending request to Groq API...
INFO - Received response from Groq/groq/compound (length: 1847 chars)
INFO - Groq/groq/compound extracted 12 predictions

[1/12] Processing...
  Novak Djokovic vs Carlos Alcaraz
  → Predicted: Carlos Alcaraz
  NEW - Saved to database (ID: 456)

... (more predictions) ...

============================================================
SCRAPING COMPLETE
============================================================
Predictions found: 12
New predictions saved: 10
Failed/Skipped: 2
Execution time: 8.43 seconds
```

### No Predictions:

```
INFO - Groq/groq/compound-mini returned empty list
WARNING - No predictions extracted by Grok
```

**This is normal** - site may not have predictions posted yet.

---

## 🔄 What Changed from Selenium

| Before (Selenium) | After (Groq API) |
|-------------------|------------------|
| ❌ Blocked by Cloudflare | ✅ Bypasses automatically |
| ❌ Needed Chrome browser | ✅ No browser needed |
| ❌ Required server/VM | ✅ Runs in GitHub Actions |
| ❌ 5-10 minute runtime | ✅ 10-30 second runtime |
| ❌ Complex setup | ✅ Simple API calls |
| ❌ Brittle (DOM changes) | ✅ AI adapts to changes |

---

## 📚 Documentation Links

- **Groq API Docs:** https://console.groq.com/docs
- **Groq Models:** https://console.groq.com/docs/models
- **Built-in Tools:** https://console.groq.com/docs/tool-use/built-in-tools
- **API Keys:** https://console.groq.com/keys
- **Usage Dashboard:** https://console.groq.com/usage

---

## 💡 Pro Tips

1. **Test sparingly** - Free tier has rate limits, but production (5x/day) is fine
2. **Check logs** - `logs/grok_response.txt` has raw AI responses
3. **Be patient** - Matchstat updates throughout the day
4. **Monitor usage** - Check https://console.groq.com/usage
5. **Use mini as fallback** - If `groq/compound` is rate-limited, script tries `groq/compound-mini`

---

## ✅ Final Checklist

- [ ] Groq API key obtained (starts with `gsk_`)
- [ ] Added to `.env` as `GROK_API_KEY`
- [ ] Ran `python verify_groq_setup.py` (all checks pass)
- [ ] Ran `python test_grok_api.py` (both tests pass)
- [ ] Added `GROK_API_KEY` to GitHub Secrets
- [ ] Enabled GitHub Actions
- [ ] (Optional) Setup Telegram notifications

---

## 🆘 Still Having Issues?

1. **Check API key:** Must start with `gsk_` (Groq, not `xai-` from xAI)
2. **Check rate limits:** Visit https://console.groq.com/usage
3. **Check logs:** `logs/scraper.log` and `logs/grok_response.txt`
4. **Wait and retry:** Rate limits reset every minute
5. **Check site:** Visit https://matchstat.com/tennis/ manually

---

**You're all set! The scraper will run automatically 5x/day in GitHub Actions.** 🎾🤖
