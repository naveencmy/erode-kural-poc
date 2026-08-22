"""Mail Integration and Dispatch Engine for Erode Collectorate.

Supports full bidirectional email workflows:
- Inbound: IMAP polling & on-demand ingestion into Bulk Grievance Workflow.
- Outbound: SMTP transmission of official Tamil acknowledgement letters & generated DOCX files.
- Diagnostics: Live connection test for NIC, Gmail, Outlook, or custom enterprise mail servers.
"""

import email
from email import policy
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import BytesParser
import imaplib
import logging
import smtplib
import ssl
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from pipeline.database import (
    log_audit,
    record_source,
    save_sent_email,
    list_sent_emails,
    get_source,
)
from pipeline.ingestion import (
    process_raw_email,
    get_stored_imap_password,
    set_stored_imap_password,
)

logger = logging.getLogger("CollectorateMailEngine")


def test_mail_servers(
    imap_server: Optional[str] = None,
    imap_port: Optional[int] = None,
    imap_user: Optional[str] = None,
    imap_pwd: Optional[str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_pwd: Optional[str] = None,
    smtp_tls: bool = True,
    smtp_ssl: bool = False,
) -> Dict[str, Any]:
    """Perform live diagnostic connection tests for both IMAP and SMTP."""
    if hasattr(config, "reload_env"):
        config.reload_env()

    srv_imap = str(imap_server or config.IMAP_SERVER).strip()
    port_imap = imap_port or config.IMAP_PORT
    if ":" in srv_imap:
        parts = srv_imap.split(":")
        srv_imap = parts[0]
        try:
            port_imap = int(parts[1])
        except (ValueError, IndexError):
            pass

    usr_imap = imap_user or config.IMAP_USERNAME
    pwd_imap = imap_pwd or get_stored_imap_password(usr_imap)

    srv_smtp = str(smtp_server or config.SMTP_SERVER).strip()
    port_smtp = smtp_port or config.SMTP_PORT
    if ":" in srv_smtp:
        parts = srv_smtp.split(":")
        srv_smtp = parts[0]
        try:
            port_smtp = int(parts[1])
        except (ValueError, IndexError):
            pass

    usr_smtp = smtp_user or config.SMTP_USERNAME
    pwd_smtp = smtp_pwd or config.SMTP_PASSWORD

    results = {
        "timestamp": datetime.now().isoformat(),
        "imap": {"status": "untested", "server": srv_imap, "port": port_imap, "message": ""},
        "smtp": {"status": "untested", "server": srv_smtp, "port": port_smtp, "message": ""},
    }

    # 1. Test IMAP
    is_local_imap = srv_imap in ("localhost", "127.0.0.1")
    if is_local_imap:
        results["imap"] = {
            "status": "success",
            "server": srv_imap,
            "port": port_imap,
            "inbox_count": 2,
            "message": "Mailpit உள்ளூர் முறை: உள்வரும் அஞ்சல்கள் உள்ளூர் மாதிரி பெட்டியிலிருந்து (Dev Mailbox) பெறப்படுகின்றன.",
        }
    elif not usr_imap or not pwd_imap:
        results["imap"] = {
            "status": "failed",
            "server": srv_imap,
            "port": port_imap,
            "message": "மின்னஞ்சல் பயனர் பெயர் அல்லது கடவுச்சொல் வழங்கப்படவில்லை (Missing credentials)",
        }
    else:
        mail = None
        try:
            if port_imap == 993:
                mail = imaplib.IMAP4_SSL(srv_imap, port_imap, timeout=8)
            else:
                mail = imaplib.IMAP4(srv_imap, port_imap, timeout=8)
                mail.starttls()
            mail.login(usr_imap, pwd_imap)
            status, info = mail.select("INBOX", readonly=True)
            msg_count = info[0].decode("utf-8") if info and info[0] else "0"
            results["imap"] = {
                "status": "success",
                "server": srv_imap,
                "port": port_imap,
                "inbox_count": int(msg_count),
                "message": f"IMAP இணைப்பு வெற்றிகரமாக இணைக்கப்பட்டது. பெறப்பட்ட அஞ்சல்கள்: {msg_count}",
            }
        except Exception as e:
            results["imap"] = {
                "status": "failed",
                "server": srv_imap,
                "port": port_imap,
                "message": f"IMAP இணைப்பு தோல்வி: {str(e)}",
            }
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    # 2. Test SMTP
    is_local_smtp = srv_smtp in ("localhost", "127.0.0.1") or port_smtp in (1025, 2525)
    if not is_local_smtp and (not usr_smtp or not pwd_smtp):
        results["smtp"] = {
            "status": "failed",
            "server": srv_smtp,
            "port": port_smtp,
            "message": "SMTP பயனர் பெயர் அல்லது கடவுச்சொல் வழங்கப்படவில்லை (Missing credentials)",
        }
    else:
        smtp_client = None
        try:
            if smtp_ssl or port_smtp == 465:
                context = ssl.create_default_context()
                smtp_client = smtplib.SMTP_SSL(srv_smtp, port_smtp, context=context, timeout=8)
            else:
                smtp_client = smtplib.SMTP(srv_smtp, port_smtp, timeout=8)
                if smtp_tls and not is_local_smtp:
                    context = ssl.create_default_context()
                    smtp_client.starttls(context=context)

            if usr_smtp and pwd_smtp:
                smtp_client.login(usr_smtp, pwd_smtp)

            results["smtp"] = {
                "status": "success",
                "server": srv_smtp,
                "port": port_smtp,
                "message": f"SMTP அனுப்பும் சர்வர் வெற்றிகரமாக இணைக்கப்பட்டது ({srv_smtp}:{port_smtp}) [Mailpit/Local Ready]",
            }
        except Exception as e:
            results["smtp"] = {
                "status": "failed",
                "server": srv_smtp,
                "port": port_smtp,
                "message": f"SMTP இணைப்பு தோல்வி: {str(e)}",
            }
        finally:

            if smtp_client:
                try:
                    smtp_client.quit()
                except Exception:
                    pass

    return results


from email.header import decode_header


def _decode_mime_header(header_value: Optional[str]) -> str:
    """Safely decode RFC2047 MIME encoded email headers into unicode strings."""
    if not header_value:
        return ""
    try:
        decoded_parts = decode_header(header_value)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result)
    except Exception:
        return str(header_value)


def fetch_recent_inbox_emails(
    imap_server: Optional[str] = None,
    imap_port: Optional[int] = None,
    imap_user: Optional[str] = None,
    imap_pwd: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Fetch recent incoming emails from IMAP INBOX with fast header retrieval."""
    srv = imap_server or config.IMAP_SERVER
    port = imap_port or config.IMAP_PORT
    usr = imap_user or config.IMAP_USERNAME
    pwd = imap_pwd or get_stored_imap_password(usr)

    if not usr or not pwd:
        # Fallback to local dev mailbox if credentials are not configured
        return _fetch_local_dev_mailbox(limit=limit)

    mail = None
    emails_list = []
    try:
        if port == 993:
            mail = imaplib.IMAP4_SSL(srv, port, timeout=10)
        else:
            mail = imaplib.IMAP4(srv, port, timeout=10)
            mail.starttls()

        mail.login(usr, pwd)
        mail.select("INBOX", readonly=True)
        
        # Use UID search for reliable message identification
        status, response = mail.uid("search", None, "ALL")

        if status == "OK" and response and response[0]:
            uids = response[0].split()
            target_uids = uids[-limit:] if len(uids) > limit else uids
            
            # Fetch headers in reverse order (newest first)
            for uid_bytes in reversed(target_uids):
                uid_str = uid_bytes.decode("utf-8")
                try:
                    # Fast fetch: only headers and text snippet (avoids downloading large attachments)
                    res, data = mail.uid("fetch", uid_bytes, "(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<0.500>)")
                    if res == "OK" and data:
                        raw_header = b""
                        raw_body_snippet = b""
                        for part in data:
                            if isinstance(part, tuple) and len(part) >= 2:
                                if b"HEADER" in part[0]:
                                    raw_header += part[1]
                                elif b"TEXT" in part[0]:
                                    raw_body_snippet += part[1]
                                else:
                                    raw_header += part[1]

                        parsed_msg = BytesParser(policy=policy.default).parsebytes(raw_header)
                        
                        subject = _decode_mime_header(parsed_msg.get("Subject")) or "(தலைப்பு இல்லை / No Subject)"
                        sender = _decode_mime_header(parsed_msg.get("From")) or "தெரியாதவர்"
                        recipient = _decode_mime_header(parsed_msg.get("To")) or usr
                        date_str = str(parsed_msg.get("Date", ""))

                        snippet = ""
                        if raw_body_snippet:
                            try:
                                snippet = raw_body_snippet.decode("utf-8", errors="replace").strip()
                            except Exception:
                                snippet = str(raw_body_snippet)[:180]

                        emails_list.append({
                            "uid": uid_str,
                            "subject": subject,
                            "sender": sender,
                            "recipient": recipient,
                            "date": date_str,
                            "snippet": snippet[:180],
                            "has_attachments": False,
                            "attachments": [],
                            "is_ingested": False,
                        })
                except Exception as item_err:
                    logger.debug(f"Skipping UID {uid_str} due to fetch issue: {item_err}")
                    continue

        return {
            "status": "success",
            "count": len(emails_list),
            "source": "live_imap",
            "server": f"{srv}:{port}",
            "emails": emails_list,
        }

    except Exception as e:
        logger.warning(f"IMAP fetch error: {e}. Falling back to local mailbox.")
        fallback = _fetch_local_dev_mailbox(limit=limit)
        fallback["warning"] = f"IMAP இணைப்பு கிடைக்கவில்லை ({e}). உள்ளூர் அஞ்சல்கள் காட்டப்படுகின்றன."
        return fallback

    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass


def _fetch_local_dev_mailbox(limit: int = 20) -> Dict[str, Any]:
    """Read local simulated dev mailbox files from uploads/emails/."""
    dev_dir = config.UPLOADS_INCOMING_EMAILS_DIR
    emails_list = []
    
    # If dev dir is empty, seed a couple of sample grievance emails
    sample_files = list(dev_dir.glob("*.eml"))
    if not sample_files:
        _seed_sample_grievance_emails()
        sample_files = list(dev_dir.glob("*.eml"))

    for i, eml_file in enumerate(sorted(sample_files, key=lambda f: f.stat().st_mtime, reverse=True)[:limit]):
        try:
            with open(eml_file, "rb") as f:
                parsed_msg = BytesParser(policy=policy.default).parse(f)
                
                body_text = ""
                if parsed_msg.is_multipart():
                    for part in parsed_msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body_text = part.get_content()
                                break
                            except Exception:
                                pass
                else:
                    try:
                        body_text = parsed_msg.get_content()
                    except Exception:
                        pass

                attachments = []
                if parsed_msg.is_multipart():
                    for part in parsed_msg.walk():
                        fn = part.get_filename()
                        if fn:
                            attachments.append(fn)

                emails_list.append({
                    "uid": f"local_{eml_file.stem}",
                    "file_name": eml_file.name,
                    "subject": parsed_msg.get("Subject", eml_file.stem),
                    "sender": parsed_msg.get("From", "citizen.erode@tn.gov.in"),
                    "recipient": parsed_msg.get("To", "collectorate.erode@tn.gov.in"),
                    "date": parsed_msg.get("Date", datetime.fromtimestamp(eml_file.stat().st_mtime).strftime("%a, %d %b %Y %H:%M:%S")),
                    "snippet": (body_text or "")[:180],
                    "has_attachments": len(attachments) > 0,
                    "attachments": attachments,
                    "is_ingested": False,
                })
        except Exception as e:
            logger.warning(f"Error reading local eml {eml_file}: {e}")

    return {
        "status": "success",
        "count": len(emails_list),
        "source": "local_dev_mailbox",
        "server": "Local Mailbox (Development Mode)",
        "emails": emails_list,
    }


def _seed_sample_grievance_emails():
    """Create sample Tamil grievance emails in local incoming mailbox for testing."""
    sample1 = """From: r.murugesan.erode@gmail.com
To: collectorate.erode@tn.gov.in
Subject: பட்டா பெயர் மாற்றம் கோரிக்கை மனு - பவானி வட்டம்
Date: Wed, 19 Aug 2026 10:15:00 +0530
Content-Type: text/plain; charset="utf-8"

மதிப்பிற்குரிய மாவட்ட ஆட்சியர் அவர்களுக்கு,
வணக்கம். எனது தந்தை பெயரில் உள்ள பவானி வட்டம் காலிங்கராயன்பாளையம் புல எண் 45/2 நிலத்திற்கு பட்டா பெயர் மாற்றம் செய்ய விண்ணப்பித்து 30 நாட்களாக நிலுவையில் உள்ளது.
உடனடி நடவடிக்கை எடுக்க வேண்டுகிறேன்.

இவண்,
ஆர். முருகேசன்,
செல்: 9443123456, பவானி.
"""
    sample2 = """From: lakshmi.erode99@gmail.com
To: collectorate.erode@tn.gov.in
Subject: முதியோர் உதவித்தொகை கோரும் மனு - பெருந்துறை
Date: Thu, 20 Aug 2026 08:45:00 +0530
Content-Type: text/plain; charset="utf-8"

மதிப்பிற்குரிய மாவட்ட ஆட்சியர் அவர்களுக்கு,
நான் பெருந்துறை வட்டத்தில் வசிக்கும் 68 வயது முதியவர். எனது கணவர் இறந்துவிட்டார். ஆதரவற்ற நிலையில் உள்ள எனக்கு முதியோர் உதவித்தொகை வழங்க ஆவண செய்யுமாறு தாழ்மையுடன் கேட்டுக்கொள்கிறேன்.

இவண்,
லட்சுமி, பெருந்துறை.
"""
    try:
        (config.UPLOADS_INCOMING_EMAILS_DIR / "sample_patta_petition.eml").write_text(sample1, encoding="utf-8")
        (config.UPLOADS_INCOMING_EMAILS_DIR / "sample_pension_petition.eml").write_text(sample2, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Seed email error: {e}")


def ingest_email_by_uid(
    uid: str,
    officer_id: str = "OFFICER",
    imap_server: Optional[str] = None,
    imap_port: Optional[int] = None,
    imap_user: Optional[str] = None,
    imap_pwd: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest a specific email (by UID or local filename) directly into the Bulk Grievance Workflow."""
    raw_bytes = None
    filename = f"email_{uid}.eml"

    # Check if it is a local dev mailbox file
    if uid.startswith("local_"):
        file_stem = uid.replace("local_", "")
        eml_path = config.UPLOADS_INCOMING_EMAILS_DIR / f"{file_stem}.eml"
        if eml_path.exists():
            raw_bytes = eml_path.read_bytes()
            filename = eml_path.name

    # Otherwise fetch live from IMAP
    if not raw_bytes:
        srv = imap_server or config.IMAP_SERVER
        port = imap_port or config.IMAP_PORT
        usr = imap_user or config.IMAP_USERNAME
        pwd = imap_pwd or get_stored_imap_password(usr)
        if not usr or not pwd:
            raise ValueError("IMAP credentials not configured")

        mail = None
        try:
            if port == 993:
                mail = imaplib.IMAP4_SSL(srv, port, timeout=20)
            else:
                mail = imaplib.IMAP4(srv, port, timeout=20)
                mail.starttls()
            mail.login(usr, pwd)
            mail.select("INBOX", readonly=True)
            
            # First attempt UID fetch
            res, data = mail.uid("fetch", uid.encode("utf-8"), "(BODY.PEEK[])")
            if res == "OK" and data and data[0] and isinstance(data[0], tuple):
                raw_bytes = data[0][1]
            else:
                # Fallback to standard sequence fetch
                res2, data2 = mail.fetch(uid.encode("utf-8"), "(BODY.PEEK[])")
                if res2 == "OK" and data2 and data2[0] and isinstance(data2[0], tuple):
                    raw_bytes = data2[0][1]
        except (TimeoutError, imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError) as imap_err:
            logger.warning(f"IMAP fetch failed for UID {uid}: {imap_err}")
            raise RuntimeError(f"மின்னஞ்சலை IMAP சர்வரிலிருந்து பெறுவதில் தாமதம்/தோல்வி ({imap_err})")
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    if not raw_bytes:
        raise ValueError(f"மின்னஞ்சல் உள்ளடக்கத்தைப் பெற முடியவில்லை (UID: {uid})")

    # Process through pipeline
    source_id, saved_path = process_raw_email(raw_bytes, filename=filename)
    
    # Process through OCR & entity extraction orchestrator
    from pipeline.orchestrator import get_pipeline
    pipeline = get_pipeline()
    pipeline.process_source(source_id, file_path=saved_path)

    log_audit(
        source_id=source_id,
        action="EMAIL_INGESTED_TO_WORKFLOW",
        officer_id=officer_id,
        details=f"Email {uid} ({filename}) ingested into bulk workflow queue.",
    )

    return {
        "status": "success",
        "source_id": source_id,
        "file_name": filename,
        "message": f"மின்னஞ்சல் வெற்றிகரமாக மனுவாக உட்கொள்ளப்பட்டது (Source ID: {source_id})",
    }



def send_official_email(
    to_email: str,
    subject: str,
    body: str,
    officer_id: str = "OFFICER",
    source_id: Optional[str] = None,
    attachment_path: Optional[str] = None,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_pwd: Optional[str] = None,
    smtp_tls: bool = True,
    smtp_ssl: bool = False,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Transmit an official email with optional DOCX/PDF attachment and log to audit."""
    if not to_email or "@" not in to_email:
        raise ValueError("செல்லுபடியாகும் பெறுநர் மின்னஞ்சல் முகவரி தேவை (Invalid recipient email)")

    if hasattr(config, "reload_env"):
        config.reload_env()

    srv = str(smtp_server or config.SMTP_SERVER).strip()
    port = smtp_port or config.SMTP_PORT
    if ":" in srv:
        parts = srv.split(":")
        srv = parts[0]
        try:
            port = int(parts[1])
        except (ValueError, IndexError):
            pass
    usr = smtp_user or config.SMTP_USERNAME
    pwd = smtp_pwd or config.SMTP_PASSWORD
    
    # Verified sender address on Brevo
    sender_addr = from_email or config.SMTP_FROM_EMAIL or "naveenatdevine@gmail.com"

    sender_name = from_name or config.SMTP_FROM_NAME

    is_local_smtp = srv in ("localhost", "127.0.0.1") or port in (1025, 2525)
    if not is_local_smtp and (not usr or not pwd):
        raise ValueError(
            "மின்னஞ்சல் பயனர் பெயர் அல்லது App Password சேமிக்கப்படவில்லை (Missing SMTP credentials)."
        )

    email_id = f"eml_{uuid.uuid4().hex[:10]}"

    # Build MIME message
    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{sender_addr}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    sender_domain = sender_addr.split("@")[-1] if "@" in sender_addr else "gmail.com"
    msg["Message-ID"] = email.utils.make_msgid(domain=sender_domain)

    # Add Tamil body text (Plain & HTML)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach file if specified
    if attachment_path:
        att_file = Path(attachment_path)
        if att_file.exists():
            with open(att_file, "rb") as f:
                part = MIMEApplication(f.read(), Name=att_file.name)
                part["Content-Disposition"] = f'attachment; filename="{att_file.name}"'
                msg.attach(part)

    # Live SMTP Transmission
    smtp_client = None
    try:
        if smtp_ssl or port == 465:
            ctx = ssl.create_default_context()
            smtp_client = smtplib.SMTP_SSL(srv, port, context=ctx, timeout=15)
        else:
            smtp_client = smtplib.SMTP(srv, port, timeout=15)
            if smtp_tls and not is_local_smtp:
                ctx = ssl.create_default_context()
                smtp_client.starttls(context=ctx)

        if usr and pwd and not is_local_smtp:
            smtp_client.login(usr, pwd)

        smtp_client.send_message(msg)


        save_sent_email(
            email_id=email_id,
            recipient_email=to_email,
            subject=subject,
            body=body,
            officer_id=officer_id,
            source_id=source_id,
            attachment_path=attachment_path,
            status="sent",
        )
        log_audit(
            source_id=source_id,
            action="EMAIL_SENT_LIVE",
            officer_id=officer_id,
            details=f"Live email sent via {srv} from {sender_addr} to {to_email}: {subject}",
        )

        return {
            "status": "success",
            "email_id": email_id,
            "mode": "live_smtp",
            "sender": sender_addr,
            "recipient": to_email,
            "message": f"மின்னஞ்சல் ({sender_addr} வழியாக) வெற்றிகரமாக அனுப்பப்பட்டது: {to_email}",
        }


    except Exception as e:
        save_sent_email(
            email_id=email_id,
            recipient_email=to_email,
            subject=subject,
            body=body,
            officer_id=officer_id,
            source_id=source_id,
            attachment_path=attachment_path,
            status="failed",
            error_message=str(e),
        )
        log_audit(
            source_id=source_id,
            action="EMAIL_SEND_FAILED",
            officer_id=officer_id,
            details=f"Email delivery failed to {to_email}: {str(e)}",
        )
        raise RuntimeError(f"மின்னஞ்சல் அனுப்புதல் தோல்வி: {str(e)}")

    finally:
        if smtp_client:
            try:
                smtp_client.quit()
            except Exception:
                pass
