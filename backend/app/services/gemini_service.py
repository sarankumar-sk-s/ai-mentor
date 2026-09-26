import logging
import json
import time
import hashlib
from typing import Optional, Dict, Any, Tuple

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"

class GeminiError(Exception):
    """Custom exception raised when Gemini API call fails or is rate-limited."""
    pass

# Global In-Memory TTL Cache for Gemini AI Responses (5 min TTL)
_ai_cache: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 300.0

# Global Rate Limit Cooldown State
_rate_limit_until: float = 0.0

def reset_cooldown_and_cache():
    """Helper function to reset rate limit cooldown state and cache (useful for testing)."""
    global _rate_limit_until
    _rate_limit_until = 0.0
    _ai_cache.clear()

import re

def _sanitize_log_msg(msg: str) -> str:
    """Masks API keys in log messages to prevent credential leakage."""
    if not msg:
        return ""
    clean_msg = str(msg)
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if api_key and api_key in clean_msg:
        clean_msg = clean_msg.replace(api_key, "[REDACTED_API_KEY]")

    clean_msg = re.sub(r'AIzaSy[A-Za-z0-9_-]{33}', '[REDACTED_API_KEY]', clean_msg)
    clean_msg = re.sub(r'(key|api_key|token)=([^\s&]+)', r'\1=[REDACTED_KEY]', clean_msg, flags=re.IGNORECASE)
    return clean_msg

def _get_cache_key(prompt: str, schema: Optional[dict], model: str) -> str:
    schema_str = json.dumps(schema, sort_keys=True) if schema else ""
    raw = f"{model}:{prompt}:{schema_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _get_from_cache(cache_key: str) -> Optional[Any]:
    now = time.time()
    if cache_key in _ai_cache:
        timestamp, data = _ai_cache[cache_key]
        if now - timestamp < CACHE_TTL_SECONDS:
            logger.info("Retrieved AI structured response from in-memory cache.")
            return data
        else:
            del _ai_cache[cache_key]
    return None

def _store_in_cache(cache_key: str, data: Any) -> None:
    _ai_cache[cache_key] = (time.time(), data)

def generate_structured(
    prompt: str,
    schema: dict,
    model: str = DEFAULT_GEMINI_MODEL
) -> dict:
    """
    Generates structured JSON output using Google GenAI SDK (google-genai) with:
    - Model default: gemini-3.1-flash-lite
    - TTL response caching to eliminate duplicate calls
    - Rate limit (429 / RESOURCE_EXHAUSTED) detection with instant fallback abort
    - Log sanitization to prevent API key leaks
    - Source metadata tagging ('_source': 'gemini')
    """
    global _rate_limit_until

    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured in settings.")

    # 1. Check Rate Limit Cooldown
    now = time.time()
    if now < _rate_limit_until:
        logger.warning(_sanitize_log_msg(
            "Gemini API rate-limit cooldown active. Aborting API call directly to fallback handler."
        ))
        raise GeminiError("Gemini API is currently rate-limited (cooldown active).")

    # 2. Check In-Memory Response Cache
    cache_key = _get_cache_key(prompt, schema, model)
    cached_res = _get_from_cache(cache_key)
    if cached_res is not None:
        return cached_res

    try:
        from google import genai
    except ImportError as e:
        raise GeminiError(f"google-genai SDK is not installed: {str(e)}")

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        clean_err = _sanitize_log_msg(str(e))
        raise GeminiError(f"Failed to initialize Gemini Client: {clean_err}")

    config = {
        "response_mime_type": "application/json",
        "response_schema": schema
    }

    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Calling Gemini API model '{model}' (Attempt {attempt}/{max_attempts})")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            if not response or not hasattr(response, "text") or not response.text:
                raise GeminiError("Gemini API returned an empty or invalid response.")

            parsed_data = json.loads(response.text)
            if not isinstance(parsed_data, dict):
                raise GeminiError(f"Expected dict from Gemini JSON response, got {type(parsed_data).__name__}")

            # Tag response metadata with source = 'gemini'
            parsed_data["_source"] = "gemini"

            # Store in cache
            _store_in_cache(cache_key, parsed_data)
            return parsed_data

        except Exception as exc:
            err_msg = str(exc)
            clean_err = _sanitize_log_msg(err_msg)
            status_code = getattr(exc, "status_code", getattr(exc, "code", None))

            # Detect HTTP 429 / Rate Limit / Quota Exhaustion
            is_rate_limit = (
                (isinstance(status_code, int) and status_code == 429) or
                "429" in err_msg or
                "RESOURCE_EXHAUSTED" in err_msg or
                "Quota exceeded" in err_msg or
                "rate-limit" in err_msg.lower()
            )

            if is_rate_limit:
                # Set 60-second rate limit cooldown and abort retries immediately
                _rate_limit_until = time.time() + 60.0
                logger.warning(_sanitize_log_msg(
                    f"Gemini API rate limit (429) detected: {clean_err}. Cooldown set for 60s. Aborting retries."
                ))
                raise GeminiError(f"Gemini API rate-limit detected: {clean_err}") from exc

            # Detect retryable transient server errors (500, 502, 503, 504, UNAVAILABLE)
            is_transient = (
                (isinstance(status_code, int) and status_code >= 500) or
                "500" in err_msg or "502" in err_msg or "503" in err_msg or "504" in err_msg or
                "UNAVAILABLE" in err_msg or "INTERNAL" in err_msg
            )

            if is_transient and attempt < max_attempts:
                logger.warning(_sanitize_log_msg(
                    f"Gemini transient server error on attempt {attempt}: {clean_err}. Retrying in 1 second..."
                ))
                time.sleep(1)
                continue
            else:
                logger.error(_sanitize_log_msg(f"Gemini API call failed permanently: {clean_err}"))
                raise GeminiError(f"Gemini API execution error: {clean_err}") from exc


class GeminiService:
    """
    Centralized service layer managing Google Gemini AI interactions (using gemini-3.1-flash-lite).
    """
    def __init__(self, api_key: Optional[str] = None, gemini_wrapper: Optional[Any] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key) and time.time() >= _rate_limit_until

    async def generate_text(self, prompt: str, model_name: str = DEFAULT_GEMINI_MODEL) -> str:
        if not self.is_configured():
            return "Gemini API is currently rate-limited or unconfigured."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception as e:
            clean_err = _sanitize_log_msg(str(e))
            raise GeminiError(f"Gemini text generation error: {clean_err}")

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        model: str = DEFAULT_GEMINI_MODEL
    ) -> dict:
        return generate_structured(prompt=prompt, schema=schema, model=model)

    async def analyze_profile_skills(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"Analyze profile: {user_profile}"
        schema = {
            "type": "object",
            "properties": {
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
                "current_skills": {"type": "array", "items": {"type": "string"}},
                "required_skills": {"type": "array", "items": {"type": "string"}},
                "industry_relevant_skills": {"type": "array", "items": {"type": "string"}},
                "skill_gaps": {"type": "array", "items": {"type": "string"}},
                "priority_skills": {"type": "array", "items": {"type": "string"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            },
            "required": [
                "strengths", "weaknesses", "current_skills", "required_skills",
                "industry_relevant_skills", "skill_gaps", "priority_skills", "recommendations"
            ]
        }
        try:
            analysis_dict = generate_structured(prompt=prompt, schema=schema, model=DEFAULT_GEMINI_MODEL)
            analysis_dict["source"] = "gemini"
            return {"status": "success", "analysis": analysis_dict}
        except Exception as e:
            clean_err = _sanitize_log_msg(str(e))
            return {"status": "error", "message": clean_err, "analysis": None}
