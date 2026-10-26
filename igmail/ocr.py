import base64
import io
import sys
from dataclasses import dataclass

from PIL import Image

from . import config
from .groq_client import chat

OCR_MAX_SIDE = 1600
NO_TEXT = "[METİN YOK]"
PROMPT = (
    "Bu görseldeki tüm yazıyı okuma sırasıyla, olduğu dilde ve aynen çıkar. "
    "Satır ve paragraf yapısını koru. Yorum, açıklama, çeviri veya başlık ekleme. "
    f"Görselde hiç yazı yoksa yalnızca {NO_TEXT} yaz."
)


@dataclass
class SlideText:
    index: int
    text: str
    engine: str


def _data_url(img: Image.Image) -> str:
    img = img.copy()
    img.thumbnail((OCR_MAX_SIDE, OCR_MAX_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def groq_ocr(client, img: Image.Image) -> str:
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": _data_url(img)}},
        ],
    }]
    return chat(client, config.VISION_MODEL, messages)


def tesseract_ocr(img: Image.Image) -> str:
    import pytesseract
    return pytesseract.image_to_string(img, lang="tur+eng").strip()


def ocr_slides(slides: list[Image.Image], client=None) -> list[SlideText]:
    results = []
    for i, img in enumerate(slides, 1):
        text, engine = None, "groq"
        if client is not None:
            try:
                text = groq_ocr(client, img)
            except Exception as e:  # limit, model kaldırılmış, ağ hatası vb.
                print(f"[ocr] slayt {i}: Groq hata ({e!r}), Tesseract'a geçiliyor", file=sys.stderr)
        if text is None:
            engine = "tesseract"
            text = tesseract_ocr(img)
        if not text or text.strip() == NO_TEXT:
            text = ""
        results.append(SlideText(i, text, engine))
    return results


def format_slides(results: list[SlideText]) -> str:
    blocks = []
    for r in results:
        tag = " (Tesseract)" if r.engine == "tesseract" else ""
        blocks.append(f"--- Slayt {r.index}{tag} ---\n{r.text or '(metin yok)'}")
    return "\n\n".join(blocks)
