"""Pipeline Package for Erode Collectorate System V0.2.

Core processing pipeline:
  Ingestion → OCR → Entity Extraction → Classification → Draft Generation

Shared infrastructure used across modules (Content, Data, Document Summary).
"""

from .database import (
    get_db_connection,
    get_source_details,
    init_db,
    log_audit,
    record_source,
    update_source_status,
)
from .extraction import TamilEntityExtractor, compute_entity_confidence, normalize_tamil_date
from .ingestion import (
    FileSystemWatcher,
    compute_file_sha256,
    compute_sha256,
    process_file_path,
)
from .ocr_engine import IndicOCREngine
from .verhoeff import generate_verhoeff, validate_verhoeff

__all__ = [
    # Database layer
    "init_db",
    "get_db_connection",
    "record_source",
    "update_source_status",
    "log_audit",
    "get_source_details",
    # Ingestion
    "FileSystemWatcher",
    "process_file_path",
    "compute_sha256",
    "compute_file_sha256",
    # OCR
    "IndicOCREngine",
    # Entity extraction
    "TamilEntityExtractor",
    "normalize_tamil_date",
    "compute_entity_confidence",
    # Utilities
    "validate_verhoeff",
    "generate_verhoeff",
]
