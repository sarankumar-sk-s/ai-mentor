import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Global singleton client instance
_supabase_client = None

def get_supabase_client():
    """
    Returns configured Supabase client instance.
    If SUPABASE_URL or SUPABASE_KEY is missing, returns None with a warning log.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not configured in environment.")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        logger.info("Supabase PostgreSQL client successfully initialized.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None
