import pytest
from unittest.mock import patch, MagicMock
from app.gotify_client import GotifyClient

def test_gotify_client_init():
    client = GotifyClient("http://test.local/", "user", "pass")
    assert client.base_url == "http://test.local"
    assert client.username == "user"
    assert client.password == "pass"
    assert client.client_token is None
    assert client.app_token is None

@patch("app.gotify_client.requests.get")
def test_setup_token_client_token(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"name": "FastAPI_Notify_App", "token": "A123456789"}]
    mock_get.return_value = mock_resp

    client = GotifyClient("http://test.local", "user", "C987654321")
    client.setup_token()
    
    assert client.client_token == "C987654321"
    assert client.app_token == "A123456789"

@patch("app.gotify_client.requests.post")
def test_send_notification_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"id": 1}
    mock_post.return_value = mock_resp

    client = GotifyClient("http://test.local", "user", "pass")
    client.app_token = "A123456789"
    
    result = client.send_notification("Test Title", "Test Message")
    assert result == {"id": 1}

def test_send_notification_no_token():
    client = GotifyClient("http://test.local", "user", "pass")
    with pytest.raises(ValueError, match="App Token not set"):
        client.send_notification("Title", "Message")
