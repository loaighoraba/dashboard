from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

client = TestClient(app)
SECRET = "test-secret"


def override_settings(**values: str) -> None:
    # _env_file=None keeps a local .env from leaking into tests
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, **values)


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def cron_secret() -> None:
    override_settings(cron_secret_token=SECRET)


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


def test_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)
    override_settings()
    response = client.post("/webhooks/cron", headers={"X-Cron-Secret": SECRET})
    assert response.status_code == 500
