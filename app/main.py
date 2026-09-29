from fastapi import FastAPI

from app.routers import webhooks

app = FastAPI(title="Dashboard")

app.include_router(webhooks.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Loai Ghoraba dashboard"}
