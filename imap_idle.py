# imap_idle.py

import time
import ssl
import email

from imapclient import IMAPClient

from config import (
    NAVER_ID,
    NAVER_APP_PASSWORD,
    IMAP_HOST,
    TARGET_SENDERS,
    FORWARD_TO,
    IDLE_TIMEOUT,
)
from state import load_state, save_state
from forwarder import forward_mail
from utils import get_sender, sender_matches


class MailWatcher:
    def __init__(self):
        self.processed_uids = load_state()

    def process_new_mail(self, server):
        messages = server.search(["UNSEEN"])

        for uid in messages:
            uid_str = str(uid)

            if uid_str in self.processed_uids:
                continue

            raw = server.fetch([uid], ["RFC822"])
            msg = email.message_from_bytes(raw[uid][b"RFC822"])

            sender = get_sender(msg)

            if not sender_matches(sender, TARGET_SENDERS):
                continue

            try:
                forward_mail(msg, FORWARD_TO)
                self.processed_uids.add(uid_str)
                print(f"[포워딩 완료] UID={uid}, sender={sender}")
            except Exception as e:
                print(f"[에러] UID={uid}, error={e}")

        save_state(self.processed_uids)

    def run(self):
        context = ssl.create_default_context()

        with IMAPClient(IMAP_HOST, ssl=True, ssl_context=context) as server:
            server.login(NAVER_ID, NAVER_APP_PASSWORD)
            server.select_folder("INBOX")

            print("IMAP IDLE 시작")

            while True:
                try:
                    server.idle()
                    print("IDLE 진입")

                    start = time.time()

                    while time.time() - start < IDLE_TIMEOUT:
                        responses = server.idle_check(timeout=30)

                        if responses:
                            print("📩 새 메일 감지")
                            self.process_new_mail(server)

                    server.idle_done()
                    print("IDLE 재시작")

                except Exception as e:
                    print(f"연결 오류: {e}")
                    time.sleep(5)
