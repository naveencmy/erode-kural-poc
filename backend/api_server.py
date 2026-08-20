"""Backward-compatible re-export — Application has moved to server.py.

This shim ensures existing imports like `from api_server import app`
and `uvicorn api_server:app` continue to work.
"""

from server import app  # noqa: F401
