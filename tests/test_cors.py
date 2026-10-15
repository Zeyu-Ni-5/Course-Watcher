from fastapi.testclient import TestClient

from app.main import app


def test_frontend_can_preflight_watch_mutations():
    with TestClient(app) as client:
        response = client.options('/watches/1', headers={
            'Origin': 'http://localhost:5173',
            'Access-Control-Request-Method': 'PATCH',
            'Access-Control-Request-Headers': 'content-type',
        })
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_unconfigured_origin_cannot_read_cross_origin_response():
    with TestClient(app) as client:
        response = client.options('/watches', headers={
            'Origin': 'https://untrusted.example',
            'Access-Control-Request-Method': 'POST',
        })
    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers
