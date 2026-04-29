# main.py

from imap_polling import MailWatcher

if __name__ == "__main__":
    watcher = MailWatcher()
    watcher.run()
