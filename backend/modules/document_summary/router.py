"""REST API Router for Module 1 — Document Summarization and Dynamic Prompt Suggestions."""

import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

import config
from modules.document_summary.extractor import ContentExtractor, detect_file_type
from modules.document_summary.fingerprinter import ContentFingerprinter
from modules.document_summary.suggestion_engine import DynamicSuggestionEngine
from modules.document_summary.summarizer import DocumentSummarizer
from pipeline.database import (
    approve_document_summary,
    get_content_fingerprint,
    get_document_summary,
    get_prompt_suggestions,
    get_source,
    list_document_summaries,
    log_audit,
    record_source,
    record_suggestion_click,
    save_content_fingerprint,
    save_ocr_results,
)

logger = logging.getLogger("DocumentSummaryRouter")

router = APIRouter(prefix="/api/v1", tags=["Module 1: Document Summarization & Suggestions"])

# Initialize singletons
extractor = ContentExtractor()
fingerprinter = ContentFingerprinter()
suggestion_engine = DynamicSuggestionEngine()
summarizer = DocumentSummarizer()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class SummarizeRequest(BaseModel):
    summary_type: str = "executive"  # executive | department | policy | action_points
    officer_id: str = "OFFICER"


class SuggestionsGenerateRequest(BaseModel):
    source_id: str
    module_context: str = "document"  # document | data_viz | general_assistant | content_gen
    officer_id: str = "OFFICER"


class SuggestionClickRequest(BaseModel):
    clicked: bool = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/document/upload")
async def api_upload_and_analyze_document(
    file: UploadFile = File(...),
    officer_id: str = "OFFICER",
):
    """Upload PDF, Excel, Image, CSV, or DOCX document and automatically produce an AI content fingerprint."""
    try:
        # Read file bytes & compute sha256
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="வெற்று கோப்பு பதிவேற்றப்பட்டது (Empty file uploaded)")

        hasher = hashlib.sha256(content_bytes)
        source_id = f"doc_{hasher.hexdigest()[:14]}"

        # Save to documents upload folder
        clean_name = Path(file.filename or "document.pdf").name
        dest_path = config.UPLOADS_DOCUMENTS_DIR / f"{source_id}_{clean_name}"
        with open(dest_path, "wb") as f:
            f.write(content_bytes)

        # Record in sources table with absolute path
        record_source(
            source_id=source_id,
            source_type="scan" if any(dest_path.suffix.lower().endswith(x) for x in ["png", "jpg", "jpeg", "pdf"]) else "email",
            raw_path=str(dest_path.resolve()),
            status="pending",
            assigned_officer=officer_id,
        )

        # 1. Structure extraction
        extracted = extractor.extract(dest_path)

        # Persist extracted text in ocr_results table for instant context retrieval
        ext_text = (extracted.get("text") or "").strip()
        save_ocr_results(
            source_id=source_id,
            page_number=1,
            full_text=ext_text,
            blocks_json=json.dumps(extracted.get("blocks", [])),
            avg_confidence=0.95,
            ocr_engine="extractor",
        )

        # 2. Content fingerprinting (AI-driven)
        fingerprint = fingerprinter.fingerprint(extracted)

        # 3. Store fingerprint in sources & cache table
        save_content_fingerprint(
            source_id=source_id,
            fingerprint=fingerprint,
            file_type=extracted.get("file_type", "unknown"),
            content_type=fingerprint.get("content_type", "general"),
        )

        # 4. Generate initial suggestions preview
        sug_res = suggestion_engine.generate(
            source_id=source_id,
            module_context="document",
            officer_id=officer_id,
        )
        suggestions = sug_res.get("suggestions", [])

        log_audit(
            source_id=source_id,
            action="DOCUMENT_UPLOADED",
            officer_id=officer_id,
            details=f"Uploaded {file.filename} (Type: {extracted.get('file_type')}, Content: {fingerprint.get('content_type')})",
        )

        return {
            "status": "analyzed",
            "source_id": source_id,
            "file_name": file.filename,
            "file_type": extracted.get("file_type", "unknown"),
            "detected_language": "ta",
            "page_count": extracted.get("page_count", 1),
            "fingerprint": fingerprint,
            "suggestions": suggestions,
            "suggestions_preview": len(suggestions),
        }

    except Exception as e:
        logger.exception("Upload and analysis failed")
        raise HTTPException(status_code=500, detail=f"ஆவண பகுப்பாய்வு தோல்வி: {str(e)}")


@router.post("/document/{source_id}/summarize")
async def api_summarize_document(
    source_id: str,
    req: SummarizeRequest = SummarizeRequest(),
):
    """Generate structured multi-type document summary with page citations and hallucination scoring."""
    try:
        res = summarizer.summarize(
            source_id=source_id,
            summary_type=req.summary_type,
            officer_id=req.officer_id,
        )
        return res
    except Exception as e:
        logger.exception("Summarization failed")
        raise HTTPException(status_code=500, detail=f"சுருக்கம் தயாரித்தல் தோல்வி: {str(e)}")


@router.get("/document/{source_id}/summary/{summary_id}")
async def api_get_document_summary(source_id: str, summary_id: str):
    """Retrieve single document summary by summary_id."""
    summary = get_document_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="சுருக்கம் கிடைக்கவில்லை (Summary not found)")
    return summary


@router.get("/document/{source_id}/summaries")
async def api_list_document_summaries(source_id: str):
    """Retrieve all generated summaries for a document."""
    summaries = list_document_summaries(source_id)
    return {"source_id": source_id, "count": len(summaries), "summaries": summaries}


@router.post("/document/{source_id}/summary/{summary_id}/approve")
async def api_approve_document_summary(
    source_id: str,
    summary_id: str,
    officer_id: str = "OFFICER",
):
    """Approve a document summary for official filing."""
    success = approve_document_summary(summary_id, officer_id=officer_id)
    if not success:
        raise HTTPException(status_code=404, detail="சுருக்கம் புதுப்பிக்க முடியவில்லை")

    log_audit(
        source_id=source_id,
        action="DOCUMENT_SUMMARY_APPROVED",
        officer_id=officer_id,
        details=f"Summary {summary_id} approved by {officer_id}",
    )
    return {"status": "success", "message": "சுருக்கம் வெற்றிகரமாக அங்கீகரிக்கப்பட்டது"}


@router.post("/suggestions/generate")
async def api_generate_dynamic_suggestions(req: SuggestionsGenerateRequest):
    """Generate dynamic context-aware prompt suggestions with zero hardcoding."""
    try:
        res = suggestion_engine.generate(
            source_id=req.source_id,
            module_context=req.module_context,
            officer_id=req.officer_id,
        )
        return res
    except Exception as e:
        logger.exception("Suggestion generation failed")
        raise HTTPException(status_code=500, detail=f"பரிந்துரை உருவாக்கம் தோல்வி: {str(e)}")


@router.get("/suggestions")
async def api_get_dynamic_suggestions(
    source_id: str = Query(..., description="Document source_id"),
    module_context: str = Query("document", description="Module tab context"),
    officer_id: str = Query("OFFICER", description="Officer ID"),
):
    """Fetch or dynamically generate suggestions for a given source and context."""
    res = suggestion_engine.generate(
        source_id=source_id,
        module_context=module_context,
        officer_id=officer_id,
    )
    return res


@router.post("/suggestions/{suggestion_id}/click")
async def api_track_suggestion_click(
    suggestion_id: str,
    req: SuggestionClickRequest = SuggestionClickRequest(),
):
    """Record an officer click on a prompt suggestion to adapt personalization CTR ranking."""
    success = record_suggestion_click(suggestion_id)
    return {
        "status": "success" if success else "not_found",
        "suggestion_id": suggestion_id,
        "is_clicked": True,
    }
