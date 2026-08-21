"""Erode Collectorate AI System — FastAPI Application Factory.

Slim entrypoint that mounts all domain-specific routers and middleware.
Run via:  uvicorn server:app --reload --host 0.0.0.0 --port 8000
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.database import init_db

# ---------------------------------------------------------------------------
# Lifespan — Startup / Shutdown hooks
# ---------------------------------------------------------------------------
_watcher = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan: initialise DB and start background file watcher on startup."""
    global _watcher
    init_db()

    # Start background file watcher for auto-processing scanned documents
    try:
        from pipeline.ingestion import FileSystemWatcher
        from routers.bulk import get_pipeline

        pipeline = get_pipeline()

        def on_new_scan(source_id: str, dest_path: Path):
            pipeline.process_source(source_id, file_path=dest_path)

        _watcher = FileSystemWatcher(callback=on_new_scan)
        _watcher.start()
    except Exception as e:
        print(f"Warning: Could not start background watcher: {e}")

    yield  # Application is running

    # Shutdown
    if _watcher:
        try:
            _watcher.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Erode Collectorate AI System API",
    version="1.0.0",
    description="REST API for the Erode District Collectorate AI-Powered Administrative Assistant",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount Domain Routers
# ---------------------------------------------------------------------------
from routers.system import router as system_router
from routers.bulk import router as bulk_router
from routers.mail import router as mail_router
from routers.audit import router as audit_router
from routers.content import router as content_router
from modules.data_viz.router import router as data_viz_router
from modules.document_summary.router import router as document_summary_router

app.include_router(system_router)
app.include_router(bulk_router)
app.include_router(mail_router)
app.include_router(audit_router)
app.include_router(content_router)
app.include_router(data_viz_router)
app.include_router(document_summary_router)

# Also expose v1 alias (/api/data/*) for frontend compatibility
app.include_router(data_viz_router, prefix="")
