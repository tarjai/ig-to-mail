import subprocess
from pathlib import Path

WHISPER_MAX_BYTES = 24 * 1024 * 1024  # Groq free tier limiti 25MB
SEGMENT_SECONDS = 1200


class NoAudioError(Exception):
    pass


def _ffmpeg(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True, text=True, timeout=600,
    )


def first_frame(video: Path) -> Path:
    out = video.with_suffix(".frame.jpg")
    res = _ffmpeg("-i", str(video), "-frames:v", "1", "-q:v", "2", str(out))
    if res.returncode != 0 or not out.exists():
        raise RuntimeError(f"Videodan kare alınamadı: {video.name}\n{res.stderr}")
    return out


def extract_audio(video: Path) -> list[Path]:
    """Whisper için 16kHz mono mp3 çıkarır; limit aşılırsa parçalara böler."""
    out = video.with_suffix(".mp3")
    res = _ffmpeg("-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(out))
    if res.returncode != 0 or not out.exists():
        if "does not contain any stream" in res.stderr or "matches no streams" in res.stderr:
            raise NoAudioError(f"{video.name} dosyasında ses yok")
        raise RuntimeError(f"Ses çıkarılamadı: {video.name}\n{res.stderr}")
    if out.stat().st_size <= WHISPER_MAX_BYTES:
        return [out]

    pattern = video.with_name(f"{video.stem}.part%03d.mp3")
    res = _ffmpeg("-i", str(out), "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
                  "-c", "copy", str(pattern))
    if res.returncode != 0:
        raise RuntimeError(f"Ses bölünemedi: {res.stderr}")
    return sorted(video.parent.glob(f"{video.stem}.part*.mp3"))
