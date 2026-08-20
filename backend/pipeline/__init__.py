"""Pipeline Package for Erode Collectorate Bulk Workflow Module V0.2.

Core grievance processing pipeline:
  Ingestion → OCR → Entity Extraction → Classification → Draft Generation

Note: Mail functionality has been moved to `modules.mail.engine`.
      Legacy imports via `pipeline.mail_engine` are still supported via shim.
"""

from .classification import DepartmentClassifier
from .database import (
    generate_department_file_number,
    get_db_connection,
    get_imap_cursor,
    get_source_details,
    init_db,
    log_audit,
    record_source,
    save_classification,
    save_draft,
    save_entities,
    save_ocr_correction,
    save_ocr_results,
    update_draft_approval,
    update_imap_cursor,
    update_source_status,
)
from .extraction import TamilEntityExtractor, compute_entity_confidence, normalize_tamil_date
from .generation import TamilDraftGenerator, export_draft_to_docx
from .ingestion import (
    FileSystemWatcher,
    IMAPPoller,
    compute_file_sha256,
    compute_sha256,
    process_file_path,
    process_raw_email,
    test_imap_connection,
)
from .ocr_engine import IndicOCREngine
from .orchestrator import WorkflowPipeline
from .verhoeff import generate_verhoeff, validate_verhoeff

__all__ = [
    # Database layer
    "init_db",
    "get_db_connection",
    "record_source",
    "update_source_status",
    "save_ocr_results",
    "save_ocr_correction",
    "save_entities",
    "save_classification",
    "save_draft",
    "generate_department_file_number",
    "update_draft_approval",
    "log_audit",
    "get_imap_cursor",
    "update_imap_cursor",
    "get_source_details",
    # Ingestion
    "IMAPPoller",
    "FileSystemWatcher",
    "process_file_path",
    "process_raw_email",
    "compute_sha256",
    "compute_file_sha256",
    "test_imap_connection",
    # OCR
    "IndicOCREngine",
    # Entity extraction
    "TamilEntityExtractor",
    "normalize_tamil_date",
    "compute_entity_confidence",
    # Classification
    "DepartmentClassifier",
    # Draft generation
    "TamilDraftGenerator",
    "export_draft_to_docx",
    # Orchestrator
    "WorkflowPipeline",
    # Utilities
    "validate_verhoeff",
    "generate_verhoeff",
]
