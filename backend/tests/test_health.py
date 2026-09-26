def test_health_endpoint(client):
    """
    Test GET /api/health returns 200 OK and health status schema.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PrepPilot Backend"
    assert "database" in data
    assert "gemini" in data

def test_root_endpoint(client):
    """
    Test GET / returns welcome JSON.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs" in data
    assert data["docs"] == "/docs"
