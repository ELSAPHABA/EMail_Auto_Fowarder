# state.py

import json
import os
from config import STATE_FILE

def load_state():
    if not os.path.exists(STATE_FILE):
        return set()

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_state(uids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(uids), f)