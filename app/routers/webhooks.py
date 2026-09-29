from fastapi import APIRouter, Security
from pydantic import BaseModel

from app.security import verify_cron_secret

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class MessageResponse(BaseModel):
    message: str


@router.post("/cron", dependencies=[Security(verify_cron_secret)])
def run_cron() -> MessageResponse:
    return MessageResponse(message="Cron job completed successfully")
