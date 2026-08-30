"""Master Entrypoint for Erode District Collectorate AI System."""

import argparse
import logging
import sys

import config
from pipeline.database import init_db
from server import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CollectorateMain")


def run_api(port: int = 8000):
    """Launch FastAPI REST API server for React frontend."""
    import uvicorn
    logger.info(f"Starting FastAPI API Server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)


def run_ui():
    """Launch Streamlit Operator Cockpit."""
    import subprocess
    app_path = config.BASE_DIR / "streamlit_ui" / "app.py"
    logger.info(f"Launching Streamlit Cockpit: {app_path}")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port=8501", "--server.headless=true"])


def run_all(port: int = 8000):
    """Initialize DB and start FastAPI backend server."""
    logger.info("Initializing SQLite DB schema...")
    init_db()
    logger.info(f"Starting Backend API on port {port}...")
    run_api(port=port)


def main():
    parser = argparse.ArgumentParser(description="Erode District Collectorate AI System")
    parser.add_argument(
        "--mode",
        choices=["ui", "api", "all"],
        default="api",
        help="Execution mode (default: api)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for API server (default: 8000)")
    args = parser.parse_args()

    init_db()

    if args.mode in ("api", "all"):
        run_all(port=args.port)
    else:
        run_ui()


if __name__ == "__main__":
    main()
