# state.py

import json
import os

from config import STATE_FILE


def _empty_state():
    return {
        "uidvalidity": None,
        "highestmodseq": None,
        "last_seen_uid": 0,
        "processed_uids": set(),
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        return _empty_state()

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        state = _empty_state()
        state["processed_uids"] = {str(uid) for uid in data}
        return state

    state = _empty_state()
    state["uidvalidity"] = data.get("uidvalidity")
    state["highestmodseq"] = data.get("highestmodseq")
    state["last_seen_uid"] = int(data.get("last_seen_uid") or 0)
    state["processed_uids"] = {
        str(uid)
        for uid in data.get("processed_uids", [])
    }
    return state


def save_state(state):
    data = {
        "uidvalidity": state["uidvalidity"],
        "highestmodseq": state["highestmodseq"],
        "last_seen_uid": state["last_seen_uid"],
        "processed_uids": sorted(state["processed_uids"], key=int),
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
