import os
import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

cron_secret_header = APIKeyHeader(
    name="X-Cron-Secret",
    scheme_name="CronSecret",
    description="Shared secret for scheduled jobs (matches CRON_SECRET_TOKEN).",
    auto_error=False,
)


def verify_cron_secret(
    x_cron_secret: Annotated[str | None, Security(cron_secret_header)],
) -> None:
    expected = os.environ.get("CRON_SECRET_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured",
        )
    if x_cron_secret is None or not secrets.compare_digest(
        x_cron_secret.encode(), expected.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing cron secret",
        )
