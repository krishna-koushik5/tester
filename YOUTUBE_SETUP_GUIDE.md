# YouTube Podcast Analyzer - Setup Guide

## 📋 What You Need to Add

### Step 1: Add Your YouTube Channel URLs

**File to edit:** `youtube_competitors.json`

Replace the example channels with your actual competitor YouTube channels:

```json
{
  "channels": [
    {
      "name": "Lex Fridman Podcast",
      "url": "https://www.youtube.com/@lexfridman",
      "search_terms": ["podcast", "episode", "#"]
    },
    {
      "name": "Joe Rogan Experience",
      "url": "https://www.youtube.com/@joerogan",
      "search_terms": ["JRE", "podcast", "episode"]
    }
  ],
  "settings": {
    "transcription": {
      "method": "openai_whisper",
      "api_key": "YOUR_OPENAI_API_KEY_HERE_OR_LEAVE_EMPTY"
    },
    "summarization": {
      "method": "gemini",
      "api_key": "YOUR_GEMINI_API_KEY_HERE",
      "model": "gemini-1.5-flash"
    },
    "date_range_days": 7
  }
}
```

**⭐ Recommended (FULLY FREE):** 
- Use **YouTube transcripts** for transcription (FREE!)
- Use **Gemini** for summarization (FREE!)

**How to find YouTube channel URLs:**
- Go to the competitor's YouTube channel
- Copy the URL from the address bar
- Format should be: `https://www.youtube.com/@channelname` or `https://www.youtube.com/channel/CHANNEL_ID`

**search_terms:** Keywords to filter videos (e.g., ["podcast", "episode"]). Videos must contain at least one of these terms.

---

### Step 2: Install Required Packages

**Run this command:**
```bash
pip install -r requirements.txt
```

**What this installs:**
- `yt-dlp` - For downloading YouTube videos/audio
- `youtube-transcript-api` - For extracting FREE YouTube transcripts
- `google-generativeai` - For summarization using Gemini (FREE!)
- `openai` - Optional, for paid transcription/summarization

---

### Step 3: Get API Keys

**⭐ Fully FREE Setup (Recommended!):**

#### Use YouTube Transcripts (FREE!) + Gemini (FREE!)

**No payment required!**

1. **Transcription:** Uses YouTube's FREE automatic transcripts
   - No API key needed
   - Works for most videos with captions enabled
   - Already configured by default!

2. **Summarization:** Use Google Gemini (FREE!)
   - Get free API key at: https://aistudio.google.com/app/apikey
   - Click "Create API Key"
   - Copy your API key
   - Add to `youtube_competitors.json`:
     ```json
     "transcription": {
       "method": "youtube",
       "api_key": ""
     },
     "summarization": {
       "method": "gemini",
       "api_key": "YOUR_GEMINI_API_KEY_HERE",
       "model": "gemini-1.5-flash"
     }
     ```

**Total Cost: $0.00!** 🎉

#### Alternative Options:

**Option B: Use OpenAI (Paid)**
- For better transcription accuracy, use OpenAI Whisper
- Cost: ~$0.36 per hour of podcast
- Set `"method": "openai_whisper"` in transcription settings

**Option C: Skip Transcription**
- If transcripts not available, set `"method": "skip"`
- Still get summaries using Gemini (FREE!)

---

### Step 4: Install FFmpeg (Required for Audio Extraction)

**Windows:**
1. Download from: https://ffmpeg.org/download.html
2. Extract and add to PATH, OR
3. Install via Chocolatey: `choco install ffmpeg`
4. Install via Scoop: `scoop install ffmpeg`

**Mac:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

---

### Step 5: Test the Setup

**Run a test:**
```bash
python youtube_podcast_analyzer.py
```

**What should happen:**
1. Loads channels from `youtube_competitors.json`
2. Fetches videos from last 7 days
3. Filters by search terms
4. Downloads audio for each video
5. Transcribes using OpenAI Whisper
6. Summarizes using GPT
7. Saves results to `youtube_analysis_results.json`

---

## 🎯 How It Works

### Workflow:

1. **Channel Fetching**
   - Uses yt-dlp to get channel videos
   - Filters by date (last 7 days)
   - Filters by search terms in title/description

2. **Audio Extraction**
   - Downloads audio as MP3 (192kbps)
   - Saves to temporary directory
   - Cleans up after transcription

3. **Transcription**
   - Uses OpenAI Whisper API
   - Converts audio to text
   - Handles long videos automatically

4. **Summarization**
   - Uses GPT-4o-mini (fast, cheap)
   - Creates concise summaries
   - Extracts key topics

5. **Display**
   - Shows in web UI (YouTube tab)
   - Includes full transcript (expandable)
   - Summary and key topics

---

## ⚙️ Configuration Options

### Change Date Range:
```json
"settings": {
  "date_range_days": 14  // Last 14 days instead of 7
}
```

### Change Gemini Model:
```json
"summarization": {
  "method": "gemini",
  "model": "gemini-1.5-pro"  // More powerful (if you have Pro access)
}
```

### Or use OpenAI GPT:
```json
"summarization": {
  "method": "openai_gpt",
  "model": "gpt-4o"  // More accurate but slower and more expensive
}
```

### Use YouTube Transcripts (FREE! - Default):
```json
"transcription": {
  "method": "youtube",
  "api_key": ""  // No API key needed!
}
```

### Skip Transcription (if not available):
```json
"transcription": {
  "method": "skip",
  "api_key": ""
}
```

### Use Same API Key for Both:
```json
"settings": {
  "transcription": {
    "api_key": "sk-..."  // Same key
  },
  "summarization": {
    "api_key": "sk-..."  // Same key
  }
}
```

---

## 🐛 Troubleshooting

### "yt-dlp not installed"
```bash
pip install yt-dlp
```

### "FFmpeg not found"
- Install FFmpeg (see Step 4)
- Make sure it's in your PATH
- Restart terminal/IDE

### "API key not configured"
- **For Gemini:** Get free API key at https://aistudio.google.com/app/apikey
- **For OpenAI:** Get API key at https://platform.openai.com/api-keys
- Add to `youtube_competitors.json` in the correct field
- Gemini keys start with different format, OpenAI keys start with `sk-`

### "No videos found"
- Check channel URL is correct
- Verify channel has videos in last 7 days
- Check search terms match video titles/descriptions

### "No transcript found"
- Video may not have captions enabled
- Try a different video
- Some videos disable transcripts
- Set `"method": "skip"` if transcripts unavailable

### Videos not appearing:
- Channel URL format might be wrong
- Try using channel ID instead: `https://www.youtube.com/channel/CHANNEL_ID`
- Or handle format: `https://www.youtube.com/@channelname`

---

## 💡 Tips

1. **Start with 1-2 channels** to test before adding more
2. **Monitor API costs** - Check OpenAI usage dashboard
3. **Long podcasts take time** - 1 hour podcast = ~5-10 minutes to process
4. **Cache results** - Results saved to `youtube_analysis_results.json`
5. **Adjust search terms** - Make them specific to find podcasts only

---

## 🚀 Usage

**Web Interface:**
1. Start Flask app: `python app.py`
2. Open browser: `http://localhost:5000`
3. Click "YouTube Podcasts" tab
4. Click "Analyze YouTube Podcasts"

**Command Line:**
```bash
python youtube_podcast_analyzer.py
```

---

## 📊 Output Format

Results saved to `youtube_analysis_results.json`:
```json
{
  "podcasts": [
    {
      "video_id": "...",
      "title": "Podcast Title",
      "channel": "Channel Name",
      "url": "https://youtube.com/watch?v=...",
      "published_date": "2024-01-15 10:00:00",
      "duration": 3600,
      "views": 50000,
      "summary": "Comprehensive summary...",
      "transcript": "Full transcript...",
      "key_topics": ["Topic1", "Topic2", "Topic3"]
    }
  ],
  "stats": {
    "total_podcasts": 5,
    "total_duration": 18000,
    "channels_analyzed": 2
  }
}
```

---

## 🔒 Privacy & Terms

- **YouTube Terms:** Respect YouTube's terms of service
- **API Keys:** Never commit API keys to git (use `.env` or config files not in repo)
- **Data Storage:** Transcripts stored locally, delete if needed

---

## 📝 Next Steps

Once setup is complete:
1. ✅ Add your competitor channels
2. ✅ Add OpenAI API keys
3. ✅ Install FFmpeg
4. ✅ Test with one channel
5. ✅ View results in web UI

**Ready to start?** Edit `youtube_competitors.json` and add your channels!

