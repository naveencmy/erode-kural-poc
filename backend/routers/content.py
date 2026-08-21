"""Content Router — Chat assistant and content generation stubs."""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Content & Chat"])


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
# Endpoints
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


@router.post("/api/content/generate")
async def generate_content(req: ContentGenerateRequest):
    """Official content generation — stub."""
    return {
        "template_type": req.template_type,
        "status": "pending",
        "message": "அலுவலக உள்ளடக்க தொகுதி விரைவில் இணைக்கப்படும்.",
    }
