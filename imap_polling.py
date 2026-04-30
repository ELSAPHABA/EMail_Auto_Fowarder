# imap_polling.py

import email
import ssl
import time
from datetime import datetime

from imapclient import IMAPClient

from config import (
    FORWARD_TO,
    IMAP_HOST,
    IMAP_MAILBOX,
    NAVER_APP_PASSWORD,
    NAVER_ID,
    POLL_INTERVAL,
    RECONNECT_DELAY,
    TARGET_SENDERS,
)
from forwarder import forward_mail
from state import load_state, save_state
from utils import get_sender, imap_from_terms, sender_matches


class MailWatcher:
    def __init__(self):
        self.state = load_state()
        self.from_terms = imap_from_terms(TARGET_SENDERS)

    def run(self):
        print(f"IMAP Polling 시작: mailbox={IMAP_MAILBOX}, interval={POLL_INTERVAL}s")
        print(f"서버 FROM 검색어: {', '.join(self.from_terms) or '(none)'}")

        while True:
            try:
                self._run_connection()
            except Exception as e:
                print(f"연결 오류: {e}")
                time.sleep(RECONNECT_DELAY)

    def _run_connection(self):
        context = ssl.create_default_context()

        with IMAPClient(IMAP_HOST, ssl=True, ssl_context=context) as server:
            server.login(NAVER_ID, NAVER_APP_PASSWORD)

            while True:
                self._poll_once(server)
                time.sleep(POLL_INTERVAL)

    def _poll_once(self, server):
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last_uid = self.state["last_uid"]
        print(f"[Polling] {checked_at} mailbox={IMAP_MAILBOX}, last_uid={last_uid}")

        select_response = server.select_folder(IMAP_MAILBOX)
        uidnext = self._response_int(select_response, b"UIDNEXT")
        search_end_uid = uidnext - 1 if uidnext else last_uid

        if search_end_uid <= last_uid:
            print("[Polling] 새 UID 없음")
            return

        candidate_uids = self._search_candidate_uids(server, last_uid + 1)
        print(
            "[Polling] "
            f"검색범위={last_uid + 1}:*, 후보={len(candidate_uids)}"
        )

        next_last_uid = self._process_candidates(server, candidate_uids)
        if next_last_uid is None:
            next_last_uid = search_end_uid

        self.state["last_uid"] = max(last_uid, next_last_uid)
        save_state(self.state)
        print(f"[Polling] 저장된 last_uid={self.state['last_uid']}")

    def _search_candidate_uids(self, server, start_uid):
        uid_range = f"{start_uid}:*"

        if not self.from_terms:
            return sorted(server.search(["UID", uid_range]))

        uids = set()
        for term in self.from_terms:
            matched = server.search(["UID", uid_range, "FROM", term])
            uids.update(matched)

        return sorted(uids)

    def _process_candidates(self, server, uids):
        if not uids:
            return None

        headers = server.fetch(uids, ["BODY.PEEK[HEADER]"])
        last_completed_uid = uids[0] - 1

        for uid in uids:
            try:
                header_msg = self._message_from_fetch(headers.get(uid), "HEADER")
                sender = get_sender(header_msg)

                if not sender_matches(sender, TARGET_SENDERS):
                    print(f"[스킵] UID={uid}, sender={sender}")
                    last_completed_uid = uid
                    continue

                full = server.fetch([uid], ["BODY[]"])
                msg = self._message_from_fetch(full.get(uid), "BODY")

                forward_mail(msg, FORWARD_TO)
                print(f"[포워딩 완료] UID={uid}, sender={sender}")
                last_completed_uid = uid
            except Exception as e:
                print(f"[에러] UID={uid}, error={e}")
                break

        return last_completed_uid

    @staticmethod
    def _message_from_fetch(fetch_data, expected_name):
        if not fetch_data:
            raise RuntimeError(f"{expected_name} fetch response is empty")

        payload = None
        for key, value in fetch_data.items():
            if isinstance(key, bytes) and key.upper().startswith(b"BODY["):
                payload = value
                break

        if payload is None:
            raise RuntimeError(f"{expected_name} fetch payload is missing")

        return email.message_from_bytes(payload)

    @staticmethod
    def _response_int(response, key):
        value = response.get(key)
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            value = value[0]
        if isinstance(value, bytes):
            value = value.decode("ascii")
        return int(value)
