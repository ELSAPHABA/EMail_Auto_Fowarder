# EMail_Auto_Fowarder
Automatically forwards selected incoming email with IMAP polling.

The watcher polls every 20 seconds by default and uses IMAP
CONDSTORE/QRESYNC state (`UIDVALIDITY`, `UIDNEXT`, `HIGHESTMODSEQ`) to detect
mailbox changes without relying on IMAP IDLE.

`TARGET_SENDERS` accepts comma-separated sender patterns.

Examples:
- `alert@example.com`
- `*@openai.com`
- `*@*.openai.com`

Polling interval can be changed with `POLL_INTERVAL`.
