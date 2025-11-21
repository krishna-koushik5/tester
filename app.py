"""
Flask web application for Instagram Competitor Analyzer
"""

from flask import Flask, render_template, jsonify
from instagram_competitor_analyzer import CompetitorAnalyzer
import json
from datetime import datetime

app = Flask(__name__)

# Global analyzer instance
analyzer = None


def get_analyzer():
    """Get or create analyzer instance, reloading accounts each time"""
    global analyzer
    # Always create a new instance to ensure accounts are reloaded from file
    # This ensures we pick up any changes to competitor_accounts.json
    analyzer = CompetitorAnalyzer()
    return analyzer


@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")


@app.route("/api/analyze")
def analyze():
    """Run analysis and return results"""
    try:
        print("API: Starting analysis...")
        analyzer_instance = get_analyzer()
        print(f"API: Processing {len(analyzer_instance.competitor_accounts)} accounts")
        results = analyzer_instance.analyze_competitors()
        print("API: Analysis complete, returning results")
        reels = results.get("reels", [])
        posts = results.get("posts", [])
        all_posts = results.get("all", [])

        # Get summary statistics - always return stats even if empty
        stats = {
            "total_posts": 0,
            "average_engagement": 0,
            "top_engagement": 0,
            "accounts_analyzed": 0,
            "carousel_count": 0,
            "photo_count": 0,
            "reel_count": 0,
            "video_count": 0,
            "total_views": 0,
        }

        if all_posts:
            reel_count = len(reels)
            video_count = sum(
                1 for p in posts if p.get("is_video") and not p.get("is_reel")
            )
            total_views = sum(p.get("views", 0) or 0 for p in reels if p.get("views"))

            # Sort all_posts by engagement to get the true top engagement
            sorted_all_posts = sorted(
                all_posts, key=lambda x: x["engagement"], reverse=True
            )

            # Get top engagement from the highest engagement post (could be from reels or posts)
            top_engagement = 0
            if sorted_all_posts:
                top_engagement = sorted_all_posts[0]["engagement"]
            elif reels:
                # If no posts but reels exist, check reel performance
                top_engagement = (
                    max((r.get("reel_performance", 0) or 0) for r in reels)
                    if reels
                    else 0
                )
            elif posts:
                top_engagement = posts[0]["engagement"] if posts else 0

            stats = {
                "total_posts": len(all_posts),
                "average_engagement": (
                    round(sum(p["engagement"] for p in all_posts) / len(all_posts))
                    if all_posts
                    else 0
                ),
                "top_engagement": top_engagement,
                "accounts_analyzed": len(set(p["username"] for p in all_posts)),
                "carousel_count": sum(1 for p in posts if p.get("is_carousel")),
                "photo_count": sum(
                    1
                    for p in posts
                    if not p.get("is_carousel") and not p.get("is_video")
                ),
                "reel_count": reel_count,
                "video_count": video_count,
                "total_views": total_views,
            }

        return jsonify(
            {
                "success": True,
                "reels": reels,
                "posts": posts,
                "all": all_posts,  # For backward compatibility
                "stats": stats,
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error in /api/analyze: {str(e)}")
        print(f"Traceback: {error_details}")
        return (
            jsonify(
                {"success": False, "error": str(e), "error_details": error_details}
            ),
            500,
        )


@app.route("/api/accounts")
def get_accounts():
    """Get list of competitor accounts"""
    try:
        analyzer_instance = get_analyzer()
        return jsonify(
            {"success": True, "accounts": analyzer_instance.competitor_accounts}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    print("Starting Instagram Competitor Analyzer Web App...")
    if not debug:
        print(f"Production mode - Running on port {port}")
    else:
        print(
            f"Debug mode - Open your browser and navigate to: http://localhost:{port}"
        )
    app.run(debug=debug, host="0.0.0.0", port=port)
