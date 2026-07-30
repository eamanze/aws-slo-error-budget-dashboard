import pytest

from app.app import create_app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("FAULT_TOKEN", "test-token")
    application = create_app()
    application.config.update(TESTING=True, FAULT_TOKEN="test-token")
    with application.test_client() as test_client:
        yield test_client
        test_client.delete("/admin/fault", headers={"X-Fault-Token": "test-token"})


def test_index_is_healthy(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_faults_are_authenticated_and_deterministic(client):
    assert client.post("/admin/fault", json={"error_rate": 1}).status_code == 401
    configured = client.post(
        "/admin/fault",
        json={"error_rate": 1, "unhealthy": True},
        headers={"X-Fault-Token": "test-token"},
    )
    assert configured.status_code == 200
    assert client.get("/").status_code == 503
    assert client.get("/readyz").status_code == 503


def test_metrics_include_request_series(client):
    client.get("/")
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert b"http_requests_total" in metrics.data
    assert b"http_request_duration_seconds_bucket" in metrics.data
