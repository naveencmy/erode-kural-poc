"""Audit Router — Immutable audit trail endpoint."""

from fastapi import APIRouter, Query

from pipeline.database import get_db_connection

router = APIRouter(tags=["Audit"])


@router.get("/api/audit")
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
