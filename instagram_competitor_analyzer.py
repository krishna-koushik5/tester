"""
Instagram Competitor Analyzer
Fetches top performing posts from competitor accounts in the last week
"""

import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Union
import instaloader
from pathlib import Path
import io

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


class CompetitorAnalyzer:
    def __init__(self, accounts_file: str = "competitor_accounts.json"):
        """Initialize the analyzer with competitor accounts"""
        import os
        
        # Get absolute path to accounts file (for serverless/deployed environments)
        if not os.path.isabs(accounts_file):
            # Try to find the file in the current directory or parent
            script_dir = os.path.dirname(os.path.abspath(__file__))
            accounts_path = os.path.join(script_dir, accounts_file)
            if os.path.exists(accounts_path):
                accounts_file = accounts_path
            else:
                # Try parent directory
                parent_path = os.path.join(os.path.dirname(script_dir), accounts_file)
                if os.path.exists(parent_path):
                    accounts_file = parent_path
        
        print(f"📁 Loading accounts from: {accounts_file}")
        
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )
        self.accounts_file = accounts_file
        self.competitor_accounts = self.load_accounts()

    def load_accounts(self) -> List[str]:
        """Load competitor account list from JSON file"""
        try:
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                accounts = data.get("accounts", [])
                # Filter out empty strings and strip whitespace
                accounts = [acc.strip() for acc in accounts if acc and acc.strip()]
                print(
                    f"📋 Loaded {len(accounts)} accounts: {', '.join(['@' + a for a in accounts])}"
                )
                return accounts
        except FileNotFoundError:
            print(
                f"Error: {self.accounts_file} not found. Please create it with your competitor accounts."
            )
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.accounts_file}")
            sys.exit(1)

    def get_week_range(self) -> tuple:
        """Get the date range for the last 7 days"""
        from datetime import timezone

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        return start_date, end_date

    def fetch_posts_from_account(
        self, username: str, start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """Fetch posts from a specific account within date range"""
        posts = []
        import time

        start_time = time.time()
        try:
            print(f"Fetching posts from @{username}...")
            profile = instaloader.Profile.from_username(self.loader.context, username)
            print(f"   Profile loaded for @{username}, fetching posts...")

            # Limit to checking first 50 posts to speed up (most accounts post 1-10 times per week)
            # We only need to check recent posts to find last week's content
            max_posts_to_check = 50
            posts_checked = 0
            consecutive_old_posts = (
                0  # Track how many posts are older than our date range
            )

            for post in profile.get_posts():
                posts_checked += 1

                # Get post date first to check if we should continue
                post_date = post.date_utc if hasattr(post, "date_utc") else post.date
                if post_date.tzinfo is None:
                    from datetime import timezone

                    post_date = post_date.replace(tzinfo=timezone.utc)

                # Early exit: if we've seen 10 consecutive posts older than our date range, stop
                if post_date < start_date:
                    consecutive_old_posts += 1
                    if consecutive_old_posts >= 10:
                        print(
                            f"   ✓ Reached posts older than date range for @{username} (checked {posts_checked} posts)"
                        )
                        break
                else:
                    consecutive_old_posts = 0  # Reset counter if we find a recent post

                # Stop if we've checked too many posts (safety limit)
                if posts_checked > max_posts_to_check:
                    print(
                        f"   ⚠️  Reached limit of {max_posts_to_check} posts checked for @{username}"
                    )
                    break

                # Only include posts from the last week (post_date already set above)
                if start_date <= post_date <= end_date:
                    # Check if it's a carousel post
                    is_carousel = post.typename == "GraphSidecar"
                    carousel_metrics = None

                    if is_carousel:
                        # Get carousel slides and their metrics
                        try:
                            # Get the number of slides in the carousel
                            # instaloader provides mediacount for carousel posts
                            slide_count = getattr(post, "mediacount", 0)

                            # If mediacount is not available, try to get from sidecar nodes
                            if slide_count == 0:
                                try:
                                    sidecar_nodes = list(post.get_sidecar_nodes())
                                    slide_count = (
                                        len(sidecar_nodes) if sidecar_nodes else 1
                                    )
                                except:
                                    slide_count = 1

                            # For carousel posts, Instagram shows total likes for the entire carousel
                            # Individual slide likes are not publicly available via API
                            carousel_metrics = {
                                "is_carousel": True,
                                "slide_count": slide_count,
                                "total_likes": post.likes,  # Total likes for the carousel
                                "note": "Carousel posts share likes across all slides - individual slide likes not available",
                            }
                        except Exception as e:
                            print(
                                f"    Warning: Could not get carousel details: {str(e)}"
                            )
                            carousel_metrics = {
                                "is_carousel": True,
                                "slide_count": 1,
                                "total_likes": post.likes,
                            }

                    # Calculate engagement rate (likes + comments)
                    likes = post.likes
                    comments = post.comments
                    engagement = likes + comments

                    # Get video views for Reels/videos (check for all posts, not just is_video)
                    views = None
                    try:
                        # Try to get video view count (available for Reels and video posts)
                        views = getattr(post, "video_view_count", None)
                        # Alternative attribute names that might be used
                        if views is None:
                            views = getattr(post, "view_count", None)
                        if views is None:
                            views = getattr(post, "views", None)
                    except Exception as e:
                        views = None

                    # Check if it's a Reel or Video - SIMPLIFIED AND AGGRESSIVE DETECTION
                    is_reel = False
                    is_video_post = False
                    reel_indicators = []

                    try:
                        # PRIMARY CHECK: If it's marked as a video, it's either a reel or video
                        is_video_post = getattr(post, "is_video", False)

                        # Get typename (removed debug print to speed up)
                        typename = getattr(post, "typename", "")

                        if is_video_post:
                            reel_indicators.append("is_video")

                            # Check typename for more specific identification (already got it above)
                            if typename:
                                typename_lower = typename.lower()
                                # Check for various reel type names
                                if "reel" in typename_lower or typename == "GraphReel":
                                    is_reel = True
                                    reel_indicators.append("typename_reel")
                                elif typename == "GraphVideo":
                                    # GraphVideo in modern Instagram is almost always a Reel
                                    is_reel = True
                                    reel_indicators.append("GraphVideo_reel")
                                else:
                                    # Any video type - treat as reel (Instagram mostly uses Reels now)
                                    is_reel = True
                                    reel_indicators.append("video_as_reel")

                            # Check for view count (Reels typically have views)
                            if views is not None and views > 0:
                                reel_indicators.append("has_views")
                                # If it has views, it's very likely a reel
                                if not is_reel:
                                    is_reel = True
                                    reel_indicators.append("views_indicate_reel")

                            # Check for reel-specific attributes
                            if hasattr(post, "is_reel"):
                                if getattr(post, "is_reel", False):
                                    is_reel = True
                                    reel_indicators.append("is_reel_attribute")

                            # Check video duration (Reels are typically 15-90 seconds)
                            if hasattr(post, "video_duration"):
                                duration = getattr(post, "video_duration", 0)
                                if 0 < duration <= 90:  # Reels are usually short
                                    reel_indicators.append("short_duration")
                                    if not is_reel:
                                        is_reel = True
                                        reel_indicators.append(
                                            "duration_indicates_reel"
                                        )

                            # FINAL FALLBACK: If it's a video and we haven't determined it's a reel yet,
                            # treat it as a reel anyway (most modern Instagram videos are Reels)
                            if not is_reel:
                                is_reel = True
                                reel_indicators.append("default_video_to_reel")

                        # Check URL structure as additional indicator (Reels use /reel/ instead of /p/)
                        if hasattr(post, "url"):
                            post_url = post.url
                            if post_url and "/reel/" in post_url.lower():
                                is_reel = True
                                reel_indicators.append("url_pattern")

                    except Exception as e:
                        # Fallback: if it's a video, treat as reel
                        if is_video_post:
                            is_reel = True
                            reel_indicators.append("fallback_video")
                        # Silently handle reel detection errors to speed up
                        pass

                    # For reels, use views as performance metric, fallback to likes if views not available
                    reel_performance = None
                    if is_reel:
                        reel_performance = views if views is not None else likes

                    # Construct the correct URL based on post type (reels use /reel/, others use /p/)
                    if is_reel:
                        post_url = f"https://www.instagram.com/reel/{post.shortcode}/"
                    else:
                        post_url = f"https://www.instagram.com/p/{post.shortcode}/"

                    post_data = {
                        "username": username,
                        "post_url": post_url,
                        "shortcode": post.shortcode,
                        "date": post_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "likes": likes,
                        "comments": comments,
                        "engagement": engagement,
                        "views": views,  # Views for Reels/videos
                        "reel_performance": reel_performance,  # Performance metric for reels (views or likes)
                        "caption": (
                            post.caption[:100] + "..."
                            if post.caption and len(post.caption) > 100
                            else (post.caption or "No caption")
                        ),
                        "is_video": is_video_post,
                        "is_reel": is_reel,
                        "is_carousel": is_carousel,
                        "carousel_metrics": carousel_metrics,
                    }
                    posts.append(post_data)

                    post_type = (
                        "Carousel"
                        if is_carousel
                        else (
                            "Reel"
                            if is_reel
                            else ("Video" if is_video_post else "Photo")
                        )
                    )
                    carousel_info = (
                        f" ({carousel_metrics['slide_count']} slides)"
                        if is_carousel
                        else ""
                    )
                    views_info = f", {views:,} views" if views is not None else ""
                    reel_debug = (
                        f" [indicators: {', '.join(reel_indicators)}]"
                        if is_reel and reel_indicators
                        else ""
                    )
                    print(
                        f"  Found {post_type} post from {post_date.strftime('%Y-%m-%d')} - {likes} likes, {comments} comments{views_info}{carousel_info}{reel_debug}"
                    )

                # Stop if we've gone past the date range
                elif post_date < start_date:
                    break

        except instaloader.exceptions.ProfileNotExistsException:
            print(f"❌ Error: Account @{username} does not exist or is private")
            print(f"   Skipping @{username} and continuing with other accounts...")
            return []
        except instaloader.exceptions.LoginRequiredException:
            print(f"❌ Error: Account @{username} is private. Login may be required.")
            print(f"   Skipping @{username} and continuing with other accounts...")
            return []
        except instaloader.exceptions.ConnectionException as e:
            print(f"⚠️  Connection error for @{username}: {str(e)}")
            print(
                f"   This might be a rate limit. Skipping @{username} and continuing with other accounts..."
            )
            print(
                f"   💡 Tip: Wait a few minutes and try again, or reduce the number of accounts"
            )
            return []
        except Exception as e:
            print(f"❌ Error fetching posts from @{username}: {str(e)}")
            import traceback

            print(f"   Full error: {traceback.format_exc()}")
            print(f"   Skipping @{username} and continuing with other accounts...")
            return []

        elapsed_time = time.time() - start_time
        if not posts:
            print(
                f"   ℹ️  No posts found from @{username} in the last week (took {elapsed_time:.1f}s)"
            )
        else:
            print(
                f"   ✅ Found {len(posts)} posts from @{username} (took {elapsed_time:.1f}s)"
            )

        return posts

    def analyze_competitors(self) -> Dict:
        """Analyze all competitor accounts and get top posts, separated by reels and posts"""
        start_date, end_date = self.get_week_range()
        print(
            f"\nAnalyzing posts from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
        )

        all_posts = []
        successful_accounts = []
        failed_accounts = []

        print(
            f"📊 Processing {len(self.competitor_accounts)} accounts: {', '.join(['@' + a for a in self.competitor_accounts])}\n"
        )

        import time
        
        for i, account in enumerate(self.competitor_accounts):
            account = account.strip()
            print(f"\n{'='*60}")
            print(
                f"Processing account {i+1}/{len(self.competitor_accounts)}: @{account}"
            )
            print(f"{'='*60}")

            # Add delay between accounts to avoid rate limiting (except for first account)
            # Reduced delay for faster processing on Vercel (2 seconds instead of 5)
            if i > 0:
                delay_seconds = 2  # 2 second delay between accounts (reduced for Vercel timeout)
                print(f"⏳ Waiting {delay_seconds} seconds before processing next account...")
                time.sleep(delay_seconds)

            try:
                posts = self.fetch_posts_from_account(account, start_date, end_date)
                if posts:
                    print(f"✅ Found {len(posts)} posts from @{account}")
                    all_posts.extend(posts)
                    successful_accounts.append(account)
                else:
                    print(
                        f"⚠️  No posts found from @{account} in the last week (or account may be private/inaccessible)"
                    )
                    failed_accounts.append(f"{account} (no posts found)")
            except Exception as e:
                print(f"❌ Failed to process @{account}: {str(e)}")
                import traceback

                print(f"   Error details: {traceback.format_exc()}")
                failed_accounts.append(f"{account} (error: {str(e)[:50]}...)")

            # Add a small delay between accounts to avoid rate limiting
            # Minimal delay for faster processing on Vercel
            if i < len(self.competitor_accounts) - 1:
                import time

                delay = 1  # Reduced to 1 second for faster processing
                print(f"   Waiting {delay} seconds before next account...")
                time.sleep(delay)

        print(f"\n{'='*60}")
        print(f"📈 Total posts collected: {len(all_posts)}")
        print(f"{'='*60}")
        print(f"\n📋 Account Processing Summary:")
        if successful_accounts:
            print(
                f"   ✅ Successfully processed: {', '.join(['@' + a for a in successful_accounts])}"
            )
        if failed_accounts:
            print(
                f"   ❌ Failed/Skipped: {', '.join(['@' + a for a in failed_accounts])}"
            )
        print()

        # Separate reels from posts
        reels = [p for p in all_posts if p.get("is_reel")]
        posts = [p for p in all_posts if not p.get("is_reel")]

        # Sort reels by performance (views if available, otherwise likes)
        reels.sort(key=lambda x: x.get("reel_performance", 0) or 0, reverse=True)

        # Sort posts by engagement (likes + comments)
        posts.sort(key=lambda x: x["engagement"], reverse=True)

        # Limit to top 10 reels and top 10 posts
        reels = reels[:10]
        posts = posts[:10]

        return {
            "reels": reels,
            "posts": posts,
            "all": all_posts,  # Keep all for backward compatibility
        }

    def display_results(self, top_posts: List[Dict], limit: int = 10):
        """Display the top performing posts"""
        print("\n" + "=" * 80)
        print(f"TOP {min(limit, len(top_posts))} PERFORMING POSTS FROM LAST WEEK")
        print("=" * 80 + "\n")

        if not top_posts:
            print("No posts found in the last week from the specified accounts.")
            return

        for i, post in enumerate(top_posts[:limit], 1):
            print(f"{i}. @{post['username']}")
            print(f"   Date: {post['date']}")
            print(
                f"   Engagement: {post['engagement']:,} ({post['likes']:,} likes, {post['comments']:,} comments)"
            )
            print(f"   URL: {post['post_url']}")
            # Safely print caption with Unicode support
            caption = post["caption"]
            try:
                print(f"   Caption: {caption}")
            except UnicodeEncodeError:
                # Fallback: encode and replace problematic characters
                caption_safe = caption.encode("utf-8", errors="replace").decode(
                    "utf-8", errors="replace"
                )
                print(f"   Caption: {caption_safe}")

            # Display post type with carousel/reel info
            if post.get("is_carousel"):
                carousel_info = post.get("carousel_metrics", {})
                slide_count = carousel_info.get("slide_count", "N/A")
                print(f"   Type: Carousel ({slide_count} slides)")
                print(f"   Carousel Likes: {post['likes']:,} (total for all slides)")
            elif post.get("is_reel"):
                views = post.get("views")
                views_str = f" - {views:,} views" if views is not None else ""
                print(f"   Type: Reel{views_str}")
            else:
                post_type = "Video" if post.get("is_video") else "Photo"
                views = post.get("views")
                views_str = f" - {views:,} views" if views is not None else ""
                print(f"   Type: {post_type}{views_str}")
            print()

    def save_results(
        self, top_posts: List[Dict], filename: str = "competitor_analysis_results.json"
    ):
        """Save results to JSON file"""
        results = {
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "week_range": {
                "start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d"),
            },
            "total_posts_found": len(top_posts),
            "top_posts": top_posts,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to {filename}")


def main():
    """Main function"""
    analyzer = CompetitorAnalyzer()

    print("Instagram Competitor Analyzer")
    print("=" * 50)
    print(f"Analyzing {len(analyzer.competitor_accounts)} competitor accounts...")

    results = analyzer.analyze_competitors()
    reels = results["reels"]
    posts = results["posts"]
    all_posts = results["all"]

    # Display reels separately
    if reels:
        print("\n" + "=" * 80)
        print(f"TOP {min(10, len(reels))} PERFORMING REELS FROM LAST WEEK")
        print("=" * 80 + "\n")
        analyzer.display_results(reels, limit=10)

    # Display posts separately
    if posts:
        print("\n" + "=" * 80)
        print(f"TOP {min(10, len(posts))} PERFORMING POSTS FROM LAST WEEK")
        print("=" * 80 + "\n")
        analyzer.display_results(posts, limit=10)

    # Save results to file
    analyzer.save_results(all_posts)

    # Summary statistics
    if all_posts:
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(f"Total posts found: {len(all_posts)}")
        print(f"Reels: {len(reels)}")
        print(f"Posts: {len(posts)}")
        if all_posts:
            print(
                f"Average engagement: {sum(p['engagement'] for p in all_posts) / len(all_posts):.0f}"
            )
            print(f"Top engagement: {all_posts[0]['engagement']:,}")
            print(f"Accounts analyzed: {len(set(p['username'] for p in all_posts))}")


if __name__ == "__main__":
    main()
