# fowarder.py

import ssl
import smtplib
from email.message import EmailMessage
from email.utils import formatdate

from config import NAVER_ID, NAVER_APP_PASSWORD, SMTP_HOST, SMTP_PORT
from utils import decode_mime, extract_text


def forward_mail(msg, forward_to):
    subject = decode_mime(msg.get("Subject"))
    sender = decode_mime(msg.get("From"))
    date = msg.get("Date")

    body = extract_text(msg)

    fwd = EmailMessage()
    fwd["From"] = NAVER_ID
    fwd["To"] = forward_to
    fwd["Subject"] = f"[FWD] {subject}"
    fwd["Date"] = formatdate(localtime=True)

    fwd.set_content(f"""
자동 전달 메일

원본 발신자: {sender}
원본 날짜: {date}
원본 제목: {subject}

----- 본문 -----

{body}
""")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as smtp:
        smtp.login(NAVER_ID, NAVER_APP_PASSWORD)
        smtp.send_message(fwd)