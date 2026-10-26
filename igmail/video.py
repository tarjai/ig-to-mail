import re
from pathlib import Path

from . import config
from .groq_client import chat

TURKISH = {"tr", "turkish", "türkçe", "turkce"}
CHUNK_CHARS = 4000
SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")
TRANSLATE_SYSTEM = (
    "Profesyonel bir çevirmensin. Kullanıcının verdiği konuşma transkriptini akıcı ve doğal "
    "Türkçeye çevir. Anlamı koru, özetleme. Yalnızca çeviriyi yaz; açıklama ekleme."
)


def transcribe(client, audio_parts: list[Path]) -> tuple[str, str]:
    texts, language = [], ""
    for part in audio_parts:
        with part.open("rb") as f:
            res = client.audio.transcriptions.create(
                file=(part.name, f.read()),
                model=config.WHISPER_MODEL,
                response_format="verbose_json",
                temperature=0,
            )
        texts.append((res.text or "").strip())
        extra = getattr(res, "model_extra", None) or {}
        language = language or getattr(res, "language", None) or extra.get("language") or ""
    return "\n".join(t for t in texts if t), language.lower()


def is_turkish(language: str) -> bool:
    return language.strip().lower() in TURKISH


def chunk_text(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Cümle sınırlarından ~limit karakterlik parçalara böler; tek cümle limiti aşarsa sert keser."""
    chunks, cur = [], ""
    for sentence in SENTENCE_RE.split(text.strip()):
        while len(sentence) > limit:
            chunks.append(sentence[:limit])
            sentence = sentence[limit:]
        if cur and len(cur) + 1 + len(sentence) > limit:
            chunks.append(cur)
            cur = ""
        cur = f"{cur} {sentence}" if cur else sentence
    if cur:
        chunks.append(cur)
    return chunks


def translate_to_turkish(client, text: str) -> str:
    out = []
    for chunk in chunk_text(text):
        out.append(chat(client, config.TEXT_MODEL, [
            {"role": "system", "content": TRANSLATE_SYSTEM},
            {"role": "user", "content": chunk},
        ], max_tokens=8192))
    return "\n".join(out)
