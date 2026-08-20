"""Erode District Collectorate - Bulk Workflow Automation Module V0.2 Cockpit.

Featuring Grounded Drafting, Grounding Inspector, Verhoeff Validation, Sequence Counters,
Inline OCR Corrections, DOCX Export, Windows Keyring IMAP, and Guarded Bulk Approvals.
"""

import html
import importlib
import io
import json
import os
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config
importlib.reload(config)

import pipeline.database
import pipeline.extraction
import pipeline.generation
import pipeline.ingestion
import pipeline.orchestrator
import pipeline

importlib.reload(pipeline.database)
importlib.reload(pipeline.extraction)
importlib.reload(pipeline.generation)
importlib.reload(pipeline.ingestion)
importlib.reload(pipeline.orchestrator)
importlib.reload(pipeline)

from pipeline.database import (
    generate_department_file_number,
    get_db_connection,
    get_imap_cursor,
    get_source_details,
    init_db,
    log_audit,
    save_draft,
    update_draft_approval,
    update_imap_cursor,
    update_source_status,
)
from pipeline.generation import TamilDraftGenerator, export_draft_to_docx
from pipeline.ingestion import (
    IMAPPoller,
    compute_file_sha256,
    get_stored_imap_password,
    process_file_path,
    process_raw_email,
    set_stored_imap_password,
    test_imap_connection,
)
from pipeline.orchestrator import WorkflowPipeline

# Page setup
st.set_page_config(
    page_title="Erode Collectorate - Bulk Workflow Automation V0.2",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB on load
init_db()

pipeline = WorkflowPipeline()

# Custom SVG & Theme Styling
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 20px 24px;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        color: #ffffff;
        font-size: 26px;
        margin: 0;
        padding-bottom: 5px;
    }
    .main-header p {
        color: #d1e3ff;
        font-size: 14px;
        margin: 0;
    }
    .result-card {
        background: #f8fafc;
        border-left: 5px solid #1e3c72;
        padding: 18px;
        border-radius: 6px;
        margin-top: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .low-conf-word {
        background-color: #ffd166;
        color: #1a1a1a;
        border: 1px solid #e09f3e;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 700;
    }
    .normal-word {
        color: #f8fafc;
    }
    .ocr-text-box {
        border: 1px solid #334155;
        padding: 18px;
        border-radius: 6px;
        background-color: #0f172a;
        color: #f8fafc;
        font-size: 15px;
        line-height: 1.8;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    /* Grounding Inspector Styles */
    .grounding-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 15px;
    }
    .grounding-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
        margin-bottom: 8px;
        border-radius: 6px;
        background: #0f172a;
        border: 1px solid #334155;
    }
    .grounded-line-green {
        border-left: 4px solid #10b981;
        padding-left: 12px;
        margin-bottom: 6px;
        background: rgba(16, 185, 129, 0.08);
        border-radius: 0 4px 4px 0;
    }
    .grounded-line-yellow {
        border-left: 4px solid #f59e0b;
        padding-left: 12px;
        margin-bottom: 6px;
        background: rgba(245, 158, 11, 0.08);
        border-radius: 0 4px 4px 0;
    }
    .grounded-line-red {
        border-left: 4px solid #ef4444;
        padding-left: 12px;
        margin-bottom: 6px;
        background: rgba(239, 68, 68, 0.12);
        border-radius: 0 4px 4px 0;
    }
    .grounded-line-template {
        padding-left: 12px;
        margin-bottom: 4px;
        color: #94a3b8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def svg_badge(badge_type: str, label: str = "") -> str:
    """Generate clean SVG vector badges for Grounding and Status."""
    if badge_type == "GROUNDED":
        txt = label or "GROUNDED"
        return f"""<span style="display:inline-flex; align-items:center; gap:5px; background:#064e3b; color:#34d399; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; border:1px solid #059669;">
            <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='3'><circle cx='12' cy='12' r='10'/><path d='m9 12 2 2 4-4'/></svg> {txt}</span>"""
    elif badge_type == "INFERRED":
        txt = label or "INFERRED"
        return f"""<span style="display:inline-flex; align-items:center; gap:5px; background:#78350f; color:#fde047; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; border:1px solid #d97706;">
            <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='3'><path d='M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83'/></svg> {txt}</span>"""
    elif badge_type == "MISSING":
        txt = label or "MISSING"
        return f"""<span style="display:inline-flex; align-items:center; gap:5px; background:#7f1d1d; color:#f87171; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; border:1px solid #dc2626;">
            <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='3'><circle cx='12' cy='12' r='10'/><line x1='15' y1='9' x2='9' y2='15'/><line x1='9' y1='9' x2='15' y2='15'/></svg> {txt}</span>"""
    elif badge_type == "AUTO":
        txt = label or "AUTO-GEN"
        return f"""<span style="display:inline-flex; align-items:center; gap:5px; background:#c2410c; color:#fed7aa; padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; border:1px solid #ea580c;">
            <svg width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='3'><path d='M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'/></svg> {txt}</span>"""
    else:
        return f"""<span style="display:inline-flex; align-items:center; gap:4px; background:#334155; color:#cbd5e1; padding:2px 8px; border-radius:4px; font-weight:600; font-size:11px;">{label}</span>"""


def load_metrics():
    """Load real-time metrics directly from SQLite database."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sources")
        total_sources = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sources WHERE status = 'draft_ready'")
        draft_ready_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sources WHERE status = 'approved'")
        approved_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sources WHERE status = 'pending'")
        pending_count = cur.fetchone()[0]

        return total_sources, draft_ready_count, approved_count, pending_count
    finally:
        conn.close()


# Sidebar Navigation & Context
with st.sidebar:
    emblem_svg_path = ROOT_DIR / "streamlit_ui" / "assets" / "tn_emblem.svg"
    if emblem_svg_path.exists():
        svg_content = emblem_svg_path.read_text(encoding="utf-8")
        st.markdown(f"<div style='text-align:center; margin-bottom:10px;'>{svg_content}</div>", unsafe_allow_html=True)
    else:
        st.markdown("### 🏛️")

    st.markdown("### ஈரோடு மாவட்ட ஆட்சியரகம்")
    st.markdown("**Erode District Collectorate**  \n*Bulk Workflow Module V0.2*")
    st.divider()

    st.markdown("#### ⚙️ கணினி விவரங்கள்")
    st.markdown(f"- **LLM**: `{getattr(config, 'OLLAMA_MODEL', 'qwen2.5:7b')}`")
    st.markdown("- **OCR**: `Indic-OCR (Transformer / PyMuPDF)`")
    st.markdown(f"- **IMAP**: `{getattr(config, 'IMAP_SERVER', 'imap.nic.in')}:{getattr(config, 'IMAP_PORT', 993)}`")
    st.markdown(f"- **DB**: `{config.DATABASE_PATH.name}`")
    st.divider()

    st.markdown("#### 👤 அதிகாரி உள்நுழைவு")
    current_officer = st.text_input("அதிகாரி ஐடி (Officer ID)", value="DRO_ERODE_01")
    st.caption("All approvals, edits, and sequence generations are recorded into the SQLite audit log.")


# Top Header Banner
st.markdown(
    """
    <div class="main-header">
        <h1>🏛️ ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம் - மொத்த மனுக்கள் தானியங்கி தொகுதி</h1>
        <p>Erode Collectorate Bulk Workflow Automation System — Anti-Hallucination & Grounded Drafting V0.2</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Metric KPI Row
m_total, m_ready, m_appr, m_pend = load_metrics()
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("மொத்த மனுக்கள் (Total)", m_total)
kpi2.metric("வரைவு தயார் (Drafts Ready)", m_ready)
kpi3.metric("ஒப்புதல் பெற்றது (Approved)", m_appr)
kpi4.metric("நிலுவை (Pending Ingest)", m_pend)

st.divider()

# Tab Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 வரவு கண்காணிப்பு (Ingestion)",
    "🔍 எழுத்துணரி பார்வை (OCR Review)",
    "✍️ செயலாக்க வரிசை & வரைவு (Queue & Drafting)",
    "📊 பகுப்பாய்வு (Analytics)",
    "🛡️ தணிக்கை பதிவு (Audit Trail)",
])


# ==============================================================================
# TAB 1: INGESTION & PIPELINE TRIGGER
# ==============================================================================
with tab1:
    st.subheader("மனுக்கள் வரத்து மற்றும் உட்கொள்ளல் (Ingestion Management)")

    col_t1_l, col_t1_r = st.columns([1, 1])

    with col_t1_l:
        st.markdown("#### 📡 NIC மின்னஞ்சல் உட்கொள்ளல் முறை (IMAP Server)")
        imap_mode = st.radio(
            "உட்கொள்ளல் முறை (Ingestion Mode):",
            ["🔴 Development Mode (Local Mailbox)", "🟢 Production Mode (NIC IMAP)"],
            index=0,
        )

        if "Production" in imap_mode:
            st.info("NIC அரசு மின்னஞ்சல் சர்வர்: `imap.nic.in:993` (SSL)")
            srv = st.text_input("IMAP Server:", value=config.IMAP_SERVER)
            usr = st.text_input("Username / Email:", value=config.IMAP_USERNAME)
            pwd = st.text_input("Password (Stored in Windows Credential Manager):", type="password", value=get_stored_imap_password(usr) or "")

            col_btn_test, col_btn_save = st.columns([1, 1])
            with col_btn_save:
                if st.button("🔐 கடவுச்சொல்லைப் பாதுகாப்பாக சேமி (Save in Keyring)"):
                    if usr and pwd:
                        if set_stored_imap_password(usr, pwd):
                            st.success("கடவுச்சொல் Windows Credential Manager-ல் வெற்றிகரமாக சேமிக்கப்பட்டது.")
                    else:
                        st.warning("பயனர் பெயர் மற்றும் கடவுச்சொல்லை உள்ளிடவும்.")

            with col_btn_test:
                if st.button("🔗 இணைப்பைச் சோதி (Test IMAP Connection)"):
                    with st.spinner("Connecting to imap.nic.in:993 with SSL..."):
                        is_ok, msg, subjs = test_imap_connection(srv, 993, usr, pwd)
                        if is_ok:
                            st.success(msg)
                            if subjs:
                                st.markdown("##### 📩 அண்மைய மின்னஞ்சல்கள் (Latest Subjects):")
                                for s in subjs:
                                    st.write(f"- {s}")
                        else:
                            st.error(msg)
        else:
            st.info(f"உள்ளூர் மின்னஞ்சல் பெட்டி (`{config.UPLOADS_INCOMING_EMAILS_DIR.name}/`) கண்காணிக்கப்படுகிறது.")
            last_uid = get_imap_cursor()
            st.write(f"- **கடைசி UID Cursor:** `{last_uid}`")
            st.write(f"- **உள்ளூர் மின்னஞ்சல் கோப்புறை:** `{config.UPLOADS_INCOMING_EMAILS_DIR}`")

        if st.button("🔄 இப்போது மின்னஞ்சல்களைச் சோதி (Poll Emails Now)"):
            with st.spinner("Polling mailbox..."):
                poller = IMAPPoller()
                new_ids = poller.poll_once()
                if new_ids:
                    st.success(f"{len(new_ids)} புதிய மனுக்கள் உட்கொள்ளப்பட்டன! உடனே செயலாக்கப்படுகிறது...")
                    for sid in new_ids:
                        pipeline.process_source(sid)
                    st.rerun()
                else:
                    st.info("புதிய மின்னஞ்சல் மனுக்கள் எதுவும் வரவில்லை.")

    with col_t1_r:
        st.markdown("#### 📤 உள்ளூர் ஆவணம் பதிவேற்றம் (Manual Upload & Instant Pipeline)")
        uploaded_file = st.file_uploader(
            "மனுக்கள் (.pdf, .png, .jpg, .eml) பதிவேற்றவும்",
            type=["pdf", "png", "jpg", "jpeg", "eml", "tiff"],
        )
        if uploaded_file is not None:
            if st.button("🚀 மனுவை உடனே செயலாக்கு (Process Uploaded Document)"):
                with st.spinner("Processing through Ingestion, Indic OCR, Tamil Extraction, and Grounded Drafting..."):
                    file_bytes = uploaded_file.getvalue()
                    ext = Path(uploaded_file.name).suffix.lower()

                    if ext == ".eml":
                        source_id, fpath = process_raw_email(file_bytes, filename=uploaded_file.name)
                    else:
                        temp_dest = config.UPLOADS_SCANNED_DIR / uploaded_file.name
                        with open(temp_dest, "wb") as f:
                            f.write(file_bytes)
                        source_id, fpath = process_file_path(temp_dest)

                    res = pipeline.process_source(source_id, file_path=fpath)
                    st.session_state["latest_processed_id"] = source_id
                    st.session_state["success_banner"] = f"மனு வெற்றிகரமாக செயலாக்கப்பட்டது! (கோப்பு: {uploaded_file.name})"

    # Display Persistent Result Card
    if "success_banner" in st.session_state:
        st.success(st.session_state["success_banner"])

    latest_id = st.session_state.get("latest_processed_id")
    if latest_id:
        latest_info = get_source_details(latest_id)
        if latest_info:
            st.markdown("---")
            st.markdown("### ✨ அண்மையில் செயலாக்கப்பட்ட மனு முடிவு (Instant Processing Result Card)")

            card_col1, card_col2 = st.columns([1, 1])
            with card_col1:
                raw_fname = Path(latest_info.get("raw_path", "")).name if latest_info.get("raw_path") else "Document"
                st.markdown(f"**📄 கோப்பு பெயர் (File Name):** `{raw_fname}`")
                st.markdown(f"**Source ID:** `{latest_id[:16]}...` | **வகை:** `{latest_info.get('source_type')}` | **நிலை:** `{latest_info.get('status')}`")
                cls = latest_info.get("classification")
                if cls:
                    st.markdown(f"**ஒதுக்கப்பட்ட துறை:** `{cls.get('department')}` | **முன்னுரிமை:** `{cls.get('priority')}` ({cls.get('final_decision')})")

                st.markdown("##### 📌 பிரித்தெடுக்கப்பட்ட விவரங்கள் (Entities):")
                ent_list = latest_info.get("entities", [])
                if ent_list:
                    st.dataframe(pd.DataFrame(ent_list)[["entity_type", "entity_value", "validation_status", "confidence"]])

            with card_col2:
                st.markdown("##### 📝 உருவாக்கப்பட்ட வரைவு ஒப்புதல் கடிதம் (Generated Draft):")
                draft_info = latest_info.get("draft")
                if draft_info:
                    st.code(draft_info.get("draft_text", "")[:1200], language="text")
                    st.caption(f"Template Used: `{draft_info.get('template_used')}` | Missing Score: **{draft_info.get('hallucination_score')}**")

            st.info("👉 இப்போது **Tab 2 (OCR Review)** சென்று எழுத்துணரியை திருத்தலாம் அல்லது **Tab 3 (Queue)** சென்று Grounding Inspector-ஐ சரிபார்க்கலாம்.")


# ==============================================================================
# TAB 2: OCR REVIEW & INLINE CORRECTION
# ==============================================================================
with tab2:
    st.subheader("Indic-OCR தமிழ் எழுத்துணரி மதிப்பாய்வு & திருத்தம் (OCR Review & Correction)")

    conn = get_db_connection()
    sources_with_ocr = pd.read_sql_query(
        "SELECT s.source_id, s.source_type, s.raw_path, s.status, o.avg_confidence, o.full_text_corrected "
        "FROM sources s LEFT JOIN ocr_results o ON s.source_id = o.source_id "
        "ORDER BY s.received_at DESC",
        conn,
    )
    conn.close()

    if sources_with_ocr.empty:
        st.info("எந்த ஆவணங்களும் இன்னும் பெறப்படவில்லை. Tab 1-ல் ஒரு ஆவணத்தை பதிவேற்றவும்.")
    else:
        sources_with_ocr["file_name"] = sources_with_ocr["raw_path"].apply(lambda p: Path(p).name if p else "Document")
        src_ids = sources_with_ocr["source_id"].tolist()
        latest_id = st.session_state.get("latest_processed_id")
        default_index = src_ids.index(latest_id) if latest_id in src_ids else 0

        selected_source_id = st.selectbox(
            "மதிப்பாய்வு செய்ய ஆவணத்தைத் தேர்ந்தெடுக்கவும் (Select Document):",
            src_ids,
            index=default_index,
            format_func=lambda x: f"📄 {sources_with_ocr.loc[sources_with_ocr['source_id']==x, 'file_name'].values[0]} ({sources_with_ocr.loc[sources_with_ocr['source_id']==x, 'source_type'].values[0]}) — Status: {sources_with_ocr.loc[sources_with_ocr['source_id']==x, 'status'].values[0]} [ID: {x[:8]}...]",
        )

        ocr_mode = st.radio(
            "செயல்முறை முறை (Review Mode):",
            ["👁️ பார்வை முறை (Formatted View)", "✏️ உரை திருத்த முறை (Inline OCR Correction)"],
            horizontal=True,
        )

        details = get_source_details(selected_source_id)
        if details:
            col_ocr_l, col_ocr_r = st.columns([1, 1])

            with col_ocr_l:
                st.markdown("#### 📄 மூல ஆவணம் (Raw Document Preview)")
                raw_path = Path(details["raw_path"])
                if raw_path.exists():
                    ext = raw_path.suffix.lower()
                    if ext in [".png", ".jpg", ".jpeg"]:
                        st.image(str(raw_path), width="stretch")
                    elif ext == ".pdf":
                        try:
                            import pymupdf as fitz
                            doc = fitz.open(str(raw_path))
                            page = doc[0]
                            pix = page.get_pixmap(dpi=150)
                            img_bytes = pix.tobytes("png")
                            st.image(img_bytes, caption=f"{raw_path.name} (Page 1 of {len(doc)})", width="stretch")
                        except Exception as pdf_err:
                            st.info(f"PDF ஆவணம்: `{raw_path.name}` ({raw_path.stat().st_size} bytes)")
                    elif ext == ".eml":
                        st.code(raw_path.read_text(encoding="utf-8", errors="replace")[:1200], language="text")
                    else:
                        st.info(f"கோப்பு: `{raw_path.name}` ({raw_path.stat().st_size} bytes)")
                else:
                    st.warning("மூலக் கோப்பு வட்டில் காணப்படவில்லை.")

            with col_ocr_r:
                st.markdown("#### 🔤 பிரித்தெடுக்கப்பட்ட தமிழ் உரை (Extracted OCR Text)")
                ocr_pages = details.get("ocr_pages", [])
                if ocr_pages:
                    for p_idx, page in enumerate(ocr_pages):
                        page_num = page["page_number"]
                        st.caption(f"பக்கம் {page_num} | நம்பிக்கை குறியீடு (Avg Conf): **{page['avg_confidence']:.2f}** | Engine: `{page['ocr_engine']}`")
                        
                        raw_text = page.get("full_text_corrected") or page.get("full_text", "")

                        if "திருத்த முறை" in ocr_mode:
                            st.markdown("##### ✍️ OCR உரையை நேரடியாக திருத்தவும்:")
                            page_unique_id = page.get("id", p_idx)
                            edited_text = st.text_area(
                                f"Page {page_num} Text Editor:",
                                value=raw_text,
                                height=280,
                                key=f"ocr_edit_area_{selected_source_id}_{page_unique_id}_{page_num}_{p_idx}",
                            )
                            if st.button("✍️ திருத்தத்தை உறுதிசெய் & மீண்டும் பிரித்தெடு (Confirm & Re-Extract)", key=f"confirm_ocr_edit_{selected_source_id}_{page_unique_id}_{page_num}_{p_idx}"):
                                with st.spinner("Re-extracting entities and updating draft with corrected OCR text..."):
                                    pipeline.reprocess_from_corrected_ocr(
                                        source_id=selected_source_id,
                                        page_number=page_num,
                                        corrected_text=edited_text,
                                        officer_id=current_officer,
                                    )
                                    st.success("திருத்தப்பட்ட உரையிலிருந்து விபரங்கள் மற்றும் வரைவு வெற்றிகரமாக புதுப்பிக்கப்பட்டன!")
                                    st.rerun()
                        else:
                            # Formatted High-Contrast View
                            if raw_text and raw_text.strip():
                                highlighted_html = ""
                                for line in raw_text.splitlines():
                                    line_html = ""
                                    for word in line.split():
                                        if config.LOW_CONF_FLAG in word:
                                            clean = word.replace(config.LOW_CONF_FLAG, "")
                                            line_html += f"<span class='low-conf-word'>{clean} [?]</span> "
                                        else:
                                            line_html += f"<span class='normal-word'>{word}</span> "
                                    highlighted_html += f"<div style='margin-bottom: 4px;'>{line_html}</div>"

                                st.markdown(
                                    f"<div class='ocr-text-box'>{highlighted_html}</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.info("இந்த பக்கத்தில் உரை எதுவும் இல்லை.")
                else:
                    st.info("இந்த ஆவணத்திற்கான எழுத்துணரி இன்னும் செயலாக்கப்படவில்லை.")


# ==============================================================================
# TAB 3: QUEUE, GROUNDING INSPECTOR & ACTIONS
# ==============================================================================
with tab3:
    st.subheader("மனுக்கள் செயலாக்க வரிசை மற்றும் அதிகாரி ஒப்புதல் (Queue & Approvals)")

    conn = get_db_connection()
    queue_df = pd.read_sql_query(
        """
        SELECT 
            s.source_id,
            s.raw_path,
            s.source_type,
            s.received_at,
            s.status,
            c.department,
            c.priority,
            c.final_decision,
            d.hallucination_score,
            d.officer_approved
        FROM sources s
        LEFT JOIN classifications c ON s.source_id = c.source_id
        LEFT JOIN drafts d ON s.source_id = d.source_id
        ORDER BY 
            CASE c.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
            s.received_at DESC
        """,
        conn,
    )
    conn.close()

    if not queue_df.empty:
        queue_df["file_name"] = queue_df["raw_path"].apply(lambda p: Path(p).name if p else "Document")
        cols = ["file_name", "department", "priority", "status", "hallucination_score", "source_type", "source_id"]
        display_cols = [c for c in cols if c in queue_df.columns]
        table_view_df = queue_df[display_cols]
    else:
        table_view_df = queue_df

    # Filter Bar
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        status_filter = st.multiselect("நிலை (Status Filter)", ["pending", "ocr_done", "classified", "draft_ready", "approved", "rejected"], default=["draft_ready", "pending", "approved"])
    with f_col2:
        dept_filter = st.multiselect("துறை (Department Filter)", list(config.DEPARTMENTS.keys()))
    with f_col3:
        prio_filter = st.multiselect("முன்னுரிமை (Priority Filter)", ["HIGH", "MEDIUM", "LOW"])

    filtered_df = table_view_df.copy()
    if status_filter:
        filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]
    if dept_filter:
        filtered_df = filtered_df[filtered_df["department"].isin(dept_filter)]
    if prio_filter:
        filtered_df = filtered_df[filtered_df["priority"].isin(prio_filter)]

    st.dataframe(filtered_df, width="stretch")

    # Bulk Actions Bar
    st.markdown("#### ⚡ மொத்த நடவடிக்கைகள் (Bulk Actions)")
    bulk_col1, bulk_col2, bulk_col3 = st.columns([2, 1, 1])

    with bulk_col1:
        all_candidate_ids = filtered_df["source_id"].tolist() if not filtered_df.empty else []
        selected_bulk_ids = st.multiselect("செயல்படுத்த வேண்டிய மனுக்களைத் தேர்ந்தெடுக்கவும் (Multi-Select):", all_candidate_ids)

    with bulk_col2:
        if st.button("📥 Export Selected (.zip)"):
            if not selected_bulk_ids:
                st.warning("மனுக்களைத் தேர்ந்தெடுக்கவும்.")
            else:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for s_id in selected_bulk_ids:
                        d_info = get_source_details(s_id)
                        if d_info and d_info.get("draft"):
                            d_text = d_info["draft"].get("draft_text", "")
                            docx_temp = config.UPLOADS_PROCESSED_DIR / f"ack_{s_id[:12]}.docx"
                            export_draft_to_docx(d_text, s_id, docx_temp)
                            zip_file.write(docx_temp, arcname=f"ack_{s_id[:12]}.docx")
                st.download_button(
                    label="💾 ZIP கோப்பை பதிவிறக்கு (Download ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="Erode_Collectorate_Approved_Drafts.zip",
                    mime="application/zip",
                )

    with bulk_col3:
        if st.button("✅ மொத்த ஒப்புதல் (Bulk Approve)"):
            if not selected_bulk_ids:
                st.warning("மனுக்களைத் தேர்ந்தெடுக்கவும்.")
            else:
                # Guard: check hallucination scores
                blocked = []
                for s_id in selected_bulk_ids:
                    d_info = get_source_details(s_id)
                    score = d_info.get("draft", {}).get("hallucination_score", 1.0) if d_info else 1.0
                    if score >= 0.2:
                        blocked.append((s_id, score))

                if blocked:
                    st.error(f"⚠️ அங்கீகரிக்கப்படாத உருப்படிகள் உள்ளன ({len(blocked)} மனுக்களில் விடுபட்ட தகவல்கள் >= 0.20 உள்ளன). தனித்தனியாக மதிப்பாய்வு செய்யவும்.")
                else:
                    for s_id in selected_bulk_ids:
                        update_draft_approval(s_id, True, current_officer)
                    st.success(f"{len(selected_bulk_ids)} மனுக்கள் வெற்றிகரமாக அங்கீகரிக்கப்பட்டன!")
                    st.rerun()

    st.divider()
    st.markdown("### ✍️ வரைவு மதிப்பாய்வு & Grounding Inspector (Draft Review & Actions)")

    if not filtered_df.empty:
        q_ids = filtered_df["source_id"].tolist()
        latest_id = st.session_state.get("latest_processed_id")
        q_default_index = q_ids.index(latest_id) if latest_id in q_ids else 0

        file_map = dict(zip(filtered_df["source_id"], filtered_df["file_name"]))
        action_source_id = st.selectbox(
            "செயல்படுத்த வேண்டிய மனு (Select Document):",
            q_ids,
            index=q_default_index,
            format_func=lambda x: f"📄 {file_map.get(x, x[:16])} — Status: {filtered_df.loc[filtered_df['source_id']==x, 'status'].values[0]} [ID: {x[:8]}...]",
        )
        target_details = get_source_details(action_source_id)

        if target_details:
            draft_obj = target_details.get("draft") or {}
            grounding_map = draft_obj.get("grounding_map") or {}
            missing_fields = draft_obj.get("missing_fields", [])
            hallucination_score = draft_obj.get("hallucination_score", 0.0)

            # Reconstruct grounding_map if missing from older legacy runs
            if not grounding_map and target_details.get("entities"):
                grounding_map = {}
                for ent in target_details["entities"]:
                    e_type = ent["entity_type"]
                    e_val = ent["entity_value"]
                    if e_val and e_val != config.MISSING_DATA_PLACEHOLDER and "[தகவல் இல்லை]" not in str(e_val):
                        grounding_map[e_type] = {
                            "value": e_val,
                            "source": "ocr",
                            "confidence": ent.get("confidence", 0.95),
                            "validation_status": ent.get("validation_status", "verified"),
                            "source_chunk": ent.get("source_chunk", ""),
                        }

            col_act_l, col_act_r = st.columns([1, 1])

            # Left Column: Grounding Inspector
            with col_act_l:
                inspect_toggle = st.toggle("🏷️ Grounding Inspector (மூல ஆதார சரிபார்ப்பு)", value=True)

                if inspect_toggle:
                    st.markdown("##### 🔍 புலங்களின் மூல ஆதார நிலை (Field Provenance Breakdown):")
                    
                    fields_order = ["applicant_name", "file_number", "date", "mobile_number", "aadhaar_number", "taluk", "village", "survey_number"]
                    for f in fields_order:
                        g_info = grounding_map.get(f) or {}
                        val = g_info.get("value")
                        src = g_info.get("source")
                        conf = g_info.get("confidence", 0.0)
                        status = g_info.get("validation_status", "missing")

                        if val and val != config.MISSING_DATA_PLACEHOLDER and "[தகவல் இல்லை]" not in str(val):
                            if src == "system":
                                badge = svg_badge("INFERRED")
                                cite = "Source: System Context"
                                val_disp = f"**{val}**"
                            elif src == "auto":
                                badge = svg_badge("AUTO")
                                cite = "Source: Officer Generated"
                                val_disp = f"**{val}**"
                            else:
                                badge = svg_badge("GROUNDED")
                                chunk_cited = g_info.get('source_chunk', '')[:30]
                                cite = f"Source: OCR chunk (`{chunk_cited}`) | Conf: **{conf:.2f}**" if chunk_cited else f"Source: OCR Extracted | Conf: **{conf:.2f}**"
                                val_disp = f"**{val}**"
                        else:
                            badge = svg_badge("MISSING")
                            cite = "<span style='color:#ef4444; font-weight:bold;'>விடுபட்டது — கைமுறையாக நிரப்பவும்</span>"
                            val_disp = "<span style='color:#ef4444;'>[தகவல் இல்லை]</span>"

                        st.markdown(
                            f"""
                            <div class="grounding-item">
                                <div>
                                    <span style="font-weight:600; font-size:14px;">{f}</span>: {val_disp}<br>
                                    <span style="font-size:11px; color:#94a3b8;">{cite}</span>
                                </div>
                                <div>{badge}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                # Sequential File Number Generator Button
                st.markdown("---")
                st.markdown("##### 🔢 கோப்பு எண் தானியங்கி உருவாக்கம் (Deterministic Sequence Generator):")
                cls_info = target_details.get("classification") or {}
                dept = cls_info.get("department", "பொது_வழக்கு")

                if st.button(f"🔢 {dept} துறைக்கு புதிய கோப்பு எண் உருவாக்கு (Generate File No)"):
                    new_file_no = generate_department_file_number(dept, current_officer, source_id=action_source_id)
                    # Re-render draft with new file number
                    ents = {e["entity_type"]: e["entity_value"] for e in target_details.get("entities", [])}
                    ents["file_number"] = new_file_no
                    pipeline.drafter.render_draft(action_source_id, dept, ents)
                    st.success(f"புதிய கோப்பு எண் ஒதுக்கப்பட்டது: `{new_file_no}`")
                    st.rerun()

            # Right Column: Draft Acknowledgment & Officer Actions
            with col_act_r:
                st.markdown("#### 📄 வரைவு ஒப்புகைச் சீட்டு (Draft Acknowledgment)")
                draft_text = draft_obj.get("draft_text", "")

                if inspect_toggle and draft_text:
                    # Render with colored left borders
                    st.markdown("<div class='grounding-box'>", unsafe_allow_html=True)
                    for line in draft_text.splitlines():
                        if not line.strip():
                            continue
                        if "தகவல் இல்லை" in line:
                            st.markdown(f"<div class='grounded-line-red'>{html.escape(line)} {svg_badge('MISSING')}</div>", unsafe_allow_html=True)
                        elif any(k in line for k in ["நாள்", "2026", "2020"]) and "system" in str(grounding_map.get("date", {}).get("source")):
                            st.markdown(f"<div class='grounded-line-yellow'>{html.escape(line)} {svg_badge('INFERRED')}</div>", unsafe_allow_html=True)
                        elif ":" in line and any(k in line for k in ["பெயர்", "வட்டம்", "கிராமம்", "எண்"]):
                            st.markdown(f"<div class='grounded-line-green'>{html.escape(line)} {svg_badge('GROUNDED')}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='grounded-line-template'>{html.escape(line)}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.code(draft_text, language="text")

                # Action Buttons
                st.markdown("##### 🛠️ அதிகாரி நடவடிக்கைகள் (Officer Approval & Export):")
                act_col1, act_col2, act_col3 = st.columns(3)

                with act_col1:
                    edit_draft_mode = st.toggle("✏️ வரைவைத் திருத்து (Edit)", key="edit_draft_toggle")

                with act_col2:
                    if st.button("🔄 வரைவை மீண்டும் உருவாக்கு (Regenerate)"):
                        dept = (target_details.get("classification") or {}).get("department", "பொது_வழக்கு")
                        ents = {e["entity_type"]: e["entity_value"] for e in target_details.get("entities", [])}
                        pipeline.drafter.render_draft(action_source_id, dept, ents)
                        st.success("வரைவு மீண்டும் புதுப்பிக்கப்பட்டது!")
                        st.rerun()

                with act_col3:
                    is_approved = target_details.get("status") == "approved"
                    if is_approved:
                        st.success("✅ ஆவணம் ஏற்கெனவே அங்கீகரிக்கப்பட்டது")
                    else:
                        if missing_fields:
                            st.warning(f"⚠️ {len(missing_fields)} விடுபட்ட தகவல்கள் உள்ளன.")
                            if st.button("✅ உறுதிசெய்து ஒப்புதல் அளி (Approve Anyway)"):
                                update_draft_approval(action_source_id, True, current_officer)
                                log_audit(
                                    source_id=action_source_id,
                                    action="OFFICER_APPROVED_WITH_MISSING",
                                    officer_id=current_officer,
                                    details=f"Approved with missing fields: {missing_fields}",
                                )
                                st.success("வரைவு ஒப்புதல் அளிக்கப்பட்டது!")
                                st.rerun()
                        else:
                            if st.button("✅ ஒப்புதல் அளி (Approve)"):
                                update_draft_approval(action_source_id, True, current_officer)
                                st.success("வரைவு ஒப்புதல் அளிக்கப்பட்டது!")
                                st.rerun()

                # Inline Draft Text Editor if toggled
                if edit_draft_mode:
                    st.markdown("##### ✏️ வரைவு உரை திருத்தம் (Manual Draft Override):")
                    edited_draft_text = st.text_area("வரைவு உரை:", value=draft_text, height=300, key=f"draft_edit_box_{action_source_id}")
                    if st.button("💾 திருத்திய வரைவைச் சேமி (Save Draft Edit)", key=f"save_draft_edit_btn_{action_source_id}"):
                        save_draft(
                            source_id=action_source_id,
                            draft_text=edited_draft_text,
                            template_used=draft_obj.get("template_used", "manual_edit"),
                            hallucination_score=draft_obj.get("hallucination_score", 0.0),
                            grounding_map=grounding_map,
                            missing_fields=missing_fields,
                        )
                        log_audit(
                            source_id=action_source_id,
                            action="OFFICER_EDITED_DRAFT",
                            officer_id=current_officer,
                            details="Officer manually edited draft acknowledgment text",
                        )
                        st.success("திருத்தப்பட்ட வரைவு வெற்றிகரமாக சேமிக்கப்பட்டது!")
                        st.rerun()

                # Export to DOCX
                st.markdown("---")
                docx_out = config.UPLOADS_PROCESSED_DIR / f"ack_{action_source_id[:12]}.docx"
                export_draft_to_docx(draft_text, action_source_id, docx_out)
                
                with open(docx_out, "rb") as f:
                    docx_bytes = f.read()

                st.download_button(
                    label="📄 அதிகாரப்பூர்வ .docx கடிதத்தை பதிவிறக்கு (Download DOCX)",
                    data=docx_bytes,
                    file_name=f"Erode_Collectorate_Ack_{action_source_id[:8]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"download_docx_btn_{action_source_id}",
                )


# ==============================================================================
# TAB 4: ANALYTICS
# ==============================================================================
with tab4:
    st.subheader("மனுக்கள் பகுப்பாய்வு மற்றும் புள்ளிவிவரங்கள் (Department Analytics)")
    conn = get_db_connection()
    df_cls = pd.read_sql_query(
        "SELECT department, priority, final_decision, count(*) as count FROM classifications GROUP BY department, priority, final_decision",
        conn,
    )
    conn.close()

    if df_cls.empty:
        st.info("பகுப்பாய்வுக்கான தரவுகள் எதுவும் இல்லை.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏛️ துறை வாரியாக மனுக்கள் (Petitions by Department)")
            dept_counts = df_cls.groupby("department")["count"].sum().reset_index()
            st.bar_chart(dept_counts.set_index("department"))

        with c2:
            st.markdown("#### ⚡ முன்னுரிமை பங்கீடு (Priority Distribution)")
            prio_counts = df_cls.groupby("priority")["count"].sum().reset_index()
            st.bar_chart(prio_counts.set_index("priority"))


# ==============================================================================
# TAB 5: AUDIT TRAIL
# ==============================================================================
with tab5:
    st.subheader("பாதுகாப்பான தணிக்கைப் பதிவு (Immutable Audit Trail)")
    st.caption("All actions, OCR corrections, sequence generations, and officer approvals are logged permanently.")

    conn = get_db_connection()
    audit_df = pd.read_sql_query("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100", conn)
    conn.close()

    if audit_df.empty:
        st.info("தணிக்கை பதிவுகள் எதுவும் இல்லை.")
    else:
        st.dataframe(audit_df, width="stretch")
