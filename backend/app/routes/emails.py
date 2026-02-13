from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import db
from ..services.classifier import classify_email
from ..services.ai_client import generate_reply_ai
from ..services.email_client import send_reply
from ..services.template_engine import render_template, build_variables
from ..services.translator import translate_baidu
from ..services.test_email_generator import generateTestEmails

router = APIRouter(prefix="/api/emails", tags=["emails"])


class EmailSendRequest(BaseModel):
    reply: str
    category_id: Optional[int] = None


class AnalyzeRequest(BaseModel):
    force_ai: bool = False


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "zh"


@router.get("")
def list_emails(status: Optional[str] = None):
    if status:
        rows = db.fetch_all("SELECT * FROM emails WHERE status = ? ORDER BY received_at DESC", (status,))
    else:
        rows = db.fetch_all("SELECT * FROM emails ORDER BY received_at DESC")
    return [dict(row) for row in rows]


@router.get("/{email_id}")
def get_email(email_id: int):
    row = db.fetch_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    return dict(row)


@router.post("/sync")
def sync_emails():
    from ..scheduler.poller import EmailPoller

    poller = EmailPoller()
    try:
        poller.pull_once()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    return {"status": "ok"}


@router.post("/{email_id}/analyze")
def analyze(email_id: int, payload: AnalyzeRequest):
    """
    两阶段处理：
    1. 分类（关键词 > AI语义 > 默认）
    2. 生成回复（模板匹配 > AI生成）
    """
    email_row = db.fetch_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    categories = [dict(row) for row in db.fetch_all("SELECT * FROM categories ORDER BY priority DESC")]
    if not categories:
        raise HTTPException(status_code=400, detail="No categories")

    templates = [dict(row) for row in db.fetch_all("SELECT * FROM templates")]
    ai_key = db.get_setting("deepseek_api_key", "")
    base_url = db.get_setting("deepseek_base_url", "https://api.deepseek.com")
    model = db.get_setting("deepseek_model", "deepseek-chat")
    email_text = email_row["body_text"] or email_row["subject"]

    # ── 阶段一：分类 ──
    category, confidence, method, reason = classify_email(
        email_text, categories, ai_key, base_url, model,
    )

    # ── 阶段二：生成回复 ──
    reply = None
    reply_source = None

    # 优先匹配模板
    template_row = db.fetch_one(
        "SELECT * FROM templates WHERE category_id = ? ORDER BY id DESC LIMIT 1",
        (category["id"],),
    )
    if template_row:
        # 从邮件内容提取变量并渲染模板
        template_dict = dict(template_row)
        variables = build_variables(
            dict(email_row),
            template_dict.get("variables"),
            company_name="Your Fashion Store",
            company_email="support@yourfashion.com",
            company_phone="+1 (800) 555-0123"
        )
        reply = render_template(template_dict["content"], variables)
        reply_source = "template"
    elif ai_key:
        # 无模板时调用 AI 生成回复
        reply_result = generate_reply_ai(
            api_key=ai_key,
            email_text=email_text,
            category_name=category["name"],
            category_description=category.get("description", ""),
            base_url=base_url,
            model=model,
        )
        if reply_result:
            reply = reply_result.get("body", "")
            reply_source = "ai"

    # 持久化结果
    db.execute(
        "UPDATE emails SET category_id = ?, confidence = ?, ai_reply = ? WHERE id = ?",
        (category["id"], confidence, reply, email_id),
    )

    # 构建返回的变量信息（用于前端显示）
    extracted_vars = {}
    matched_template_id = None
    if template_row:
        template_dict = dict(template_row)
        matched_template_id = template_dict["id"]
        extracted_vars = build_variables(
            dict(email_row),
            template_dict.get("variables"),
            company_name="Your Fashion Store",
            company_email="support@yourfashion.com",
            company_phone="+1 (800) 555-0123"
        )

    return {
        "category": category,
        "confidence": confidence,
        "method": method,
        "reason": reason,
        "reply": reply,
        "reply_source": reply_source,
        "templates": templates,
        "extracted_variables": extracted_vars,
        "matched_template_id": matched_template_id,
    }


@router.post("/{email_id}/generate-reply")
def generate_reply(email_id: int):
    """手动触发 AI 生成回复（当用户不满意模板时使用）"""
    email_row = db.fetch_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    ai_key = db.get_setting("deepseek_api_key", "")
    if not ai_key:
        raise HTTPException(status_code=400, detail="AI key not configured")

    base_url = db.get_setting("deepseek_base_url", "https://api.deepseek.com")
    model = db.get_setting("deepseek_model", "deepseek-chat")
    email_text = email_row["body_text"] or email_row["subject"]

    # 获取分类信息
    categories = [dict(row) for row in db.fetch_all("SELECT * FROM categories ORDER BY priority DESC")]
    category_id = email_row["category_id"]
    category = next((c for c in categories if c["id"] == category_id), categories[0])

    reply_result = generate_reply_ai(
        api_key=ai_key,
        email_text=email_text,
        category_name=category["name"],
        category_description=category.get("description", ""),
        base_url=base_url,
        model=model,
    )

    if not reply_result:
        raise HTTPException(status_code=500, detail="Failed to generate reply")

    return {
        "reply": reply_result.get("body", ""),
        "reply_source": "ai",
    }


@router.post("/{email_id}/send")
def send_email(email_id: int, payload: EmailSendRequest):
    email_row = db.fetch_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not email_row:
        raise HTTPException(status_code=404, detail="Email not found")

    account = db.fetch_one("SELECT * FROM mail_accounts ORDER BY updated_at DESC LIMIT 1")
    if not account:
        raise HTTPException(status_code=400, detail="Mail account not configured")

    response = send_reply(
        host=account["smtp_host"],
        port=account["smtp_port"],
        username=account["username"],
        password=account["password"],
        to_addr=email_row["sender"],
        subject=f"Re: {email_row['subject']}",
        body=payload.reply,
        use_ssl=bool(account["use_ssl"]),
    )

    db.execute(
        "UPDATE emails SET status = 'sent', final_reply = ?, category_id = ? WHERE id = ?",
        (payload.reply, payload.category_id or email_row["category_id"], email_id),
    )

    db.execute(
        "INSERT INTO email_actions (email_id, ai_category_id, ai_confidence, final_category_id, sent_at, smtp_response) VALUES (?, ?, ?, ?, ?, ?)",
        (
            email_id,
            email_row["category_id"],
            email_row["confidence"],
            payload.category_id or email_row["category_id"],
            datetime.utcnow().isoformat(),
            response,
        ),
    )

    return {"status": "sent"}


@router.post("/translate")
def translate_text(payload: TranslateRequest):
    """翻译文本（用于回复内容翻译预览）"""
    baidu_appid = db.get_setting("baidu_appid", "")
    baidu_secret = db.get_setting("baidu_secret", "")
    
    if not baidu_appid or not baidu_secret:
        raise HTTPException(status_code=400, detail="Baidu translation not configured")
    
    translation = translate_baidu(payload.text, baidu_appid, baidu_secret, payload.target_lang)
    
    if translation is None:
        raise HTTPException(status_code=500, detail="Translation failed")
    
    return {"translation": translation}


@router.delete("/{email_id}")
def delete_email(email_id: int):
    """删除邮件（软删除，防止 sync 时重新拉取）"""
    row = db.fetch_one("SELECT * FROM emails WHERE id = ?", (email_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Email not found")
    
    db.execute("UPDATE emails SET status = 'deleted' WHERE id = ?", (email_id,))
    return {"status": "deleted"}


class TestEmailRequest(BaseModel):
    target_email: str = "yo17765767816@163.com"
    count: int = 3
    email_types: Optional[list[str]] = None


@router.post("/test/generate")
def generate_test_emails(payload: TestEmailRequest):
    """
    生成测试邮件并发送到指定邮箱

    支持的邮件类型:
    - shipping: 催发货
    - refund: 申请退款
    - delivery: 未收到快递
    """
    # 限制只能发送到测试邮箱
    allowed_email = "yo17765767816@163.com"
    if payload.target_email.lower() != allowed_email.lower():
        raise HTTPException(
            status_code=400,
            detail=f"Only {allowed_email} is allowed for testing"
        )

    result = generateTestEmails(
        target_email=payload.target_email,
        count=payload.count,
        email_types=payload.email_types
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to send emails"))

    return result
