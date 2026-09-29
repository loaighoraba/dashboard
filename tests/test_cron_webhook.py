import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SECRET = "test-secret"


@pytest.fixture
def cron_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRON_SECRET_TOKEN", SECRET)


def test_valid_secret(cron_secret: None) -> None:
    response = client.post("/webhooks/cron", headers={"X-Cron-Secret": SECRET})
    assert response.status_code == 200
    assert response.json() == {"message": "Cron job completed successfully"}


def test_wrong_secret(cron_secret: None) -> None:
    response = client.post("/webhooks/cron", headers={"X-Cron-Secret": "wrong"})
    assert response.status_code == 401


def test_missing_header(cron_secret: None) -> None:
    response = client.post("/webhooks/cron")
    assert response.status_code == 401


def test_env_var_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)
    response = client.post("/webhooks/cron", headers={"X-Cron-Secret": SECRET})
    assert response.status_code == 500
