import os


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


GROQ_API_KEY = env("GROQ_API_KEY")
VISION_MODEL = env("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
TEXT_MODEL = env("GROQ_TEXT_MODEL", "qwen/qwen3.8-27b")
WHISPER_MODEL = env("GROQ_WHISPER_MODEL", "whisper-large-v3")

IG_SESSIONID = env("IG_SESSIONID")
IG_CSRFTOKEN = env("IG_CSRFTOKEN")
IG_DS_USER_ID = env("IG_DS_USER_ID")

GMAIL_USER = env("GMAIL_USER")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD")
MAIL_TO = env("MAIL_TO", GMAIL_USER)
# DRY_RUN=1: mail yerine work/ altına .eml yazar (lokal test için)
DRY_RUN = env("DRY_RUN") in ("1", "true", "yes")

HEALTHCHECK_URL = env("HEALTHCHECK_URL")
