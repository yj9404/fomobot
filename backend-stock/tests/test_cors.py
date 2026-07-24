from fastapi.testclient import TestClient
from fomobot.main import app

client = TestClient(app)

def test_cors_headers():
    """
    CORS preflight request (OPTIONS) should return restricted allowed headers.
    """
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-headers" in response.headers
    # Test that the restricted headers are present and not '*'
    assert "Accept" in response.headers["access-control-allow-headers"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]
    assert "*" not in response.headers["access-control-allow-headers"]
