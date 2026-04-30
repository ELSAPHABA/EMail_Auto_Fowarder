# config.py

import os

from dotenv import load_dotenv

load_dotenv()


def _require_env(name):
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Required environment variable is not set: {name}")
    return value.strip()


def _parse_target_senders(value):
    return {
        _normalize_sender_pattern(sender)
        for sender in value.split(",")
        if sender.strip()
    }


def _normalize_sender_pattern(sender):
    sender = sender.strip().lower()
    if sender.startswith("<") and sender.endswith(">"):
        sender = sender[1:-1].strip()
    return sender


NAVER_ID = _require_env("NAVER_ID")
NAVER_APP_PASSWORD = _require_env("NAVER_APP_PASSWORD")
FORWARD_TO = _require_env("FORWARD_TO")

TARGET_SENDERS = _parse_target_senders(_require_env("TARGET_SENDERS"))

IMAP_HOST = os.getenv("IMAP_HOST", "imap.naver.com").strip()
IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.naver.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

STATE_FILE = os.getenv("STATE_FILE", "forwarded_uids.json").strip()
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))
