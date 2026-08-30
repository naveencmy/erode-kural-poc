"""Configuration and Environment Settings for Erode Collectorate AI System."""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip().strip("'\"")
                os.environ[_k] = _v

DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_SCANNED_DIR = UPLOADS_DIR / "scanned"
UPLOADS_PROCESSED_DIR = UPLOADS_DIR / "processed"

UPLOADS_DATASETS_DIR = UPLOADS_DIR / "datasets"
UPLOADS_DOCUMENTS_DIR = UPLOADS_DIR / "documents"
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_CHARTS_DIR = OUTPUTS_DIR / "charts"
OUTPUTS_CONTENT_DIR = OUTPUTS_DIR / "content"

# Ensure runtime directories exist
for directory in [
    DATA_DIR,
    TEMPLATES_DIR,
    UPLOADS_DIR,
    UPLOADS_SCANNED_DIR,
    UPLOADS_PROCESSED_DIR,
    UPLOADS_DATASETS_DIR,
    UPLOADS_DOCUMENTS_DIR,
    OUTPUTS_DIR,
    OUTPUTS_CHARTS_DIR,
    OUTPUTS_CONTENT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

# Development Mode
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
