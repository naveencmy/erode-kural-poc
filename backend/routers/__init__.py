"""API Routers — Domain-separated FastAPI route definitions.

Each router handles a specific functional domain:
  - system:  Application config, stats, and static asset serving
  - bulk:    Grievance workflow (ingest, list, approve, draft, export)
  - mail:    Email hub (connection test, inbox, send, sent-logs, config)
  - audit:   Immutable audit trail
  - content: Chat assistant, document summarization, content generation stubs
"""
