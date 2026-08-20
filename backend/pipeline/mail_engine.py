"""Backward-compatible re-export — Mail Engine has moved to modules.mail.engine.

This shim ensures existing imports like `from pipeline.mail_engine import ...`
continue to work without modification during the migration period.
"""

# Re-export all public symbols from the new canonical location
from modules.mail.engine import (  # noqa: F401
    fetch_recent_inbox_emails,
    ingest_email_by_uid,
    send_official_email,
    test_mail_servers,
)

# Also re-export internal test helper if referenced by legacy code
try:
    from modules.mail.engine import _fetch_local_dev_mailbox  # noqa: F401
except ImportError:
    pass
