"""Content Router — Chat assistant, document summarization, and content generation stubs."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from modules.official_content.generator import OfficialContentGenerator
from modules.official_content.exporter import export_to_docx, export_to_pdf
from pipeline.database import (
    save_official_content,
    list_official_content,
    get_official_content,
    update_content_docx_path,
    log_audit,
)

logger = logging.getLogger("ContentRouter")
router = APIRouter(tags=["Module 3 - Official Content"])
_generator = OfficialContentGenerator()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    officer_id: str
    source_id: Optional[str] = None
    context: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    template_type: str
    fields: Dict[str, Any]
    officer_id: str


from pipeline.rag_engine import CollectorateRAGEngine

rag_engine = CollectorateRAGEngine()


# ---------------------------------------------------------------------------
# Official Content Generation endpoints
# ---------------------------------------------------------------------------

@router.post("/api/content/generate")
async def generate_content(req: ContentGenerateRequest):
    """
    Generate and persist an official Tamil Nadu government document from the submitted request.
    
    Parameters:
    	req (ContentGenerateRequest): Request containing the template type, subject and details, and officer identifier.
    
    Returns:
    	dict: Generated document identifiers, metadata, text, source, and success message.
    
    Raises:
    	HTTPException: With status 422 for missing subjects, unsupported template types, or generation validation errors; with status 500 for unexpected failures.
    """
    subject = req.fields.get("subject", "").strip()
    details = req.fields.get("details", "").strip()

    if not subject:
        raise HTTPException(status_code=422, detail="Subject is required.")

    valid_types = ["press_release", "circular", "memo", "meeting_minutes"]
    if req.template_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid template_type. Must be one of: {valid_types}",
        )

    try:
        result = _generator.generate(
            template_type=req.template_type,
            subject=subject,
            details=details,
            officer_id=req.officer_id,
        )

        # Persist to DB
        save_official_content(
            content_id=result["content_id"],
            template_type=result["template_type"],
            ref_number=result["ref_number"],
            subject=result["subject"],
            details=result["details"],
            generated_text=result["generated_text"],
            content_body=result["content_body"],
            officer_id=result["officer_id"],
            source=result["source"],
        )

        # Audit log
        try:
            log_audit(
                source_id=None,
                action="CONTENT_GENERATED",
                officer_id=req.officer_id,
                details=f"Template: {req.template_type} | Ref: {result['ref_number']} | Subject: {subject[:80]}",
            )
        except Exception:
            pass  # Audit failure must not block generation

        return {
            "status": "success",
            "content_id": result["content_id"],
            "ref_number": result["ref_number"],
            "template_type": result["template_type"],
            "template_title_ta": result["template_title_ta"],
            "template_title_en": result["template_title_en"],
            "subject": result["subject"],
            "generated_text": result["generated_text"],
            "date_display": result["date_display"],
            "officer_id": result["officer_id"],
            "source": result["source"],
            "message": f"ஆவணம் வெற்றிகரமாக உருவாக்கப்பட்டது — {result['ref_number']}",
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Content generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


@router.get("/api/content/history")
async def get_content_history(officer_id: Optional[str] = None, limit: int = 20):
    """
    List previously generated official content documents.
    
    Parameters:
        officer_id (Optional[str]): Restricts results to content created by the specified officer.
        limit (int): Maximum number of records to return.
    
    Returns:
        A dictionary containing the result status, record count, and content items.
    """
    records = list_official_content(officer_id=officer_id, limit=limit)
    return {"status": "success", "count": len(records), "items": records}


class CustomExportRequest(BaseModel):
    custom_text: Optional[str] = None


@router.get("/api/content/{content_id}/export-docx")
@router.post("/api/content/{content_id}/export-docx")
async def export_content_docx(content_id: str, req: Optional[CustomExportRequest] = None):
    """Export a generated content record as a formatted DOCX file.
    
    Parameters:
        content_id (str): Identifier of the content record to export.
        req (Optional[CustomExportRequest]): Optional replacement text for the exported document.
    
    Returns:
        FileResponse: The generated DOCX file.
    """
    record = get_official_content(content_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found.")

    try:
        body = req.custom_text if (req and req.custom_text) else record["content_body"]
        content_data = {
            "content_id": record["content_id"],
            "template_type": record["template_type"],
            "template_title_ta": _get_title(record["template_type"], "ta"),
            "template_title_en": _get_title(record["template_type"], "en"),
            "ref_number": record["ref_number"],
            "subject": record["subject"],
            "content_body": body,
            "officer_id": record["officer_id"],
            "date_display": datetime.fromisoformat(record["created_at"]).strftime("%d-%m-%Y"),
        }

        docx_path = export_to_docx(content_data)
        update_content_docx_path(content_id, str(docx_path))

        filename = f"{record['ref_number'].replace('/', '_')}_{record['template_type']}.docx"

        try:
            log_audit(
                source_id=None,
                action="CONTENT_EXPORTED_DOCX",
                officer_id=record["officer_id"],
                details=f"Ref: {record['ref_number']} exported as DOCX",
            )
        except Exception:
            pass

        return FileResponse(
            path=str(docx_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"DOCX export failed for {content_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DOCX export failed: {str(e)}")


@router.get("/api/content/{content_id}/export-pdf")
@router.post("/api/content/{content_id}/export-pdf")
async def export_content_pdf(content_id: str, req: Optional[CustomExportRequest] = None):
    """Export a generated content record as a formatted PDF file.
    
    Parameters:
        content_id (str): Identifier of the content record to export.
        req (Optional[CustomExportRequest]): Optional replacement text for the exported document.
    
    Returns:
        FileResponse: The generated PDF file.
    """
    record = get_official_content(content_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found.")

    try:
        body = req.custom_text if (req and req.custom_text) else record["content_body"]
        content_data = {
            "content_id": record["content_id"],
            "template_type": record["template_type"],
            "template_title_ta": _get_title(record["template_type"], "ta"),
            "template_title_en": _get_title(record["template_type"], "en"),
            "ref_number": record["ref_number"],
            "subject": record["subject"],
            "content_body": body,
            "officer_id": record["officer_id"],
            "date_display": datetime.fromisoformat(record["created_at"]).strftime("%d-%m-%Y"),
        }

        pdf_path = export_to_pdf(content_data)
        filename = f"{record['ref_number'].replace('/', '_')}_{record['template_type']}.pdf"

        try:
            log_audit(
                source_id=None,
                action="CONTENT_EXPORTED_PDF",
                officer_id=record["officer_id"],
                details=f"Ref: {record['ref_number']} exported as PDF",
            )
        except Exception:
            pass

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"PDF export failed for {content_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


def _get_title(template_type: str, lang: str) -> str:
    """Return the localized title for a content template, falling back to its template type.
    
    Parameters:
        template_type (str): Identifier of the content template.
        lang (str): Language code used to select the localized title.
    
    Returns:
        str: The localized template title or the template type when no title is available.
    """
    from modules.official_content.templates import TEMPLATE_REGISTRY
    entry = TEMPLATE_REGISTRY.get(template_type, {})
    return entry.get(f"title_{lang}", template_type)


# ---------------------------------------------------------------------------
# Chat & Document stubs (unchanged)
# ---------------------------------------------------------------------------

@router.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Processes a chat request and returns workflow status information with retrieved source metadata.
    
    Parameters:
    	req (ChatRequest): Chat message, officer identifier, optional source identifier, and context.
    
    Returns:
    	dict: A response containing a timestamp-based message ID, source metadata, engine information, and a Tamil status message.
    """
    result = rag_engine.query(
        message=req.message,
        officer_id=req.officer_id,
        source_id=req.source_id,
        context=req.context,
    )
    return {
        "message_id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "sources": result.get("sources", []),
        "engine": result.get("engine", "RAG"),
        "blocks": [
            {
                "type": "text",
                "content": f"வணக்கம்! உங்கள் செய்தி பெறப்பட்டது: \"{req.message}\". "
                           "தற்போது மொத்த பணிப்பாய்வு (Bulk Workflow) தொகுதி முழுமையாக இயங்குகிறது. "
                           "மற்ற தொகுதிகள் இணைக்கப்பட்டு வருகின்றன.",
            },
        ],
    }


@router.post("/api/document/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Accepts a document upload and marks it for processing.
    
    Parameters:
    	file (UploadFile): The document uploaded for processing.
    
    Returns:
    	dict: The generated document identifier, original filename, processing status, and pending summarization message.
    """
    return {
        "document_id": f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "file_name": file.filename,
        "status": "processing",
        "message": "ஆவண சுருக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }


@router.get("/api/document/{doc_id}/summary")
async def get_document_summary(doc_id: str):
    """Return the pending summary status for a document.
    
    Parameters:
        doc_id (str): Identifier of the document whose summary is requested.
    
    Returns:
        dict: Document identifier, pending status, and a message indicating that summarization is not yet available.
    """
    return {
        "document_id": doc_id,
        "status": "pending",
        "message": "ஆவண சுருக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }


@router.post("/api/content/generate")
async def generate_content(req: ContentGenerateRequest):
    """Official content generation — stub."""
    return {
        "template_type": req.template_type,
        "status": "pending",
        "message": "அலுவலக உள்ளடக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }
