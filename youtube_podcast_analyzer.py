"""
YouTube Podcast Analyzer
Fetches podcasts from competitor YouTube channels, transcribes, and summarizes them
"""

import json
import sys
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import io
from collections import Counter

try:
    import yt_dlp
except ImportError:
    print("⚠️  Warning: yt-dlp not installed. Install it with: pip install yt-dlp")
    yt_dlp = None

try:
    import openai
except ImportError:
    print("⚠️  Warning: openai not installed. Install it with: pip install openai")
    openai = None

try:
    import google.generativeai as genai
except ImportError:
    print(
        "⚠️  Warning: google-generativeai not installed. Install it with: pip install google-generativeai"
    )
    genai = None


# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


class YouTubePodcastAnalyzer:
    def __init__(self, channels_file: str = "youtube_competitors.json"):
        """Initialize the analyzer with YouTube channel configurations"""
        self.channels_file = channels_file
        self.config = self.load_config()
        self.competitor_channels = self.config.get("channels", [])
        self.settings = self.config.get("settings", {})
        self.temp_dir = tempfile.mkdtemp(prefix="youtube_analyzer_")

    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(self.channels_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                channels = data.get("channels", [])
                # Filter out empty entries
                channels = [
                    ch for ch in channels if ch and (ch.get("name") or ch.get("url"))
                ]
                print(f"📋 Loaded {len(channels)} YouTube channels")
                return data
        except FileNotFoundError:
            print(f"Warning: {self.channels_file} not found. Creating template file...")
            self.create_template_file()
            return {"channels": [], "settings": {}}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {self.channels_file}")
            return {"channels": [], "settings": {}}

    def load_channels(self) -> List[Dict]:
        """Load competitor channel configurations from JSON file (backward compatibility)"""
        return self.competitor_channels

    def create_template_file(self):
        """Create a template YouTube competitors file"""
        template = {
            "channels": [
                {
                    "name": "Example Channel",
                    "url": "https://www.youtube.com/@example",
                    "search_terms": ["podcast", "episode"],
                }
            ]
        }
        with open(self.channels_file, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2)
        print(f"Created template file: {self.channels_file}")

    def get_week_range(self) -> tuple:
        """Get the date range for the last 7 days"""
        from datetime import timezone

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        return start_date, end_date

    def analyze_competitors(self) -> Dict:
        """
        Analyze all competitor YouTube channels for podcasts
        Returns: Dictionary with podcasts, stats, etc.
        """
        start_date, end_date = self.get_week_range()
        print(f"\n🔍 Analyzing podcasts from {start_date.date()} to {end_date.date()}")

        all_podcasts = []

        for channel_config in self.competitor_channels:
            channel_name = channel_config.get("name", "Unknown")
            channel_url = channel_config.get("url", "")
            search_terms = channel_config.get("search_terms", ["podcast", "episode"])

            print(f"\n📺 Processing channel: {channel_name}")
            try:
                podcasts = self.fetch_podcasts_from_channel(
                    channel_url, channel_name, start_date, end_date, search_terms
                )
                all_podcasts.extend(podcasts)
                print(f"   Found {len(podcasts)} podcast(s)")
            except Exception as e:
                print(f"   Error processing {channel_name}: {str(e)}")
                continue

        # Sort by published date (newest first)
        all_podcasts.sort(key=lambda x: x.get("published_date", ""), reverse=True)

        # Calculate stats
        stats = self.calculate_stats(all_podcasts)

        return {
            "podcasts": all_podcasts,
            "stats": stats,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def fetch_podcasts_from_channel(
        self,
        channel_url: str,
        channel_name: str,
        start_date: datetime,
        end_date: datetime,
        search_terms: List[str],
    ) -> List[Dict]:
        """
        Fetch podcasts from a YouTube channel using yt-dlp
        """
        if not yt_dlp:
            print("   ⚠️  yt-dlp not installed. Cannot fetch videos.")
            return []

        podcasts = []

        try:
            # Configure yt-dlp options - use channel videos page directly
            # Limit to fewer videos to speed up and avoid too many API calls
            ydl_opts = {
                "quiet": True,  # Reduce output
                "no_warnings": True,  # Suppress warnings
                "extract_flat": True,  # Extract flat first to avoid format testing
                "ignoreerrors": True,
                "playlistend": 20,  # Check up to 20 videos to find 3 from this week
                "skip_download": True,  # Don't download videos
            }

            # Use channel URL directly - yt-dlp handles different formats
            # For @username format, use /videos endpoint
            if "/@" in channel_url:
                channel_videos_url = channel_url.rstrip("/") + "/videos"
            elif "/channel/" in channel_url:
                channel_videos_url = channel_url.rstrip("/") + "/videos"
            else:
                channel_videos_url = channel_url

            print(f"   📺 Fetching videos from: {channel_videos_url}")

            # Fetch videos from channel
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    # Extract videos from channel videos page using flat extraction
                    # This avoids format testing which causes 403 errors
                    info = ydl.extract_info(
                        channel_videos_url, download=False, process=False
                    )

                    # Get entries from flat extraction
                    entries = []
                    if isinstance(info, dict):
                        entries = info.get("entries", [])
                        # Filter out None entries
                        if entries:
                            entries = [e for e in entries if e is not None]
                        # If entries is None or empty, try to extract from info itself
                        if not entries and "id" in info:
                            # Single video
                            entries = [info]

                    if not entries:
                        print(f"   ℹ️  No videos found for {channel_name}")
                        return []

                    print(f"   📋 Found {len(entries)} videos in flat extraction")

                    # Process videos one by one until we find 3 from this week
                    # Stop early once we have 3 matching videos to save time
                    max_podcasts_per_channel = 3  # Only get 3 podcasts per channel
                    matching_videos = []
                    videos_to_check = min(
                        20, len(entries)
                    )  # Check max 20 videos to find 3 matches

                    print(
                        f"   🔄 Checking up to {videos_to_check} videos to find {max_podcasts_per_channel} from this week..."
                    )
                    print(
                        f"   📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                    )

                    for idx, entry in enumerate(entries[:videos_to_check]):
                        # Stop if we already found 3 matching videos from this week
                        if len(matching_videos) >= max_podcasts_per_channel:
                            print(
                                f"   ✅ Found {max_podcasts_per_channel} podcasts from this week, stopping..."
                            )
                            break

                        if not entry or not isinstance(entry, dict):
                            continue

                        video_id = entry.get("id")
                        if not video_id:
                            continue

                        # Get full video info for metadata (date, title, etc.)
                        try:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            # Process with minimal options to get metadata without format testing
                            video_info_opts = {
                                "quiet": True,
                                "no_warnings": True,
                                "skip_download": True,
                                "extract_flat": False,  # Need full info for dates
                                "ignoreerrors": True,
                                # Don't test formats - just get metadata
                                "format": None,  # Don't select format
                            }
                            with yt_dlp.YoutubeDL(video_info_opts) as video_ydl:
                                # Extract info without format processing
                                video_info = video_ydl.extract_info(
                                    video_url, download=False, process=False
                                )
                                # Process only metadata, not formats
                                if video_info:
                                    video_info = video_ydl.process_ie_result(
                                        video_info, download=False
                                    )

                            if not video_info or not isinstance(video_info, dict):
                                continue

                            # Get video metadata
                            title = video_info.get("title", "")
                            upload_date_str = video_info.get("upload_date", "")

                            if not title:
                                continue

                            # Parse upload date
                            upload_date = None
                            try:
                                if upload_date_str and len(upload_date_str) >= 8:
                                    upload_date = datetime.strptime(
                                        upload_date_str[:8], "%Y%m%d"
                                    )
                                    upload_date = upload_date.replace(
                                        tzinfo=start_date.tzinfo
                                    )
                                else:
                                    timestamp = video_info.get("timestamp")
                                    if timestamp:
                                        upload_date = datetime.fromtimestamp(
                                            timestamp, tz=start_date.tzinfo
                                        )
                                    else:
                                        continue
                            except (ValueError, TypeError):
                                continue

                            # Filter by date range - must be from this week
                            if upload_date < start_date or upload_date > end_date:
                                continue

                            # Found a video from this week! Add it to the list
                            matching_videos.append(video_info)
                            print(
                                f"   ✅ Found #{len(matching_videos)}: {title[:60]}... ({upload_date.strftime('%Y-%m-%d')})"
                            )

                        except Exception as e:
                            # If processing fails, skip this video
                            continue

                    if not matching_videos:
                        print(
                            f"   ℹ️  No videos found from this week for {channel_name}"
                        )
                        return []

                    print(
                        f"   ✅ Found {len(matching_videos)} video(s) from this week, processing..."
                    )

                    # Process matching videos (already have full metadata)
                    for entry in matching_videos:
                        # Get video metadata again (already processed above)
                        video_id = entry.get("id")
                        title = entry.get("title", "")
                        description = entry.get("description", "") or ""
                        upload_date_str = entry.get("upload_date", "")
                        duration = entry.get("duration", 0) or 0
                        view_count = entry.get("view_count", 0) or 0
                        url = (
                            entry.get("webpage_url")
                            or entry.get("url")
                            or f"https://www.youtube.com/watch?v={video_id}"
                        )

                        # Parse upload date again
                        upload_date = None
                        try:
                            if upload_date_str and len(upload_date_str) >= 8:
                                upload_date = datetime.strptime(
                                    upload_date_str[:8], "%Y%m%d"
                                )
                                upload_date = upload_date.replace(
                                    tzinfo=start_date.tzinfo
                                )
                            else:
                                timestamp = entry.get("timestamp")
                                if timestamp:
                                    upload_date = datetime.fromtimestamp(
                                        timestamp, tz=start_date.tzinfo
                                    )
                        except:
                            continue

                        # Download and transcribe audio
                        print(f"   📥 Processing: {title[:60]}...")

                        podcast_data = {
                            "video_id": video_id,
                            "title": title,
                            "channel": channel_name,
                            "url": url,
                            "published_date": upload_date.strftime("%Y-%m-%d %H:%M:%S"),
                            "duration": duration,
                            "views": view_count,
                            "summary": "",
                            "transcript": "",
                            "key_topics": [],
                        }

                        # Transcribe and summarize
                        try:
                            import time

                            # Minimal delay between videos for faster processing
                            time.sleep(
                                5
                            )  # 5 second delay between videos (reduced for speed)

                            # Single attempt - no retries for faster processing
                            transcript = None
                            for attempt in range(1):  # Single attempt only
                                try:
                                    transcript = self.transcribe_video(url)

                                    # Check if video should be skipped (no English audio)
                                    if transcript == "SKIP_NO_ENGLISH":
                                        print(
                                            f"   ⏭️  Skipping video - No English audio/subtitles detected"
                                        )
                                        break  # Stop trying, skip this video

                                    if (
                                        transcript
                                        and "Error" not in transcript
                                        and "429" not in transcript
                                    ):
                                        break  # Success!
                                    else:
                                        break  # Single attempt - return immediately
                                except Exception as e:
                                    # Single attempt - return error immediately
                                    transcript = f"Error extracting transcript: {str(e)}"

                            # Skip this video if no English audio/subtitles - move to next video immediately
                            if transcript == "SKIP_NO_ENGLISH":
                                print(
                                    f"   ⏭️  Skipping video and moving to next one (non-English detected)"
                                )
                                continue  # Skip to next video in the loop

                            if (
                                transcript
                                and len(transcript.strip()) > 50
                                and "Error" not in transcript
                            ):
                                # Add delay before summarization
                                time.sleep(2)  # 2 second delay before API call

                                # Single attempt - no retries for faster processing
                                summary = None
                                for attempt in range(1):  # Single attempt only
                                    try:
                                        summary = self.summarize_transcript(transcript)
                                        if (
                                            summary
                                            and "Error" not in summary
                                            and "429" not in summary
                                        ):
                                            break  # Success!
                                        else:
                                            break  # Single attempt - return immediately
                                    except Exception as e:
                                    # Single attempt - return error immediately
                                    summary = f"Error generating summary: {str(e)}"

                                if summary and "Error" not in summary:
                                    key_topics = self.extract_key_topics(transcript)

                                    podcast_data["transcript"] = transcript
                                    podcast_data["summary"] = summary
                                    podcast_data["key_topics"] = key_topics

                                    print(f"   ✅ Transcribed and summarized")
                                else:
                                    print(f"   ⚠️  Summary error: {summary}")
                                    podcast_data["transcript"] = transcript
                                    podcast_data["summary"] = (
                                        "Summary not available - API error"
                                    )
                                    podcast_data["key_topics"] = []
                            else:
                                print(f"   ⚠️  No transcript available: {transcript}")
                                podcast_data["transcript"] = (
                                    transcript
                                    if transcript
                                    else "Transcript not available"
                                )
                                podcast_data["summary"] = (
                                    "Summary not available - no transcript"
                                )
                                podcast_data["key_topics"] = []
                        except Exception as e:
                            print(f"   ⚠️  Transcription/summarization error: {str(e)}")
                            podcast_data["transcript"] = (
                                f"Transcription error: {str(e)}"
                            )
                            podcast_data["summary"] = "Summary not available"
                            podcast_data["key_topics"] = []

                        podcasts.append(podcast_data)

                except Exception as e:
                    print(f"   ⚠️  Error extracting videos: {str(e)}")
                    return []

        except Exception as e:
            print(f"   ❌ Error fetching from {channel_name}: {str(e)}")
            return []

        return podcasts

    def extract_channel_id(self, url: str) -> Optional[str]:
        """Extract YouTube channel ID from URL"""
        # Handle different URL formats
        patterns = [
            r"youtube\.com/channel/([a-zA-Z0-9_-]+)",
            r"youtube\.com/@([a-zA-Z0-9_-]+)",
            r"youtube\.com/c/([a-zA-Z0-9_-]+)",
            r"youtube\.com/user/([a-zA-Z0-9_-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def transcribe_video(self, video_url: str) -> str:
        """Transcribe audio from YouTube video using YouTube's free transcripts"""
        transcription_method = self.settings.get("transcription", {}).get(
            "method", "youtube"
        )

        if transcription_method == "youtube":
            return self.transcribe_with_youtube(video_url)
        elif transcription_method == "openai_whisper":
            return self.transcribe_with_openai_whisper(video_url)
        elif transcription_method == "skip":
            # Skip transcription
            return "Transcription skipped."
        else:
            # Default to YouTube transcripts
            return self.transcribe_with_youtube(video_url)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def transcribe_with_youtube(self, video_url: str) -> str:
        """Extract transcript from YouTube video using yt-dlp (FREE!)"""
        if not yt_dlp:
            return "yt-dlp not installed. Install it with: pip install yt-dlp"

        # Retry with exponential backoff
        import time

        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Configure yt-dlp to extract subtitles only (no video/audio download)
                # Updated yt-dlp should handle this better, but we'll still minimize format testing
                ydl_opts = {
                    "skip_download": True,  # Don't download anything
                    "quiet": True,  # Minimize output
                    "no_warnings": True,
                    "ignoreerrors": True,
                    "extract_flat": False,  # Need full info for subtitles
                    # Don't write subtitles to files, just get metadata
                    "writesubtitles": False,
                    "writeautomaticsub": False,
                    # ONLY request English subtitles - no other languages
                    "subtitleslangs": ["en", "en-US", "en-GB"],
                    # Use bestaudio format to minimize format testing (we don't actually need it)
                    "format": "bestaudio/best",
                    # List only subtitles to reduce format processing
                    "listsubtitles": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Extract video info - newer yt-dlp handles this better
                    # This should get subtitle metadata without extensive format testing
                    info = ydl.extract_info(video_url, download=False)

                # Check if subtitles are available
                subtitles = info.get("subtitles", {})
                automatic_captions = info.get("automatic_captions", {})

                # ONLY get English subtitles - no other languages
                # If not English, skip immediately (don't transcribe)
                subtitle_lang = None
                subtitle_data = None

                # Try manual English subtitles first
                for lang in ["en", "en-US", "en-GB"]:
                    if lang in subtitles:
                        subtitle_lang = lang
                        subtitle_data = subtitles[lang]
                        break

                # If no manual English subtitles, try automatic English captions
                if not subtitle_lang:
                    for lang in ["en", "en-US", "en-GB"]:
                        if lang in automatic_captions:
                            subtitle_lang = lang
                            subtitle_data = automatic_captions[lang]
                            break

                # ONLY English - don't try other languages
                # Skip immediately if no English (stop processing this video)
                if not subtitle_lang:
                    print(
                        f"   ⏭️  Skipping video - No English subtitles available (non-English audio detected)"
                    )
                    return "SKIP_NO_ENGLISH"  # Special marker to skip this video

                if not subtitle_lang or not subtitle_data:
                    print(
                        f"   ⏭️  Skipping video - No English subtitles available (non-English audio detected)"
                    )
                    return "SKIP_NO_ENGLISH"  # Special marker to skip this video

                # Get subtitle URL (usually VTT format)
                subtitle_url = None
                if subtitle_data:
                    # Find VTT or best format
                    for fmt in subtitle_data:
                        if fmt.get("ext") == "vtt" or "vtt" in fmt.get("url", ""):
                            subtitle_url = fmt.get("url")
                            break
                    # If no VTT, get first available
                    if not subtitle_url and subtitle_data:
                        subtitle_url = subtitle_data[0].get("url")

                if not subtitle_url:
                    return f"Could not get subtitle URL for video: {video_url}"

                # Download and parse subtitle
                import urllib.request
                import urllib.error

                subtitle_file = os.path.join(
                    self.temp_dir, f"sub_{abs(hash(video_url)) % 1000000}.vtt"
                )

                # Download subtitle with error handling
                try:
                    urllib.request.urlretrieve(subtitle_url, subtitle_file)
                except urllib.error.HTTPError as e:
                    if e.code == 429:  # Too Many Requests
                        raise Exception(f"HTTP Error 429: Too Many Requests")
                    else:
                        raise Exception(f"HTTP Error {e.code}: {e.reason}")
                except Exception as e:
                    raise Exception(f"Error downloading subtitle: {str(e)}")

                # Parse VTT file
                transcript_text = self.parse_vtt_subtitle(subtitle_file)

                # Clean up
                try:
                    os.remove(subtitle_file)
                except:
                    pass

                return transcript_text

            except Exception as e:
                error_str = str(e)
                # Check if it's a rate limiting error
                if (
                    "429" in error_str
                    or "Too Many Requests" in error_str
                    or "rate limit" in error_str.lower()
                    or "403" in error_str
                    or "Forbidden" in error_str
                ):
                    # Single attempt - return error immediately if rate limited
                    return f"Error: Rate limited. Please try again later."
                else:
                    # Non-rate-limit error, don't retry
                    return f"Error extracting transcript with yt-dlp: {error_str}"

        # If we get here, all retries failed
        return f"Error extracting transcript after {max_retries} attempts."

    def parse_vtt_subtitle(self, vtt_file: str) -> str:
        """Parse WebVTT subtitle file and extract text"""
        try:
            with open(vtt_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse VTT format
            lines = content.split("\n")
            transcript_lines = []

            i = 0
            while i < len(lines):
                line = lines[i].strip()

                # Skip WEBVTT header and other metadata
                if line.startswith("WEBVTT") or line.startswith("NOTE") or not line:
                    i += 1
                    continue

                # Skip timestamp lines (contain -->)
                if "-->" in line:
                    i += 1
                    # Next lines until empty are the text
                    text_parts = []
                    while i < len(lines) and lines[i].strip():
                        text_line = lines[i].strip()
                        # Remove HTML tags if any
                        text_line = re.sub(r"<[^>]+>", "", text_line)
                        if text_line:
                            text_parts.append(text_line)
                        i += 1
                    if text_parts:
                        transcript_lines.append(" ".join(text_parts))
                    i += 1
                else:
                    i += 1

            return " ".join(transcript_lines)

        except Exception as e:
            return f"Error parsing VTT file: {str(e)}"

    def transcribe_with_openai_whisper(self, video_url: str) -> str:
        """Transcribe using OpenAI Whisper API"""
        api_key = self.settings.get("transcription", {}).get("api_key", "")

        if not api_key or not openai:
            return "OpenAI API key not configured or openai package not installed."

        try:
            # Initialize OpenAI client (new API v1.0+)
            client = openai.OpenAI(api_key=api_key)

            # Download audio using yt-dlp
            audio_hash = abs(hash(video_url)) % 1000000
            audio_path = os.path.join(self.temp_dir, f"audio_{audio_hash}.mp3")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": audio_path.replace(".mp3", ".%(ext)s"),
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Find the actual audio file
            audio_files = [
                f
                for f in os.listdir(self.temp_dir)
                if str(audio_hash) in f or f.endswith(".mp3")
            ]
            if not audio_files:
                return "Failed to download audio"

            actual_audio_path = os.path.join(self.temp_dir, audio_files[0])

            # Transcribe with OpenAI Whisper
            with open(actual_audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )
                text = transcript.text

            # Clean up
            try:
                os.remove(actual_audio_path)
            except:
                pass

            return text

        except Exception as e:
            return f"Transcription error: {str(e)}"

    def summarize_transcript(self, transcript: str) -> str:
        """Summarize transcript using AI"""
        if not transcript or len(transcript.strip()) < 50:
            return "Transcript too short to summarize."

        summarization_method = self.settings.get("summarization", {}).get(
            "method", "gemini"
        )

        if summarization_method == "gemini":
            return self.summarize_with_gemini(transcript)
        elif summarization_method == "openai_gpt":
            return self.summarize_with_gpt(transcript)
        else:
            # Simple extractive summary as fallback
            sentences = transcript.split(".")
            return ". ".join(sentences[:3]) + "..."

    def summarize_with_gemini(self, transcript: str) -> str:
        """Summarize using Google Gemini (FREE!)"""
        api_key = self.settings.get("summarization", {}).get("api_key", "")
        model_name = self.settings.get("summarization", {}).get(
            "model", "gemini-1.5-flash"
        )

        if not api_key or not genai:
            # Fallback to simple summary
            sentences = transcript.split(".")
            return ". ".join(sentences[:5]) + "..."

        # Single attempt - no retries for faster processing
        import time

        max_retries = 1

        for attempt in range(max_retries):
            try:
                # Configure Gemini API
                genai.configure(api_key=api_key)

                # Get model
                model = genai.GenerativeModel(model_name)

                # Truncate transcript if too long (Gemini has token limits)
                # Gemini 1.5 Flash supports up to 1M tokens, but let's limit for speed
                max_chars = 30000  # ~7500 tokens for safety
                if len(transcript) > max_chars:
                    transcript = transcript[:max_chars] + "..."

                # Create prompt for LONG, DETAILED summary (1-hour videos need extensive summaries)
                prompt = f"""Please provide a VERY DETAILED and COMPREHENSIVE summary of this podcast transcript. This is for a 1-hour video, so provide extensive coverage of all topics, insights, and discussions.

Provide a thorough summary covering:
- All main topics discussed in detail
- Key insights and takeaways for each topic
- Important points, quotes, and examples from speakers
- Detailed explanations of concepts discussed
- Overall themes and conclusions
- Important business lessons or advice shared

Make this summary detailed enough that someone can understand the full content of this podcast without watching it. Include specific details, numbers, examples, and important quotes.

Transcript:
{transcript}

Summary (be VERY detailed and comprehensive):"""

                # Generate summary with MUCH more tokens for 1-hour videos
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 8000,  # Much larger for 1-hour videos (was 3000)
                    },
                )

                summary = response.text.strip()
                # Ensure we return the full summary
                if summary:
                    return summary
                else:
                    return "Summary generation returned empty response."

            except Exception as e:
                error_msg = str(e)
                error_str = str(e)
                # Check if it's a rate limiting error
                if (
                    "429" in error_str
                    or "Too Many Requests" in error_str
                    or "rate limit" in error_str.lower()
                    or "quota" in error_str.lower()
                    or "RESOURCE_EXHAUSTED" in error_str
                ):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                        print(
                            f"   ⏳ Rate limited on summarization, waiting {wait_time}s before retry {attempt + 2}/{max_retries}..."
                        )
                        time.sleep(wait_time)
                        continue  # Retry
                    else:
                        return f"Error: Rate limited after {max_retries} attempts during summarization. Please try again later."
                else:
                    # Not a rate limit error, return immediately
                    # Fallback to simple summary
                    sentences = transcript.split(".")
                    fallback = ". ".join(sentences[:5]) + "..."
                    print(f"   ⚠️  Gemini summarization error: {error_msg}")
                    return fallback

        # If we get here, attempt failed
        return f"Error: Summarization failed."

    def summarize_with_gpt(self, transcript: str) -> str:
        """Summarize using OpenAI GPT"""
        api_key = self.settings.get("summarization", {}).get("api_key", "")
        model = self.settings.get("summarization", {}).get("model", "gpt-4o-mini")

        if not api_key or not openai:
            # Fallback to simple summary
            sentences = transcript.split(".")
            return ". ".join(sentences[:5]) + "..."

        try:
            # Initialize OpenAI client (new API v1.0+)
            client = openai.OpenAI(api_key=api_key)

            # Truncate transcript if too long (GPT has token limits)
            max_chars = 12000  # ~3000 tokens
            if len(transcript) > max_chars:
                transcript = transcript[:max_chars] + "..."

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes podcast transcripts into concise, informative summaries.",
                    },
                    {
                        "role": "user",
                        "content": f"Please provide a comprehensive summary of this podcast transcript:\n\n{transcript}",
                    },
                ],
                max_tokens=500,
                temperature=0.7,
            )

            summary = response.choices[0].message.content.strip()
            return summary

        except Exception as e:
            # Fallback to simple summary
            sentences = transcript.split(".")
            return ". ".join(sentences[:5]) + "..."

    def extract_key_topics(self, transcript: str) -> List[str]:
        """Extract key topics from transcript"""
        if not transcript or len(transcript.strip()) < 50:
            return []

        # Simple keyword extraction (can be improved with NLP)
        # Look for capitalized words and common phrases
        words = transcript.split()
        capitalized = [
            w.strip(".,!?;:") for w in words if w and w[0].isupper() and len(w) > 3
        ]

        # Count frequency
        topic_counts = Counter(capitalized)

        # Return top 5 topics
        top_topics = [topic for topic, count in topic_counts.most_common(5)]
        return top_topics[:5]

    def calculate_stats(self, podcasts: List[Dict]) -> Dict:
        """Calculate statistics from podcasts"""
        if not podcasts:
            return {
                "total_podcasts": 0,
                "total_duration": 0,
                "channels_analyzed": 0,
            }

        total_duration = sum(p.get("duration", 0) for p in podcasts)
        channels_analyzed = len(set(p.get("channel", "") for p in podcasts))

        return {
            "total_podcasts": len(podcasts),
            "total_duration": total_duration,
            "channels_analyzed": channels_analyzed,
        }


if __name__ == "__main__":
    analyzer = YouTubePodcastAnalyzer()
    results = analyzer.analyze_competitors()

    # Save results
    output_file = "youtube_analysis_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Analysis complete! Results saved to {output_file}")
    print(f"📊 Stats: {results['stats']}")
