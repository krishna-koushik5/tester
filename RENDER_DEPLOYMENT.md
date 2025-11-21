# Render Deployment Guide - Instagram Competitor Analyzer

## Why Render Instead of Vercel?

✅ **Free tier supports longer timeouts** (no 10-second limit)  
✅ **Better for Flask apps** with long-running processes  
✅ **Already configured** with `render.yaml`  
✅ **Free tier available** (750 hours/month)  

## Quick Deployment Steps

### Step 1: Push to GitHub (Already Done!)
Your code is already at: `https://github.com/krishna-koushik5/tester`

### Step 2: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub (easiest way)

### Step 3: Deploy Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Select the `tester` repository
4. Configure:
   - **Name**: `instagram-competitor-analyzer` (or any name)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: `.` (root)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --timeout 300 --workers 2 --threads 4`
   - **Plan**: `Free` (or `Starter` for better performance)

### Step 4: Deploy!
1. Click **"Create Web Service"**
2. Render will automatically:
   - Install dependencies
   - Build your app
   - Deploy to a live URL

### Step 5: Get Your Live URL
Once deployed, you'll get a URL like:
```
https://instagram-competitor-analyzer.onrender.com
```

## Configuration Files (Already Ready!)

✅ **`render.yaml`** - Auto-configuration file  
✅ **`Procfile`** - Process configuration  
✅ **`requirements.txt`** - Dependencies  

## Important Notes

### Free Tier Limits:
- **750 hours/month** - Plenty for personal use
- **Spins down after 15 min** of inactivity
- **First request after spin-down** may take 30-60 seconds (cold start)
- **After that**, requests are fast!

### No Environment Variables Needed!
Unlike Vercel, you don't need to set any environment variables. Everything works out of the box.

### Timeout Settings:
- **300 seconds (5 minutes)** timeout configured
- Should handle all 8 accounts easily
- Even if it takes 60-90 seconds, it's fine!

## Troubleshooting

**Slow first request?**
- Normal on free tier (cold start)
- Subsequent requests are fast

**Timeout errors?**
- Shouldn't happen with 300-second timeout
- If it does, reduce accounts or upgrade to Starter plan

**Build errors?**
- Check that all dependencies are in `requirements.txt`
- Make sure Python version is 3.11.0

**Instagram 403 errors?**
- Instagram rate limiting (normal)
- Wait 15-30 minutes and try again
- Reduce number of accounts if persistent

## Comparison: Render vs Vercel

| Feature | Render (Free) | Vercel (Free) |
|---------|---------------|---------------|
| Timeout | 300+ seconds | 10 seconds ❌ |
| Flask Support | Native ✅ | Needs wrapper |
| Cold Start | 30-60s | Fast |
| Monthly Hours | 750 | Unlimited |
| Best For | Long tasks ✅ | Quick requests |

**Verdict: Render is perfect for your Instagram analyzer!** 🎯

