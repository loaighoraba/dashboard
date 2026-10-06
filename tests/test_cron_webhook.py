from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from app.config import Settings, get_settings
from app.main import app

client = TestClient(app)
SECRET = "test-secret"


class SettingsWithoutEnvFile(Settings):
    # Keeps a local .env from leaking into tests
    model_config = SettingsConfigDict(env_file=None)


def override_settings(**values: SecretStr) -> None:
    app.dependency_overrides[get_settings] = lambda: SettingsWithoutEnvFile(**values)


@pytest.fixture(autouse=True)
def clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


class TestCronWebhookWithSecret:
    @pytest.fixture(autouse=True)
    def cron_secret(self) -> None:
        override_settings(cron_secret_token=SecretStr(SECRET))

    def test_valid_secret(self) -> None:
        response = client.post("/webhooks/cron", headers={"X-Cron-Secret": SECRET})
        assert response.status_code == 200
        assert response.json() == {"message": "Cron job completed successfully"}

    def test_wrong_secret(self) -> None:
        response = client.post("/webhooks/cron", headers={"X-Cron-Secret": "wrong"})
        assert response.status_code == 401

    def test_missing_header(self) -> None:
        response = client.post("/webhooks/cron")
        assert response.status_code == 401


def test_secret_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRON_SECRET_TOKEN", raising=False)
    override_settings()
    response = client.post("/webhooks/cron", headers={"X-Cron-Secret": SECRET})
    assert response.status_code == 500
