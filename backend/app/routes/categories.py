from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import db

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryRequest(BaseModel):
    name: str
    description: str | None = None
    keywords: str | None = None
    is_default: bool = False
    priority: int = 0


@router.get("")
def list_categories():
    rows = db.fetch_all("SELECT * FROM categories ORDER BY priority DESC")
    return [dict(row) for row in rows]


@router.post("")
def create_category(payload: CategoryRequest):
    category_id = db.execute(
        "INSERT INTO categories (name, description, keywords, is_default, priority) VALUES (?, ?, ?, ?, ?)",
        (payload.name, payload.description, payload.keywords, int(payload.is_default), payload.priority),
    )
    return {"id": category_id}


@router.put("/{category_id}")
def update_category(category_id: int, payload: CategoryRequest):
    db.execute(
        "UPDATE categories SET name = ?, description = ?, keywords = ?, is_default = ?, priority = ? WHERE id = ?",
        (payload.name, payload.description, payload.keywords, int(payload.is_default), payload.priority, category_id),
    )
    return {"status": "ok"}


@router.delete("/{category_id}")
def delete_category(category_id: int):
    existing = db.fetch_one("SELECT * FROM categories WHERE id = ?", (category_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    return {"status": "deleted"}
