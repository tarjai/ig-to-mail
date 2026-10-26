import html
import smtplib
import ssl
import time
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from . import config


@dataclass
class Attachment:
    filename: str
    data: bytes
    maintype: str
    subtype: str


def _html_body(sections: list[tuple[str, str]]) -> str:
    parts = []
    for title, body in sections:
        parts.append(
            f"<h3 style='font-family:sans-serif;margin:18px 0 6px'>{html.escape(title)}</h3>"
            f"<div style='font-family:sans-serif;font-size:14px;line-height:1.5;white-space:pre-wrap'>"
            f"{html.escape(body)}</div>"
        )
    return "<html><body>" + "".join(parts) + "</body></html>"


def build(subject: str, sections: list[tuple[str, str]], attachments: list[Attachment] = ()) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_USER or "ig-to-mail@localhost"
    msg["To"] = config.MAIL_TO or msg["From"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="ig-to-mail")
    msg.set_content("\n\n".join(f"== {t} ==\n{b}" for t, b in sections))
    msg.add_alternative(_html_body(sections), subtype="html")
    for a in attachments:
        msg.add_attachment(a.data, maintype=a.maintype, subtype=a.subtype, filename=a.filename)
    return msg


def send(msg: EmailMessage, dry_run_dir: Path | None = None, attempts: int = 3) -> None:
    if config.DRY_RUN:
        out = (dry_run_dir or Path("work")) / f"mail-{int(time.time())}.eml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(bytes(msg))
        print(f"[mail] DRY_RUN: {out}")
        return
    if not (config.GMAIL_USER and config.GMAIL_APP_PASSWORD):
        raise RuntimeError("GMAIL_USER / GMAIL_APP_PASSWORD tanımlı değil")
    for i in range(attempts):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=60) as s:
                s.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
                s.send_message(msg)
            print(f"[mail] gönderildi -> {msg['To']}")
            return
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, OSError):
            if i == attempts - 1:
                raise
            time.sleep(5 * (i + 1))
