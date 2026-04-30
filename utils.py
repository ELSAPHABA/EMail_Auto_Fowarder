# utils.py

from email.header import decode_header
from email.utils import parseaddr
from fnmatch import fnmatchcase

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


def normalize_sender_pattern(pattern):
    pattern = pattern.strip().lower()
    if pattern.startswith("<") and pattern.endswith(">"):
        pattern = pattern[1:-1].strip()
    return pattern


def sender_matches(sender, patterns):
    return any(fnmatchcase(sender, pattern) for pattern in patterns)


def imap_from_terms(patterns):
    terms = set()

    for pattern in patterns:
        pattern = normalize_sender_pattern(pattern)

        if "*" not in pattern and "?" not in pattern:
            terms.add(pattern)
            continue

        if pattern.startswith("*@*."):
            terms.add(pattern[4:])
            continue

        if pattern.startswith("*@"):
            terms.add(pattern[2:].lstrip("*."))
            continue

        if "@" in pattern:
            _, domain = pattern.rsplit("@", 1)
            term = domain.replace("*", "").replace("?", "").lstrip(".")
        else:
            term = pattern.replace("*", "").replace("?", "").strip(".")

        if term:
            terms.add(term)

    return sorted(terms)


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
