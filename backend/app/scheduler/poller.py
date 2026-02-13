import asyncio
import logging
import re
from datetime import datetime
from typing import Optional

from ..db import db
from ..services.email_client import fetch_unreplied
from ..services.translator import translate_baidu
from ..services.classifier import classify_email
from ..services.template_engine import build_variables, render_template
from ..utils import detect_language

logger = logging.getLogger(__name__)


class EmailPoller:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self, interval_seconds: int) -> None:
        if self._task:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(interval_seconds))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run(self, interval_seconds: int) -> None:
        while self._running:
            try:
                await asyncio.to_thread(self.pull_once)
            except Exception:
                pass
            await asyncio.sleep(interval_seconds)

    def pull_once(self) -> None:
        account = db.fetch_one("SELECT * FROM mail_accounts ORDER BY updated_at DESC LIMIT 1")
        if not account:
            logger.warning("No mail account configured")
            raise ValueError("No mail account configured")

        logger.info(f"Fetching emails from {account['username']}")

        try:
            emails = fetch_unreplied(
                host=account["imap_host"],
                port=account["imap_port"],
                username=account["username"],
                password=account["password"],
                use_ssl=bool(account["use_ssl"]),
            )
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}", exc_info=True)
            raise ValueError(f"Failed to fetch emails: {e}") from e

        if not emails:
            logger.info("No new emails to process")
            return

        logger.info(f"Processing {len(emails)} new email(s)")

        baidu_appid = db.get_setting("baidu_appid", "")
        baidu_secret = db.get_setting("baidu_secret", "")
        target_lang = db.get_setting("target_lang", "zh")

        # 获取分类配置
        categories = [dict(row) for row in db.fetch_all("SELECT * FROM categories ORDER BY priority DESC")]
        ai_key = db.get_setting("deepseek_api_key", "")
        base_url = db.get_setting("deepseek_base_url", "https://api.deepseek.com")
        model = db.get_setting("deepseek_model", "deepseek-chat")

        for item in emails:
            if db.fetch_one("SELECT 1 FROM emails WHERE message_id = ?", (item["message_id"],)):
                logger.info(f"Email {item['message_id']} already exists, skipping")
                continue
            language = detect_language(item["body_text"] or item["subject"])
            translation = None
            if language and language.lower() not in ("zh", "zh-cn"):
                logger.info(f"Translating email from {language} to {target_lang}")
                # 清理 HTML 标签，只翻译纯文本，避免 URL 超长
                text_to_translate = item["body_text"] or ""
                text_to_translate = re.sub(r'<[^>]+>', '', text_to_translate)  # 移除 HTML 标签
                text_to_translate = text_to_translate.strip()[:2000]  # 限制长度
                translation = translate_baidu(text_to_translate, baidu_appid, baidu_secret, target_lang)

            # 保存邮件获取ID
            email_id = db.execute(
                """
                INSERT INTO emails
                (message_id, sender, subject, body_text, body_html, received_at, language, translation, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    item["message_id"],
                    item["sender"],
                    item["subject"],
                    item["body_text"],
                    item["body_html"],
                    item["received_at"],
                    language,
                    translation,
                    datetime.utcnow().isoformat(),
                ),
            )

            # 获取刚插入的邮件记录
            email_row = db.fetch_one("SELECT * FROM emails WHERE id = ?", (email_id,))
            if not email_row:
                logger.warning(f"Failed to retrieve inserted email {email_id}")
                continue

            # 自动分类
            email_text = email_row["body_text"] or email_row["subject"]
            if categories:
                category, confidence, method, reason = classify_email(
                    email_text, categories, ai_key, base_url, model
                )

                # 尝试生成 AI 回复（模板或 AI）
                reply = None
                template_row = db.fetch_one(
                    "SELECT * FROM templates WHERE category_id = ? ORDER BY id DESC LIMIT 1",
                    (category["id"],),
                )
                if template_row:
                    template_dict = dict(template_row)
                    variables = build_variables(
                        dict(email_row),
                        template_dict.get("variables"),
                        company_name="Your Fashion Store",
                        company_email="support@yourfashion.com",
                        company_phone="+1 (800) 555-0123"
                    )
                    reply = render_template(template_dict["content"], variables)

                # 更新邮件的分类和 AI 回复
                db.execute(
                    "UPDATE emails SET category_id = ?, confidence = ?, ai_reply = ? WHERE id = ?",
                    (category["id"], confidence, reply, email_id),
                )

                logger.info(f"Auto-classified email {email_id}: {category['name']} ({method}, confidence: {confidence:.2f})")

            logger.info(f"Saved email: {item['subject'][:50] if item['subject'] else 'No subject'}")

        logger.info(f"Successfully processed {len(emails)} email(s)")
