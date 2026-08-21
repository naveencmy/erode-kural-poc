"""Configuration and Environment Settings for Erode Collectorate Bulk Workflow Module."""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_EMAILS_DIR = UPLOADS_DIR / "emails"
UPLOADS_SCANNED_DIR = UPLOADS_DIR / "scanned"
UPLOADS_PROCESSED_DIR = UPLOADS_DIR / "processed"
UPLOADS_INCOMING_EMAILS_DIR = UPLOADS_DIR / "incoming_dev_mailbox"

UPLOADS_DATASETS_DIR = UPLOADS_DIR / "datasets"
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_CHARTS_DIR = OUTPUTS_DIR / "charts"
OUTPUTS_CONTENT_DIR = OUTPUTS_DIR / "content"

# Ensure runtime directories exist
for directory in [
    DATA_DIR,
    TEMPLATES_DIR,
    UPLOADS_DIR,
    UPLOADS_EMAILS_DIR,
    UPLOADS_SCANNED_DIR,
    UPLOADS_PROCESSED_DIR,
    UPLOADS_INCOMING_EMAILS_DIR,
    UPLOADS_DATASETS_DIR,
    OUTPUTS_DIR,
    OUTPUTS_CHARTS_DIR,
    OUTPUTS_CONTENT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# Development Mode (true allows offline local mailbox ingestion without live NIC IMAP credentials)
DEV_MODE = os.getenv("DEV_MODE", "true").lower() in ("true", "1", "yes")

# Database Configuration
DATABASE_PATH = BASE_DIR / "collectorate_workflow.db"
MASTER_LOCATIONS_DB = DATA_DIR / "master_locations.db"
TAMIL_GLOSSARY_FILE = DATA_DIR / "tamil_govt_glossary.txt"

# Module 2 Constraints (8GB RAM optimization)
MAX_DATASET_SIZE_MB = int(os.getenv("MAX_DATASET_SIZE_MB", "50"))
MAX_DATASET_ROWS = int(os.getenv("MAX_DATASET_ROWS", "100000"))
QUERY_TIMEOUT_SEC = int(os.getenv("QUERY_TIMEOUT_SEC", "30"))

# Erode District Master Taluks
ERODE_TALUKS = [
    "ஈரோடு",
    "பெருந்துறை",
    "பவானி",
    "கொடுமுடி",
    "மொடக்குறிச்சி",
    "அந்தியூர்",
    "கோபிசெட்டிபாளையம்",
    "சத்தியமங்கலம்",
    "நம்பியூர்",
    "தாளவாடி",
]

# IMAP Configuration (Gmail / NIC Govt Mail / Custom)
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USERNAME = os.getenv("IMAP_USERNAME", "naveenatdevine@gmail.com")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")
IMAP_BATCH_SIZE = int(os.getenv("IMAP_BATCH_SIZE", "50"))
IMAP_POLL_INTERVAL_SEC = int(os.getenv("IMAP_POLL_INTERVAL_SEC", "30"))

# SMTP Configuration (Outbound Acknowledgements / Official Mail)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "naveenatdevine@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "naveenatdevine@gmail.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "ஈரோடு மாவட்ட ஆட்சியரகம் (Erode Collectorate)")

# OCR Engine Configuration

OCR_DPI = int(os.getenv("OCR_DPI", "300"))
DESKEW_ANGLE_THRESHOLD_DEG = float(os.getenv("DESKEW_ANGLE_THRESHOLD_DEG", "2.0"))
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.85"))
LOW_CONF_FLAG = "[?]"

# LLM Configuration (Ollama - Local Qwen2.5 7B Q4_K_M)
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "15"))
AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.75"))

# Anti-Hallucination Default
MISSING_DATA_PLACEHOLDER = "[தகவல் இல்லை]"
AADHAAR_REDACTED_PLACEHOLDER = "[Aadhaar Redacted]"

# Department Categories & Tamil Labels
DEPARTMENTS = {
    "வருவாய்": "Revenue Department",
    "சமூக_நலன்": "Social Welfare Department",
    "பொதுப்பணித்துறை": "Public Works & Infrastructure",
    "காவல்துறை": "Police & Law Enforcement",
    "பதிவுத்துறை": "Registration & Stamps",
    "பொது_வழக்கு": "General & Grievance Redressal"
}

PRIORITY_LEVELS = ["HIGH", "MEDIUM", "LOW"]

