import json
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import config

URL_RE = re.compile(r"https?://\S+")
POST_RE = re.compile(r"instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")
SHARE_RE = re.compile(r"instagram\.com/share/")
AUTH_HINTS = ("login", "checkpoint", "challenge", "401", "authorizationerror", "authrequired")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)


class DownloadError(Exception):
    pass


class CookieError(DownloadError):
    pass


@dataclass
class Post:
    url: str
    shortcode: str
    username: str = ""
    caption: str = ""
    media: list[Path] = field(default_factory=list)

    @property
    def images(self) -> list[Path]:
        return [p for p in self.media if p.suffix.lower() in IMAGE_EXT]

    @property
    def videos(self) -> list[Path]:
        return [p for p in self.media if p.suffix.lower() in VIDEO_EXT]


def _resolve_share_link(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.geturl()


def normalize_url(raw: str) -> tuple[str, str]:
    """Shortcut'tan gelen metin/URL'den kanonik post URL'si ve shortcode döndürür."""
    m = URL_RE.search(raw.strip())
    if not m:
        raise DownloadError(f"Geçerli bir URL bulunamadı: {raw!r}")
    url = m.group(0)
    if SHARE_RE.search(url):
        url = _resolve_share_link(url)
    m = POST_RE.search(url)
    if not m:
        raise DownloadError(f"Instagram post/reel linki değil: {url}")
    code = m.group(1)
    return f"https://www.instagram.com/p/{code}/", code


def _write_config(path: Path) -> None:
    cookies = {"sessionid": config.IG_SESSIONID}
    if config.IG_CSRFTOKEN:
        cookies["csrftoken"] = config.IG_CSRFTOKEN
    if config.IG_DS_USER_ID:
        cookies["ds_user_id"] = config.IG_DS_USER_ID
    # "merged": sesli tek mp4 dosyası (DASH/yt-dlp bağımlılığı yok)
    cfg = {"extractor": {"instagram": {"cookies": cookies, "videos": "merged", "audio": False}}}
    path.write_text(json.dumps(cfg))


def _run_gallery_dl(url: str, outdir: Path, cfg: Path) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable, "-m", "gallery_dl",
        "--config", str(cfg),
        "-D", str(outdir),
        "-f", "{num:>03}.{extension}",
        "--write-metadata",
        "--no-mtime",
        url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def _media_files(outdir: Path) -> list[Path]:
    files = [p for p in outdir.iterdir() if p.suffix.lower() in IMAGE_EXT | VIDEO_EXT]
    return sorted(files, key=lambda p: p.name)


def download(raw_url: str, workdir: Path, attempts: int = 3) -> Post:
    if not config.IG_SESSIONID:
        raise CookieError("IG_SESSIONID secret'ı tanımlı değil")
    url, code = normalize_url(raw_url)
    outdir = workdir / code
    outdir.mkdir(parents=True, exist_ok=True)
    cfg = workdir / "gallery-dl.json"
    _write_config(cfg)

    log = ""
    for i in range(attempts):
        res = _run_gallery_dl(url, outdir, cfg)
        log = (res.stdout + "\n" + res.stderr).strip()
        print(log, file=sys.stderr)
        files = _media_files(outdir)
        if files:
            break
        if any(h in log.lower() for h in AUTH_HINTS):
            raise CookieError(f"Instagram oturumu reddetti (cookie geçersiz/süresi dolmuş olabilir).\n\n{log}")
        if i < attempts - 1:
            time.sleep(5 * 3**i)
    else:
        raise DownloadError(f"Medya indirilemedi ({attempts} deneme).\n\n{log}")

    post = Post(url=url, shortcode=code, media=files)
    meta_files = sorted(outdir.glob("*.json"))
    if meta_files:
        meta = json.loads(meta_files[0].read_text())
        post.username = meta.get("username") or meta.get("owner_username") or ""
        post.caption = meta.get("description") or ""
    return post
