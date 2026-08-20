"""Bulk Router — Grievance workflow endpoints (ingest, list, approve, draft, export)."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
from pipeline.database import (
    generate_department_file_number,
    get_db_connection,
    get_source_details,
    log_audit,
    save_draft,
    update_draft_approval,
)
from pipeline.generation import TamilDraftGenerator, export_draft_to_docx
from pipeline.ingestion import process_file_path
from pipeline.orchestrator import WorkflowPipeline

router = APIRouter(tags=["Bulk Workflow"])

# ---------------------------------------------------------------------------
# Lazy pipeline singleton
# ---------------------------------------------------------------------------
_pipeline: Optional[WorkflowPipeline] = None


def get_pipeline() -> WorkflowPipeline:
    global _pipeline
    if _pipeline is None:
        from pipeline.database import init_db
        init_db()
        _pipeline = WorkflowPipeline()
    return _pipeline


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class ApprovalRequest(BaseModel):
    officer_id: str
    action: str = "approve"  # approve | reject


class DraftEditRequest(BaseModel):
    officer_id: str
    draft_text: str


class FileNumberRequest(BaseModel):
    department: str
    officer_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/api/bulk/items")
async def list_bulk_items(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all workflow items with filters — connected to real SQLite data."""
    conn = get_db_connection()
    try:
        query = """
            SELECT s.source_id, s.source_type, s.raw_path, s.received_at,
                   s.processed_at, s.status,
                   c.department, c.priority, c.final_decision,
                   d.hallucination_score, d.officer_approved
            FROM sources s
            LEFT JOIN classifications c ON s.source_id = c.source_id
            LEFT JOIN drafts d ON s.source_id = d.source_id
        """
        conditions = []
        params: list = []

        if status:
            conditions.append("s.status = ?")
            params.append(status)
        if department:
            conditions.append("c.department = ?")
            params.append(department)
        if priority:
            conditions.append("c.priority = ?")
            params.append(priority)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY s.received_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()

        items = []
        for r in rows:
            raw_path = Path(r["raw_path"])
            items.append({
                "source_id": r["source_id"],
                "source_type": r["source_type"],
                "file_name": raw_path.name,
                "received_at": r["received_at"],
                "processed_at": r["processed_at"],
                "status": r["status"] or "pending",
                "department": r["department"] or "—",
                "priority": r["priority"] or "LOW",
                "final_decision": r["final_decision"],
                "hallucination_score": r["hallucination_score"],
                "officer_approved": bool(r["officer_approved"]) if r["officer_approved"] is not None else False,
            })
        return {"items": items, "total": len(items)}
    finally:
        conn.close()


@router.get("/api/bulk/{source_id}")
async def get_bulk_item_detail(source_id: str):
    """Full details for a single workflow item — OCR, entities, classification, draft, grounding."""
    details = get_source_details(source_id)
    if not details:
        raise HTTPException(status_code=404, detail="Source not found")

    result = dict(details)
    result["file_name"] = Path(result.get("raw_path", "")).name
    return result


@router.post("/api/bulk/{source_id}/approve")
async def approve_item(source_id: str, req: ApprovalRequest):
    """Approve or reject a draft."""
    details = get_source_details(source_id)
    if not details:
        raise HTTPException(status_code=404, detail="Source not found")

    is_approve = req.action == "approve"
    update_draft_approval(source_id, is_approve, req.officer_id)
    log_audit(
        source_id=source_id,
        action="OFFICER_APPROVED" if is_approve else "OFFICER_REJECTED",
        officer_id=req.officer_id,
        details=f"Action: {req.action}",
    )
    return {"status": "ok", "action": req.action, "source_id": source_id}


@router.post("/api/bulk/{source_id}/edit-draft")
async def edit_draft_endpoint(source_id: str, req: DraftEditRequest):
    """Officer manually edits draft text."""
    details = get_source_details(source_id)
    if not details:
        raise HTTPException(status_code=404, detail="Source not found")

    draft_obj = details.get("draft") or {}
    save_draft(
        source_id=source_id,
        draft_text=req.draft_text,
        template_used=draft_obj.get("template_used", "manual_edit"),
        hallucination_score=draft_obj.get("hallucination_score", 0.0),
        grounding_map=draft_obj.get("grounding_map", {}),
        missing_fields=draft_obj.get("missing_fields", []),
    )
    log_audit(
        source_id=source_id,
        action="OFFICER_EDITED_DRAFT",
        officer_id=req.officer_id,
        details="Manual draft edit via React UI",
    )
    return {"status": "ok"}


@router.post("/api/bulk/{source_id}/generate-file-number")
async def gen_file_number(source_id: str, req: FileNumberRequest):
    """Generate deterministic sequential file number."""
    file_no = generate_department_file_number(req.department, req.officer_id, source_id=source_id)
    return {"file_number": file_no, "source_id": source_id}


@router.get("/api/bulk/{source_id}/export-docx")
async def export_docx_endpoint(source_id: str):
    """Export approved draft as .docx file."""
    details = get_source_details(source_id)
    if not details or not details.get("draft"):
        raise HTTPException(status_code=404, detail="Draft not found")

    draft_text = details["draft"].get("draft_text", "")
    docx_path = config.UPLOADS_PROCESSED_DIR / f"ack_{source_id[:12]}.docx"
    export_draft_to_docx(draft_text, source_id, docx_path)

    return FileResponse(
        path=str(docx_path),
        filename=f"Erode_Collectorate_Ack_{source_id[:8]}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/api/bulk/ingest")
async def ingest_file_endpoint(file: UploadFile = File(...)):
    """Upload and ingest a scanned document or email."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".eml"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    dest_dir = config.UPLOADS_SCANNED_DIR if ext != ".eml" else config.UPLOADS_EMAILS_DIR
    dest_path = dest_dir / file.filename
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    source_id, processed_path = process_file_path(dest_path)
    pipeline = get_pipeline()
    result = pipeline.process_source(source_id, file_path=processed_path)

    return {
        "source_id": source_id,
        "file_name": file.filename,
        "status": result.get("status", "draft_ready"),
        "department": result.get("classification", {}).get("department"),
    }
