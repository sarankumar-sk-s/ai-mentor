import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

class GeminiClientWrapper:
    """
    Wrapper for Google Gemini API Client SDK.
    """
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.client = None
        self.sdk_type = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured.")
            return

        try:
            # Try new official google-genai SDK first
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.sdk_type = "google-genai"
                logger.info("Gemini Client initialized with google-genai SDK.")
                return
            except ImportError:
                pass

            # Fallback to google-generativeai SDK
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                self.client = genai_legacy
                self.sdk_type = "google-generativeai"
                logger.info("Gemini Client initialized with google-generativeai SDK.")
                return
            except ImportError:
                logger.warning("Neither google-genai nor google-generativeai SDK is installed.")
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")

    def is_ready(self) -> bool:
        return self.client is not None

def get_gemini_wrapper() -> GeminiClientWrapper:
    return GeminiClientWrapper()
