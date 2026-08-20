"""Unit and Integration Tests for Mail Integration & Dispatch Engine."""

import os
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import config
from api_server import app
from pipeline.database import (
    init_db,
    get_db_connection,
    save_sent_email,
    list_sent_emails,
    get_source,
)
from pipeline.mail_engine import (
    test_mail_servers,
    fetch_recent_inbox_emails,
    ingest_email_by_uid,
    send_official_email,
)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup isolated test database and folders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "test_mail_workflow.db"
        monkeypatch.setattr(config, "DATABASE_PATH", db_path)
        monkeypatch.setattr(config, "UPLOADS_INCOMING_EMAILS_DIR", tmp_path / "incoming_dev_mailbox")
        monkeypatch.setattr(config, "UPLOADS_EMAILS_DIR", tmp_path / "emails")
        monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
        monkeypatch.setattr(config, "DEV_MODE", True)
        
        config.UPLOADS_INCOMING_EMAILS_DIR.mkdir(parents=True, exist_ok=True)
        config.UPLOADS_EMAILS_DIR.mkdir(parents=True, exist_ok=True)
        init_db(db_path)
        yield db_path


def test_mail_servers_check():
    """Verify test_mail_servers executes and returns dict structure."""
    results = test_mail_servers(imap_user="", imap_pwd="", smtp_user="", smtp_pwd="")
    assert "imap" in results
    assert "smtp" in results


def test_mail_diagnostics_missing_credentials():
    """Verify diagnostic connection test handles unconfigured credentials safely."""
    results = test_mail_servers(imap_user="", imap_pwd="", smtp_user="", smtp_pwd="")
    assert results["imap"]["status"] == "failed"
    assert results["smtp"]["status"] == "failed"


def test_fetch_received_emails_dev_mailbox():
    """Verify inbox poller retrieves seeded Tamil grievance emails."""
    res = fetch_recent_inbox_emails()
    assert res["status"] == "success"
    assert res["count"] >= 2
    emails = res["emails"]
    assert any("பட்டா" in e["subject"] for e in emails)
    assert any("முதியோர்" in e["subject"] for e in emails)


def test_ingest_email_to_bulk_workflow():
    """Verify an incoming email can be ingested directly into the Bulk Grievance Workflow queue."""
    inbox_res = fetch_recent_inbox_emails()
    target_uid = inbox_res["emails"][0]["uid"]

    ingest_res = ingest_email_by_uid(uid=target_uid, officer_id="DRO_ERODE_01")
    assert ingest_res["status"] == "success"
    assert len(ingest_res["source_id"]) == 64 or ingest_res["source_id"].startswith("src_")

    # Verify source is stored in SQLite
    src = get_source(ingest_res["source_id"])
    assert src is not None
    assert src["status"] in ("pending_ocr", "ocr_complete", "ready_for_review", "draft_ready")




def test_send_official_email_simulation():
    """Verify outbound official email transmission and DB logging."""
    res = send_official_email(
        to_email="citizen.test@erode.tn.gov.in",
        subject="மனு எண் 1005/REV/2026 ஒப்புகை கடிதம்",
        body="வணக்கம். தங்களின் மனு பெறப்பட்டு கோப்பு எண் 1005/REV/2026 ஒதுக்கப்பட்டுள்ளது.",
        officer_id="DRO_ERODE_01",
    )
    assert res["status"] == "success"
    assert res["recipient"] == "citizen.test@erode.tn.gov.in"

    # Verify record in database
    sent_logs = list_sent_emails()
    assert len(sent_logs) >= 1
    assert sent_logs[0]["recipient_email"] == "citizen.test@erode.tn.gov.in"
    assert "1005/REV/2026" in sent_logs[0]["subject"]


def test_api_mail_endpoints():
    """Verify full FastAPI /api/v2/mail/* endpoints."""
    client = TestClient(app)

    # 1. GET /api/v2/mail/config
    cfg_resp = client.get("/api/v2/mail/config")
    assert cfg_resp.status_code == 200
    assert "imap_server" in cfg_resp.json()

    # 2. GET /api/v2/mail/received
    inbox_resp = client.get("/api/v2/mail/received?limit=10")
    assert inbox_resp.status_code == 200
    data = inbox_resp.json()
    assert data["status"] == "success"
    assert len(data["emails"]) >= 2

    # 3. POST /api/v2/mail/ingest
    target_uid = data["emails"][0]["uid"]
    ingest_resp = client.post("/api/v2/mail/ingest", json={"uid": target_uid, "officer_id": "DRO_01"})
    assert ingest_resp.status_code == 200
    assert "source_id" in ingest_resp.json()

    # 4. POST /api/v2/mail/send
    send_resp = client.post("/api/v2/mail/send", json={
        "recipient_email": "murugesan.erode@gmail.com",
        "subject": "மனு தீர்வு கடிதம்",
        "body": "தங்கள் மனு மீதான நடவடிக்கை எடுக்கப்பட்டு வருகிறது.",
        "officer_id": "DRO_01",
    })
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] == "success"

    # 5. GET /api/v2/mail/sent-logs
    logs_resp = client.get("/api/v2/mail/sent-logs")
    assert logs_resp.status_code == 200
    assert len(logs_resp.json()["sent_emails"]) >= 1
