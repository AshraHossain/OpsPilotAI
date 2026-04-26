"""
Basic smoke tests for the FastAPI endpoints.
Run with: pytest tests/test_api.py -v
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_approve_and_get():
    resp = client.post("/approve", json={
        "incident_id": "test-001",
        "approved": True,
        "approver": "ashraf@example.com",
    })
    assert resp.status_code == 200
    assert resp.json()["approved"] is True

    resp2 = client.get("/approve/test-001")
    assert resp2.status_code == 200
    assert resp2.json()["approved"] is True


def test_approve_not_found():
    resp = client.get("/approve/nonexistent-id")
    assert resp.status_code == 404


@patch("api.main.run_scaling_analysis", return_value="Scale to 3 replicas.")
def test_trigger_scale_analysis(mock_fn):
    resp = client.post("/trigger/scale-analysis", json={
        "event_type": "manual",
        "repo": "org/myapp",
        "deployment_name": "myapp-api",
        "environment": "production",
    })
    assert resp.status_code == 200
    assert "scaling_analysis" in resp.json()["action"]
    mock_fn.assert_called_once()
