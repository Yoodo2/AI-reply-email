from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class MailAccountRequest(BaseModel):
    email: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    use_ssl: bool = True


class SettingsRequest(BaseModel):
    fetch_interval: int = 300
    target_lang: str = "zh"
    baidu_appid: str
    baidu_secret: str
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"


@router.get("")
def get_settings():
    settings = db.get_settings()
    account = db.fetch_one("SELECT * FROM mail_accounts ORDER BY updated_at DESC LIMIT 1")
    return {
        "settings": settings,
        "mail_account": dict(account) if account else None,
    }


@router.post("")
def update_settings(payload: SettingsRequest):
    db.set_setting("fetch_interval", str(payload.fetch_interval))
    db.set_setting("target_lang", payload.target_lang)
    db.set_setting("baidu_appid", payload.baidu_appid)
    db.set_setting("baidu_secret", payload.baidu_secret)
    db.set_setting("deepseek_api_key", payload.deepseek_api_key)
    db.set_setting("deepseek_base_url", payload.deepseek_base_url)
    db.set_setting("deepseek_model", payload.deepseek_model)
    return {"status": "ok"}


@router.post("/mail-account")
def update_mail_account(payload: MailAccountRequest):
    db.execute(
        """
        INSERT INTO mail_accounts
        (email, imap_host, imap_port, smtp_host, smtp_port, username, password, use_ssl, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.email,
            payload.imap_host,
            payload.imap_port,
            payload.smtp_host,
            payload.smtp_port,
            payload.username,
            payload.password,
            int(payload.use_ssl),
            datetime.utcnow().isoformat(),
        ),
    )
    return {"status": "ok"}
