from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import db

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateRequest(BaseModel):
    category_id: int
    name: str
    content: str
    variables: str | None = None


@router.get("")
def list_templates():
    rows = db.fetch_all("SELECT * FROM templates ORDER BY id DESC")
    return [dict(row) for row in rows]


@router.post("")
def create_template(payload: TemplateRequest):
    template_id = db.execute(
        "INSERT INTO templates (category_id, name, content, variables) VALUES (?, ?, ?, ?)",
        (payload.category_id, payload.name, payload.content, payload.variables),
    )
    return {"id": template_id}


@router.put("/{template_id}")
def update_template(template_id: int, payload: TemplateRequest):
    db.execute(
        "UPDATE templates SET category_id = ?, name = ?, content = ?, variables = ? WHERE id = ?",
        (payload.category_id, payload.name, payload.content, payload.variables, template_id),
    )
    return {"status": "ok"}


@router.delete("/{template_id}")
def delete_template(template_id: int):
    existing = db.fetch_one("SELECT * FROM templates WHERE id = ?", (template_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Template not found")
    db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    return {"status": "deleted"}
