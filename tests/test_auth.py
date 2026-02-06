import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os

# Create the mock BEFORE importing app.main to ensure clean state if needed,
# though we are patching app.main.client instance attributes mostly.
from app.main import app, client

# Set up the client mock
# We don't want any actual network calls
client.setup_token = MagicMock(side_effect=lambda: setattr(client, 'app_token', 'mock_token'))
client.send_notification = MagicMock(return_value={"id": 1, "appid": 1, "message": "test"})
# Also ensure app_token is set so we don't hit the retry logic inside the route immediately
client.app_token = "mock_token"

@pytest.fixture
def test_client():
    return TestClient(app)

def test_no_password_env_var(test_client):
    """
    Test that when NOTIFYPASS is not set, we can post without password.
    """
    with patch("app.main.NOTIFYPASS", None):
        response = test_client.post("/notify", json={"title": "Test", "message": "Msg"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"

def test_password_env_var_set_no_password_provided(test_client):
    """
    Test that when NOTIFYPASS is set, posting without password fails.
    """
    with patch("app.main.NOTIFYPASS", "secret123"):
        response = test_client.post("/notify", json={"title": "Test", "message": "Msg"})
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]

def test_password_env_var_set_wrong_password(test_client):
    """
    Test that when NOTIFYPASS is set, posting with wrong password fails.
    """
    with patch("app.main.NOTIFYPASS", "secret123"):
        response = test_client.post("/notify", json={"title": "Test", "message": "Msg", "password": "wrong"})
        assert response.status_code == 401
        assert "Unauthorized" in response.json()["detail"]

def test_password_env_var_set_correct_password(test_client):
    """
    Test that when NOTIFYPASS is set, posting with correct password succeeds.
    """
    with patch("app.main.NOTIFYPASS", "secret123"):
        response = test_client.post("/notify", json={"title": "Test", "message": "Msg", "password": "secret123"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
