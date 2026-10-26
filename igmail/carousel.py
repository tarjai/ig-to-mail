import io
from pathlib import Path

from PIL import Image, ImageOps

from .download import VIDEO_EXT
from .media import first_frame

MAX_WIDTH = 1080
GAP = 8
GAP_COLOR = (255, 255, 255)
JPEG_MAX_DIM = 65000
MAX_BYTES = 15 * 1024 * 1024  # base64 ile ~20MB, Gmail 25MB sınırının altında


def load_slides(media: list[Path]) -> list[Image.Image]:
    slides = []
    for path in media:
        src = first_frame(path) if path.suffix.lower() in VIDEO_EXT else path
        with Image.open(src) as im:
            slides.append(ImageOps.exif_transpose(im).convert("RGB"))
    return slides


def stitch(slides: list[Image.Image], max_width: int = MAX_WIDTH, gap: int = GAP) -> Image.Image:
    if not slides:
        raise ValueError("Birleştirilecek görsel yok")
    width = min(max_width, min(s.width for s in slides))
    resized = [s if s.width == width else s.resize((width, round(s.height * width / s.width)), Image.LANCZOS)
               for s in slides]
    height = sum(s.height for s in resized) + gap * (len(resized) - 1)

    canvas = Image.new("RGB", (width, height), GAP_COLOR)
    y = 0
    for s in resized:
        canvas.paste(s, (0, y))
        y += s.height + gap

    if height > JPEG_MAX_DIM:
        scale = JPEG_MAX_DIM / height
        canvas = canvas.resize((round(width * scale), JPEG_MAX_DIM), Image.LANCZOS)
    return canvas


def to_jpeg(img: Image.Image, max_bytes: int = MAX_BYTES) -> bytes:
    for quality in (88, 80, 70, 60, 50):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        if buf.tell() <= max_bytes:
            return buf.getvalue()
    img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    return to_jpeg(img, max_bytes)
