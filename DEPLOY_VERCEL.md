# 🚀 Deploy Dashboard to Vercel (Free Forever)

## ✅ What You're Deploying

**A serverless dashboard that:**
- Runs 24/7 on Vercel (free tier)
- Connects directly to your Neon database
- No local server needed
- Updates automatically when you push to GitHub

---

## 📋 Prerequisites

1. ✅ GitHub repository (you have this)
2. ✅ Neon database (you have this)
3. ⏳ Vercel account (free - we'll create)

---

## 🎯 Deployment Steps (10 Minutes)

### Step 1: Create Vercel Account

1. Go to: https://vercel.com/signup
2. Click **"Continue with GitHub"**
3. Authorize Vercel to access your GitHub
4. ✅ Account created!

### Step 2: Import Your Repository

1. On Vercel dashboard, click **"Add New..."** → **"Project"**
2. Find `matchstat_thing` in the list
3. Click **"Import"**

### Step 3: Configure Project

**Root Directory:**
- Click **"Edit"** next to Root Directory
- Set to: `dashboard`
- This tells Vercel where your dashboard files are

**Environment Variables:**
- Click **"Environment Variables"**
- Add one variable:
  - **Name:** `DATABASE_URL`
  - **Value:** Your full Neon connection string from `.env`
  - Example: `postgresql://user:pass@ep-xxx.neon.tech/db?sslmode=require`

### Step 4: Deploy!

1. Click **"Deploy"**
2. Wait 1-2 minutes (Vercel builds your app)
3. ✅ **You'll get a URL like:** `https://matchstat-thing.vercel.app`

---

## 🎉 That's It!

**Your dashboard is now live at:**
`https://your-project-name.vercel.app`

**Features:**
- ✅ Accessible from anywhere (phone, tablet, laptop)
- ✅ Updates automatically (connects to your Neon DB)
- ✅ Free forever (Vercel free tier)
- ✅ HTTPS included
- ✅ Fast global CDN

---

## 🔄 Auto-Deploy on Push

**Bonus:** Whenever you push to GitHub, Vercel automatically redeploys!

```bash
git add .
git commit -m "Update dashboard"
git push
```

Vercel will detect the push and redeploy within 1 minute.

---

## 🐛 Troubleshooting

### "Build failed" Error

**Check:**
1. Root directory is set to `dashboard`
2. `DATABASE_URL` environment variable is set correctly
3. Database URL includes `?sslmode=require` at the end

### Dashboard shows "Error loading data"

**Check:**
1. Environment variable `DATABASE_URL` is correct
2. Copy exact value from your `.env` file
3. Test locally first: `python dashboard/api.py`

### Can't find repository on Vercel

1. Go to: https://vercel.com/account/login-connections
2. Reconnect GitHub
3. Grant access to `matchstat_thing` repository

---

## 📱 Using Your Dashboard

### Share with Others

Your dashboard URL is public! Share with:
- Friends
- Family
- Anyone interested in tennis predictions

**Privacy:** They can only **view** stats, not modify data.

### Bookmark on Phone

1. Open dashboard on phone browser
2. Click **"Add to Home Screen"** (iOS)
3. Or **"Install App"** (Android)
4. Now it's like a native app!

---

## 🔧 Updating Dashboard

**To make changes:**

1. Edit files in `dashboard/` folder locally
2. Test: `python dashboard/api.py`
3. Commit and push:
   ```bash
   git add dashboard/
   git commit -m "Update dashboard design"
   git push
   ```
4. Vercel auto-deploys in ~1 minute

---

## 💡 Pro Tips

### Custom Domain (Optional)

Want `tennis-tracker.yourdomain.com`?
1. Buy domain ($10-15/year)
2. Vercel → Settings → Domains
3. Add your domain
4. Follow DNS instructions

### Monitor Deployments

- Vercel dashboard shows all deployments
- See build logs if something fails
- Rollback to previous version with one click

### Performance

- Vercel caches static files globally
- Your dashboard loads fast worldwide
- No server management needed

---

## 📊 What Happens Now

```
You Push → GitHub → Vercel Auto-Deploys → Live in 60 seconds!
```

**Your workflow:**
1. GitHub Actions scrapes predictions (5x/day)
2. Saves to Neon database
3. Dashboard on Vercel reads from Neon
4. You check dashboard anytime: `https://your-app.vercel.app`

**Everything runs in the cloud - no local server needed!** ☁️

---

## ✅ Checklist

Before deploying, confirm:
- [ ] Vercel account created
- [ ] Repository connected to Vercel
- [ ] Root directory set to `dashboard`
- [ ] `DATABASE_URL` environment variable added
- [ ] Database URL includes `?sslmode=require`

After deploying, test:
- [ ] Dashboard loads
- [ ] Shows your 2 predictions
- [ ] Stats display correctly
- [ ] Charts render

---

**Ready to deploy?** Follow Step 1 above! 🚀
