import os
import pytest
from fastapi.testclient import TestClient

# Ensure the app picks up this key via python-dotenv or os.getenv
os.environ["LLM_ROUTER_API_KEY"] = "testkey"

from app.main import app  # noqa: E402

client = TestClient(app)

@pytest.fixture(autouse=True)
def _override_settings(monkeypatch):
    """
    Make sure any settings loaded at import time pick up our test key.
    """
    monkeypatch.setenv("LLM_ROUTER_API_KEY", "testkey")

def test_chat_missing_key():
    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": "ping"}]
    }
    # No X-API-Key header → should be 403 with FastAPI's default detail
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

def test_chat_invalid_key():
    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": "ping"}]
    }
    # Wrong X-API-Key header → should be 403 with our custom detail
    response = client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"X-API-Key": "badkey"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or missing API Key"

def test_chat_authorized():
    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": "ping"}]
    }
    # Correct X-API-Key → should succeed
    response = client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"X-API-Key": "testkey"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "choices" in data
    assert isinstance(data["choices"], list)
