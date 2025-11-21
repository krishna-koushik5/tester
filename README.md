# Instagram Competitor Analyzer

A tool to analyze your competitors' Instagram accounts and find their top-performing posts from the last week.

## Features

- Analyzes multiple competitor accounts simultaneously
- Filters posts from the last 7 days
- Ranks posts by engagement (likes + comments)
- **Detects and tracks carousel posts** with slide count and likes metrics
- Displays top performing posts with detailed metrics
- Saves results to JSON file for further analysis

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure competitor accounts:**
   - Open `competitor_accounts.json`
   - Add Instagram usernames (without @) to the `accounts` array
   - Example:
   ```json
   {
     "accounts": [
       "competitor1",
       "competitor2",
       "competitor3"
     ]
   }
   ```

## Usage

### Web Interface (Recommended)

Start the web server:
```bash
python app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

The web interface provides:
- Beautiful, modern UI with visual cards
- Real-time analysis with loading indicators
- Statistics dashboard showing key metrics
- Detailed post cards with engagement metrics
- Carousel post detection with slide counts
- Click to view posts directly on Instagram

### Command Line Interface

Alternatively, run the analyzer from command line:
```bash
python instagram_competitor_analyzer.py
```

The script will:
1. Fetch posts from all competitor accounts
2. Filter posts from the last 7 days
3. Rank them by total engagement (likes + comments)
4. Display the top 20 posts in the console
5. Save all results to `competitor_analysis_results.json`

## Output

The script displays:
- Post ranking
- Account username
- Post date and time
- Engagement metrics (likes, comments, total engagement)
- Post URL
- Caption preview
- Post type (Photo/Video/Carousel with slide count)
- Carousel metrics (for carousel posts)

Results are also saved to `competitor_analysis_results.json` for further analysis.

## Important Notes

⚠️ **Limitations:**
- Only works with **public** Instagram accounts
- Private accounts cannot be accessed without authentication
- Instagram may rate-limit requests if you analyze too many accounts
- Some accounts may have hidden like counts (these won't be accessible)

⚠️ **Rate Limiting:**
- Instagram may temporarily block requests if you make too many in a short time
- Consider adding delays between account requests if analyzing many accounts
- The tool respects Instagram's rate limits automatically

## Customization

You can modify the script to:
- Change the time range (currently 7 days)
- Adjust the number of top posts displayed
- Add more metrics (views, saves, etc.)
- Filter by post type (photos only, videos only)

## Troubleshooting

**"Account does not exist or is private":**
- Make sure the account is public
- Verify the username is correct (no @ symbol)

**"No posts found":**
- The accounts may not have posted in the last week
- Check the date range in the script

**Rate limiting errors:**
- Wait a few minutes and try again
- Reduce the number of accounts being analyzed

