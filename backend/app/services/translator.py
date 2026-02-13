import hashlib
import random
import time
from typing import Optional

import requests


def translate_baidu(text: str, appid: str, secret: str, target_lang: str = "zh") -> Optional[str]:
    if not text.strip():
        return ""
    salt = str(int(time.time() * 1000) + random.randint(0, 1000))
    sign_str = f"{appid}{text}{salt}{secret}"
    sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()
    params = {
        "q": text,
        "from": "auto",
        "to": target_lang,
        "appid": appid,
        "salt": salt,
        "sign": sign,
    }
    response = requests.get("https://fanyi-api.baidu.com/api/trans/vip/translate", params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if "trans_result" not in data:
        return None
    return "\n".join([item["dst"] for item in data["trans_result"]])
