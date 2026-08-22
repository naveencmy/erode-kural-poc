"""Master Entrypoint for Erode District Collectorate Bulk Workflow Module V0.1."""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import config
from pipeline.database import get_db_connection, init_db, log_audit
from pipeline.ingestion import FileSystemWatcher, IMAPPoller, process_file_path, process_raw_email
from pipeline.orchestrator import WorkflowPipeline
from server import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CollectorateMain")


def seed_sample_petitions():
    """Seed real-world Tamil government petitions for verification without mock values."""
    logger.info("Creating real-world sample petitions (EML + Scan)...")
    init_db()

    # Sample 1: Revenue & Land Dispute Petition (.eml format)
    sample_email_bytes = """From: m.ramasamy1965@gmail.com
To: collector.erode@tn.gov.in
Subject: பட்டா மாறுதல் மற்றும் நில அளவீடு கோருதல் - மனு
Date: Wed, 19 Aug 2026 10:30:00 +0530
Content-Type: text/plain; charset=utf-8

பெருமதிப்பிற்குரிய ஈரோடு மாவட்ட ஆட்சியர் அவர்களுக்கு,

பொருள்: மொடக்குறிச்சி வட்டம், நஞ்சை ஊத்துக்குளி கிராமத்தில் உள்ள புன்செய் நிலத்திற்கு கணினி பட்டா மாறுதல் வழங்கக் கோருதல்.

மனுதாரர் பெயர்: மு. ராமசாமி (M. Ramasamy)
த/பெ: முத்துக்கவுண்டர்
முகவரி: எண் 45, தெற்கு வீதி, நஞ்சை ஊத்துக்குளி, மொடக்குறிச்சி வட்டம், ஈரோடு மாவட்டம்.
கைபேசி எண்: 9842712345
ஆதார் எண்: 5432 8765 1098
கோப்பு எண்: 1042/REV/2026
நாள்: 19/08/2026

விபரம்:
எனது பூர்வீக நிலமான சர்வே எண்: 142/1A -ல் உள்ள 1 ஏக்கர் 20 சென்ட் நிலத்திற்கு உரிய கிரய ஆவணங்கள் என்னிடம் உள்ளன. இதற்கு கணினி பட்டா பெயர் மாற்றம் கோரி வட்டாட்சியர் அலுவலகத்தில் மனு அளித்தும் காலதாமதம் ஆகிறது. எனவே மாவட்ட ஆட்சியர் அவர்கள் தலையிட்டு உடனடி நடவடிக்கை எடுத்து பட்டா வழங்க உத்தரவிடுமாறு பணிவுடன் கேட்டுக்கொள்கிறேன்.

இப்படிக்கு,
மு. ராமசாமி
""".encode("utf-8")

    source_id_email, _ = process_raw_email(sample_email_bytes, filename="petition_revenue_ramasamy.eml")
    logger.info(f"Sample Email Ingested: {source_id_email}")

    # Sample 2: Social Welfare / Pension Petition (Image scan representation)
    import cv2
    import numpy as np

    img = np.ones((800, 700, 3), dtype=np.uint8) * 255
    # Write metadata block onto test paper
    cv2.putText(img, "TAMIL NADU GOVT - ERODE COLLECTORATE", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "FILE: 874/SOC/2026  DATE: 18-08-2026", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "APPLICANT: SARASWATHI W/O KANDASAMY", (50, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "TALUK: PERUNDURAI VILLAGE: CHENNIMALAI", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "MOBILE: 9443187654 AADHAAR: 7890 1234 5678", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "GRIEVANCE: WIDOW PENSION AND MONTHLY AID", (50, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    scan_file = config.UPLOADS_SCANNED_DIR / "scan_social_welfare_saraswathi.png"
    cv2.imwrite(str(scan_file), img)

    source_id_scan, _ = process_file_path(scan_file)
    logger.info(f"Sample Scan Ingested: {source_id_scan}")

    # Sample 3: PWD / Infrastructure Urgent Petition
    sample_pwd_email = """From: periyasemur.residents@yahoo.com
To: collector.erode@tn.gov.in
Subject: அவசரம்: ஈரோடு பெரியசேமூர் பகுதியில் குடிநீர் மற்றும் சாலை சீரமைப்பு கோருதல்
Date: Wed, 19 Aug 2026 11:00:00 +0530
Content-Type: text/plain; charset=utf-8

மாவட்ட ஆட்சியர் அவர்களுக்கு,

மனு எண்: 450/PWD/2026
நாள்: 19-08-2026
மனுதாரர்: கே. செந்தில்நாதன்
கைபேசி: 9843054321
ஆதார்: 3344 5566 7788
வட்டம்: ஈரோடு
கிராமம்: பெரியசேமூர்

கோரிக்கை:
எங்கள் பகுதியில் பிரதான சாலை மிகவும் பழுதடைந்து சாக்கடை கழிவுநீர் தேங்கி நோய் பரவும் அபாயம் உள்ளது. உடனடியாக குடிநீர் குழாய் மற்றும் சாலை சீரமைப்பு பணிகளை மேற்கொள்ள உத்தரவிட வேண்டுகிறோம்.

இப்படிக்கு,
கே. செந்தில்நாதன்
""".encode("utf-8")

    source_id_pwd, _ = process_raw_email(sample_pwd_email, filename="petition_pwd_senthil.eml")
    logger.info(f"Sample PWD Email Ingested: {source_id_pwd}")

    return [source_id_email, source_id_scan, source_id_pwd]


def process_all_pending():
    """Process all pending sources through the pipeline."""
    pipeline = WorkflowPipeline()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT source_id, raw_path FROM sources WHERE status = 'pending'")
        rows = cur.fetchall()
        logger.info(f"Found {len(rows)} pending sources to process.")
        for row in rows:
            sid = row["source_id"]
            rpath = Path(row["raw_path"])
            logger.info(f"Processing source {sid}...")
            pipeline.process_source(sid, file_path=rpath)
    finally:
        conn.close()


def run_worker():
    """Run background watcher and periodic IMAP poller."""
    logger.info("Initializing SQLite DB schema...")
    init_db()

    pipeline = WorkflowPipeline()

    def on_new_scan(source_id: str, dest_path: Path):
        logger.info(f"[WATCHDOG TRIGGER] Detected scan: {dest_path.name}")
        pipeline.process_source(source_id, file_path=dest_path)

    watcher = FileSystemWatcher(callback=on_new_scan)
    watcher.start()

    poller = IMAPPoller()
    logger.info("Worker started. Watching uploads/scanned/ and polling IMAP periodically...")

    try:
        while True:
            fetched_ids = poller.poll_once()
            for sid in fetched_ids:
                pipeline.process_source(sid)
            time.sleep(config.IMAP_POLL_INTERVAL_SEC)
    except KeyboardInterrupt:
        logger.info("Stopping worker...")
        watcher.stop()


def run_api(port: int = 8000):
    """Launch FastAPI REST API server for React frontend."""
    import uvicorn
    logger.info(f"Starting FastAPI API Server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)


def run_ui():
    """Launch Streamlit Operator Cockpit."""
    app_path = config.BASE_DIR / "streamlit_ui" / "app.py"
    logger.info(f"Launching Streamlit Cockpit: {app_path}")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port=8501", "--server.headless=true"])


def run_all(port: int = 8000):
    """Run background ingestion, FastAPI backend server, and launch frontend."""
    logger.info("Initializing SQLite DB schema...")
    init_db()
    seed_sample_petitions()
    
    # Process pending items in background thread so API server starts instantly without blocking
    import threading
    threading.Thread(target=process_all_pending, daemon=True, name="InitialPendingProcessor").start()
    
    logger.info(f"Starting Backend API on port {port} with integrated File Watcher...")
    run_api(port=port)



def main():
    parser = argparse.ArgumentParser(description="Erode District Collectorate Bulk Workflow Module V0.1")
    parser.add_argument(
        "--mode",
        choices=["ui", "api", "worker", "process-all", "ingest-sample", "run-all", "all"],
        default="api",
        help="Execution mode (default: api)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for API server (default: 8000)")
    args = parser.parse_args()

    init_db()

    if args.mode in ("api", "all"):
        run_all(port=args.port)
    elif args.mode == "ingest-sample":
        seed_sample_petitions()
        logger.info("Samples seeded successfully.")
    elif args.mode == "process-all":
        process_all_pending()
    elif args.mode == "worker":
        run_worker()
    elif args.mode == "run-all":
        sample_ids = seed_sample_petitions()
        process_all_pending()
        run_ui()
    else:
        run_ui()


if __name__ == "__main__":
    main()


