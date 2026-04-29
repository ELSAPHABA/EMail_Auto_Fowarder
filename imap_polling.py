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
from utils import get_sender, sender_matches


class MailWatcher:
    def __init__(self):
        self.state = load_state()
        self.use_qresync = False

    def run(self):
        print(f"IMAP Polling 시작: mailbox={IMAP_MAILBOX}, interval={POLL_INTERVAL}s")

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
            self.use_qresync = self._enable_sync_extensions(server)

            select_response = self._select_mailbox(server)
            self._poll_once(server, select_response)

            while True:
                time.sleep(POLL_INTERVAL)
                self._poll_once(server)

    def _enable_sync_extensions(self, server):
        capabilities = self._capability_names(server.capabilities())

        if "CONDSTORE" not in capabilities and "QRESYNC" not in capabilities:
            raise RuntimeError(
                "IMAP server does not advertise CONDSTORE or QRESYNC capabilities"
            )

        if "ENABLE" not in capabilities:
            return False

        if "QRESYNC" in capabilities:
            try:
                enabled = self._capability_names(server.enable("QRESYNC"))
                if "QRESYNC" in enabled:
                    print("QRESYNC 활성화")
                    return True
            except Exception as e:
                print(f"QRESYNC 활성화 실패, CONDSTORE로 계속 진행: {e}")

        if "CONDSTORE" in capabilities:
            enabled = self._capability_names(server.enable("CONDSTORE"))
            if "CONDSTORE" in enabled:
                print("CONDSTORE 활성화")

        return False

    def _select_mailbox(self, server):
        if self.use_qresync and self._has_qresync_baseline():
            try:
                return self._select_mailbox_qresync(server)
            except Exception as e:
                print(f"QRESYNC SELECT 실패, 일반 SELECT로 재동기화: {e}")

        response = server.select_folder(IMAP_MAILBOX)
        if b"HIGHESTMODSEQ" not in response:
            all_uids = server.search(["ALL"])
            if all_uids:
                server.fetch([all_uids[0]], ["MODSEQ"])
            response = server.select_folder(IMAP_MAILBOX)

        if b"HIGHESTMODSEQ" not in response:
            raise RuntimeError("CONDSTORE is not active for the selected mailbox")

        return response

    def _select_mailbox_qresync(self, server):
        uidvalidity = self.state["uidvalidity"]
        highestmodseq = self.state["highestmodseq"]
        last_seen_uid = self.state["last_seen_uid"]
        known_uids = f"1:{last_seen_uid}" if last_seen_uid else None

        if known_uids:
            params = f"(QRESYNC ({uidvalidity} {highestmodseq} {known_uids}))"
        else:
            params = f"(QRESYNC ({uidvalidity} {highestmodseq}))"

        tag = server._imap._command(
            "SELECT",
            server._normalise_folder(IMAP_MAILBOX),
            params,
        )
        typ, data = server._imap._command_complete("SELECT", tag)
        server._checkok("select", typ, data)
        return server._process_select_response(server._imap.untagged_responses)

    def _poll_once(self, server, select_response=None):
        checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Polling] {checked_at} mailbox={IMAP_MAILBOX}")

        previous_uidvalidity = self.state["uidvalidity"]
        previous_modseq = self.state["highestmodseq"]
        previous_last_uid = self.state["last_seen_uid"]

        if select_response is None:
            select_response = self._select_mailbox(server)

        current_uidvalidity = self._response_int(select_response, b"UIDVALIDITY")
        current_highestmodseq = self._response_int(select_response, b"HIGHESTMODSEQ")
        current_uidnext = self._response_int(select_response, b"UIDNEXT")

        if previous_uidvalidity and previous_uidvalidity != current_uidvalidity:
            print("UIDVALIDITY 변경 감지, 저장된 UID 상태 초기화")
            self.state["processed_uids"].clear()
            previous_modseq = None
            previous_last_uid = 0

        self.state["uidvalidity"] = current_uidvalidity

        candidate_uids = self._candidate_uids(
            server,
            previous_modseq,
            previous_last_uid,
        )
        failed_uids = self._process_candidate_uids(server, candidate_uids)

        if failed_uids:
            retry_floor = min(failed_uids) - 1
            if retry_floor > self.state["last_seen_uid"]:
                self.state["last_seen_uid"] = retry_floor
            print(f"처리 실패 UID 재시도 예정: {sorted(failed_uids)}")
        else:
            self.state["highestmodseq"] = current_highestmodseq
            self.state["last_seen_uid"] = max(
                self.state["last_seen_uid"],
                current_uidnext - 1 if current_uidnext else 0,
                max(candidate_uids, default=0),
            )

        save_state(self.state)

    def _candidate_uids(self, server, previous_modseq, previous_last_uid):
        candidates = set()

        if previous_modseq:
            changed_uids = server.search(["MODSEQ", str(previous_modseq)])
            candidates.update(changed_uids)
        else:
            candidates.update(server.search(["UNSEEN"]))

        if previous_last_uid:
            new_uids = server.search(["UID", f"{previous_last_uid + 1}:*"])
            candidates.update(new_uids)

        processed = self.state["processed_uids"]
        return sorted(uid for uid in candidates if str(uid) not in processed)

    def _process_candidate_uids(self, server, uids):
        failed_uids = set()

        for uid in uids:
            uid_str = str(uid)

            try:
                raw = server.fetch([uid], ["RFC822", "MODSEQ"])
                if uid not in raw or b"RFC822" not in raw[uid]:
                    raise RuntimeError("RFC822 fetch response is empty")

                msg = email.message_from_bytes(raw[uid][b"RFC822"])
                sender = get_sender(msg)

                if sender_matches(sender, TARGET_SENDERS):
                    forward_mail(msg, FORWARD_TO)
                    print(f"[포워딩 완료] UID={uid}, sender={sender}")

                self.state["processed_uids"].add(uid_str)
            except Exception as e:
                failed_uids.add(uid)
                print(f"[에러] UID={uid}, error={e}")

        return failed_uids

    def _has_qresync_baseline(self):
        return bool(self.state["uidvalidity"] and self.state["highestmodseq"])

    @staticmethod
    def _capability_names(capabilities):
        return {
            capability.decode("ascii", errors="replace").upper()
            if isinstance(capability, bytes)
            else str(capability).upper()
            for capability in capabilities
        }

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
