"""Content Router — Chat assistant, document summarization, and content generation stubs."""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

router = APIRouter(tags=["Content & Chat"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    officer_id: str
    context: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    template_type: str
    fields: Dict[str, Any]
    officer_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/api/chat")
async def chat(req: ChatRequest):
    """General assistant chat — stub, ready for Ollama connection."""
    return {
        "message_id": f"msg_{datetime.now().strftime('%Y%m%d%H%M%S')}",
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
    """Document summarization upload — stub."""
    return {
        "document_id": f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "file_name": file.filename,
        "status": "processing",
        "message": "ஆவண சுருக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }


@router.get("/api/document/{doc_id}/summary")
async def get_document_summary(doc_id: str):
    """Document summary retrieval — stub."""
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
