import os
import requests
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import AsyncGenerator, Any
from pydantic import BaseModel
from app.gotify_client import GotifyClient

logger = logging.getLogger(__name__)

# Environment Variables
GOTIFY_ENDPOINT = os.getenv("GOTIFY_ENDPOINT", "https://gotify.tpk.pw")
GOTIFY_USERNAME = os.getenv("GOTIFY_USERNAME", "")
GOTIFY_PASSWORD = os.getenv("GOTIFY_PASSWORD", "")
NOTIFYPASS = os.getenv("NOTIFYPASS")

client = GotifyClient(GOTIFY_ENDPOINT, GOTIFY_USERNAME, GOTIFY_PASSWORD)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    # Startup logic
    logger.info("Starting up... Setting up Gotify Client")
    try:
        client.setup_token()
        # Send Hello World on startup as per "The first goal"
        client.send_notification("System", "Hello World - NotifyApp Started")
        logger.info("Startup notification sent.")
    except (ValueError, requests.RequestException) as e:
        logger.error(f"Failed to initialize Gotify client: {e}")
        # We don't crash the app, but notify endpoints will fail
    
    yield
    
    # Shutdown logic (optional)
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class NotificationRequest(BaseModel):
    title: str
    message: str
    priority: int = 5
    password: str | None = None

@app.get("/")
async def read_index() -> FileResponse:
    return FileResponse('app/static/index.html')

@app.post("/notify")
async def send_notification(notification: NotificationRequest) -> dict[str, Any]:
    if NOTIFYPASS:
        if notification.password != NOTIFYPASS:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid password")

    if not client.app_token:
        # Try to setup again if it failed on startup
        try:
            client.setup_token()
        except (ValueError, requests.RequestException) as e:
            raise HTTPException(status_code=500, detail=f"Gotify configuration error: {str(e)}") from e

    try:
        result = client.send_notification(notification.title, notification.message, notification.priority)
        return {"status": "success", "data": result}
    except (ValueError, requests.RequestException) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
