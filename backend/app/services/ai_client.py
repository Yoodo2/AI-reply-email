import json
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 底层通用调用
# ---------------------------------------------------------------------------

def _call_llm(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    temperature: float = 0.2,
) -> Optional[str]:
    if not api_key:
        return None

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# 阶段一：分类
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM_PROMPT = """\
你是一个专业的客服邮件分类引擎。
你的唯一任务是：根据邮件内容，从给定的分类列表中选择最匹配的一个。

规则：
1. 仔细阅读邮件内容，理解客户核心意图。
2. 将意图与分类列表逐一比对，选择最接近的分类。
3. 如果没有任何分类能匹配，category_id 返回 0。
4. confidence 是你对该分类的把握程度，0-1 之间。
5. reason 用一句话说明为什么选择该分类。

你必须且只能输出一个合法的 JSON 对象，不要输出任何其他文字、解释或 markdown 标记。
输出格式：
{"category_id": <int>, "confidence": <float>, "reason": "<string>"}
"""


def classify_email_ai(
    api_key: str,
    email_text: str,
    categories: List[Dict],
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
) -> Optional[Dict]:
    """
    阶段一：AI 分类。
    输入：邮件正文 + 分类列表
    输出：{"category_id": int, "confidence": float, "reason": str} 或 None
    """
    cat_lines = []
    for c in categories:
        line = f'- ID={c["id"]}  名称="{c["name"]}"'
        if c.get("description"):
            line += f'  描述="{c["description"]}"'
        cat_lines.append(line)

    user_prompt = f"""\
【分类列表】
{chr(10).join(cat_lines)}

【邮件内容】
{email_text[:4000]}
"""

    raw = _call_llm(api_key, CLASSIFY_SYSTEM_PROMPT, user_prompt, base_url, model, temperature=0.1)
    if not raw:
        return None

    # 尝试从返回中提取 JSON
    raw = raw.strip()
    # 处理 ```json ... ``` 包裹
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(raw)
        return {
            "category_id": int(result.get("category_id", 0)),
            "confidence": float(result.get("confidence", 0.0)),
            "reason": str(result.get("reason", "")),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse classify response: {e}\nRaw: {raw[:500]}")
        return None


# ---------------------------------------------------------------------------
# 阶段二：生成回复
# ---------------------------------------------------------------------------

REPLY_SYSTEM_PROMPT = """\
你是一个专业的客服回复撰写助手。
根据邮件内容和已识别的分类，撰写一封礼貌、专业、简洁的客服回复。

规则：
1. 使用与客户邮件相同的语言回复（中文邮件用中文回复，英文邮件用英文回复）。
2. 回复要直接解决客户的问题或给出明确的下一步操作。
3. 语气亲切专业，不要过于生硬也不要过于口语化。
4. 不要编造订单号、日期等具体信息，用 {订单号}、{日期} 等占位符代替。
5. 回复长度适中，通常 3-6 句话。

你必须且只能输出一个合法的 JSON 对象，不要输出任何其他文字、解释或 markdown 标记。
输出格式：
{"subject": "<回复邮件主题>", "body": "<回复正文>"}
"""


def generate_reply_ai(
    api_key: str,
    email_text: str,
    category_name: str,
    category_description: str = "",
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
) -> Optional[Dict]:
    """
    阶段二：AI 生成回复。
    输入：邮件正文 + 分类信息
    输出：{"subject": str, "body": str} 或 None
    """
    user_prompt = f"""\
【邮件分类】{category_name}
【分类描述】{category_description or "无"}

【原始邮件】
{email_text[:4000]}
"""

    raw = _call_llm(api_key, REPLY_SYSTEM_PROMPT, user_prompt, base_url, model, temperature=0.4)
    if not raw:
        return None

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        result = json.loads(raw)
        return {
            "subject": str(result.get("subject", "")),
            "body": str(result.get("body", "")),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse reply response: {e}\nRaw: {raw[:500]}")
        # 如果 JSON 解析失败但有内容，直接当作纯文本回复
        if raw:
            return {"subject": "", "body": raw}
        return None
