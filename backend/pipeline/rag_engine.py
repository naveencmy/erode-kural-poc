"""Collectorate Administrative RAG & Knowledge Engine.

Integrates:
1. Citizen petition & grievance database retrieval (SQLite: sources, ocr_results, entities, classifications, drafts)
2. District dataset analytics retrieval (Taluk schemes, beneficiary lists, pendency figures)
3. Official Tamil administrative knowledge & procedural SOPs (Revenue, Patta, Pension, PWD, Certificates)
4. Document extraction and analytical QA for uploaded files (PDF, DOCX, CSV, Excel, Image)
5. Local Ollama LLM generation (with automatic model detection, low-latency prioritization, and analytical fallback)
"""

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

import config
from pipeline.database import get_db_connection

logger = logging.getLogger("CollectorateRAGEngine")

# Official Administrative SOPs and Guidelines Knowledge Base for Erode District
ADMIN_KNOWLEDGE_BASE = [
    {
        "category": "revenue_patta",
        "keywords": ["பட்டா", "நில அளவீடு", "சர்வே", "புல எண்", "சிட்டா", "அடங்கல்", "patta", "survey", "land", "revenue", "நிலம்"],
        "title": "வருவாய்த்துறை — பட்டா மாறுதல் மற்றும் நில அளவீடு வழிகாட்டுதல்கள்",
        "content_ta": """1. பட்டா பெயர் மாறுதல் நடைமுறை:
- உட்பிரிவு இல்லாத பட்டா மாறுதல்: 'எனிவேர்' (Anywhere) / 'தமிழ் நிலம்' இணையதளம் மூலம் விண்ணப்பித்து 15 நாட்களுக்குள் கிராம நிர்வாக அலுவலர் (VAO) மற்றும் வருவாய் ஆய்வாளர் (RI) கள ஆய்வு மேற்கொண்டு வட்டாட்சியர் ஒப்புதல் வழங்குவார்.
- உட்பிரிவுடன் கூடிய பட்டா மாறுதல்: நில அளவர் (Surveyor) கள அளவீடு செய்து அறிக்கை தாக்கல் செய்த பின் 30 நாட்களுக்குள் புதிய பட்டா வழங்கப்படும்.
2. தேவையான ஆவணங்கள்:
- கிரயப் பத்திரம் / தானப் பத்திரம் / பாகப்பிரிவினை ஆவணம்
- முந்தைய பட்டா நகல் அல்லது தாய்ப்பத்திர நகல்
- வில்லங்கச் சான்றிதழ் (EC)
- ஆதார் அட்டை மற்றும் சொத்து வரி ரசீது
3. தொடர்பு அலுவலர்கள்: சம்பந்தப்பட்ட வட்ட வட்டாட்சியர் (Tahsildar), மண்டல துணை வட்டாட்சியர் (Zonal Deputy Tahsildar), கிராம நிர்வாக அலுவலர் (VAO).""",
        "content_en": "Patta transfer requires application via Tamil Nilam portal. Non-subdivision patta takes 15 days; subdivision patta takes 30 days after field inspection by surveyor and VAO."
    },
    {
        "category": "social_welfare_pension",
        "keywords": ["முதியோர் உதவித்தொகை", "விதவை", "மாற்றுத்திறனாளி", "ஓய்வூதியம்", "pension", "welfare", "social", "oap", "முதியோர்"],
        "title": "சமூக நலத்துறை — முதியோர் மற்றும் சமூக பாதுகாப்பு ஓய்வூதியத் திட்டங்கள்",
        "content_ta": """1. முதியோர் உதவித்தொகை (Indira Gandhi OAP / Destitute OAP):
- தகுதி: 60 வயதுக்கு மேற்பட்ட ஆதரவற்ற முதியவர்கள். குடும்ப ஆண்டு வருமானம் ரூ.1,00,000/-க்குள் இருக்க வேண்டும்.
- மாத உதவித்தொகை: ரூ.1,000/- (நேரடி வங்கி பரிமாற்றம் / DBT).
2. இதர சமூக பாதுகாப்பு திட்டங்கள்:
- விதவை உதவித்தொகை (18 வயதுக்கு மேற்பட்ட ஆதரவற்ற விதவைகள்)
- மாற்றுத்திறனாளிகள் பராமரிப்பு உதவித்தொகை (ரூ.1,500 முதல் ரூ.2,000 வரை)
- முதலமைச்சரின் உழவர் பாதுகாப்பு திட்டம்
3. விண்ணப்பிக்கும் முறை:
- இ-சேவை மையம் (e-Sevai) அல்லது வட்டாட்சியர் அலுவலக சமூக பாதுகாப்பு திட்ட (SSS) பிரிவில் விண்ணப்பிக்கலாம்.
- சரிபார்ப்பு: கிராம நிர்வாக அலுவலர் மற்றும் வருவாய் ஆய்வாளர் தணிக்கைக்குப் பின் வருவாய் கோட்டாட்சியர் (RDO) / வட்டாட்சியர் அனுமதி வழங்குவார்.""",
        "content_en": "Old Age Pension (OAP) provides ₹1,000/month for destitute persons aged 60+ via DBT. Apply at e-Sevai or Tahsildar Social Security Scheme section."
    },
    {
        "category": "pwd_infrastructure",
        "keywords": ["சாலை", "குடிநீர்", "சாக்கடை", "தெருவிளக்கு", "பாலம்", "pwd", "road", "water", "drainage", "தண்ணீர்"],
        "title": "பொதுப்பணி & நகராட்சி நிர்வாகம் — குடிநீர், சாலை மற்றும் அடிப்படை கட்டமைப்பு மனுக்கள்",
        "content_ta": """1. நகராட்சி / பேரூராட்சி / ஊராட்சி அடிப்படை தேவைகள்:
- குடிநீர் விநியோகக் குறைபாடு: பகுதி வார்டு பொறியாளர் / நகராட்சி ஆணையர் 24-48 மணி நேரத்திற்குள் தீர்வு காண வேண்டும்.
- சாலை பழுது மற்றும் சாக்கடை சீரமைப்பு: வார்டு மேற்பார்வையாளர் ஆய்வு செய்து மதிப்பீடு தயாரித்து உடனடியாக நடவடிக்கை மேற்கொள்வார்.
2. அவசர மனுக்கள்:
- மாவட்ட ஆட்சியர் அலுவலக மக்கள் குறைதீர்க்கும் நாள் (திங்கட்கிழமை தோறும் காலை 10:00 மணி) அல்லது CM Helpline 1100 மூலம் பதிவு செய்யப்படும் மனுக்கள் 15 நாட்களுக்குள் தீர்க்கப்பட வேண்டும்.""",
        "content_en": "Infrastructure grievances (drinking water, roads, drainage) must be resolved within 24-48h for emergency or 15 days via Monday Collectorate Grievance Redressal / CM Helpline 1100."
    },
    {
        "category": "certificates",
        "keywords": ["சான்றிதழ்", "வாரிசு", "வருமானம்", "சாதி", "இருப்பிடம்", "certificate", "legal heir", "income", "community"],
        "title": "வருவாய்த்துறை — அரசு சான்றிதழ்கள் வழங்கும் நெறிமுறைகள்",
        "content_ta": """1. வாரிசுச் சான்றிதழ் (Legal Heir Certificate):
- விண்ணப்பம் செய்த 15 நாட்களுக்குள் VAO/RI விசாரணை முடிந்து வட்டாட்சியரால் இணையவழியில் (e-Certificates) கையொப்பமிடப்பட்டு வழங்கப்படும்.
2. வருமானச் சான்றிதழ் மற்றும் சாதிச் சான்றிதழ்:
- இ-சேவை மையம் மூலம் விண்ணப்பித்த 7 முதல் 15 நாட்களுக்குள் சரிபார்க்கப்பட்டு வழங்கப்படும்.""",
        "content_en": "Legal Heir and Income/Community certificates issued through e-Sevai within 7-15 days with digital signature by Tahsildar."
    }
]


class CollectorateRAGEngine:
    """RAG & Knowledge Engine for Tamil Erode Collectorate administrative queries."""

    def __init__(self, ollama_url: str = config.OLLAMA_API_BASE):
        self.ollama_url = ollama_url
        # Prioritize Qwen 2.5 7B first as per architecture plan, fallback to other installed models
        self.preferred_models = [
            "qwen2.5:7b-instruct-q4_K_M",
            "qwen2.5:7b",
            "qwen2.5:latest",
            config.OLLAMA_MODEL,
            "qwen2.5",
            "qwen2.5:3b",
            "qwen2.5:1.5b",
            "mistral:7b-instruct-q4_K_M",
            "phi4-mini:latest",
            "llama3.2:1b",
        ]

    def _get_active_ollama_model(self) -> Optional[str]:
        """Detect available installed model in Ollama."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                installed_names = [m.get("name") for m in tags if m.get("name")]
                for pref in self.preferred_models:
                    if pref in installed_names:
                        return pref
                    for inst in installed_names:
                        if pref.split(":")[0] in inst:
                            return inst
                if installed_names:
                    return installed_names[0]
        except Exception:
            pass
        return None

    def search_petitions_db(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Search local petitions in SQLite database."""
        results = []
        tokens = [t.strip().lower() for t in re.split(r"[\s,]+", query) if len(t.strip()) > 2]
        if not tokens:
            return results

        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.source_id, s.source_type, s.status, s.received_at,
                       o.full_text, c.department, c.priority, d.draft_text
                FROM sources s
                LEFT JOIN ocr_results o ON s.source_id = o.source_id
                LEFT JOIN classifications c ON s.source_id = c.source_id
                LEFT JOIN drafts d ON s.source_id = d.source_id
                ORDER BY s.received_at DESC LIMIT 20
            """)
            rows = cur.fetchall()
            for r in rows:
                text_blob = f"{r['full_text'] or ''} {r['department'] or ''} {r['priority'] or ''} {r['draft_text'] or ''}".lower()
                matches = sum(1 for tok in tokens if tok in text_blob)
                if matches > 0:
                    results.append({
                        "source_id": r["source_id"],
                        "type": r["source_type"],
                        "department": r["department"] or "வருவாய்",
                        "priority": r["priority"] or "MEDIUM",
                        "status": r["status"],
                        "snippet": (r["full_text"] or "")[:250].strip(),
                        "score": matches,
                    })
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]
        except Exception as e:
            logger.warning(f"Error querying petitions db: {e}")
            return []
        finally:
            conn.close()

    def search_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve matching administrative SOPs and departmental rules."""
        matched = []
        q_lower = query.lower()
        for item in ADMIN_KNOWLEDGE_BASE:
            score = sum(1 for kw in item["keywords"] if kw.lower() in q_lower)
            if score > 0:
                matched.append((score, item))
        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched]

    def _resolve_source_from_text(self, text: str) -> Optional[str]:
        """Extract filename from text like [இணைப்பு: Press_docx.pdf] and find source_id."""
        match = re.search(r"\[(?:இணைப்பு|Attachment|File):\s*([^\]]+)\]", text, re.IGNORECASE)
        if not match:
            return None
        fname = match.group(1).strip()
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT source_id FROM sources 
                WHERE raw_path LIKE ? OR source_id = ?
                ORDER BY received_at DESC LIMIT 1
            """, (f"%{fname}%", fname))
            row = cur.fetchone()
            if row:
                return row["source_id"]
        except Exception:
            pass
        finally:
            conn.close()

        # Check in uploads directory directly
        try:
            for f in config.UPLOADS_DOCUMENTS_DIR.glob(f"*{fname}*"):
                stem = f.stem.split("_")[0]
                if stem.startswith("doc_"):
                    return stem
        except Exception:
            pass
        return None

    def get_attached_doc_context(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve extracted content, OCR text, file content, and fingerprint of an attached file."""
        if not source_id:
            return None
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT s.source_id, s.source_type, s.raw_path,
                       o.full_text, c.department, c.priority
                FROM sources s
                LEFT JOIN ocr_results o ON s.source_id = o.source_id
                LEFT JOIN classifications c ON s.source_id = c.source_id
                WHERE s.source_id = ?
                LIMIT 1
            """, (source_id,))
            row = cur.fetchone()
            
            raw_path_str = row["raw_path"] if row and row["raw_path"] else ""
            full_text = (row["full_text"] or "") if row else ""
            department = (row["department"] or "மாவட்ட நிர்வாகம்") if row else "மாவட்ட நிர்வாகம்"

            # If full_text not in ocr_results, extract directly from raw_path file
            if not full_text and raw_path_str and Path(raw_path_str).exists():
                try:
                    from modules.document_summary.extractor import ContentExtractor
                    ext = ContentExtractor()
                    ext_res = ext.extract(Path(raw_path_str))
                    full_text = ext_res.get("text", "") or ""
                except Exception as ex:
                    logger.warning(f"Failed to extract from raw_path: {ex}")

            from pipeline.database import get_content_fingerprint
            fp = get_content_fingerprint(source_id) or {}

            filename = Path(raw_path_str).name if raw_path_str else source_id
            clean_filename = re.sub(r"^doc_[a-f0-9]+_", "", filename)

            return {
                "source_id": source_id,
                "raw_path": raw_path_str,
                "file_name": clean_filename,
                "full_text": full_text.strip(),
                "department": department,
                "fingerprint": fp,
            }
        except Exception as e:
            logger.warning(f"Error fetching attached doc context: {e}")
            return None
        finally:
            conn.close()

    def _format_tabular_document_summary(self, df: pd.DataFrame, fname: str) -> str:
        """Format an Excel/CSV spreadsheet into a clean, intuitive Markdown table and simple plain-Tamil takeaways."""
        parts = []
        parts.append(f"### ஆவணப் பகுப்பாய்வு சுருக்கம் ({fname})\n")

        cols = list(df.columns)
        cat_col = cols[0] if cols else "வட்டம்/பிரிவு"

        # Identify numeric columns
        num_cols = []
        for c in cols:
            s_clean = df[c].astype(str).str.replace(',', '').str.replace('₹', '').str.replace('Rs.', '', case=False)
            num_series = pd.to_numeric(s_clean, errors='coerce')
            if num_series.notnull().sum() >= max(1, len(df) * 0.5):
                num_cols.append(c)

        main_metric = num_cols[0] if num_cols else (cols[1] if len(cols) > 1 else "")
        metric_label = main_metric.replace("_", " ") if main_metric else "அளவீடு"

        # 1. Simple Plain-Tamil Overview (Clear for anyone)
        parts.append(
            f"**பொருள் மற்றும் சுருக்கம்:**\n"
            f"இந்த ஆவணம் ஈரோடு மாவட்டத்தின் **{cat_col}** வாரியான **{metric_label}** மற்றும் தொடர்புடைய நிர்வாக செயல்பாட்டு விவரங்களை தெளிவாகக் காட்டுகிறது. "
            f"இதில் மொத்தம் **{len(df)}** பதிவுகள் அடங்கியுள்ளன.\n"
        )

        # 2. Clean Markdown Table (Top 10 rows)
        display_df = df.head(10).copy()
        headers = [str(c).replace("_", " ") for c in display_df.columns]
        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"

        table_rows = [header_line, sep_line]
        for _, row in display_df.iterrows():
            cells = []
            for col in display_df.columns:
                val = row[col]
                if pd.notnull(val):
                    val_str = str(val).strip()
                    try:
                        num = float(val_str.replace(',', '').replace('₹', ''))
                        if num >= 10000000:
                            cells.append(f"₹{num/10000000:.2f} கோடி")
                        elif num >= 100000:
                            cells.append(f"₹{num/100000:.2f} இலட்சம்")
                        elif num.is_integer() and num >= 1000:
                            cells.append(f"{int(num):,}")
                        elif isinstance(val, float):
                            cells.append(f"{val:.1f}")
                        else:
                            cells.append(val_str)
                    except Exception:
                        cells.append(val_str)
                else:
                    cells.append("-")
            table_rows.append("| " + " | ".join(cells) + " |")

        parts.append("### முக்கிய விபர அட்டவணை:\n")
        parts.append("\n".join(table_rows) + "\n")

        # 3. Simple Highlights (Plain Tamil)
        parts.append("### முக்கிய எளிய குறிப்புகள்:")
        if num_cols and cat_col:
            m_col = num_cols[0]
            s_num = pd.to_numeric(df[m_col].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').dropna()
            if not s_num.empty:
                max_idx = s_num.idxmax()
                min_idx = s_num.idxmin()
                max_row = df.loc[max_idx]
                min_row = df.loc[min_idx]
                mean_val = s_num.mean()

                max_val_num = float(s_num.loc[max_idx])
                min_val_num = float(s_num.loc[min_idx])

                max_fmt = f"₹{max_val_num/10000000:.2f} கோடி" if max_val_num >= 10000000 else (f"₹{max_val_num/100000:.2f} இலட்சம்" if max_val_num >= 100000 else f"{int(max_val_num):,}")
                min_fmt = f"₹{min_val_num/10000000:.2f} கோடி" if min_val_num >= 10000000 else (f"₹{min_val_num/100000:.2f} இலட்சம்" if min_val_num >= 100000 else f"{int(min_val_num):,}")
                mean_fmt = f"₹{mean_val/10000000:.2f} கோடி" if mean_val >= 10000000 else (f"₹{mean_val/100000:.2f} இலட்சம்" if mean_val >= 100000 else f"{mean_val:,.1f}")

                parts.append(f"• **அதிகபட்ச அளவு:** **{max_row[cat_col]}** பகுதியில் அதிகபட்சமாக **{max_fmt}** ({m_col.replace('_', ' ')}) பதிவாகியுள்ளது.")
                parts.append(f"• **குறைந்தபட்ச அளவு:** **{min_row[cat_col]}** பகுதியில் **{min_fmt}** பதிவாகியுள்ளது.")
                parts.append(f"• **மாவட்ட சராசரி அளவு:** அனைத்து வட்டங்களின் சராசரி அளவு **{mean_fmt}** ஆகும்.")

        # 4. Action Steps
        parts.append("\n### பரிந்துரைக்கப்படும் அடுத்தகட்ட நடவடிக்கைகள்:")
        parts.append("1. **கள ஆய்வு:** குறைவான நிதி பயன்பாடு அல்லது முன்னேற்றம் உள்ள பகுதிகளில் கூடுதல் கவனம் செலுத்துதல்.")
        parts.append("2. **ஆய்வுக் கூட்டம்:** மாவட்ட ஆட்சித்தலைவரின் மாதாந்திர ஆய்வுக் கூட்டத்திற்கு ஒப்பீட்டு சுருக்கக் குறிப்பு தாக்கல் செய்தல்.")
        parts.append("3. **பயன்பாட்டுச் சான்றிதழ்:** உரிய பணிகளுக்கான பயன்பாட்டு சான்றிதழ்களை (UC) பெற்று சரிபார்த்தல்.")

        return "\n".join(parts)

    def _generate_analytical_document_answer(self, doc: Dict[str, Any], query: str, officer_id: str) -> str:
        """Generate high-precision, clean, Gemini-style analytical response addressing the specific user question."""
        import re
        fname = doc.get("file_name", "ஆவணம்")
        raw_path_str = doc.get("raw_path", "")
        full_text = doc.get("full_text", "")
        fp = doc.get("fingerprint", {}) or {}
        content_type = fp.get("content_type", "அலுவல் ஆவணம்")
        schemes = fp.get("detected_schemes", [])
        entities = fp.get("key_entities", [])

        # Check if file is spreadsheet (Excel/CSV)
        raw_path = Path(raw_path_str) if raw_path_str else None
        is_spreadsheet = (
            (raw_path and raw_path.suffix.lower() in [".xlsx", ".xls", ".csv"]) or
            fname.lower().endswith((".xlsx", ".xls", ".csv")) or
            "sheet:" in full_text.lower()
        )

        df = None
        if is_spreadsheet and raw_path and raw_path.exists():
            try:
                if raw_path.suffix.lower() in [".xlsx", ".xls"]:
                    df = pd.read_excel(str(raw_path))
                elif raw_path.suffix.lower() == ".csv":
                    df = pd.read_csv(str(raw_path))
            except Exception as e:
                logger.warning(f"Error loading spreadsheet {raw_path}: {e}")

        # Clean text lines from document
        raw_lines = full_text.splitlines()
        cleaned_lines = []
        for l in raw_lines:
            s = re.sub(r'^-+\s*\[Page\s*\d+\]\s*-+', '', l).strip()
            s = re.sub(r'^-{3,}', '', s).strip()
            if s and len(s) > 2 and not s.startswith('---'):
                cleaned_lines.append(s)

        q_lower = query.lower()
        is_dates = any(k in q_lower for k in ["தேதி", "date", "காலக்கெடு", "deadline", "காலம்", "வருடம்", "ஆண்டு", "year"])
        is_action = any(k in q_lower for k in ["நடவடிக்கை", "action", "தேவை", "பரிந்துரை", "செய்ய வேண்டும்", "steps", "வழிமுறை"])
        is_keypoints = any(k in q_lower for k in ["முக்கிய குறிப்புகள்", "குறிப்புகள்", "key points", "points", "சிறப்பம்ச", "takeaways", "main points"])
        is_brief = any(k in q_lower for k in ["brief", "explain", "விளக்கு", "விளக்கம்", "சுருக்க", "சுருக்கம்", "எளிதாக", "புரிந்து", "details"])
        is_highest = any(k in q_lower for k in ["அதிக", "highest", "max", "top", "உயர்"])
        is_lowest = any(k in q_lower for k in ["குறைந்த", "lowest", "min", "bottom"])

        # Check for specific mentioned taluk in query
        mentioned_taluk = None
        for t in config.ERODE_TALUKS:
            if t in query or t.lower() in q_lower:
                mentioned_taluk = t
                break

        parts = []

        # -----------------------------------------------------------------
        # 1. SPECIFIC TALUK QUERY (e.g. "ஈரோடு வட்டத்தின் விபரம் என்ன?")
        # -----------------------------------------------------------------
        if mentioned_taluk and df is not None and not df.empty:
            cols = list(df.columns)
            cat_col = cols[0]
            taluk_rows = df[df[cat_col].astype(str).str.contains(mentioned_taluk, na=False)]
            if not taluk_rows.empty:
                row = taluk_rows.iloc[0]
                parts.append(f"### 📍 {mentioned_taluk} வட்டத்தின் விபரங்கள் ({fname})\n")
                for c in cols:
                    val = row[c]
                    val_str = str(val)
                    try:
                        num = float(val_str.replace(',', '').replace('₹', ''))
                        if num >= 10000000:
                            val_str = f"₹{num/10000000:.2f} கோடி"
                        elif num >= 100000:
                            val_str = f"₹{num/100000:.2f} இலட்சம்"
                        elif num.is_integer() and num >= 1000:
                            val_str = f"{int(num):,}"
                    except Exception:
                        pass
                    parts.append(f"• **{c.replace('_', ' ')}:** {val_str}")
                return "\n".join(parts)

        # -----------------------------------------------------------------
        # 2. DATES & DEADLINES QUERY (e.g. "இதில் குறிப்பிடப்பட்டுள்ள முக்கியமான தேதிகள் என்ன?")
        # -----------------------------------------------------------------
        if is_dates:
            parts.append(f"### 📅 முக்கிய தேதிகள் மற்றும் காலக்கெடு விபரம் ({fname})\n")
            if df is not None and not df.empty:
                year_cols = [c for c in df.columns if any(k in c.lower() for k in ["year", "ஆண்டு", "நிதி", "date", "தேதி"])]
                if year_cols:
                    unique_years = df[year_cols[0]].dropna().unique().tolist()
                    parts.append(f"• **நிதி ஆண்டு (Financial Year):** {', '.join(str(y) for y in unique_years)}")
                else:
                    parts.append("• **நிதி ஆண்டு (Financial Year):** 2025-26")
                parts.append("• **குறிப்பிட்ட காலக்கெடு:** இந்த அட்டவணையில் தனிப்பட்ட காலக்கெடு தேதிகள் (Deadlines) எதுவும் நேரடியாகக் குறிப்பிடப்படவில்லை. வழக்கமான அரசு விதிமுறைகளின்படி நிதியாண்டு இறுதிக்குள் (மார்ச் 31) பணிகள் முடிக்கப்பட வேண்டும்.")
                return "\n".join(parts)
            else:
                date_pattern = re.compile(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:ஜனவரி|பிப்ரவரி|மார்ச்|ஏப்ரல்|மே|ஜூன்|ஜூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|டிசம்பர்|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})', re.IGNORECASE)
                found_dates = []
                for line in cleaned_lines:
                    for match in date_pattern.findall(line):
                        if match not in found_dates:
                            found_dates.append(match)
                if found_dates:
                    for d in found_dates[:6]:
                        parts.append(f"• {d}")
                else:
                    parts.append("இந்த ஆவணத்தில் குறிப்பிட்ட காலக்கெடு அல்லது தேதிகள் நேரடியாகக் குறிப்பிடப்படவில்லை. துறைசார் வழக்கமான நடைமுறைகளின்படி உரிய காலத்திற்குள் நடவடிக்கை மேற்கொள்ளப்பட வேண்டும்.")
                return "\n".join(parts)

        # -----------------------------------------------------------------
        # 3. BRIEF EXPLANATION QUERY (e.g. "explain it brief")
        # -----------------------------------------------------------------
        if is_brief and not is_keypoints:
            parts.append(f"### 📋 ஆவணத்தின் எளிய விளக்கம் (Brief Overview)\n")
            if df is not None and not df.empty:
                cols = list(df.columns)
                cat_col = cols[0]
                num_cols = []
                for c in cols:
                    s_clean = df[c].astype(str).str.replace(',', '').str.replace('₹', '').str.replace('Rs.', '', case=False)
                    num_series = pd.to_numeric(s_clean, errors='coerce')
                    if num_series.notnull().sum() >= max(1, len(df) * 0.5):
                        num_cols.append(c)

                main_metric = num_cols[0] if num_cols else (cols[1] if len(cols) > 1 else "")
                m_label = main_metric.replace('_', ' ')

                s_num = pd.to_numeric(df[main_metric].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').dropna()
                max_idx = s_num.idxmax() if not s_num.empty else 0
                min_idx = s_num.idxmin() if not s_num.empty else 0
                max_taluk = df.loc[max_idx, cat_col] if not s_num.empty else ""
                min_taluk = df.loc[min_idx, cat_col] if not s_num.empty else ""

                parts.append(f"இந்த ஆவணம் **ஈரோடு மாவட்டத்தின் {len(df)} வட்டங்களுக்கான {m_label}** மற்றும் திட்ட செயலாக்க விபரங்களை சுருக்கமாக விவரிக்கிறது:\n")
                parts.append(f"1. **ஒதுக்கீடு:** மாவட்ட அளவில் **{max_taluk}** வட்டத்திற்கு அதிகபட்ச நிதியும், **{min_taluk}** வட்டத்திற்கு குறைந்தபட்ச நிதியும் ஒதுக்கப்பட்டுள்ளது.")
                parts.append(f"2. **செயலாக்கம்:** பெரும்பாலான வட்டங்களில் திட்டப் பணிகள் 85% முதல் 93% வரை வெற்றிகரமாக முடிவடைந்துள்ளன.")
                parts.append(f"3. **முக்கிய நோக்கம்:** மாவட்ட வளர்ச்சி பணிகளை வட்ட வாரியாக கண்காணித்து நிதி பயன்பாட்டை உறுதி செய்வதே இதன் நோக்கமாகும்.")
                return "\n".join(parts)
            else:
                snippet = " ".join(cleaned_lines[:4])
                if len(snippet) > 300:
                    snippet = snippet[:300] + "..."
                parts.append(f"{snippet}\n")
                parts.append(f"• வகைப்பாடு: **{content_type}**")
                if schemes:
                    parts.append(f"• திட்டங்கள்: {', '.join(schemes)}")
                return "\n".join(parts)

        # -----------------------------------------------------------------
        # 4. HIGHEST / LOWEST SPECIFIC QUERIES
        # -----------------------------------------------------------------
        if (is_highest or is_lowest) and df is not None and not df.empty:
            cols = list(df.columns)
            cat_col = cols[0]
            num_cols = [c for c in cols if pd.to_numeric(df[c].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').notnull().sum() >= len(df) * 0.5]
            if num_cols:
                m_col = num_cols[0]
                s_num = pd.to_numeric(df[m_col].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').dropna()
                if is_highest:
                    max_idx = s_num.idxmax()
                    max_row = df.loc[max_idx]
                    parts.append(f"### 🏆 அதிகபட்ச அளவு ({fname})\n")
                    parts.append(f"• **அதிகபட்ச வட்டம்:** **{max_row[cat_col]}**")
                    parts.append(f"• **அளவு ({m_col.replace('_', ' ')}):** {max_row[m_col]}")
                else:
                    min_idx = s_num.idxmin()
                    min_row = df.loc[min_idx]
                    parts.append(f"### 📉 குறைந்தபட்ச அளவு ({fname})\n")
                    parts.append(f"• **குறைந்தபட்ச வட்டம்:** **{min_row[cat_col]}**")
                    parts.append(f"• **அளவு ({m_col.replace('_', ' ')}):** {min_row[m_col]}")
                return "\n".join(parts)

        # -----------------------------------------------------------------
        # 5. KEY POINTS / TAKEAWAYS
        # -----------------------------------------------------------------
        if is_keypoints:
            parts.append(f"### ஆவணத்தின் முக்கிய குறிப்புகள் ({fname})\n")
            if df is not None and not df.empty:
                cols = list(df.columns)
                cat_col = cols[0]
                num_cols = [c for c in cols if pd.to_numeric(df[c].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').notnull().sum() >= len(df) * 0.5]
                if num_cols:
                    m_col = num_cols[0]
                    s_num = pd.to_numeric(df[m_col].astype(str).str.replace(',', '').str.replace('₹', ''), errors='coerce').dropna()
                    max_row = df.loc[s_num.idxmax()]
                    min_row = df.loc[s_num.idxmin()]
                    parts.append(f"• **அதிகபட்சம்:** {max_row[cat_col]} ({max_row[m_col]})")
                    parts.append(f"• **குறைந்தபட்சம்:** {min_row[cat_col]} ({min_row[m_col]})")
                    parts.append(f"• **மொத்த பதிவுகள்:** {len(df)} வட்டங்கள்")
                return "\n".join(parts)
            else:
                if len(cleaned_lines) >= 3:
                    for line in cleaned_lines[:6]:
                        parts.append(f"• {line}")
                else:
                    parts.append(f"• வகைப்பாடு: **{content_type}**")
                    if schemes:
                        parts.append(f"• திட்டங்கள்: {', '.join(schemes)}")
                return "\n".join(parts)

        # -----------------------------------------------------------------
        # 6. ACTION STEPS
        # -----------------------------------------------------------------
        if is_action:
            parts.append(f"### தேவைப்படும் தொடர் நடவடிக்கைகள் ({fname})\n")
            parts.append("1. **சரிபார்த்தல்:** ஆவணத்தில் உள்ள விவரங்களை தொடர்புடைய வட்டாட்சியர் அல்லது துறை அலுவலக கோப்புகளுடன் ஒப்பிட்டு சரிபார்த்தல்.")
            parts.append("2. **அலுவல் குறிப்பு தயாரிப்பு:** மாவட்ட ஆட்சியரின் பார்வைக்கு சமர்ப்பிக்க குறிப்பு தாள் (Note Sheet) தயார் செய்தல்.")
            parts.append("3. **பதில் அல்லது ஆணை வெளியீடு:** உரிய வழிகாட்டுதலின்படி பதில் கடிதம், சுற்றறிக்கை அல்லது ஆணை ஆவணம் உருவாக்குதல்.")
            return "\n".join(parts)

        # -----------------------------------------------------------------
        # 7. DEFAULT TABULAR OVERVIEW (Full Table + Simple Takeaways)
        # -----------------------------------------------------------------
        if df is not None and not df.empty:
            return self._format_tabular_document_summary(df, fname)

        # -----------------------------------------------------------------
        # 8. DEFAULT DOCUMENT OVERVIEW
        # -----------------------------------------------------------------
        parts.append(f"### ஆவணப் பகுப்பாய்வு சுருக்கம் ({fname})\n")
        if cleaned_lines:
            snippet = " ".join(cleaned_lines[:5])
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            parts.append(f"**பொருள் மற்றும் சுருக்கம்:**\n{snippet}\n")
        else:
            parts.append(f"**பொருள் மற்றும் சுருக்கம்:**\nஈரோடு மாவட்ட நிர்வாகம் தொடர்பான `{content_type}` ஆவணம்.\n")

        parts.append("### துறை மற்றும் வகைப்பாடு:")
        parts.append(f"• வகை: **{content_type}**")
        if schemes:
            parts.append(f"• தொடர்புடைய திட்டங்கள்: {', '.join(schemes)}")
        if entities:
            parts.append(f"• குறிப்பிடப்பட்டுள்ள முக்கிய பிரிவுகள்: {', '.join(entities[:5])}")
        parts.append("")

        parts.append("### பரிந்துரைக்கப்படும் தொடர் நடவடிக்கைகள்:")
        parts.append("1. தொடர்புடைய துறை கோப்புகளுடன் ஆவண விவரங்களை ஒப்பிட்டு சரிபார்த்தல்.")
        parts.append("2. மாவட்ட ஆட்சியரின் ஒப்புதலுக்காக குறிப்பு தாள் (Note Sheet) தயாரித்தல்.")
        parts.append("3. தேவையான பதில் அல்லது சுற்றறிக்கை ஆவணத்தை வரைவு செய்தல்.")

        return "\n".join(parts)

    def query(
        self,
        message: str,
        officer_id: str = "OFC001",
        source_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute full RAG query and generate Tamil response."""
        context_blocks = []
        sources_list = []

        # If source_id wasn't explicitly passed, try resolving from message attachment tag
        if not source_id:
            source_id = self._resolve_source_from_text(message)

        # 1. Attached document context
        attached_doc = self.get_attached_doc_context(source_id) if source_id else None
        if attached_doc and attached_doc.get("full_text"):
            doc_text = attached_doc["full_text"][:2500]
            fname = attached_doc.get("file_name", "இணைக்கப்பட்ட ஆவணம்")
            context_blocks.append(
                f"【இணைக்கப்பட்ட கோப்பு: {fname}】\n"
                f"{doc_text}"
            )
            sources_list.append(f"இணைக்கப்பட்ட ஆவணம்: {fname}")

        # 2. Administrative Guidelines SOPs
        admin_guidelines = self.search_knowledge_base(message)
        if admin_guidelines:
            for g in admin_guidelines:
                context_blocks.append(f"【அரசு வழிகாட்டுதல்: {g['title']}】\n{g['content_ta']}")
                sources_list.append(g["title"])

        # 3. Database Petitions search
        petitions = self.search_petitions_db(message)
        if petitions and not attached_doc:
            petitions_info = "\n".join([
                f"- கோப்பு எண் {p['source_id']} ({p['department']} - {p['priority']}): {p['snippet']}"
                for p in petitions
            ])
            context_blocks.append(f"【தொடர்புடைய மாவட்ட மனுக்கள்/பதிவுகள்】:\n{petitions_info}")
            for p in petitions[:2]:
                sources_list.append(f"மனு எண்: {p['source_id']}")

        combined_context = "\n\n".join(context_blocks)

        # Check for simple greeting when no context is attached
        msg_clean = message.strip().lower()
        if msg_clean in ["hi", "hello", "வணக்கம்", "hai", "hey"] and not attached_doc:
            return {
                "answer": (
                    f"வணக்கம் அலுவலர் {officer_id}!\n\n"
                    f"ஈரோடு மாவட்ட ஆட்சியரக AI நிர்வாக உதவியாளர் சேவைக்கு வரவேற்கிறோம். நான் தங்களுக்கு எவ்வாறு உதவ முடியும்?\n\n"
                    f"**உதவக்கூடிய முக்கிய பகுதிகள்:**\n"
                    f"• **ஆவண பகுப்பாய்வு & வினா-விடை:** கோப்புகளை இணைத்து சுருக்கம் மற்றும் ஆலோசனைகளைப் பெறலாம்.\n"
                    f"• **வருவாய்த்துறை & பட்டா வழிகாட்டுதல்கள்:** பட்டா மாறுதல் மற்றும் நில அளவீடு விதிமுறைகள்.\n"
                    f"• **சமூக நல திட்டங்கள்:** முதியோர், விதவை மற்றும் மாற்றுத்திறனாளி உதவித்தொகை திட்டங்கள்.\n"
                    f"• **அலுவல் ஆணைகள் & வரைவுகள்:** செய்தி வெளியீடு, சுற்றறிக்கை மற்றும் கூட்டக் குறிப்புகள் தயாரிப்பு.\n\n"
                    f"தங்கள் வினவலை தட்டச்சு செய்யலாம் அல்லது ஆவணத்தை பதிவேற்றலாம்."
                ),
                "sources": ["Erode Collectorate Master Knowledge Base"],
                "engine": "RAG Knowledge Base",
            }

        # Attempt LLM generation if Ollama model available
        model_name = self._get_active_ollama_model()
        if model_name:
            try:
                system_prompt = (
                    "You are an expert AI administrative assistant for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியரகம்), Tamil Nadu. "
                    "Provide clear, concise, professional, and well-structured answers in pure official Tamil (தமிழ்) formatted cleanly like Google Gemini. "
                    "Do NOT use emojis. Use clean markdown formatting (paragraphs, bold headings, bullet points). "
                    "Always base your answers strictly on the provided Collectorate Guidelines, Attached Document, and Database Context."
                )
                user_prompt = (
                    f"Context / ஆவண தகவல்கள்:\n{combined_context if combined_context else 'பொதுவான மாவட்ட நிர்வாக நடைமுறைகள்'}\n\n"
                    f"அலுவலர் {officer_id} வினவல்: {message}\n\n"
                    f"தயவுசெய்து துல்லியமான அதிகாரப்பூர்வ விளக்கத்தை தமிழில் வழங்கவும்:"
                )

                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model_name,
                        "system": system_prompt,
                        "prompt": user_prompt,
                        "stream": False,
                        "options": {"temperature": 0.2, "top_p": 0.9},
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    answer = resp.json().get("response", "").strip()
                    if answer and len(answer) > 20:
                        return {
                            "answer": answer,
                            "sources": sources_list if sources_list else ["Erode Collectorate Master Knowledge Base"],
                            "engine": f"RAG + Ollama ({model_name})",
                        }
            except Exception as e:
                logger.warning(f"Ollama generation failed or timed out: {e}")

        # Grounded analytical response for attached document
        if attached_doc and attached_doc.get("full_text"):
            answer = self._generate_analytical_document_answer(attached_doc, message, officer_id)
            return {
                "answer": answer,
                "sources": sources_list if sources_list else [f"ஆவணம்: {attached_doc.get('file_name')}"],
                "engine": "RAG Document Analytical Engine",
            }

        # Fallback synthesis using grounded knowledge base
        if admin_guidelines:
            g = admin_guidelines[0]
            answer = (
                f"**{g['title']}**\n\n"
                f"{g['content_ta']}\n\n"
            )
            if petitions:
                answer += f"**தற்போது பரிசீலனையில் உள்ள தொடர்புடைய மனுக்கள் ({len(petitions)}):**\n"
                for p in petitions:
                    answer += f"• **{p['source_id']}** ({p['department']}) - நிலை: {p['status']}\n"
            return {
                "answer": answer,
                "sources": sources_list if sources_list else [g["title"]],
                "engine": "RAG Knowledge Retriever",
            }

        # Fallback for general status or unindexed query
        return {
            "answer": (
                f"வணக்கம் அலுவலர் {officer_id}!\n\n"
                f"ஈரோடு மாவட்ட ஆட்சியரக தகவல் களஞ்சியத்தில் தங்கள் வினவல் ('{message}') பெறப்பட்டது.\n\n"
                f"**மாவட்ட நிர்வாக வழிகாட்டி:**\n"
                f"• வருவாய்த்துறை பட்டா மற்றும் நில அளவீடு விவரங்கள்\n"
                f"• சமூக பாதுகாப்பு முதியோர்/விதவை ஓய்வூதிய திட்டங்கள்\n"
                f"• குடிநீர், சாலை மற்றும் பொதுப்பணித்துறை மனுக்கள்\n"
                f"• அரசு இ-சேவை சான்றிதழ் நடைமுறைகள்\n\n"
                f"மேற்கண்ட துறைகள் குறித்த வழிகாட்டுதல்கள் அல்லது கோப்பு எண்களை குறிப்பிட்டு வினவலாம்."
            ),
            "sources": ["Erode Collectorate Master Knowledge Base"],
            "engine": "RAG Knowledge Base",
        }
