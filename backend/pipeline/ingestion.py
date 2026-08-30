"""Ingestion and Watchdog Layer for NIC IMAP and Scanned PDF/Image Watcher."""

import email
import hashlib
import imaplib
import logging
import os
import shutil
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import keyring
except ImportError:
    keyring = None

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import config
from pipeline.database import (
    get_imap_cursor,
    log_audit,
    record_source,
    update_imap_cursor,
)

logger = logging.getLogger("CollectorateIngestion")

KEYRING_SERVICE = "ErodeCollectorate_IMAP"
_IN_MEMORY_CREDS: Dict[str, str] = {}


def get_stored_imap_password(username: str = "") -> Optional[str]:
    """Retrieve IMAP password from Windows Credential Manager or fallback."""
    if keyring:
        try:
            val = keyring.get_password(KEYRING_SERVICE, username)
            if val:
                return val
        except Exception as e:
            logger.warning(f"Keyring read note: {e}")
    return _IN_MEMORY_CREDS.get(username) or getattr(config, 'IMAP_PASSWORD', '')


def set_stored_imap_password(username: str, password: str) -> bool:
    """Store IMAP password into Windows Credential Manager or in-memory fallback."""
    _IN_MEMORY_CREDS[username] = password
    if keyring:
        try:
            keyring.set_password(KEYRING_SERVICE, username, password)
            return True
        except Exception as e:
            logger.error(f"Keyring write error: {e}")
    return True


def test_imap_connection(
    server: str = "imap.gmail.com",
    port: int = 993,
    username: str = "",
    password: Optional[str] = None,
) -> Tuple[bool, str, List[str]]:
    """Test SSL connection to IMAP server and fetch top 5 subject lines."""
    pwd = password or get_stored_imap_password(username)
    if not username or not pwd:
        return False, "பயனர் பெயர் அல்லது கடவுச்சொல் வழங்கப்படவில்லை (Missing credentials)", []

    mail = None
    subjects = []
    try:
        mail = imaplib.IMAP4_SSL(server, port, timeout=10)
        mail.login(username, pwd)
        mail.select("INBOX", readonly=True)
        status, response = mail.search(None, "ALL")
        if status == "OK" and response and response[0]:
            msg_ids = response[0].split()
            last_5 = msg_ids[-5:]
            for m_id in reversed(last_5):
                res, data = mail.fetch(m_id, "(BODY[HEADER.FIELDS (SUBJECT)])")
                if res == "OK" and data:
                    hdr_str = data[0][1].decode("utf-8", errors="replace")
                    subj = hdr_str.replace("Subject:", "").strip()
                    subjects.append(subj or "(No Subject)")
        return True, "இணைப்பு வெற்றிகரமாக முடிந்தது (Connected to NIC IMAP)", subjects
    except Exception as e:
        return False, f"இணைப்பு தோல்வி: {e}", []
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def compute_bytes_sha256(data: bytes) -> str:
    """Compute SHA-256 hash from raw bytes for idempotency key."""
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha256(data_or_path: Any) -> str:
    """Convenience alias for computing SHA-256 on bytes or file path."""
    if isinstance(data_or_path, (str, Path)):
        return compute_file_sha256(Path(data_or_path))
    return compute_bytes_sha256(data_or_path)


def process_raw_email(raw_email_bytes: bytes, filename: Optional[str] = None) -> Tuple[str, Path]:
    """Store raw .eml bytes, create source record in SQLite, and return source_id and saved path."""
    source_id = compute_bytes_sha256(raw_email_bytes)
    fname = filename or f"{source_id}.eml"
    dest_path = (getattr(config, 'UPLOADS_EMAILS_DIR', config.UPLOADS_DIR / 'emails')) / fname

    with open(dest_path, "wb") as f:
        f.write(raw_email_bytes)

    record_source(
        source_id=source_id,
        source_type="email",
        raw_path=str(dest_path),
        status="pending",
    )
    log_audit(
        source_id=source_id,
        action="EMAIL_INGESTED",
        officer_id="SYSTEM_IMAP",
        details=f"Stored email {fname} with hash {source_id}",
    )
    logger.info(f"Ingested raw email: {source_id} -> {dest_path}")
    return source_id, dest_path


def process_file_path(file_path: Path) -> Tuple[str, Path]:
    """Store scanned document (PDF/Image) with duplicate-free hashing and record source."""
    source_id = compute_file_sha256(file_path)
    file_ext = file_path.suffix.lower()

    # Preserve original filename in managed scanned directory
    if file_path.parent.resolve() == config.UPLOADS_SCANNED_DIR.resolve():
        dest_path = file_path
    else:
        dest_path = config.UPLOADS_SCANNED_DIR / file_path.name
        if file_path.resolve() != dest_path.resolve():
            shutil.copy2(str(file_path), str(dest_path))

    record_source(
        source_id=source_id,
        source_type="scan",
        raw_path=str(dest_path),
        status="pending",
    )
    log_audit(
        source_id=source_id,
        action="SCAN_INGESTED",
        officer_id="SYSTEM_SCAN_WATCHER",
        details=f"Stored scan {dest_path.name} with hash {source_id}",
    )
    logger.info(f"Ingested scanned document: {source_id} -> {dest_path}")
    return source_id, dest_path


class IMAPPoller:
    """Resilient IMAP Poller connecting to NIC email server with cursor checkpointing and local dev mailbox fallback."""

    def __init__(
        self,
        server: str = "imap.gmail.com",
        port: int = 993,
        username: str = "",
        password: Optional[str] = None,
        mailbox: str = "INBOX",
        batch_size: int = 50,
    ):
        self.server = server
        self.port = port
        self.username = username
        self.password = password or get_stored_imap_password(username)
        self.mailbox = mailbox
        self.batch_size = batch_size

    def poll_local_dev_mailbox(self) -> List[str]:
        """Poll local incoming_dev_mailbox folder for offline development testing."""
        ingested_ids: List[str] = []
        dev_dir = getattr(config, 'UPLOADS_INCOMING_EMAILS_DIR', config.UPLOADS_DIR / 'incoming_dev_mailbox')
        if not dev_dir.exists():
            return ingested_ids

        eml_files = sorted(list(dev_dir.glob("*.eml")))
        last_uid = get_imap_cursor()

        for eml_file in eml_files[: self.batch_size]:
            try:
                with open(eml_file, "rb") as f:
                    raw_bytes = f.read()
                source_id, _ = process_raw_email(raw_bytes, filename=eml_file.name)
                ingested_ids.append(source_id)
                eml_file.unlink(missing_ok=True)
                last_uid += 1
            except Exception as e:
                logger.error(f"Error processing local dev email {eml_file}: {e}")

        if ingested_ids:
            update_imap_cursor(last_uid)
            logger.info(f"[DEV MAILBOX] Ingested {len(ingested_ids)} emails from {dev_dir.name} (Cursor -> {last_uid})")

        return ingested_ids

    def poll_once(self) -> List[str]:
        """Fetch unseen emails since last_uid, update cursor, and return ingested source_ids."""
        pwd = self.password or get_stored_imap_password(self.username)
        if not self.username or not pwd:
            return self.poll_local_dev_mailbox()

        last_uid = get_imap_cursor()
        ingested_ids: List[str] = []

        mail = None
        try:
            logger.info(f"Connecting to IMAP {self.server}:{self.port} (Last UID: {last_uid})...")
            mail = imaplib.IMAP4_SSL(self.server, self.port)
            mail.login(self.username, pwd)
            mail.select(self.mailbox, readonly=True)

            search_criterion = f"UID {last_uid + 1}:*" if last_uid > 0 else "UNSEEN"
            status, response = mail.uid("search", None, search_criterion)

            if status != "OK" or not response or not response[0]:
                return ingested_ids

            uid_list = [int(u) for u in response[0].split() if u.isdigit()]
            new_uids = sorted([u for u in uid_list if u > last_uid])[: self.batch_size]

            if new_uids:
                logger.info(f"Found {len(new_uids)} new emails on IMAP server.")

            max_processed_uid = last_uid
            for uid in new_uids:
                res, msg_data = mail.uid("fetch", str(uid), "(BODY.PEEK[])")
                if res != "OK" or not msg_data:
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw_bytes = response_part[1]
                        source_id, _ = process_raw_email(raw_bytes, filename=f"email_uid_{uid}.eml")
                        ingested_ids.append(source_id)

                max_processed_uid = max(max_processed_uid, uid)

            if max_processed_uid > last_uid:
                update_imap_cursor(max_processed_uid)
                logger.info(f"Updated IMAP cursor last_uid -> {max_processed_uid}")

        except Exception as e:
            logger.warning(f"IMAP connection note ({e}). Checking local dev mailbox fallback.")
            return self.poll_local_dev_mailbox()
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass

        return ingested_ids


class ScannedFileHandler(FileSystemEventHandler):
    """Watchdog event handler for monitoring newly dropped scans or emails."""

    def __init__(self, callback: Optional[Callable[[str, Path], None]] = None):
        super().__init__()
        self.callback = callback
        self.supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".eml"}

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        ext = file_path.suffix.lower()
        if ext in self.supported_exts:
            logger.info(f"New scan file detected: {file_path}")
            try:
                source_id, dest = process_file_path(file_path)
                if self.callback:
                    self.callback(source_id, dest)
            except Exception as e:
                logger.error(f"Error handling dropped scan {file_path}: {e}")


class FileSystemWatcher:
    """Watches scanned uploads directory using watchdog Observer."""

    def __init__(self, callback: Optional[Callable[[str, Path], None]] = None):
        self.callback = callback
        self.observer = Observer()
        self.handler = ScannedFileHandler(callback=self.callback)

    def start(self) -> None:
        """Start watchdog observers on uploads directories."""
        config.UPLOADS_SCANNED_DIR.mkdir(parents=True, exist_ok=True)

        self.observer.schedule(self.handler, str(config.UPLOADS_SCANNED_DIR), recursive=False)
        self.observer.start()
        logger.info(f"Started FileSystemWatcher on {config.UPLOADS_SCANNED_DIR}")

    def stop(self) -> None:
        """Stop watchdog observers."""
        self.observer.stop()
        self.observer.join()
        logger.info("Stopped FileSystemWatcher.")


