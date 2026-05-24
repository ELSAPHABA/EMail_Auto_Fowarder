#!/bin/sh
set -eu

STATE_FILE="${STATE_FILE:-forwarded_uids.json}"
STATE_DIR="$(dirname "$STATE_FILE")"

if [ "$STATE_DIR" != "." ]; then
  mkdir -p "$STATE_DIR"
fi

exec "$@"
