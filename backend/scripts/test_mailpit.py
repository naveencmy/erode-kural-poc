#!/usr/bin/env python3
"""Script to verify and test sending emails to local Mailpit service (127.0.0.1:1025)
and validating receipt via Mailpit REST API (http://localhost:8025/api/v1/messages).
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.mail_engine import send_official_email, test_mail_servers


def check_mailpit_web_ui(base_url="http://localhost:8025"):
    """Check if Mailpit web service is running and accessible."""
    try:
        req = urllib.request.Request(f"{base_url}/api/v1/messages")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"✅ Mailpit Web API is live at {base_url} (Current message count: {data.get('total', 0)})")
                return True
    except Exception as e:
        print(f"⚠️  Mailpit Web API at {base_url} is not responding ({e}).")
        print("   If you haven't started Mailpit yet, run:")
        print("   docker run -d --name mailpit -p 8025:8025 -p 1025:1025 axllent/mailpit")
        return False


def test_mailpit_smtp():
    """Send a test official Tamil acknowledgement petition email to Mailpit."""
    print("\n--- 1. Testing Mailpit SMTP Connection (127.0.0.1:1025) ---")
    diag = test_mail_servers(
        smtp_server="127.0.0.1",
        smtp_port=1025,
        smtp_tls=False,
        smtp_ssl=False,
    )
    print("SMTP Diagnostic Status:", diag["smtp"]["status"])
    print("SMTP Diagnostic Message:", diag["smtp"]["message"])

    print("\n--- 2. Dispatching Sample Tamil Acknowledgement Email ---")
    sample_to = "citizen.test.erode@gmail.com"
    sample_sub = "மனு எண் 1008/REV/2026 - ஒப்புகை கடிதம் (Mailpit Test)"
    sample_body = (
        "தமிழ்நாடு அரசு - மக்கள் குறைதீர்க்கும் பிரிவு\n"
        "மாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு மாவட்டம்\n\n"
        "மதிப்பிற்குரிய மனுதாரர் அவர்களுக்கு,\n"
        "தங்கள் மனு எண் 1008/REV/2026 பெறப்பட்டு உரிய நடவடிக்கைக்கு அனுப்பப்பட்டுள்ளது.\n\n"
        "இவண்,\nமாவட்ட வருவாய் அலுவலர், ஈரோடு."
    )

    res = send_official_email(
        to_email=sample_to,
        subject=sample_sub,
        body=sample_body,
        officer_id="DRO_ERODE_01",
        smtp_server="127.0.0.1",
        smtp_port=1025,
        smtp_tls=False,
        smtp_ssl=False,
        from_email="collectorate.erode@tn.gov.in",
        from_name="ஈரோடு மாவட்ட ஆட்சியரகம்",
    )
    print("Send Result:", json.dumps(res, indent=2, ensure_ascii=False))

    print("\n--- 3. Verifying Receipt in Mailpit REST API ---")
    try:
        req = urllib.request.Request("http://localhost:8025/api/v1/messages")
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            messages = data.get("messages", [])
            print(f"Total messages in Mailpit: {len(messages)}")
            if messages:
                latest = messages[0]
                print(f"📬 Latest Email Subject: {latest.get('Subject')}")
                print(f"👤 To: {latest.get('To')}")
                print("🎉 Email successfully captured by Mailpit!")
                print("👉 View it in your browser at: http://localhost:8025")
    except Exception as e:
        print(f"Could not query Mailpit API ({e}). Check http://localhost:8025 manually.")


if __name__ == "__main__":
    check_mailpit_web_ui()
    test_mailpit_smtp()
