"""Dataset Ingestion & Registration Engine for Module 2: Data & Visualization.

Accepts Excel (.xlsx, .xls) and CSV datasets, computes deterministic SHA256
dataset IDs, validates schema, profiles columns, and registers records.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import config
from pipeline.database import save_dataset, save_dataset_columns
from modules.data_viz.profiler import profile_dataset_columns
from modules.data_viz.schema_detector import detect_dataset_language
from modules.data_viz.utils import audit_data_event


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum for exact file deduplication and dataset ID."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return f"ds_{sha256.hexdigest()[:16]}"


def ingest_dataset_file(
    file_path: Path,
    officer_id: str,
    source_id: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest, parse, and profile an Excel or CSV file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size_bytes = file_path.stat().st_size
    max_bytes = config.MAX_DATASET_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValueError(f"File size ({file_size_bytes / (1024*1024):.1f} MB) exceeds maximum allowed {config.MAX_DATASET_SIZE_MB} MB.")

    ext = file_path.suffix.lower()
    if ext not in (".xlsx", ".xls", ".csv"):
        raise ValueError("Invalid file format. Supported formats: Excel (.xlsx, .xls), CSV.")

    dataset_id = compute_sha256(file_path)

    # Store file in dedicated dataset directory
    dest_dir = config.UPLOADS_DATASETS_DIR / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / file_path.name
    if not dest_file.exists() or dest_file != file_path:
        shutil.copy2(file_path, dest_file)

    # Load dataframe
    try:
        if ext in (".xlsx", ".xls"):
            excel_file = pd.ExcelFile(dest_file)
            target_sheet = sheet_name or excel_file.sheet_names[0]
            df = pd.read_excel(excel_file, sheet_name=target_sheet)
        else:
            target_sheet = "Sheet1"
            # Try utf-8 first, fallback to latin-1 / cp1252
            try:
                df = pd.read_csv(dest_file, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(dest_file, encoding="cp1252")
    except Exception as e:
        raise ValueError(f"Failed to read dataset content: {e}")

    if df.empty:
        raise ValueError("The uploaded dataset contains no data rows.")

    # Clean column headers
    df.columns = [str(c).strip() for c in df.columns]

    row_count = len(df)
    col_count = len(df.columns)
    lang = detect_dataset_language(df)

    # Profile all columns deterministically
    columns_profile = profile_dataset_columns(df)

    # Save to SQLite
    save_dataset(
        dataset_id=dataset_id,
        officer_id=officer_id,
        file_name=file_path.name,
        file_path=str(dest_file),
        file_size_bytes=file_size_bytes,
        row_count=row_count,
        column_count=col_count,
        status="ready",
        source_id=source_id,
        sheet_name=target_sheet,
        language_detected=lang,
    )

    save_dataset_columns(dataset_id, columns_profile)

    # Audit events
    audit_data_event(
        action="DATASET_UPLOADED",
        details=f"Uploaded {file_path.name} ({row_count} rows, {col_count} cols)",
        officer_id=officer_id,
        dataset_id=dataset_id,
    )
    audit_data_event(
        action="SCHEMA_DETECTED",
        details=f"Detected {col_count} columns schema with {lang} language profile",
        officer_id=officer_id,
        dataset_id=dataset_id,
    )

    return {
        "dataset_id": dataset_id,
        "file_name": file_path.name,
        "row_count": row_count,
        "column_count": col_count,
        "status": "ready",
        "sheet_name": target_sheet,
        "language_detected": lang,
        "columns": columns_profile,
        "message": f"தரவு வெற்றிகரமாக பதிவேற்றப்பட்டது. {col_count} நெடுவரிசைகள் கண்டறியப்பட்டன.",
    }


def load_dataset_dataframe(dataset_path: str, sheet_name: str = "Sheet1") -> pd.DataFrame:
    """Load DataFrame from stored dataset path safely."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file missing: {path}")

    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, sheet_name=sheet_name)
    else:
        try:
            return pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="cp1252")
