# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-08-21

### Added

#### Module 1: Document Summarization & Dynamic RAG
- Multi-format document ingestion (PDF, Excel, CSV, DOCX, Plain Text, Scanned Images).
- AI Content Fingerprinting via local Qwen 2.5 7B with deterministic fallback.
- Dynamic Prompt Suggestion Engine — zero-hardcoded, 100% grounded in uploaded content.
- CTR-based suggestion ranking with historical officer preference tracking.
- Anti-Hallucination Verification Barrier with fact-checking against document fingerprints.
- Multi-type executive summarization: Briefs, Allocation Tables, Policy Summaries, Action Items.

#### Module 2: Data Analytics & Interactive Visualization
- 2-Split conversational knowledge architecture (Visual Analytics + AI Knowledge Chat).
- AST-sandboxed Pandas execution engine — blocks `import`, `exec`, `eval`, `open`, `os`, `sys`.
- Five chart types: Bar, Line, Pie/Donut, Area, Scatter with Tamil administrative labels.
- High-resolution 2× DPI PNG export with clean formatting and Tamil header stamps.
- 1.5× IQR outlier and anomaly detection with Tamil explanations.
- One-click CSV data export.

#### Module 3: Official Content Generation & Template Studio
- Four official Tamil Nadu government templates: Press Release, Circular, Memorandum, Meeting Minutes.
- Inline rich text editing with real-time preview.
- Dual export: formatted `.docx` and authentic Tamil Nadu Government styled `.pdf`.
- Persistent content history with audit logging.

#### Module 4: Bulk Citizen Grievance Triage Pipeline
- Continuous hot-folder watcher for batch grievance ingestion.
- Dual-language Tesseract OCR (Tamil `tam` + English `eng`) with layout preservation.
- Deterministic Aadhaar redaction via Verhoeff checksum validation.
- Automated classification into 12 Collectorate departments with SLA tracking.
- Grounded Tamil acknowledgement letter drafting with official reference numbers.

#### Module 5: Official Mail Integration & Dispatch
- Bidirectional IMAP/SMTP email engine (NIC, Gmail, Outlook, Brevo relay).
- Inbound email ingestion directly into the Bulk Grievance Workflow queue.
- Outbound official response dispatch with TLS authentication.
- Human-in-the-loop safeguard — no autonomous email transmission.
- Full provenance logging of all sent/received emails.

#### Module 6: Immutable Security & Audit Trail
- SHA-256 cryptographic provenance for all ingested files and generated outputs.
- SQL & Pandas code provenance drawer with inspectable execution statements.
- Confidence scoring engine (High ≥ 0.85, Medium 0.60–0.84, Low < 0.60).

#### Infrastructure
- FastAPI backend with Uvicorn ASGI server.
- React 19 + Vite 8.2 frontend SPA.
- SQLite persistence with automatic schema migrations.
- ChromaDB vector store for semantic retrieval.
- Zustand global state management.
- Tamil-first bilingual UI with i18next localization.
- Tamil Nadu Government theme system (saffron/gold header, official seal).
- Automated test suite: 47+ tests across 6 test modules.

### Security
- 100% air-gapped local-first architecture — zero cloud dependencies.
- AST execution sandbox prevents remote code execution.
- Aadhaar PII redaction compliant with Indian data protection norms.
- Officer-gated outbound communications.
