import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import SettingsDep

cron_secret_header = APIKeyHeader(
    name="X-Cron-Secret",
    scheme_name="CronSecret",
    description="Shared secret for scheduled jobs (matches CRON_SECRET_TOKEN).",
    auto_error=False,
)


def verify_cron_secret(
    x_cron_secret: Annotated[str | None, Security(cron_secret_header)],
    settings: SettingsDep,
) -> None:
    token = settings.cron_secret_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured",
        )
    expected = token.get_secret_value()
    if x_cron_secret is None or not secrets.compare_digest(
        x_cron_secret.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing cron secret",
        )
