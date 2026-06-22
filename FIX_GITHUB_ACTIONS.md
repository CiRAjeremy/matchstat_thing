# 🔧 Fix GitHub Actions Database Error

## ❌ The Error You're Seeing

```
ERROR: password authentication failed for user 'neondb_owner'
```

This means GitHub Actions can't connect to your database because the `DATABASE_URL` secret is either:
1. Not set
2. Set incorrectly
3. Missing the password or other credentials

---

## ✅ How to Fix It

### Step 1: Get Your Database URL

Open your `.env` file locally and copy the `DATABASE_URL` line. It should look like:

```
postgresql://neondb_owner:YOUR_PASSWORD_HERE@ep-green-cake-aiepzqt1-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

**Important parts:**
- `neondb_owner` - username
- `YOUR_PASSWORD_HERE` - your actual password (NOT "password")
- `ep-green-cake-aiepzqt1-pooler...` - your Neon database host
- `?sslmode=require` - MUST be included

### Step 2: Add Secret to GitHub

1. Go to your GitHub repository
2. Click **Settings** (top menu)
3. In left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** button (green button top right)
5. Fill in:
   - **Name:** `DATABASE_URL` (exactly this, all caps)
   - **Secret:** Paste your full connection string from `.env`
6. Click **Add secret**

### Step 3: Verify the Secret

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. You should see `DATABASE_URL` in the list
3. You can't view the value (for security), but you can update it if needed

### Step 4: Test the Fix

1. Go to **Actions** tab
2. Click **Scrape Match Results** workflow
3. Click **Run workflow** button (right side)
4. Select branch: `main`
5. Click green **Run workflow** button
6. Wait 30-60 seconds, then refresh
7. Check if workflow runs successfully (green checkmark)

---

## 🔍 Double-Check Your Connection String

Your connection string MUST include ALL of these:

```
postgresql://[USERNAME]:[PASSWORD]@[HOST]/[DATABASE]?sslmode=require
           ↑         ↑         ↑      ↑               ↑
           |         |         |      |               |
           |         |         |      |               Required for Neon!
           |         |         |      Database name
           |         |         Neon hostname
           |         Your actual password (from Neon dashboard)
           Username (usually neondb_owner)
```

### Common Mistakes

❌ **Missing password:**
```
postgresql://neondb_owner:@ep-xxx.neon.tech/neondb?sslmode=require
                          ↑ No password!
```

❌ **Missing `?sslmode=require`:**
```
postgresql://neondb_owner:pass@ep-xxx.neon.tech/neondb
                                                       ↑ Missing SSL mode!
```

❌ **Using example values:**
```
postgresql://username:password@ep-xxx.neon.tech/matchstat?sslmode=require
              ↑        ↑         ↑
              These are placeholders - use YOUR actual values!
```

✅ **Correct format:**
```
postgresql://neondb_owner:AbCd1234XyZ@ep-green-cake-aiepzqt1-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

---

## 🔐 Where to Find Your Credentials

### Option 1: Check Your `.env` File
Your local `.env` file already has the correct connection string (that's why it works locally!)

```bash
# Open .env file and look for this line:
DATABASE_URL=postgresql://...
```

### Option 2: Get From Neon Dashboard
1. Log in to [Neon.tech](https://neon.tech)
2. Go to your project
3. Click **Connection string**
4. Copy the **Connection string** (should include password)
5. Add `?sslmode=require` at the end if not already there

---

## 🧪 Test Locally First

Before adding to GitHub, make sure your connection string works locally:

```bash
# In your project directory
.\venv\Scripts\activate

# Test connection
python -c "from src.database import test_connection; test_connection()"
```

If this shows:
```
✅ Database connected!
PostgreSQL version: PostgreSQL 18.4...
Total predictions in database: X
```

Then your `.env` file has the correct connection string! Use that same value for GitHub secret.

If it fails, fix your `.env` first before adding to GitHub.

---

## 🎯 After Fixing

Once you've added the correct `DATABASE_URL` secret:

1. **Results scraper will work** - No more authentication errors
2. **Both workflows will run automatically** according to schedule
3. **You can manually trigger workflows** from Actions tab anytime

---

## 🆘 Still Not Working?

### Check These:

1. **Secret name is exactly `DATABASE_URL`** (all caps, underscore)
2. **No extra spaces** in the secret value
3. **Includes `?sslmode=require`** at the end
4. **Password is correct** (if unsure, reset it in Neon dashboard)
5. **Connection string is one line** (no line breaks)

### Get a Fresh Connection String:

1. Go to Neon.tech dashboard
2. Click your database
3. Look for **Reset password** or **Generate new password**
4. Copy the NEW connection string they provide
5. Update both:
   - Your local `.env` file
   - GitHub secret `DATABASE_URL`

---

## ✅ Success Indicators

You'll know it's fixed when:

1. ✅ "Scrape Match Results" workflow shows **green checkmark**
2. ✅ Logs show: `✓ Database connection pool created`
3. ✅ No more "password authentication failed" errors
4. ✅ Workflow completes successfully

---

**Once fixed, both workflows will run automatically and your predictions + results will be collected daily!** 🎾
