# 🏛️ Erode District Collectorate - Bulk Workflow Automation Module V0.1

**Production-Grade Ingestion, Indic OCR, Tamil Entity Extraction, Rule/LLM Classifier & Anti-Hallucination Drafting System**

Developed for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியரகம்), Tamil Nadu to process high-volume citizen grievance petitions originating from Government NIC Email (`imap.nic.in:993`) and physical scanned paper petitions (`uploads/scanned/`).

---

## 🏗️ Architecture & Component Overview

```text
bulk_workflow_v01/
├── main.py                     # Master CLI & Service Orchestrator
├── config.py                   # Environment variables, directory paths & thresholds
├── pipeline/
│   ├── __init__.py             # Public symbols & pipeline exports
│   ├── database.py             # SQLite persistence, schema initialization & audit log
│   ├── ingestion.py            # IMAP poller with last_uid cursor & Watchdog folder monitor
│   ├── ocr_engine.py           # 300 DPI PDF conversion, OpenCV deskew (>2°), Indic OCR & Glossary check
│   ├── extraction.py           # Deterministic Tamil regex extractor, Aadhaar redactor & Master locations lookup
│   ├── classification.py       # Tamil keyword rule engine + Guarded Ollama (qwen2.5:7b) fallback
│   ├── generation.py           # Jinja2 deterministic draft generator with [தகவல் இல்லை] enforcement
│   └── orchestrator.py         # End-to-end multi-stage pipeline coordinator
├── templates/
│   ├── ack_revenue_tamil.txt   # Official Tamil Nadu Revenue Department acknowledgment template
│   ├── ack_social_tamil.txt    # Official Social Welfare & Pension acknowledgment template
│   └── ack_general_tamil.txt   # Official General Public Works & Police acknowledgment template
├── data/
│   ├── tamil_govt_glossary.txt # Authoritative Collectorate administrative Tamil glossary
│   ├── master_locations.db     # SQLite lookup database of all Erode Taluks and Revenue Villages
│   └── build_master_locations.py # Script to rebuild master locations database
├── streamlit_ui/
│   ├── __init__.py
│   └── app.py                  # 5-Tab Operator & Debug Cockpit
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py        # 17 automated unit and end-to-end pytest cases
├── requirements.txt            # Python dependencies
├── README.md                   # System documentation
└── HANDOFF.md                  # Deployment SOP, Ollama flags & performance parameters
```

---

## 🔒 Non-Negotiable Engineering Contracts Fulfilled

1. **Zero Mock / Synthetic Data**: Every record originates from real `.eml` raw payloads, local scanned documents, or live SQLite database queries.
2. **Anti-Hallucination Protocol**: Strict deterministic Jinja2 substitution. Any missing or unverified entity field automatically renders as `[தகவல் இல்லை]`.
3. **Data Privacy Compliance**: Aadhaar numbers (`\d{4}\s?\d{4}\s?\d{4}`) are automatically detected, masked, and stored as `[Aadhaar Redacted]`.
4. **Flow-State Resilience**: IMAP uses `last_uid` checkpointing in SQLite with `BODY.PEEK[]` (`mark_seen=False`). Directory watcher runs via `watchdog` with zero file loss.

---

## 🚀 Quick Start & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Automated Test Suite
```bash
pytest tests/test_pipeline.py -v
```

### 3. Launch Operator Cockpit (Streamlit Dashboard)
```bash
python main.py --mode ui
# or
streamlit run streamlit_ui/app.py
```

### 4. Background Ingestion Worker
```bash
python main.py --mode worker
```

### 5. Ingest Sample Real Petitions & Process All
```bash
python main.py --mode ingest-sample
python main.py --mode process-all
```

---

## 🖥️ 5-Tab Operator Cockpit Features

1. **Tab 1 — Ingestion Monitor (வரவு கண்காணிப்பு)**: Live IMAP `last_uid` cursor status, queue folder counts, manual IMAP fetch trigger, and instant document drag-and-drop ingestion.
2. **Tab 2 — OCR Review (எழுத்துணரி பார்வை)**: Dual-column document viewer with side-by-side raw scan and Tamil text, highlighting low-confidence tokens (`< 0.85`) with `[?]` badges.
3. **Tab 3 — Processing Queue (செயலாக்க வரிசை)**: Searchable, filterable queue with department, priority, and status filters. Includes extracted entity tables and officer **Approve** / **Reject** action buttons.
4. **Tab 4 — Live Analytics (நேரலை பகுப்பாய்வு)**: Real-time native charts generated straight from SQLite queries displaying workload by department, priority distribution, and Rule vs AI ratio.
5. **Tab 5 — Audit Log (தணிக்கை பதிவு)**: Immutable, append-only audit trail recording every ingestion, OCR run, extraction, classification, draft creation, and officer approval, with CSV export.
