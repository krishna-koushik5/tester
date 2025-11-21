# Vercel Deployment Guide for Instagram Competitor Analyzer

## Prerequisites

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

## Deployment Steps

1. **Initialize Vercel (first time only):**
   ```bash
   vercel
   ```

2. **Deploy to Production:**
   ```bash
   vercel --prod
   ```

## Important Notes

⚠️ **Flask on Vercel Limitations:**
- Vercel uses serverless functions, which have a 10-second timeout on the free tier (60 seconds on Pro)
- Long-running Instagram analysis might timeout
- Consider upgrading to Vercel Pro for longer timeouts

⚠️ **Dependencies:**
- Make sure `requirements.txt` includes all dependencies
- Vercel will automatically install dependencies during build

⚠️ **File Paths:**
- The `competitor_accounts.json` file needs to be included in deployment
- Static files in `templates/` will be included automatically

## Configuration Files

- `vercel.json` - Vercel configuration
- `api/index.py` - Serverless function handler
- `requirements.txt` - Python dependencies
- `.vercelignore` - Files to exclude from deployment

## Troubleshooting

**Timeout Errors:**
- Instagram analysis can take 30-90 seconds
- Consider using Vercel Pro for 60-second timeouts
- Or implement background job processing

**Import Errors:**
- Ensure all Python files are in the correct directory structure
- Check that `sys.path` in `api/index.py` correctly points to parent directory

**403 Errors from Instagram:**
- Instagram may rate-limit requests
- This is normal and expected
- Wait 15-30 minutes and try again

