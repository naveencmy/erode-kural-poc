"""Utility helpers and audit logging for Module 2: Data & Visualization."""

import logging
from typing import Any, Dict, Optional
from pipeline.database import log_audit

logger = logging.getLogger("DataViz")

# Tamil user-facing error messages
TAMIL_ERROR_MESSAGES = {
    "FILE_TOO_LARGE": "கோப்பு மிகப்பெரியது. 50MB க்கு குறைவாக பதிவேற்றவும்.",
    "INVALID_FORMAT": "செல்லுபடியாகும் வடிவம்: Excel (.xlsx, .xls), CSV மட்டுமே.",
    "EMPTY_FILE": "கோப்பில் தரவு இல்லை.",
    "SCHEMA_DETECTION_FAILED": "நெடுவரிசைகளை கண்டறிய முடியவில்லை.",
    "UNSAFE_CODE_BLOCKED": "உங்கள் கேள்வியை பாதுகாப்பாக செயல்படுத்த முடியவில்லை. வேறு விதமாக கேட்கவும்.",
    "EXECUTION_TIMEOUT": "கேள்வி மிகவும் சிக்கலானது. எளிமையாக கேட்கவும்.",
    "NO_DATA_MATCHES": "தரவில் பொருந்தும் மதிப்புகள் இல்லை.",
    "DATASET_NOT_FOUND": "கோரப்பட்ட தரவுத்தொகுப்பு கிடைக்கவில்லை.",
    "EXECUTION_ERROR": "குறியீட்டை செயல்படுத்துவதில் பிழை ஏற்பட்டது.",
}


def audit_data_event(
    action: str,
    details: str,
    officer_id: str,
    dataset_id: Optional[str] = None,
    ip_address: str = "127.0.0.1",
) -> None:
    """Log an immutable audit trail event for Module 2 actions."""
    try:
        log_audit(
            source_id=dataset_id,
            action=action,
            officer_id=officer_id,
            details=details,
            ip_address=ip_address,
        )
    except Exception as e:
        logger.warning(f"Audit log failure: {e}")
