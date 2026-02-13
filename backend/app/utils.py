from langdetect import detect


def detect_language(text: str) -> str:
    if not text:
        return ""
    try:
        return detect(text)
    except Exception:
        return ""
