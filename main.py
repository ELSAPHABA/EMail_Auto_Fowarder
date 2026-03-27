# main.py

from imap_idle import MailWatcher

if __name__ == "__main__":
    watcher = MailWatcher()
    watcher.run()