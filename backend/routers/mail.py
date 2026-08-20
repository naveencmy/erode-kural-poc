"""Mail Router — Email hub endpoints (connection test, inbox, send, logs, config)."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config

router = APIRouter(prefix="/api/v2/mail", tags=["Mail Hub"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class MailTestRequest(BaseModel):
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    smtp_ssl: bool = False


class MailSendRequest(BaseModel):
    recipient_email: str
    subject: str
    body: str
    officer_id: str = "OFFICER"
    source_id: Optional[str] = None
    attachment_path: Optional[str] = None


class MailIngestRequest(BaseModel):
    uid: str
    officer_id: str = "OFFICER"


class MailConfigRequest(BaseModel):
    imap_server: str
    imap_port: int = 993
    imap_user: str
    imap_password: Optional[str] = None
    smtp_server: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    smtp_ssl: bool = False
    from_email: Optional[str] = None
    from_name: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/test-connection")
async def api_test_mail_connection(req: MailTestRequest = MailTestRequest()):
    """Test IMAP and SMTP connections and return status."""
    from modules.mail.engine import test_mail_servers
    result = test_mail_servers(
        imap_server=req.imap_server,
        imap_port=req.imap_port,
        imap_user=req.imap_user,
        imap_pwd=req.imap_password,
        smtp_server=req.smtp_server,
        smtp_port=req.smtp_port,
        smtp_user=req.smtp_user,
        smtp_pwd=req.smtp_password,
        smtp_tls=req.smtp_tls,
        smtp_ssl=req.smtp_ssl,
    )
    return result


@router.get("/received")
async def api_get_received_emails(limit: int = 20):
    """Retrieve recent incoming emails from IMAP inbox or local dev mailbox."""
    from modules.mail.engine import fetch_recent_inbox_emails
    result = fetch_recent_inbox_emails(limit=limit)
    return result


@router.post("/ingest")
async def api_ingest_email(req: MailIngestRequest):
    """Ingest a specific received email into the Bulk Grievance Workflow."""
    from modules.mail.engine import ingest_email_by_uid
    try:
        res = ingest_email_by_uid(uid=req.uid, officer_id=req.officer_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send")
async def api_send_mail(req: MailSendRequest):
    """Transmit an official email via SMTP with optional attached DOCX."""
    from modules.mail.engine import send_official_email
    try:
        res = send_official_email(
            to_email=req.recipient_email,
            subject=req.subject,
            body=req.body,
            officer_id=req.officer_id,
            source_id=req.source_id,
            attachment_path=req.attachment_path,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sent-logs")
async def api_get_sent_logs(limit: int = 50):
    """Retrieve audit history of sent emails."""
    from pipeline.database import list_sent_emails
    logs = list_sent_emails(limit=limit)
    return {"status": "success", "count": len(logs), "sent_emails": logs}


@router.get("/config")
async def api_get_mail_config():
    """Retrieve current mail server configuration."""
    from pipeline.ingestion import get_stored_imap_password
    return {
        "imap_server": config.IMAP_SERVER,
        "imap_port": config.IMAP_PORT,
        "imap_user": config.IMAP_USERNAME,
        "has_imap_password": bool(get_stored_imap_password(config.IMAP_USERNAME)),
        "smtp_server": config.SMTP_SERVER,
        "smtp_port": config.SMTP_PORT,
        "smtp_user": config.SMTP_USERNAME,
        "smtp_tls": config.SMTP_USE_TLS,
        "smtp_ssl": config.SMTP_USE_SSL,
        "from_email": config.SMTP_FROM_EMAIL,
        "from_name": config.SMTP_FROM_NAME,
        "dev_mode": config.DEV_MODE,
    }


@router.post("/config")
async def api_save_mail_config(req: MailConfigRequest):
    """Update runtime mail configuration and store credentials in Windows Keyring."""
    from pipeline.ingestion import set_stored_imap_password
    config.IMAP_SERVER = req.imap_server
    config.IMAP_PORT = req.imap_port
    config.IMAP_USERNAME = req.imap_user
    if req.imap_password:
        config.IMAP_PASSWORD = req.imap_password
        set_stored_imap_password(req.imap_user, req.imap_password)

    config.SMTP_SERVER = req.smtp_server
    config.SMTP_PORT = req.smtp_port
    config.SMTP_USERNAME = req.smtp_user
    if req.smtp_password:
        config.SMTP_PASSWORD = req.smtp_password
    config.SMTP_USE_TLS = req.smtp_tls
    config.SMTP_USE_SSL = req.smtp_ssl
    if req.from_email:
        config.SMTP_FROM_EMAIL = req.from_email
    if req.from_name:
        config.SMTP_FROM_NAME = req.from_name

    return {"status": "success", "message": "மின்னஞ்சல் அமைப்புகள் வெற்றிகரமாக சேமிக்கப்பட்டன"}
