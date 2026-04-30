# state.py

import json
import os

from config import STATE_FILE


def _empty_state():
    return {
        "last_uid": 0,
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        return _empty_state()

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        state = _empty_state()
        state["last_uid"] = max((int(uid) for uid in data), default=0)
        return state

    state = _empty_state()
    state["last_uid"] = int(
        data.get("last_uid")
        or data.get("last_seen_uid")
        or 0
    )
    return state


def save_state(state):
    data = {
        "last_uid": int(state["last_uid"]),
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
