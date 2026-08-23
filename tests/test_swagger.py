import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def test_client():
    return TestClient(app)

def test_swagger_endpoint(test_client):
    """
    Test that the /swagger endpoint returns the OpenAPI JSON schema.
    """
    response = test_client.get("/swagger")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
    assert "/notify" in data["paths"]
    assert "/swagger" in data["paths"]
