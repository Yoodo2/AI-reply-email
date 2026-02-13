from typing import Dict, List, Optional, Tuple

from .ai_client import classify_email_ai


def _keyword_match(text: str, categories: List[Dict]) -> Optional[Tuple[Dict, float]]:
    lowered = text.lower()
    best = None
    for cat in categories:
        keywords = [k.strip().lower() for k in (cat.get("keywords") or "").split(",") if k.strip()]
        score = sum(1 for k in keywords if k in lowered)
        if score > 0 and (best is None or score > best[1]):
            best = (cat, float(score))
    if best:
        confidence = min(0.95, 0.6 + best[1] * 0.1)
        return best[0], confidence
    return None


def _default_category(categories: List[Dict]) -> Dict:
    for cat in categories:
        if cat.get("is_default"):
            return cat
    return categories[0]


def classify_email(
    text: str,
    categories: List[Dict],
    api_key: str,
    base_url: str,
    model: str,
) -> Tuple[Dict, float, str, str]:
    """
    分类邮件。
    返回: (category_dict, confidence, method, reason)
    method: "keyword" | "ai"
    reason: 分类原因说明
    """
    # 第一步：关键词匹配（优先级最高）
    keyword_hit = _keyword_match(text, categories)
    if keyword_hit:
        return keyword_hit[0], keyword_hit[1], "keyword", "关键词命中"

    # 第二步：AI 语义分类
    ai_result = classify_email_ai(api_key, text, categories, base_url, model)
    if ai_result:
        category_id = ai_result["category_id"]
        confidence = ai_result["confidence"]
        reason = ai_result["reason"]

        if category_id == 0:
            other_cat = next((c for c in categories if c.get("name") in ["其他", "other", "Other"]), None)
            if other_cat:
                return other_cat, 0.3, "ai", reason or "AI未匹配到明确分类"
        else:
            chosen = next((c for c in categories if c["id"] == category_id), None)
            if chosen:
                return chosen, confidence, "ai", reason

    # 兜底：默认分类
    return _default_category(categories), 0.1, "default", "无法识别，使用默认分类"
