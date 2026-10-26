import email
import email.policy
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from igmail import config, download, mailer, ocr, video
from igmail.carousel import stitch, to_jpeg


@pytest.mark.parametrize("raw,code", [
    ("https://www.instagram.com/p/ABC123xyz/?igsh=MTc4", "ABC123xyz"),
    ("https://instagram.com/reel/C_d-E1/?utm_source=ig_web", "C_d-E1"),
    ("Şuna bak https://www.instagram.com/someuser/p/XyZ_9/ harika", "XyZ_9"),
    ("https://www.instagram.com/tv/TVcode1/", "TVcode1"),
    ("https://www.instagram.com/reels/Rls42/", "Rls42"),
])
def test_normalize_url(raw, code):
    url, sc = download.normalize_url(raw)
    assert sc == code
    assert url == f"https://www.instagram.com/p/{code}/"


@pytest.mark.parametrize("raw", ["merhaba", "https://example.com/p/abc", "https://www.instagram.com/someuser/"])
def test_normalize_url_rejects(raw):
    with pytest.raises(download.DownloadError):
        download.normalize_url(raw)


def test_stitch_order_and_size():
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    slides = [Image.new("RGB", (1440, 1800), colors[0]),
              Image.new("RGB", (1080, 1350), colors[1]),
              Image.new("RGB", (1080, 1080), colors[2])]
    out = stitch(slides, gap=8)
    assert out.width == 1080
    assert out.height == 1350 + 1350 + 1080 + 16
    assert out.getpixel((10, 10)) == colors[0]
    assert out.getpixel((10, 1350 + 8 + 10)) == colors[1]
    assert out.getpixel((10, out.height - 10)) == colors[2]
    assert out.getpixel((10, 1352)) == (255, 255, 255)  # ayraç
    assert to_jpeg(out)[:2] == b"\xff\xd8"


def test_stitch_caps_jpeg_height():
    slides = [Image.new("RGB", (1080, 20000))] * 4
    out = stitch(slides)
    assert out.height <= 65000


class FailingClient:
    @property
    def chat(self):
        raise RuntimeError("rate limited")


def test_ocr_falls_back_to_tesseract(monkeypatch):
    monkeypatch.setattr(ocr, "tesseract_ocr", lambda img: "yedek metin")
    res = ocr.ocr_slides([Image.new("RGB", (100, 100))], FailingClient())
    assert res[0].engine == "tesseract" and res[0].text == "yedek metin"
    assert "Slayt 1 (Tesseract)" in ocr.format_slides(res)


def test_ocr_groq_and_no_text(monkeypatch):
    replies = iter(["<think>x</think>Merhaba dünya", ocr.NO_TEXT])
    msg = lambda: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(replies)))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: msg())))
    res = ocr.ocr_slides([Image.new("RGB", (50, 50))] * 2, client)
    assert [r.text for r in res] == ["Merhaba dünya", ""]
    assert "(metin yok)" in ocr.format_slides(res)


def test_chunk_text():
    text = ("Bu bir cümle. " * 800).strip()
    chunks = video.chunk_text(text, limit=500)
    assert all(len(c) <= 500 for c in chunks)
    assert " ".join(chunks) == text
    assert video.chunk_text("a" * 1200, limit=500) == ["a" * 500, "a" * 500, "a" * 200]


@pytest.mark.parametrize("lang,expected", [("tr", True), ("Turkish", True), ("english", False), ("", False)])
def test_is_turkish(lang, expected):
    assert video.is_turkish(lang) is expected


def test_mail_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DRY_RUN", True)
    monkeypatch.setattr(config, "GMAIL_USER", "me@example.com")
    monkeypatch.setattr(config, "MAIL_TO", "me@example.com")
    msg = mailer.build("[IG Carousel] @x – ş", [("OCR Metni", "<b>ğüş</b>")],
                       [mailer.Attachment("a.jpg", b"\xff\xd8data", "image", "jpeg")])
    mailer.send(msg, tmp_path)
    eml = next(tmp_path.glob("*.eml"))
    parsed = email.message_from_bytes(eml.read_bytes(), policy=email.policy.default)
    assert parsed["To"] == "me@example.com"
    html = parsed.get_body(("html",)).get_content()
    assert "&lt;b&gt;ğüş&lt;/b&gt;" in html
    att = list(parsed.iter_attachments())
    assert att[0].get_filename() == "a.jpg" and att[0].get_content() == b"\xff\xd8data"
