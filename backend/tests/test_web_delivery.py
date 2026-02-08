import os

from fastapi.testclient import TestClient

os.environ.setdefault("LLM_DISABLED", "true")

from backend.api.server import app  # noqa: E402


def test_api_health():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"


def test_spa_index_served():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text.lower()
