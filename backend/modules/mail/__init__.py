"""Mail Module — Email Integration & Dispatch Engine for Erode Collectorate.

Provides:
  - test_mail_servers:         Live IMAP/SMTP diagnostic connection testing
  - fetch_recent_inbox_emails: Retrieve incoming emails from IMAP or local dev mailbox
  - ingest_email_by_uid:       Ingest email into Bulk Grievance Workflow queue
  - send_official_email:       Transmit official Tamil acknowledgements via SMTP
"""

from modules.mail.engine import (
    fetch_recent_inbox_emails,
    ingest_email_by_uid,
    send_official_email,
    test_mail_servers,
)

__all__ = [
    "test_mail_servers",
    "fetch_recent_inbox_emails",
    "ingest_email_by_uid",
    "send_official_email",
]
