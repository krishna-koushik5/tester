# Deployment Guide - Competitor Analyzer

## ⚠️ IMPORTANT: ToS & Legal Considerations

This app uses:
- **yt-dlp**: May violate YouTube ToS (but widely used, low enforcement risk for public data)
- **instaloader**: Violates Instagram ToS (high risk of blocks)

**You can still host it**, but understand the risks.

---

## 🚀 Hosting Options

### **Option 1: Render (RECOMMENDED)**

**Pros:**
- Free tier available
- Easy Flask deployment
- Automatic HTTPS
- Good for background jobs

**Steps:**
1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. Connect GitHub repo
4. Create new "Web Service"
5. Select your repo
6. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --timeout 300`
   - **Environment**: Python 3
7. Add environment variables:
   - Set API keys in dashboard (don't commit them!)

**Free Tier Limits:**
- 750 hours/month
- Spins down after 15 min inactivity
- First request may be slow (cold start)

---

### **Option 2: Railway**

**Pros:**
- $5/month starter plan
- Always-on (no spin-down)
- Easy deployment

**Steps:**
1. Push to GitHub
2. Go to [railway.app](https://railway.app)
3. "New Project" → "Deploy from GitHub"
4. Select repo
5. Add environment variables in dashboard
6. Railway auto-detects Flask

---

### **Option 3: Fly.io**

**Pros:**
- Generous free tier
- Global edge locations
- Good performance

**Steps:**
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Run: `fly launch`
3. Follow prompts
4. Deploy: `fly deploy`

---

### **Option 4: Vercel (NOT RECOMMENDED for Flask)**

Vercel is optimized for serverless. Flask works but needs wrapper. Better to use Render/Railway.

---

## 🛡️ Mitigation Strategies

### **1. Environment Variables (REQUIRED)**

Never commit API keys! Set in hosting dashboard:

```
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

Update `app.py` or config files to read from `os.environ.get()`.

### **2. Add Rate Limiting**

Already in place, but increase delays:
- YouTube: 15s between videos
- Instagram: Add similar delays

### **3. User Authentication**

Limit access to prevent abuse:
- Add login system
- Use Flask-Login
- Or simple password protection

### **4. Error Handling**

Add graceful handling for blocks:
- If Instagram blocks, show friendly error
- Fallback to YouTube-only mode
- Log errors for monitoring

### **5. Rotating IPs (Advanced)**

For Instagram scraping:
- Use proxy services (paid)
- Rotate IPs per request
- More complex setup

---

## 📝 Deployment Checklist

- [ ] Push code to GitHub (private repo recommended)
- [ ] Remove any hardcoded API keys
- [ ] Set environment variables in hosting dashboard
- [ ] Test locally first
- [ ] Deploy to staging/test environment
- [ ] Test Instagram/YouTube scraping
- [ ] Monitor for blocks/errors
- [ ] Add error handling for ToS violations
- [ ] Set up monitoring/alerts (optional)

---

## 🔧 Configuration Files Created

1. **`render.yaml`** - Render deployment config
2. **`Procfile`** - Process file for gunicorn
3. **`requirements.txt`** - Updated with gunicorn

---

## ⚡ Quick Deploy to Render

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **On Render:**
   - New → Web Service
   - Connect GitHub
   - Select repo
   - Render will auto-detect Flask
   - Add environment variables
   - Deploy!

3. **Update `app.py` for production:**
   ```python
   if __name__ == "__main__":
       port = int(os.environ.get("PORT", 5000))
       app.run(host="0.0.0.0", port=port, debug=False)
   ```

---

## 🚨 What to Watch For

1. **Instagram Blocks:**
   - Error: "429 Too Many Requests"
   - Error: "403 Forbidden"
   - Solution: Increase delays, add proxies, or disable Instagram

2. **YouTube Blocks:**
   - Error: "HTTP Error 403: Forbidden"
   - Solution: Increase delays, update yt-dlp

3. **API Rate Limits:**
   - OpenAI/Gemini: Check your quota
   - Solution: Upgrade plan or cache results

---

## 💡 Best Practices

1. **Start Small:**
   - Test with 1-2 accounts first
   - Monitor for blocks
   - Scale gradually

2. **Monitor Logs:**
   - Check hosting dashboard logs
   - Set up alerts for errors

3. **Have Backup Plan:**
   - YouTube-only mode if Instagram fails
   - Manual data entry option
   - Alternative data sources

4. **Respect Rate Limits:**
   - Your current delays (15s) are good
   - Can increase if needed

---

## 🎯 Recommended Approach

**For Production:**
1. Host on **Render** or **Railway**
2. Start with **YouTube only** (lower risk)
3. Add Instagram later with heavy rate limiting
4. Add user authentication
5. Monitor for blocks
6. Have fallback options

**Risk Level:**
- YouTube: **Medium** (acceptable for public data)
- Instagram: **High** (likely to get blocked)

**Most Sustainable:**
Focus on YouTube analysis, use Instagram as experimental feature.

---

## 📞 Support

If deployment fails:
1. Check logs in hosting dashboard
2. Verify environment variables are set
3. Test locally first
4. Check Python version compatibility
5. Verify all dependencies install correctly

