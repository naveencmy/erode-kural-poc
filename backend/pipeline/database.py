"""SQLite Persistence and Audit Layer for Erode Collectorate Bulk Workflow Module V0.2."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled and row factory configured."""
    target_path = db_path or config.DATABASE_PATH
    conn = sqlite3.connect(str(target_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize all tables and migrate schema strictly conforming to Collectorate V0.2 contracts."""
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            source_type TEXT CHECK(source_type IN ('email', 'scan')),
            raw_path TEXT NOT NULL,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            status TEXT CHECK(status IN ('pending', 'ocr_done', 'classified', 'draft_ready', 'approved', 'rejected')),
            assigned_officer TEXT
        );

        CREATE TABLE IF NOT EXISTS ocr_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT REFERENCES sources(source_id) ON DELETE CASCADE,
            page_number INTEGER,
            full_text TEXT,
            blocks_json TEXT,
            avg_confidence REAL,
            ocr_engine TEXT DEFAULT 'indic_ocr',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            full_text_corrected TEXT,
            corrected_by TEXT,
            corrected_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT REFERENCES sources(source_id) ON DELETE CASCADE,
            entity_type TEXT,
            entity_value TEXT,
            confidence REAL,
            validation_status TEXT CHECK(validation_status IN ('verified', 'suspect', 'missing')),
            source_chunk TEXT
        );

        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT REFERENCES sources(source_id) ON DELETE CASCADE,
            department TEXT,
            priority TEXT,
            rule_score INTEGER,
            ai_confidence REAL,
            final_decision TEXT CHECK(final_decision IN ('rule', 'ai')),
            classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT REFERENCES sources(source_id) ON DELETE CASCADE,
            draft_text TEXT,
            template_used TEXT,
            hallucination_score REAL,
            officer_approved BOOLEAN DEFAULT 0,
            approved_by TEXT,
            approved_at TIMESTAMP,
            grounding_map TEXT,
            missing_fields TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_id TEXT,
            action TEXT,
            officer_id TEXT,
            details TEXT,
            ip_address TEXT
        );

        CREATE TABLE IF NOT EXISTS sequence_counters (
            department TEXT PRIMARY KEY,
            last_number INTEGER NOT NULL DEFAULT 1000,
            year INTEGER NOT NULL
        );


        -- Module 2: Data & Visualization Tables
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            source_id TEXT REFERENCES sources(source_id),
            officer_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size_bytes INTEGER,
            row_count INTEGER,
            column_count INTEGER,
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('uploaded', 'schema_detected', 'profiled', 'ready')),
            sheet_name TEXT DEFAULT 'Sheet1',
            language_detected TEXT DEFAULT 'mixed'
        );

        CREATE TABLE IF NOT EXISTS dataset_columns (
            column_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id TEXT REFERENCES datasets(dataset_id) ON DELETE CASCADE,
            column_name TEXT NOT NULL,
            column_name_tamil TEXT,
            column_index INTEGER,
            data_type_detected TEXT CHECK(data_type_detected IN ('text', 'number', 'date', 'boolean', 'mixed')),
            sample_values TEXT,
            null_count INTEGER,
            distinct_count INTEGER,
            min_value TEXT,
            max_value TEXT,
            mean_value REAL,
            std_dev REAL,
            is_categorical BOOLEAN DEFAULT 0,
            is_taluk_column BOOLEAN DEFAULT 0,
            is_department_column BOOLEAN DEFAULT 0,
            is_date_column BOOLEAN DEFAULT 0,
            is_amount_column BOOLEAN DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS data_queries (
            query_id TEXT PRIMARY KEY,
            dataset_id TEXT REFERENCES datasets(dataset_id),
            officer_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            question_language TEXT CHECK(question_language IN ('ta', 'en')),
            parsed_intent TEXT,
            generated_code TEXT,
            generated_sql TEXT,
            execution_status TEXT CHECK(execution_status IN ('pending', 'success', 'error', 'unsafe_blocked')),
            execution_error TEXT,
            result_json TEXT,
            result_summary TEXT,
            chart_path TEXT,
            execution_time_ms INTEGER,
            row_count_returned INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS data_insights (
            insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT REFERENCES data_queries(query_id),
            dataset_id TEXT REFERENCES datasets(dataset_id),
            insight_type TEXT CHECK(insight_type IN ('trend', 'outlier', 'anomaly', 'comparison', 'summary')),
            insight_text_tamil TEXT NOT NULL,
            insight_text_english TEXT,
            grounding_sql TEXT,
            grounding_rows TEXT,
            confidence_score REAL,
            is_verified BOOLEAN DEFAULT 0,
            verified_by TEXT,
            verified_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS charts (
            chart_id TEXT PRIMARY KEY,
            query_id TEXT REFERENCES data_queries(query_id),
            dataset_id TEXT REFERENCES datasets(dataset_id),
            chart_type TEXT CHECK(chart_type IN ('bar', 'line', 'pie', 'scatter', 'heatmap', 'table')),
            chart_title_tamil TEXT,
            chart_title_english TEXT,
            x_axis_column TEXT,
            y_axis_column TEXT,
            group_by_column TEXT,
            file_path TEXT NOT NULL,
            file_size_bytes INTEGER,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            officer_id TEXT
        );

        CREATE TABLE IF NOT EXISTS imap_cursor (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_uid INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );


        INSERT OR IGNORE INTO imap_cursor (id, last_uid, updated_at)
        VALUES (1, 0, CURRENT_TIMESTAMP);
        """)

        # Safe Column Migrations for existing databases
        cur = conn.cursor()
        
        # Check ocr_results columns
        cur.execute("PRAGMA table_info(ocr_results)")
        ocr_cols = {row["name"] for row in cur.fetchall()}
        if "full_text_corrected" not in ocr_cols:
            cur.execute("ALTER TABLE ocr_results ADD COLUMN full_text_corrected TEXT")
        if "corrected_by" not in ocr_cols:
            cur.execute("ALTER TABLE ocr_results ADD COLUMN corrected_by TEXT")
        if "corrected_at" not in ocr_cols:
            cur.execute("ALTER TABLE ocr_results ADD COLUMN corrected_at TIMESTAMP")

        # Check drafts columns
        cur.execute("PRAGMA table_info(drafts)")
        draft_cols = {row["name"] for row in cur.fetchall()}
        if "grounding_map" not in draft_cols:
            cur.execute("ALTER TABLE drafts ADD COLUMN grounding_map TEXT")
        if "missing_fields" not in draft_cols:
            cur.execute("ALTER TABLE drafts ADD COLUMN missing_fields TEXT")

    conn.close()


def record_source(
    source_id: str,
    source_type: str,
    raw_path: str,
    status: str = "pending",
    assigned_officer: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> bool:
    """Insert a new source document into the sources table if not already existing."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sources (source_id, source_type, raw_path, received_at, status, assigned_officer)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    raw_path = excluded.raw_path,
                    status = excluded.status
                """,
                (source_id, source_type, str(raw_path), datetime.utcnow().isoformat(), status, assigned_officer),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def update_source_status(source_id: str, status: str, db_path: Optional[Path] = None) -> None:
    """Update pipeline processing state."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                UPDATE sources
                SET status = ?, processed_at = ?
                WHERE source_id = ?
                """,
                (status, datetime.utcnow().isoformat(), source_id),
            )
    finally:
        conn.close()


def save_ocr_results(
    source_id: str,
    page_number: int,
    full_text: str,
    blocks_json: str,
    avg_confidence: float,
    ocr_engine: str = "indic_ocr",
    db_path: Optional[Path] = None,
) -> int:
    """Persist OCR output for a page with deduplication."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM ocr_results WHERE source_id = ? AND page_number = ?",
                (source_id, page_number),
            )
            cursor.execute(
                """
                INSERT INTO ocr_results (source_id, page_number, full_text, blocks_json, avg_confidence, ocr_engine, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, page_number, full_text, blocks_json, avg_confidence, ocr_engine, datetime.utcnow().isoformat()),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def save_ocr_correction(
    source_id: str,
    page_number: int,
    corrected_text: str,
    officer_id: str,
    db_path: Optional[Path] = None,
) -> None:
    """Persist officer-corrected OCR text and update provenance."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                UPDATE ocr_results
                SET full_text_corrected = ?, corrected_by = ?, corrected_at = ?
                WHERE source_id = ? AND page_number = ?
                """,
                (corrected_text, officer_id, datetime.utcnow().isoformat(), source_id, page_number),
            )
    finally:
        conn.close()


def save_entities(
    source_id: str,
    entities_list: List[Dict[str, Any]],
    db_path: Optional[Path] = None,
) -> None:
    """Persist extracted entity dictionary list."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM entities WHERE source_id = ?", (source_id,))
            for ent in entities_list:
                conn.execute(
                    """
                    INSERT INTO entities (source_id, entity_type, entity_value, confidence, validation_status, source_chunk)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        ent.get("entity_type", "unknown"),
                        ent.get("entity_value", ""),
                        ent.get("confidence", 1.0),
                        ent.get("validation_status", "verified"),
                        ent.get("source_chunk", ""),
                    ),
                )
    finally:
        conn.close()


def save_classification(
    source_id: str,
    department: str,
    priority: str,
    rule_score: int,
    ai_confidence: float,
    final_decision: str,
    db_path: Optional[Path] = None,
) -> int:
    """Save rule/AI classification for a source."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM classifications WHERE source_id = ?", (source_id,))
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO classifications (source_id, department, priority, rule_score, ai_confidence, final_decision, classified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source_id, department, priority, rule_score, ai_confidence, final_decision, datetime.utcnow().isoformat()),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def save_draft(
    source_id: str,
    draft_text: str,
    template_used: str,
    hallucination_score: float,
    grounding_map: Optional[Dict[str, Any]] = None,
    missing_fields: Optional[List[str]] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Save generated Tamil acknowledgment draft with provenance grounding map."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM drafts WHERE source_id = ?", (source_id,))
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO drafts (source_id, draft_text, template_used, hallucination_score, officer_approved, grounding_map, missing_fields)
                VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    source_id,
                    draft_text,
                    template_used,
                    hallucination_score,
                    json.dumps(grounding_map or {}, ensure_ascii=False),
                    json.dumps(missing_fields or [], ensure_ascii=False),
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def generate_department_file_number(
    department: str,
    officer_id: str,
    source_id: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> str:
    """Generate a deterministic sequential file number for the department: {seq}/{dept_code}/{year}."""
    conn = get_db_connection(db_path)
    current_year = datetime.now().year
    
    dept_code_map = {
        "வருவாய்": "REV",
        "சமூக_நலன்": "SOC",
        "பொதுப்பணித்துறை": "PWD",
        "காவல்துறை": "POL",
        "பதிவுத்துறை": "REG",
        "பொது_வழக்கு": "GEN",
    }
    code = dept_code_map.get(department, "GEN")

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_number, year FROM sequence_counters WHERE department = ?",
                (department,),
            )
            row = cursor.fetchone()
            
            if row:
                last_num = row["last_number"]
                stored_year = row["year"]
                if stored_year != current_year:
                    new_num = 1001
                else:
                    new_num = last_num + 1
                cursor.execute(
                    "UPDATE sequence_counters SET last_number = ?, year = ? WHERE department = ?",
                    (new_num, current_year, department),
                )
            else:
                new_num = 1001
                cursor.execute(
                    "INSERT INTO sequence_counters (department, last_number, year) VALUES (?, ?, ?)",
                    (department, new_num, current_year),
                )

            file_no = f"{new_num}/{code}/{current_year}"
    finally:
        conn.close()

    if source_id:
        log_audit(
            source_id=source_id,
            action="OFFICER_GENERATED_FILE_NUMBER",
            officer_id=officer_id,
            details=f"Generated sequential file number {file_no} for department {department}",
            db_path=db_path,
        )
    return file_no


def update_draft_approval(
    source_id: str,
    officer_approved: bool,
    approved_by: str,
    db_path: Optional[Path] = None,
) -> None:
    """Mark draft as approved/rejected by assigned officer."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            status_val = "approved" if officer_approved else "rejected"
            conn.execute(
                """
                UPDATE drafts
                SET officer_approved = ?, approved_by = ?, approved_at = ?
                WHERE source_id = ?
                """,
                (1 if officer_approved else 0, approved_by, datetime.utcnow().isoformat(), source_id),
            )
            conn.execute(
                """
                UPDATE sources
                SET status = ?, assigned_officer = ?
                WHERE source_id = ?
                """,
                (status_val, approved_by, source_id),
            )
    finally:
        conn.close()


def log_audit(
    source_id: Optional[str],
    action: str,
    officer_id: str,
    details: str,
    ip_address: str = "127.0.0.1",
    db_path: Optional[Path] = None,
) -> int:
    """Append-only audit logging."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_log (timestamp, source_id, action, officer_id, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (datetime.utcnow().isoformat(), source_id, action, officer_id, details, ip_address),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_imap_cursor(db_path: Optional[Path] = None) -> int:
    """Retrieve last fetched IMAP UID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT last_uid FROM imap_cursor WHERE id = 1")
        row = cursor.fetchone()
        return row["last_uid"] if row else 0
    finally:
        conn.close()


def update_imap_cursor(last_uid: int, db_path: Optional[Path] = None) -> None:
    """Update last fetched IMAP UID cursor checkpoint."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO imap_cursor (id, last_uid, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    last_uid = excluded.last_uid,
                    updated_at = excluded.updated_at
                """,
                (last_uid, datetime.utcnow().isoformat()),
            )
    finally:
        conn.close()


def get_source_details(source_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve joined source, ocr, entities, classification, draft, and grounding details."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,))
        src = cursor.fetchone()
        if not src:
            return None

        result: Dict[str, Any] = dict(src)

        # OCR Results (Guaranteed single latest record per page_number)
        cursor.execute(
            """
            SELECT * FROM ocr_results 
            WHERE id IN (
                SELECT MAX(id) FROM ocr_results WHERE source_id = ? GROUP BY page_number
            )
            ORDER BY page_number ASC
            """,
            (source_id,),
        )
        result["ocr_pages"] = [dict(row) for row in cursor.fetchall()]

        # Entities
        cursor.execute("SELECT * FROM entities WHERE source_id = ?", (source_id,))
        result["entities"] = [dict(row) for row in cursor.fetchall()]

        # Classification
        cursor.execute("SELECT * FROM classifications WHERE source_id = ?", (source_id,))
        cls_row = cursor.fetchone()
        result["classification"] = dict(cls_row) if cls_row else None

        # Draft
        cursor.execute("SELECT * FROM drafts WHERE source_id = ?", (source_id,))
        draft_row = cursor.fetchone()
        if draft_row:
            d_dict = dict(draft_row)
            try:
                d_dict["grounding_map"] = json.loads(d_dict.get("grounding_map") or "{}")
            except Exception:
                d_dict["grounding_map"] = {}
            try:
                d_dict["missing_fields"] = json.loads(d_dict.get("missing_fields") or "[]")
            except Exception:
                d_dict["missing_fields"] = []
            result["draft"] = d_dict
        else:
            result["draft"] = None

        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Module 2 (Data & Visualization) Database CRUD Functions
# ---------------------------------------------------------------------------

def save_dataset(
    dataset_id: str,
    officer_id: str,
    file_name: str,
    file_path: str,
    file_size_bytes: int,
    row_count: int,
    column_count: int,
    status: str = "uploaded",
    source_id: Optional[str] = None,
    sheet_name: str = "Sheet1",
    language_detected: str = "mixed",
    db_path: Optional[Path] = None,
) -> None:
    """Insert or update dataset registry record."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO datasets (
                    dataset_id, source_id, officer_id, file_name, file_path,
                    file_size_bytes, row_count, column_count, status,
                    sheet_name, language_detected
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dataset_id) DO UPDATE SET
                    file_name=excluded.file_name,
                    file_path=excluded.file_path,
                    file_size_bytes=excluded.file_size_bytes,
                    row_count=excluded.row_count,
                    column_count=excluded.column_count,
                    status=excluded.status,
                    sheet_name=excluded.sheet_name,
                    language_detected=excluded.language_detected;
                """,
                (
                    dataset_id,
                    source_id,
                    officer_id,
                    file_name,
                    str(file_path),
                    file_size_bytes,
                    row_count,
                    column_count,
                    status,
                    sheet_name,
                    language_detected,
                ),
            )
    finally:
        conn.close()


def save_dataset_columns(
    dataset_id: str,
    columns_data: List[Dict[str, Any]],
    db_path: Optional[Path] = None,
) -> None:
    """Save auto-detected column profiles for a dataset."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM dataset_columns WHERE dataset_id = ?", (dataset_id,))
            for col in columns_data:
                conn.execute(
                    """
                    INSERT INTO dataset_columns (
                        dataset_id, column_name, column_name_tamil, column_index,
                        data_type_detected, sample_values, null_count, distinct_count,
                        min_value, max_value, mean_value, std_dev,
                        is_categorical, is_taluk_column, is_department_column,
                        is_date_column, is_amount_column
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        dataset_id,
                        col["column_name"],
                        col.get("column_name_tamil"),
                        col.get("column_index", 0),
                        col.get("data_type_detected", "text"),
                        json.dumps(col.get("sample_values", []), ensure_ascii=False),
                        col.get("null_count", 0),
                        col.get("distinct_count", 0),
                        str(col.get("min_value")) if col.get("min_value") is not None else None,
                        str(col.get("max_value")) if col.get("max_value") is not None else None,
                        col.get("mean_value"),
                        col.get("std_dev"),
                        1 if col.get("is_categorical") else 0,
                        1 if col.get("is_taluk_column") else 0,
                        1 if col.get("is_department_column") else 0,
                        1 if col.get("is_date_column") else 0,
                        1 if col.get("is_amount_column") else 0,
                    ),
                )
    finally:
        conn.close()


def get_dataset(dataset_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve dataset info with full column schema."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,))
        ds = cursor.fetchone()
        if not ds:
            return None
        result = dict(ds)

        cursor.execute("SELECT * FROM dataset_columns WHERE dataset_id = ? ORDER BY column_index ASC", (dataset_id,))
        cols = []
        for r in cursor.fetchall():
            cd = dict(r)
            try:
                cd["sample_values"] = json.loads(cd.get("sample_values") or "[]")
            except Exception:
                cd["sample_values"] = []
            cols.append(cd)
        result["columns"] = cols
        return result
    finally:
        conn.close()


def list_datasets(
    officer_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """List datasets with metadata."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM datasets"
        params = []
        if officer_id:
            query += " WHERE officer_id = ?"
            params.append(officer_id)
        query += " ORDER BY upload_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def delete_dataset(dataset_id: str, db_path: Optional[Path] = None) -> bool:
    """Delete dataset and cascading records."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))
            return cursor.rowcount > 0
    finally:
        conn.close()


def save_data_query(
    query_id: str,
    dataset_id: str,
    officer_id: str,
    question_text: str,
    question_language: str = "ta",
    parsed_intent: Optional[str] = None,
    generated_code: Optional[str] = None,
    generated_sql: Optional[str] = None,
    execution_status: str = "pending",
    execution_error: Optional[str] = None,
    result_json: Optional[str] = None,
    result_summary: Optional[str] = None,
    chart_path: Optional[str] = None,
    execution_time_ms: int = 0,
    row_count_returned: int = 0,
    db_path: Optional[Path] = None,
) -> None:
    """Save natural language query audit record."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO data_queries (
                    query_id, dataset_id, officer_id, question_text,
                    question_language, parsed_intent, generated_code, generated_sql,
                    execution_status, execution_error, result_json, result_summary,
                    chart_path, execution_time_ms, row_count_returned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(query_id) DO UPDATE SET
                    parsed_intent=excluded.parsed_intent,
                    generated_code=excluded.generated_code,
                    generated_sql=excluded.generated_sql,
                    execution_status=excluded.execution_status,
                    execution_error=excluded.execution_error,
                    result_json=excluded.result_json,
                    result_summary=excluded.result_summary,
                    chart_path=excluded.chart_path,
                    execution_time_ms=excluded.execution_time_ms,
                    row_count_returned=excluded.row_count_returned;
                """,
                (
                    query_id,
                    dataset_id,
                    officer_id,
                    question_text,
                    question_language,
                    parsed_intent,
                    generated_code,
                    generated_sql,
                    execution_status,
                    execution_error,
                    result_json,
                    result_summary,
                    chart_path,
                    execution_time_ms,
                    row_count_returned,
                ),
            )
    finally:
        conn.close()


def save_data_insight(
    query_id: str,
    dataset_id: str,
    insight_type: str,
    insight_text_tamil: str,
    insight_text_english: Optional[str] = None,
    grounding_sql: Optional[str] = None,
    grounding_rows: Optional[List[int]] = None,
    confidence_score: float = 1.0,
    db_path: Optional[Path] = None,
) -> int:
    """Save an AI-generated insight with deterministic grounding."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO data_insights (
                    query_id, dataset_id, insight_type, insight_text_tamil,
                    insight_text_english, grounding_sql, grounding_rows,
                    confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    dataset_id,
                    insight_type,
                    insight_text_tamil,
                    insight_text_english,
                    grounding_sql,
                    json.dumps(grounding_rows or []),
                    confidence_score,
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_data_insights(query_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve insights for a query."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM data_insights WHERE query_id = ?", (query_id,))
        results = []
        for r in cursor.fetchall():
            row = dict(r)
            try:
                row["grounding_rows"] = json.loads(row.get("grounding_rows") or "[]")
            except Exception:
                row["grounding_rows"] = []
            results.append(row)
        return results
    finally:
        conn.close()


def save_chart_record(
    chart_id: str,
    query_id: Optional[str],
    dataset_id: str,
    chart_type: str,
    chart_title_tamil: str,
    file_path: str,
    file_size_bytes: int,
    officer_id: str,
    chart_title_english: Optional[str] = None,
    x_axis_column: Optional[str] = None,
    y_axis_column: Optional[str] = None,
    group_by_column: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    """Record a generated chart."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO charts (
                    chart_id, query_id, dataset_id, chart_type,
                    chart_title_tamil, chart_title_english, x_axis_column,
                    y_axis_column, group_by_column, file_path, file_size_bytes,
                    officer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chart_id,
                    query_id,
                    dataset_id,
                    chart_type,
                    chart_title_tamil,
                    chart_title_english,
                    x_axis_column,
                    y_axis_column,
                    group_by_column,
                    str(file_path),
                    file_size_bytes,
                    officer_id,
                ),
            )
    finally:
        conn.close()


def get_chart_record(chart_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve chart metadata."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM charts WHERE chart_id = ?", (chart_id,))
        r = cursor.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()

