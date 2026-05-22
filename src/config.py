"""Runtime configuration for the Distill pipeline.

All values are read from environment variables (or a .env file).
"""
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

SCORING_MODEL: str = os.getenv("SCORING_MODEL", "gemini-3.1-flash-lite")
SCORING_FALLBACK_MODEL: str = os.getenv("SCORING_FALLBACK_MODEL", "gemini-3.1-flash-lite")
SCORING_THRESHOLD: int = int(os.getenv("SCORING_THRESHOLD", "6"))
