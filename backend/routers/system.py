"""System Router — Application config, dashboard stats, and chart file serving."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

import config
from pipeline.database import get_db_connection

router = APIRouter(tags=["System"])


@router.get("/api/config")
async def get_app_config():
    """Return application configuration. Frontend fetches dynamic config from here."""
    return {
        "departments": config.DEPARTMENTS,
        "priority_levels": config.PRIORITY_LEVELS,
        "dev_mode": config.DEV_MODE,
        "ollama_model": config.OLLAMA_MODEL,
        "database": str(config.DATABASE_PATH.name),
        "ocr_engine": "Indic-OCR (Transformer)",
        "version": "1.0.0",
    }


@router.get("/api/stats")
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


@router.get("/outputs/charts/{chart_name}")
@router.get("/api/outputs/charts/{chart_name}")
async def serve_chart_output(chart_name: str):
    """Serve rendered chart PNG directly from outputs/charts directory."""
    chart_path = config.OUTPUTS_CHARTS_DIR / chart_name
    if not chart_path.exists() and not chart_name.endswith('.png'):
        chart_path = config.OUTPUTS_CHARTS_DIR / f"{chart_name}.png"
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="Chart image file not found")
    return FileResponse(path=str(chart_path), media_type="image/png")
