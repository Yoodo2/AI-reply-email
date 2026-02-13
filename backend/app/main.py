import asyncio
import logging
import webbrowser
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .db import db
from .routes import categories, emails, settings, templates
from .scheduler.poller import EmailPoller

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local Support Mail Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails.router)
app.include_router(categories.router)
app.include_router(templates.router)
app.include_router(settings.router)

static_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

poller = EmailPoller()


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting application...")
    db.init_db()
    interval = int(db.get_setting("fetch_interval", "300"))
    await poller.start(interval)
    logger.info(f"Email poller started with interval {interval}s")
    asyncio.get_event_loop().call_later(1.0, lambda: webbrowser.open("http://127.0.0.1:8001"))


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await poller.stop()
