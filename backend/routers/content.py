"""Content Router — Chat assistant and official content generation."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
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
from pipeline.rag_engine import CollectorateRAGEngine

logger = logging.getLogger("ContentRouter")
router = APIRouter(tags=["Module 3 - Official Content"])
_generator = OfficialContentGenerator()
rag_engine = CollectorateRAGEngine()


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


class CustomExportRequest(BaseModel):
    custom_text: Optional[str] = None


# ---------------------------------------------------------------------------
# Official Content Generation endpoints
# ---------------------------------------------------------------------------

@router.post("/api/content/generate")
async def generate_content(req: ContentGenerateRequest):
    """Generate an official Tamil Nadu government document."""
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

    language = req.fields.get("language")
    try:
        result = _generator.generate(
            template_type=req.template_type,
            subject=subject,
            details=details,
            officer_id=req.officer_id,
            language=language,
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
    """List previously generated official content documents."""
    records = list_official_content(officer_id=officer_id, limit=limit)
    return {"status": "success", "count": len(records), "items": records}


@router.get("/api/content/{content_id}/export-docx")
@router.post("/api/content/{content_id}/export-docx")
async def export_content_docx(content_id: str, req: Optional[CustomExportRequest] = None):
    """Export a generated content document as a formatted .docx file."""
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
    """Export a generated content document as a formatted official .pdf file."""
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


@router.post("/api/content/attach-file")
async def attach_content_reference_file(
    file: UploadFile = File(...),
    officer_id: str = "OFFICER",
):
    """Attach any format reference file (PDF, Word, Excel, CSV, Image, TXT, etc.) for official content generation."""
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        import hashlib
        import config
        from modules.document_summary.extractor import ContentExtractor
        
        hasher = hashlib.sha256(content_bytes)
        source_id = f"ref_{hasher.hexdigest()[:12]}"
        clean_name = Path(file.filename or "reference_document").name
        dest_path = config.UPLOADS_DOCUMENTS_DIR / f"{source_id}_{clean_name}"
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content_bytes)

        extractor = ContentExtractor()
        extracted = extractor.extract(dest_path)
        raw_text = extracted.get("text", "").strip()

        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        suggested_subject = lines[0][:100] if lines else clean_name.rsplit(".", 1)[0]
        suggested_details = "\n".join(lines[:12]) if len(lines) > 1 else raw_text[:800]

        return {
            "status": "success",
            "file_name": file.filename,
            "file_size": len(content_bytes),
            "file_type": extracted.get("file_type", "unknown"),
            "suggested_subject": suggested_subject,
            "extracted_text": raw_text[:3000],
            "suggested_details": suggested_details,
        }
    except Exception as e:
        logger.error(f"Reference file extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File extraction failed: {str(e)}")


def _get_title(template_type: str, lang: str) -> str:
    from modules.official_content.templates import TEMPLATE_REGISTRY
    entry = TEMPLATE_REGISTRY.get(template_type, {})
    return entry.get(f"title_{lang}", template_type)



# ---------------------------------------------------------------------------
# General Assistant Chat (RAG Engine)
# ---------------------------------------------------------------------------

@router.post("/api/chat")
async def chat(req: ChatRequest):
    """General assistant chat backed by Collectorate RAG and Ollama LLM."""
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
                "content": result.get("answer", "தகவல் செயலாக்க முடியவில்லை."),
            },
        ],
    }
