import pytest
import json
import time
from unittest.mock import MagicMock, patch
from app.services.gemini_service import (
    GeminiService,
    generate_structured,
    GeminiError,
    _sanitize_log_msg,
    reset_cooldown_and_cache
)

@pytest.fixture(autouse=True)
def reset_gemini_service_state():
    """Resets global rate limit cooldown timestamp and response cache before and after each test."""
    reset_cooldown_and_cache()
    yield
    reset_cooldown_and_cache()

def test_sanitize_log_msg_redacts_keys():
    """
    Test log sanitizer removes API keys and sensitive tokens.
    """
    raw_log = "API key AIzaSyA1234567890abcdefghijklmnopqrstuv failed with key=secret123"
    sanitized = _sanitize_log_msg(raw_log)
    assert "AIzaSy" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "secret123" not in sanitized

@pytest.mark.asyncio
async def test_gemini_service_generate_structured_success():
    """
    Test successful generation of structured output using gemini-3.1-flash-lite.
    """
    service = GeminiService()
    sample_response_dict = {
        "strengths": ["Python"],
        "weaknesses": ["Docker"],
        "current_skills": ["Python"],
        "required_skills": ["Python", "Docker"],
        "industry_relevant_skills": ["Kubernetes"],
        "skill_gaps": ["Docker"],
        "priority_skills": ["Docker"],
        "recommendations": ["Learn Docker"]
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_response_dict)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    schema = {"type": "object"}
    prompt = "Analyze profile for Backend Engineer " + str(time.time())

    with patch("app.config.settings.GEMINI_API_KEY", "test_mock_api_key"), \
         patch("google.genai.Client", return_value=mock_client):
        result = await service.generate_structured(prompt=prompt, schema=schema)

        assert result["_source"] == "gemini"
        assert result["strengths"] == ["Python"]
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )

@pytest.mark.asyncio
async def test_rate_limit_429_enters_cooldown_without_retry():
    """
    Test 429 rate limit error aborts retries immediately and sets cooldown timestamp.
    """
    service = GeminiService()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("HTTP 429 RESOURCE_EXHAUSTED: Quota exceeded")

    schema = {"type": "object"}
    prompt = "Rate limit test prompt " + str(time.time())

    try:
        with patch("app.config.settings.GEMINI_API_KEY", "test_mock_api_key"), \
             patch("google.genai.Client", return_value=mock_client):
            with pytest.raises(GeminiError) as exc_info:
                await service.generate_structured(prompt=prompt, schema=schema)

            assert "rate-limit" in str(exc_info.value).lower()
            # Verify call count was 1 (no repeated retries on 429)
            assert mock_client.models.generate_content.call_count == 1

            # Verify second call during cooldown throws immediately without invoking API client
            mock_client.models.generate_content.reset_mock()
            with pytest.raises(GeminiError) as exc_info2:
                await service.generate_structured(prompt="another prompt", schema=schema)

            assert "cooldown active" in str(exc_info2.value)
            assert mock_client.models.generate_content.call_count == 0
    finally:
        reset_cooldown_and_cache()

@pytest.mark.asyncio
async def test_transient_error_exponential_backoff():
    """
    Test transient 500/503 error triggers 1s backoff retry.
    """
    service = GeminiService()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("HTTP 503 Service Unavailable")

    schema = {"type": "object"}
    prompt = "Transient error test prompt " + str(time.time())

    with patch("app.config.settings.GEMINI_API_KEY", "test_mock_api_key"), \
         patch("google.genai.Client", return_value=mock_client), \
         patch("time.sleep") as mock_sleep:

        with pytest.raises(GeminiError) as exc_info:
            await service.generate_structured(prompt=prompt, schema=schema)

        assert "Gemini API execution error" in str(exc_info.value)
        # Verify 2 attempts were made
        assert mock_client.models.generate_content.call_count == 2
        mock_sleep.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_caching_reusable_ai_results():
    """
    Test caching avoids redundant Gemini API calls for identical prompt/schema.
    """
    service = GeminiService()
    sample = {"result": "cached_val"}
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    schema = {"type": "object", "properties": {"result": {"type": "string"}}}
    prompt = "Unique prompt for caching test"

    with patch("app.config.settings.GEMINI_API_KEY", "test_mock_api_key"), \
         patch("google.genai.Client", return_value=mock_client):
        res1 = await service.generate_structured(prompt=prompt, schema=schema)
        res2 = await service.generate_structured(prompt=prompt, schema=schema)

        assert res1 == res2
        assert res1["_source"] == "gemini"
        # Only 1 call made due to caching
        assert mock_client.models.generate_content.call_count == 1

def test_generate_structured_missing_api_key():
    """
    Test calling generate_structured without API key raises GeminiError immediately.
    """
    with patch("app.config.settings.GEMINI_API_KEY", ""):
        with pytest.raises(GeminiError) as exc_info:
            generate_structured(prompt="test", schema={})
        assert "GEMINI_API_KEY is not configured" in str(exc_info.value)
