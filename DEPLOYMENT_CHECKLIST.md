# 🚀 Deployment Checklist

## ✅ Pre-Deployment Verification

### 1. Code Status
- [x] Groq API integration complete
- [x] One API call fetches all predictions
- [x] Database integration working
- [x] Error handling implemented
- [x] Logging configured

### 2. GitHub Repository Setup

#### Required Secrets
Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value | Status |
|-------------|-------|--------|
| `DATABASE_URL` | Your Neon PostgreSQL connection string | ⚠️ **REQUIRED** |
| `GROK_API_KEY` | Your Groq API key (starts with `gsk_`) | ⚠️ **REQUIRED** |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | ⭕ Optional |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | ⭕ Optional |

**How to add secrets:**
```
1. Go to your GitHub repo
2. Click "Settings" tab
3. Left sidebar → "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Name: DATABASE_URL
6. Value: (paste your connection string)
7. Click "Add secret"
8. Repeat for GROK_API_KEY
```

### 3. Environment Variables Format

**DATABASE_URL** (from Neon.tech):
```
postgresql://user:password@ep-xxxx.aws.neon.tech/neondb?sslmode=require
```

**GROK_API_KEY** (from console.groq.com):
```
gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**TELEGRAM_BOT_TOKEN** (from @BotFather):
```
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**TELEGRAM_CHAT_ID** (from @userinfobot):
```
123456789
```

### 4. GitHub Actions Status

After pushing code, verify:

1. **Actions tab is enabled**
   - Go to repo → "Actions" tab
   - If disabled, click "I understand my workflows, go ahead and enable them"

2. **Workflow file is detected**
   - Should see "Scrape Predictions & Odds" in the left sidebar

3. **Manual test run**
   - Click "Scrape Predictions & Odds"
   - Click "Run workflow" button
   - Select branch (usually `main`)
   - Click green "Run workflow"
   - Wait 2-3 minutes
   - Check if it succeeds ✅ or fails ❌

### 5. Scheduled Runs

Once enabled, GitHub Actions will run automatically:

| Time (UTC) | Time (EAT) | Reason |
|------------|------------|--------|
| 06:00 | 09:00 AM | Morning predictions |
| 10:00 | 01:00 PM | Afternoon check |
| 13:00 | 04:00 PM | Prime time |
| 16:00 | 07:00 PM | Evening |
| 20:00 | 11:00 PM | Late night |

**No manual intervention needed** - it just runs!

---

## 🔧 Deployment Steps

### Step 1: Commit and Push

```bash
# Make sure you're in the project directory
cd c:\-\TO-DO\matchstat_thing

# Check what will be committed
git status

# Add all changes
git add .

# Commit with message
git commit -m "Groq API integration complete - production ready"

# Push to GitHub
git push origin main
```

### Step 2: Add GitHub Secrets

```
1. Open browser → github.com/YOUR_USERNAME/matchstat_thing
2. Click "Settings" tab
3. Sidebar → "Secrets and variables" → "Actions"
4. Add DATABASE_URL (from .env file)
5. Add GROK_API_KEY (from .env file)
6. (Optional) Add TELEGRAM_BOT_TOKEN
7. (Optional) Add TELEGRAM_CHAT_ID
```

### Step 3: Enable GitHub Actions

```
1. Click "Actions" tab
2. If prompted, click "I understand my workflows, go ahead and enable them"
3. You should see "Scrape Predictions & Odds" workflow
```

### Step 4: Test Manual Run

```
1. Actions tab → "Scrape Predictions & Odds"
2. Click "Run workflow" dropdown
3. Click green "Run workflow" button
4. Wait 2-3 minutes
5. Click on the running workflow to see logs
6. Verify it completes successfully
```

### Step 5: Verify Database

After first successful run:

```bash
# Connect to database and check
python -c "from src.database import get_connection; conn = get_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM predictions'); print(f'Predictions: {cur.fetchone()[0]}')"
```

### Step 6: Monitor

```
1. GitHub Actions → Check workflow runs
2. Telegram → Get notifications (if configured)
3. Database → Query predictions table
4. Dashboard → Run locally to view data
```

---

## 🐛 Troubleshooting

### "Secrets not found"

**Error in Actions logs:**
```
Error: GROK_API_KEY not found
```

**Solution:**
1. Go to Settings → Secrets → Actions
2. Verify secret name is exactly `GROK_API_KEY` (not `GROQ_API_KEY`)
3. Re-add the secret if needed

### "Database connection failed"

**Error:**
```
psycopg2.OperationalError: connection to server failed
```

**Solution:**
1. Check DATABASE_URL includes `?sslmode=require` at the end
2. Verify connection string from Neon.tech is correct
3. Test locally first: `python -c "from src.database import test_connection; test_connection()"`

### "Rate limited (429)"

**Error in logs:**
```
WARNING - Rate limited (429) on groq/compound-mini
```

**Solution:**
- This is normal during testing
- In production (5x/day), won't happen (runs are hours apart)
- If persistent, wait 5-10 minutes and manually trigger again

### "No predictions found"

**Warning:**
```
WARNING - No predictions extracted by Grok
```

**Solution:**
- This is NORMAL - matchstat.com posts predictions hours before matches
- Best times to check: afternoon/evening EAT (1-11 PM)
- Try again later in the day
- Check logs/grok_response.txt to see what AI found

### "Workflow not running on schedule"

**Issue:** Actions tab shows no scheduled runs

**Solution:**
1. Verify Actions are enabled (Actions tab)
2. Check if there have been commits recently (GitHub requires activity)
3. Manually trigger once to activate schedules
4. Wait for next scheduled time

---

## ✅ Success Indicators

### In GitHub Actions Logs:

```
✓ Checkout repository
✓ Set up Python 3.11
✓ Install dependencies
✓ Run prediction scraper (Grok AI)
  INFO - Using Groq AI to extract ALL predictions from Matchstat in ONE call
  INFO - Trying model: groq/compound-mini
  INFO - Received response from Groq/groq/compound-mini
  INFO - Groq/groq/compound-mini extracted 12 predictions
  INFO - New predictions saved: 10
  INFO - SCRAPING COMPLETE
✓ Workflow completed successfully
```

### In Telegram (if configured):

```
🎾 10 New Predictions

✓ Found 12 total predictions
💾 Saved 10 new to database
🤖 Source: Grok AI
⏰ 04:15 PM
```

### In Database:

```sql
SELECT COUNT(*) FROM predictions;
-- Should show increasing count after each run

SELECT player1_name, player2_name, predicted_winner 
FROM predictions 
ORDER BY created_at DESC 
LIMIT 5;
-- Shows recent predictions
```

---

## 📊 Monitoring After Deployment

### Daily Checks (First Week):

1. **GitHub Actions tab** - Check if all 5 runs succeeded
2. **Telegram** - Verify notifications arrive
3. **Database** - Check prediction count is growing

### Weekly Checks:

1. **Groq Dashboard** - https://console.groq.com/usage - Check API usage
2. **Neon Dashboard** - https://neon.tech - Check database storage
3. **GitHub Actions** - Review any failed runs

### Monthly Checks:

1. **ROI Analysis** - Run dashboard to see profitability
2. **Data Quality** - Check for duplicate predictions
3. **Error Patterns** - Review logs for recurring issues

---

## 🎯 Post-Deployment Next Steps

### Immediate (After First Successful Run):

- [ ] Verify predictions saved to database
- [ ] Test dashboard locally
- [ ] Confirm Telegram notifications work

### This Week:

- [ ] Monitor all 5 daily runs
- [ ] Check for any recurring errors
- [ ] Verify no rate limiting issues

### This Month:

- [ ] Set up results scraping (optional)
- [ ] Implement ROI calculations
- [ ] Deploy dashboard to Vercel (optional)

---

## 💰 Cost Tracking

### Groq API:
- **Free tier**: 14,400 requests/day
- **Your usage**: 5 requests/day (0.03%)
- **Cost**: $0/month ✅

### Neon Database:
- **Free tier**: 0.5 GB storage
- **Your usage**: < 0.01 GB
- **Cost**: $0/month ✅

### GitHub Actions:
- **Free tier**: Unlimited for public repos
- **Your usage**: 15 minutes/day
- **Cost**: $0/month ✅

**Total Cost: $0/month** 🎉

---

## 🆘 Support

### If Something Goes Wrong:

1. **Check GitHub Actions logs** - See exact error
2. **Review GROQ_ONLY_SETUP.md** - Detailed troubleshooting
3. **Check logs/scraper.log** - Local debugging
4. **Test locally first** - `python run_scraper.py`

### Resources:

- Groq Docs: https://console.groq.com/docs
- Groq Dashboard: https://console.groq.com/usage
- Neon Dashboard: https://console.neon.tech
- GitHub Actions: https://github.com/YOUR_USERNAME/matchstat_thing/actions

---

## ✅ Final Checklist Before Push

- [ ] All code changes committed
- [ ] .env file NOT committed (check .gitignore)
- [ ] requirements.txt includes all dependencies
- [ ] GitHub secrets ready to add
- [ ] Database connection string copied
- [ ] Groq API key copied
- [ ] Read through this checklist
- [ ] Ready to push!

---

**Once you push and add secrets, everything runs automatically. No servers, no manual work!** 🚀
