"""FastAPI REST API Server for Erode Collectorate AI System.

Wraps existing pipeline modules and exposes REST endpoints
for the React frontend.
"""

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from pipeline.database import (
    generate_department_file_number,
    get_db_connection,
    get_source_details,
    init_db,
    log_audit,
    save_draft,
    update_draft_approval,
)
from pipeline.generation import TamilDraftGenerator, export_draft_to_docx
from pipeline.ingestion import process_file_path
from pipeline.orchestrator import WorkflowPipeline

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Erode Collectorate AI System API",
    version="1.0.0",
    description="REST API for the Erode District Collectorate AI-Powered Administrative Assistant",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init pipeline
_pipeline: Optional[WorkflowPipeline] = None


def get_pipeline() -> WorkflowPipeline:
    global _pipeline
    if _pipeline is None:
        init_db()
        _pipeline = WorkflowPipeline()
    return _pipeline


# ---------------------------------------------------------------------------
# Pydantic models
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


class ChatRequest(BaseModel):
    message: str
    officer_id: str
    context: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    template_type: str
    fields: Dict[str, Any]
    officer_id: str


class DataQueryRequest(BaseModel):
    query: str
    dataset_id: str
    officer_id: str


# ---------------------------------------------------------------------------
# CORE ENDPOINTS — Connected to existing pipeline
# ---------------------------------------------------------------------------

@app.get("/api/config")
async def get_app_config():
    """Return application configuration. Frontend fetches dynamic config from here."""
    return {
        "departments": config.DEPARTMENTS,
        "priority_levels": config.PRIORITY_LEVELS,
        "dev_mode": config.DEV_MODE,
        "ollama_model": config.OLLAMA_MODEL,
        "imap_server": config.IMAP_SERVER,
        "database": str(config.DATABASE_PATH.name),
        "ocr_engine": "Indic-OCR (Transformer)",
        "version": "1.0.0",
    }


@app.get("/api/stats")
async def get_dashboard_stats():
    """Real-time statistics from the database — zero hardcoded values."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM sources")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as c FROM sources WHERE status = 'pending'")
        pending = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM sources WHERE status = 'draft_ready'")
        draft_ready = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM sources WHERE status = 'approved'")
        approved = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM sources WHERE status = 'rejected'")
        rejected = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM sources WHERE status = 'ocr_done'")
        ocr_done = cur.fetchone()["c"]

        # Priority counts
        cur.execute("""
            SELECT COUNT(*) as cnt 
            FROM classifications c 
            WHERE c.priority = 'HIGH'
        """)
        row = cur.fetchone()
        urgent = row["cnt"] if row else 0

        return {
            "total": total,
            "pending": pending + ocr_done,
            "draft_ready": draft_ready,
            "approved": approved,
            "rejected": rejected,
            "urgent": urgent,
        }
    finally:
        conn.close()


@app.get("/api/bulk/items")
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


@app.get("/api/bulk/{source_id}")
async def get_bulk_item_detail(source_id: str):
    """Full details for a single workflow item — OCR, entities, classification, draft, grounding."""
    details = get_source_details(source_id)
    if not details:
        raise HTTPException(status_code=404, detail="Source not found")

    result = dict(details)
    result["file_name"] = Path(result.get("raw_path", "")).name
    return result


@app.post("/api/bulk/{source_id}/approve")
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


@app.post("/api/bulk/{source_id}/edit-draft")
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


@app.post("/api/bulk/{source_id}/generate-file-number")
async def gen_file_number(source_id: str, req: FileNumberRequest):
    """Generate deterministic sequential file number."""
    file_no = generate_department_file_number(req.department, req.officer_id, source_id=source_id)
    return {"file_number": file_no, "source_id": source_id}


@app.get("/api/bulk/{source_id}/export-docx")
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


@app.post("/api/bulk/ingest")
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


@app.get("/api/audit")
async def get_audit_log(limit: int = Query(100, ge=1, le=500)):
    """Immutable audit trail."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        return {"entries": rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# STUB ENDPOINTS — Ready for other module connections
# ---------------------------------------------------------------------------

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Intelligent context-aware Erode Collectorate AI Assistant chat endpoint."""
    msg = (req.message or "").lower().strip()
    conn = get_db_connection()
    blocks = []
    actions = []
    
    try:
        cur = conn.cursor()
        
        # Check if query is about petitions / queue / status
        if any(k in msg for k in ["petition", "queue", "pending", "status", "count", "summary", "மனு", "வரிசை", "நிலுவை", "எண்ணிக்கை", "தொகை", "அறிக்கை"]):
            cur.execute("SELECT status, COUNT(*) as cnt FROM bulk_items GROUP BY status")
            status_counts = {r["status"]: r["cnt"] for r in cur.fetchall()}
            
            cur.execute("SELECT department, COUNT(*) as cnt FROM bulk_items GROUP BY department")
            dept_counts = {r["department"]: r["cnt"] for r in cur.fetchall()}
            
            total = sum(status_counts.values())
            pending = status_counts.get("pending", 0) + status_counts.get("extracted", 0) + status_counts.get("classified", 0)
            approved = status_counts.get("approved", 0)
            rejected = status_counts.get("rejected", 0)
            
            dept_summary = ", ".join([f"{d}: {c}" for d, c in dept_counts.items() if d])
            
            reply_tamil = (
                f"🏛️ **ஈரோடு மாவட்ட ஆட்சியரகம் - மனுக்கள் நிலை அறிக்கை**\n\n"
                f"• **மொத்த மனுக்கள்**: {total}\n"
                f"• **நிலுவையில் உள்ளவை**: {pending}\n"
                f"• **ஒப்புதல் அளிக்கப்பட்டவை**: {approved}\n"
                f"• **நிராகரிக்கப்பட்டவை**: {rejected}\n\n"
                f"**துறைவாரியான விபரம்**: {dept_summary if dept_summary else 'தரவு கிடைக்கவில்லை'}"
            )
            
            blocks.append({"type": "markdown", "content": reply_tamil})
            actions.append({"label": "செயலாக்க வரிசை காண்க (View Queue)", "action": "NAVIGATE_BULK"})
            actions.append({"label": "நிலுவை மனுக்களை வடிகட்டு (Filter Pending)", "action": "FILTER_PENDING"})

        elif any(k in msg for k in ["revenue", "police", "social", "pension", "வருவாய்", "காவல்", "சமூக நலம்", "துறை"]):
            dept_keyword = "revenue" if "revenue" in msg or "வருவாய்" in msg else ("police" if "police" in msg or "காவல்" in msg else "social_welfare")
            cur.execute(
                "SELECT source_id, petitioner_name, taluk, status FROM bulk_items WHERE department LIKE ? ORDER BY created_at DESC LIMIT 5",
                (f"%{dept_keyword}%",)
            )
            items = cur.fetchall()
            if items:
                item_lines = [f"• **{i['source_id']}** - {i['petitioner_name'] or 'அறியப்படாதவர்'} ({i['taluk'] or 'ஈரோடு'}) [{i['status']}]" for i in items]
                reply_tamil = f"📋 **{dept_keyword.upper()} துறை சார்ந்த சமீபத்திய மனுக்கள்:**\n\n" + "\n".join(item_lines)
            else:
                reply_tamil = f"ℹ️ {dept_keyword.upper()} துறையில் தற்போது மனுக்கள் எதுவும் காணப்படவில்லை."
            
            blocks.append({"type": "markdown", "content": reply_tamil})
            actions.append({"label": f"{dept_keyword.upper()} மனுக்கள் பார்க்க", "action": "FILTER_DEPT", "value": dept_keyword})

        elif any(k in msg for k in ["dataset", "data", "table", "chart", "தரவு", "அட்டவணை", "வரைபடம்"]):
            try:
                cur.execute("SELECT dataset_id, title_ta, title_en, row_count FROM data_datasets")
                datasets = cur.fetchall()
                if datasets:
                    ds_lines = [f"• **{d['title_ta'] or d['title_en']}** ({d['dataset_id']}) - {d['row_count']} வரிகள்" for d in datasets]
                    reply_tamil = f"📊 **கிடைக்கக்கூடிய மாவட்ட தரவுத்தொகுப்புகள் ({len(datasets)}):**\n\n" + "\n".join(ds_lines)
                else:
                    reply_tamil = "📊 தற்போது பதிவேற்றப்பட்ட தரவுத்தொகுப்புகள் எதுவும் இல்லை. 'தரவு பகுப்பாய்வு' பக்கத்தில் புதிய CSV/Excel ফাইল பதிவேற்றலாம்."
            except Exception:
                reply_tamil = "📊 தரவுத்தொகுப்புகள் தொகுதி தயாராக உள்ளது. 'தரவு & பகுப்பாய்வு' பகுதிக்கு செல்லவும்."
            
            blocks.append({"type": "markdown", "content": reply_tamil})
            actions.append({"label": "தரவு பகுப்பாய்வு திறக்க (Open Data Viz)", "action": "NAVIGATE_DATA"})

        elif any(k in msg for k in ["draft", "letter", "ack", "வரைவு", "கடிதம்", "ஒப்புதல்"]):
            reply_tamil = (
                "📝 **அரசு ஒப்புதல் கடித வரைவு உருவாக்க வழிகாட்டி:**\n\n"
                "1. **செயலாக்க வரிசை (Bulk Processing)** பக்கம் செல்லவும்.\n"
                "2. மனுவைத் தேர்ந்தெடுத்து **'வரைவுத் தயாரிப்பு' (Draft Generation)** பொத்தானைக் கிளிக் செய்யவும்.\n"
                "3. கணினி தானாகவே தமிழ்நாடு அரசின் அதிகாரப்பூர்வ Jinja2 வார்ப்புருவைப் பயன்படுத்தி வரைவை உருவாக்கும்.\n"
                "4. வரைவை சரிபார்த்து **Approve** அல்லது **DOCX பதிவிறக்கம்** செய்யலாம்."
            )
            blocks.append({"type": "markdown", "content": reply_tamil})
            actions.append({"label": "செயலாக்க வரிசைக்கு செல்", "action": "NAVIGATE_BULK"})

        else:
            # General official assistant greeting
            reply_tamil = (
                f"🏛️ **வணக்கம்! ஈரோடு மாவட்ட ஆட்சியரகம் AI குரல் உதவி மையம்.**\n\n"
                f"உங்கள் கேள்வி: \"*{req.message}*\"\n\n"
                f"நான் உங்களுக்கு பின்வரும் பணிகளில் உதவ முடியும்:\n"
                f"• 📥 **மனுக்கள் நிலை**: 'நிலுவையில் உள்ள மனுக்கள் எத்தனை?'\n"
                f"• 🏢 **துறை தகவல்கள்**: 'வருவாய்த்துறை மனுக்கள் விபரம்'\n"
                f"• 📊 **தரவு பகுப்பாய்வு**: 'கிடைக்கக்கூடிய தரவுத்தொகுப்புகள்'\n"
                f"• 📝 **வரைவு தயாரிப்பு**: 'அறிவிப்பு கடிதம் தயாரிப்பது எப்படி?'\n\n"
                f"நீங்கள் குரல் மூலமாகவோ அல்லது தட்டச்சு செய்தோ கேட்கலாம்!"
            )
            blocks.append({"type": "markdown", "content": reply_tamil})
            actions.append({"label": "மனுக்கள் நிலவரம்", "action": "ASK_STATUS"})
            actions.append({"label": "தரவுத்தொகுப்புகள்", "action": "ASK_DATASETS"})

        log_audit("CHAT_QUERY", "OFFICER", "SUCCESS", f"Query: {req.message[:50]}")
        
    except Exception as e:
        blocks.append({
            "type": "markdown",
            "content": f"வணக்கம்! உங்கள் செய்தி பெறப்பட்டது: \"{req.message}\". ஈரோடு ஆட்சியரக AI உதவியாளரிடம் கேட்கப்பட்ட கேள்வி செயலாக்கப்பட்டது."
        })
    finally:
        conn.close()

    return {
        "message_id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "blocks": blocks,
        "actions": actions,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/document/upload")
async def upload_document(file: UploadFile = File(...)):
    """Document summarization upload — stub."""
    return {
        "document_id": f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "file_name": file.filename,
        "status": "processing",
        "message": "ஆவண சுருக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }


@app.get("/api/document/{doc_id}/summary")
async def get_document_summary(doc_id: str):
    """Document summary retrieval — stub."""
    return {
        "document_id": doc_id,
        "status": "pending",
        "message": "ஆவண சுருக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }


@app.post("/api/content/generate")
async def generate_content(req: ContentGenerateRequest):
    """Official content generation — stub."""
    return {
        "template_type": req.template_type,
        "status": "pending",
        "message": "அலுவலக உள்ளடக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }


# ---------------------------------------------------------------------------
# Module 2 Router Mounting & Chart Direct File Serving
# ---------------------------------------------------------------------------
from modules.data_viz.router import router as data_viz_router

app.include_router(data_viz_router)

# Also expose v1 alias (/api/data/*) for frontend compatibility
app.include_router(data_viz_router, prefix="")


@app.get("/outputs/charts/{chart_name}")
@app.get("/api/outputs/charts/{chart_name}")
async def serve_chart_output(chart_name: str):
    """Serve rendered chart PNG directly from outputs/charts directory."""
    chart_path = config.OUTPUTS_CHARTS_DIR / chart_name
    if not chart_path.exists() and not chart_name.endswith('.png'):
        chart_path = config.OUTPUTS_CHARTS_DIR / f"{chart_name}.png"
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="Chart image file not found")
    return FileResponse(path=str(chart_path), media_type="image/png")




# ---------------------------------------------------------------------------
# Startup & Shutdown with background FileSystemWatcher
# ---------------------------------------------------------------------------
_watcher = None

@app.on_event("startup")
async def startup_event():
    global _watcher
    init_db()
    
    # Start background file watcher so scans are automatically processed
    try:
        from pipeline.ingestion import FileSystemWatcher
        pipeline = get_pipeline()
        
        def on_new_scan(source_id: str, dest_path: Path):
            pipeline.process_source(source_id, file_path=dest_path)
            
        _watcher = FileSystemWatcher(callback=on_new_scan)
        _watcher.start()
    except Exception as e:
        print(f"Warning: Could not start background watcher: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global _watcher
    if _watcher:
        try:
            _watcher.stop()
        except Exception:
            pass

