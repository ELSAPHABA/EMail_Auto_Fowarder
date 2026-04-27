# utils.py

from fnmatch import fnmatchcase
from email.header import decode_header
from email.utils import parseaddr

def decode_mime(value):
    if not value:
        return ""

    parts = decode_header(value)
    return "".join(
        part.decode(enc or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, enc in parts
    )


def get_sender(msg):
    _, addr = parseaddr(msg.get("From", ""))
    return addr.lower()


def sender_matches(sender, patterns):
    return any(fnmatchcase(sender, pattern) for pattern in patterns)


def extract_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

    return "(본문 없음)"
