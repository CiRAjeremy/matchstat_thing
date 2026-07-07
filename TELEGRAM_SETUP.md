# 📱 Telegram Notifications Setup Guide

Get instant alerts on your phone when predictions are scraped!

---

## 🎯 What You'll Get

**When predictions are scraped:**
```
🎾 1 New Prediction

1. T. Fritz vs A. Zverev
   📍 Tournament (Hard)
   🎯 Predicted: A. Zverev (50.5%)

⏰ 4:00 PM
```

**When results come in:**
```
📊 Results Update

✅ Correct: 8/10 (80%)
💰 ROI: +45.2 KSH ✅

✅ T. Fritz vs A. Zverev
   Predicted: A. Zverev
   Winner: A. Zverev
   ROI: +8.0 KSH

⏰ 11:00 PM
```

---

## ⚡ Quick Setup (10 Minutes)

### Step 1: Create Telegram Bot

1. Open Telegram
2. Search: `@BotFather`
3. Send: `/newbot`
4. Name it: `Tennis Tracker` (or anything)
5. Username: `your_tennis_tracker_bot` (must end with `_bot`)
6. **COPY THE TOKEN** (looks like: `1234567890:ABCdef...`)

### Step 2: Get Your Chat ID

1. Search: `@userinfobot`
2. Send: `/start`
3. **COPY YOUR ID** (looks like: `123456789`)

### Step 3: Add to `.env` File

Open `.env` and add at the end:

```env
# Telegram Notifications
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

Replace with your actual token and ID!

### Step 4: Test Locally

```bash
.\venv\Scripts\activate
python -c "from src.notifications import get_notifier; notifier = get_notifier(); notifier.test_connection()"
```

**Check your phone!** You should get: "🎾 Tennis Tracker Connected!"

### Step 5: Add to GitHub Actions

1. Go to: https://github.com/YOUR_USERNAME/matchstat_thing/settings/secrets/actions
2. Add **two secrets**:
   - Name: `TELEGRAM_BOT_TOKEN`, Value: (your token)
   - Name: `TELEGRAM_CHAT_ID`, Value: (your ID)

### Step 6: Push Changes

```bash
git add -A
git commit -m "Enable Telegram notifications"
git push
```

---

## ✅ Done!

**You'll now get notifications:**
- ✅ When new predictions are scraped (5x per day)
- ✅ When results are updated (1x per day)
- ✅ Only when there's actually new data

**No spam!** Only real updates.

---

## 🔧 Troubleshooting

### "Failed to send notification"
- Check token and chat ID are correct (no spaces)
- Make sure bot token starts with numbers, has `:`, then letters
- Chat ID is just numbers

### Not receiving messages
1. Make sure you **started a conversation** with your bot:
   - Search for your bot username in Telegram
   - Click "Start" button
2. Check `.env` file has correct values
3. Test locally first before pushing to GitHub

### Bot not found
- Username must end with `_bot`
- Search exact username from BotFather

---

## 💡 Pro Tips

### Mute Notifications at Night

In Telegram:
1. Open your bot chat
2. Click bot name → Mute
3. Choose time period or custom

### Test Anytime

```bash
python -c "from src.notifications import get_notifier; notifier = get_notifier(); notifier.send_message('Test message!')"
```

---

**That's it! You'll now get tennis prediction updates on your phone!** 🎾📱
