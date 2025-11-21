"""
Vercel serverless function handler for Instagram Competitor Analyzer
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app

# Export the Flask app for Vercel's Python runtime
# Vercel's @vercel/python will automatically handle WSGI conversion
# The app variable must be accessible at module level
