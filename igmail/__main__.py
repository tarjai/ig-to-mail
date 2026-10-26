"""Kullanım: python -m igmail {carousel|video|health} [URL]"""
import sys
import traceback
from pathlib import Path

from . import config, groq_client, mailer
from .carousel import load_slides, stitch, to_jpeg
from .download import CookieError, Post, download
from .media import NoAudioError, extract_audio
from .ocr import format_slides, ocr_slides
from .video import is_turkish, transcribe, translate_to_turkish

WORKDIR = Path("work")


def _subject(tag: str, post: Post) -> str:
    who = f"@{post.username}" if post.username else post.shortcode
    caption = " ".join(post.caption.split())
    if len(caption) > 50:
        caption = caption[:50].rstrip() + "…"
    return f"[IG {tag}] {who}" + (f" – {caption}" if caption else "")


def _post_section(post: Post) -> tuple[str, str]:
    return "Post", f"{post.url}\n\n{post.caption}".strip()


def run_carousel(post: Post) -> None:
    if not post.media:
        raise RuntimeError("Post'ta görsel bulunamadı")
    slides = load_slides(post.media)
    jpeg = to_jpeg(stitch(slides))

    try:
        client = groq_client.client()
    except RuntimeError as e:
        print(f"[ocr] {e}; yalnızca Tesseract kullanılacak", file=sys.stderr)
        client = None
    text = format_slides(ocr_slides(slides, client))

    msg = mailer.build(
        _subject("Carousel", post),
        [("OCR Metni", text), _post_section(post)],
        [
            mailer.Attachment(f"{post.shortcode}.jpg", jpeg, "image", "jpeg"),
            mailer.Attachment(f"{post.shortcode}.txt", text.encode(), "text", "plain"),
        ],
    )
    mailer.send(msg, WORKDIR)


def run_video(post: Post) -> None:
    videos = post.videos
    if not videos:
        raise RuntimeError("Bu post'ta video yok. Carousel ise diğer kısayolu kullan.")
    client = groq_client.client()

    sections, txt_parts = [], []
    for n, video in enumerate(videos, 1):
        label = f"Video {n}" if len(videos) > 1 else "Video"
        try:
            original, lang = transcribe(client, extract_audio(video))
        except NoAudioError as e:
            sections.append((label, f"(ses yok: {e})"))
            continue
        if not original:
            sections.append((label, "(konuşma algılanmadı)"))
            continue
        if is_turkish(lang):
            sections.append((f"{label} – Transkript (Türkçe)", original))
            txt_parts.append(f"== {label} ==\n{original}")
        else:
            turkish = translate_to_turkish(client, original)
            sections += [(f"{label} – Türkçe Çeviri", turkish),
                         (f"{label} – Orijinal ({lang or '?'})", original)]
            txt_parts.append(f"== {label} – Türkçe ==\n{turkish}\n\n== {label} – Orijinal ({lang}) ==\n{original}")

    sections.append(_post_section(post))
    attachments = []
    if txt_parts:
        attachments.append(mailer.Attachment(f"{post.shortcode}.txt", "\n\n".join(txt_parts).encode(), "text", "plain"))
    mailer.send(mailer.build(_subject("Video", post), sections, attachments), WORKDIR)


def run_health() -> None:
    if not config.HEALTHCHECK_URL:
        print("[health] HEALTHCHECK_URL tanımlı değil, atlanıyor")
        return
    post = download(config.HEALTHCHECK_URL, WORKDIR)
    print(f"[health] OK: {len(post.media)} medya indirildi")


def _error_mail(mode: str, url: str, exc: BaseException) -> None:
    if isinstance(exc, CookieError):
        hint = ("Instagram cookie'si geçersiz veya süresi dolmuş.\n"
                "Çözüm: yan hesapla tarayıcıdan instagram.com'a giriş yap, sessionid cookie'sini kopyala ve "
                "GitHub > Settings > Secrets > IG_SESSIONID değerini güncelle.")
    else:
        hint = "İşlem başarısız oldu. Detay aşağıda."
    tb = "".join(traceback.format_exception(exc))
    msg = mailer.build(f"[IG ❌ {mode}] {type(exc).__name__}",
                       [("Sorun", hint), ("Link", url or "-"), ("Detay", tb[-6000:])])
    mailer.send(msg, WORKDIR)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("carousel", "video", "health"):
        print(__doc__, file=sys.stderr)
        return 2
    mode, url = argv[0], (argv[1] if len(argv) > 1 else "")
    WORKDIR.mkdir(exist_ok=True)
    try:
        if mode == "health":
            run_health()
            return 0
        post = download(url, WORKDIR)
        print(f"[main] {post.shortcode}: {len(post.images)} görsel, {len(post.videos)} video")
        (run_carousel if mode == "carousel" else run_video)(post)
        return 0
    except Exception as e:
        traceback.print_exc()
        try:
            _error_mail(mode, url, e)
        except Exception:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
