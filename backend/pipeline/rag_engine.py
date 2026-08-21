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
        # Prioritize faster models for instant responses, fallback to heavier models
        self.preferred_models = [
            "llama3.2:1b",
            "phi4-mini:latest",
            "mistral:7b-instruct-q4_K_M",
            config.OLLAMA_MODEL,
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
            # Clean filename prefix if formatted like doc_xxx_name.pdf
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

    def _generate_analytical_document_answer(self, doc: Dict[str, Any], query: str, officer_id: str) -> str:
        """Generate high-precision analytical response when analyzing an attached document."""
        fname = doc.get("file_name", "ஆவணம்")
        full_text = doc.get("full_text", "")
        fp = doc.get("fingerprint", {}) or {}
        content_type = fp.get("content_type", "அலுவல் ஆவணம்")
        schemes = fp.get("detected_schemes", [])
        entities = fp.get("key_entities", [])
        
        # Clean query
        q_lower = query.lower()
        is_about = any(k in q_lower for k in ["பற்றியது", "about", "விவரம்", "what is", "விளக்கம்", "தலைப்பு"])
        is_action = any(k in q_lower for k in ["நடவடிக்கை", "action", "தேவை", "பரிந்துரை", "செய்ய வேண்டும்", "steps"])
        is_officer = any(k in q_lower for k in ["அலுவலர்", "officer", "பொறுப்பு", "who", "துறை"])

        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        first_few = " ".join(lines[:4]) if lines else full_text[:300]

        parts = []
        parts.append(f"📄 **ஆவணப் பகுப்பாய்வு அறிக்கை (`{fname}`):**\n")

        # 1. Purpose / Summary
        parts.append("📌 **ஆவணத்தின் முக்கிய நோக்கம் / பொருள்:**")
        if first_few:
            parts.append(f"• {first_few[:350]}...\n")
        else:
            parts.append(f"• ஈரோடு மாவட்ட நிர்வாகம் தொடர்பான `{content_type}` ஆவணம்.\n")

        # 2. Identified Category & Schemes
        if schemes or entities or content_type:
            parts.append("🏛️ **துறை / வகைப்பாடு:**")
            parts.append(f"• வகை: **{content_type.upper()}**")
            if schemes:
                parts.append(f"• தொடர்புடைய திட்டங்கள் / தலைப்புகள்: {', '.join(schemes)}")
            if entities:
                parts.append(f"• குறிப்பிடப்பட்டுள்ள முக்கிய பிரிவுகள்: {', '.join(entities[:5])}")
            parts.append("")

        # 3. Action Points / Next Steps
        parts.append("📋 **தேவைப்படும் தொடர் நடவடிக்கைகள் (Action Points):**")
        if is_action or is_about or not lines:
            parts.append("1. **சரிபார்த்தல்:** ஆவணத்தில் உள்ள விவரங்களை தொடர்புடைய வட்டாட்சியர் / துறை அலுவலக கோப்புகளுடன் ஒப்பிட்டு சரிபார்த்தல்.")
            parts.append("2. **அலுவல் குறிப்பு (Note Sheet) தயாரிப்பு:** மாவட்ட ஆட்சியரின் பார்வைக்கு முன்வைக்க குறிப்பு தாள் தயாரித்தல்.")
            parts.append("3. **பதில் வரைவு அல்லது சுற்றறிக்கை:** உரிய படிவத்தில் (Docx/PDF) பதில் அல்லது ஆணை ஆவணம் உருவாக்குதல்.")
        else:
            for idx, line in enumerate(lines[:3], start=1):
                parts.append(f"{idx}. {line[:120]}")

        parts.append("\n💡 *மேற்கண்ட ஆவணத்தின்படி வரைவு அறிக்கை அல்லது DOCX ஆவணம் உருவாக்க 'Official Content' பகுதியை பயன்படுத்தலாம்.*")

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
                    f"ஈரோடு மாவட்ட ஆட்சியரக AI நிர்வாக உதவியாளருக்கு தங்களை வரவேற்கிறோம். நான் தங்களுக்கு எவ்வாறு உதவ முடியும்?\n\n"
                    f"🏛️ **நான் உதவக்கூடிய முக்கிய பகுதிகள்:**\n"
                    f"• **ஆவண பகுப்பாய்வு & வினா-விடை:** கோப்புகளை இணைத்து (PDF, Word, Scan) சுருக்கம் மற்றும் ஆலோசனைகளைப் பெறலாம்.\n"
                    f"• **வருவாய்த்துறை & பட்டா வழிகாட்டுதல்கள்:** பட்டா மாறுதல், நில அளவீடு விதிமுறைகள்.\n"
                    f"• **சமூக நல திட்டங்கள்:** முதியோர்/விதவை ஓய்வூதியம், மாற்றுத்திறனாளி உதவித்தொகை.\n"
                    f"• **அலுவல் ஆணைகள் & வரைவுகள்:** செய்தி வெளியீடு, சுற்றறிக்கை, கூட்டக் குறிப்புகள் தயாரிப்பு.\n\n"
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
                    "Provide clear, professional, well-structured, and helpful answers in pure official Tamil (தமிழ்). "
                    "Always base your answers strictly on the provided Collectorate Guidelines, Attached Document, and Database Context. "
                    "If a document is attached, directly answer the officer's specific question regarding that document with key details, summary, and action items."
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
                f"📌 **{g['title']}**\n\n"
                f"{g['content_ta']}\n\n"
            )
            if petitions:
                answer += f"📂 **தற்போது பரிசீலனையில் உள்ள தொடர்புடைய மனுக்கள் ({len(petitions)}):**\n"
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
                f"🏛️ **மாவட்ட நிர்வாக வழிகாட்டி:**\n"
                f"• வருவாய்த்துறை பட்டா/நில அளவீடு விவரங்கள்\n"
                f"• சமூக பாதுகாப்பு முதியோர்/விதவை ஓய்வூதிய திட்டங்கள்\n"
                f"• குடிநீர், சாலை மற்றும் பொதுப்பணித்துறை மனுக்கள்\n"
                f"• அரசு இ-சேவை சான்றிதழ் நடைமுறைகள்\n\n"
                f"மேற்கண்ட துறைகள் குறித்த வழிகாட்டுதல்கள் அல்லது கோப்பு எண்களை குறிப்பிட்டு வினவலாம்."
            ),
            "sources": ["Erode Collectorate Master Knowledge Base"],
            "engine": "RAG Knowledge Base",
        }
