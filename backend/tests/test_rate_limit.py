import pytest
import json
from unittest.mock import MagicMock
from fastapi import Request
from app.core.rate_limit import rate_limit_exceeded_handler

def test_rate_limit_exceeded_handler_returns_429():
    """
    Test that rate_limit_exceeded_handler returns HTTP 429 with expected JSON structure.
    """
    req = Request({"type": "http", "method": "GET", "path": "/api/health", "headers": []})
    exc = MagicMock()
    exc.detail = "20 per 1 minute"

    res = rate_limit_exceeded_handler(req, exc)
    assert res.status_code == 429
    body = json.loads(res.body.decode())
    assert body["error"] == "rate_limit_exceeded"
    assert "20 per 1 minute" in body["message"]
    assert "detail" in body
