"""Collectorate Administrative RAG & Knowledge Engine.

Integrates:
1. Citizen petition & grievance database retrieval (SQLite: sources, ocr_results, entities, classifications, drafts)
2. District dataset analytics retrieval (Taluk schemes, beneficiary lists, pendency figures)
3. Official Tamil administrative knowledge & procedural SOPs (Revenue, Patta, Pension, PWD, Certificates)
4. Local Ollama LLM generation (with automatic model detection and fallback)
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
        "keywords": ["பட்டா", "நில அளவீடு", "சர்வே", "புல எண்", "சிட்டா", "அடங்கல்", "patta", "survey", "land", "revenue"],
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
        "keywords": ["முதியோர் உதவித்தொகை", "விதவை", "மாற்றுத்திறனாளி", "ஓய்வூதியம்", "pension", "welfare", "social", "oap"],
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
        "keywords": ["சாலை", "குடிநீர்", "சாக்கடை", "தெருவிளக்கு", "பாலம்", "pwd", "road", "water", "drainage"],
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
        self.preferred_models = [
            "mistral:7b-instruct-q4_K_M",
            "phi4-mini:latest",
            "llama3.2:1b",
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

    def get_attached_doc_context(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve extracted content, OCR text, and fingerprint of an attached file."""
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
            if not row:
                return None

            from pipeline.database import get_content_fingerprint
            fp = get_content_fingerprint(source_id) or {}
            return {
                "source_id": row["source_id"],
                "raw_path": row["raw_path"],
                "full_text": row["full_text"] or "",
                "department": row["department"] or "பொது",
                "fingerprint": fp,
            }
        except Exception as e:
            logger.warning(f"Error fetching attached doc context: {e}")
            return None
        finally:
            conn.close()

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

        # 1. Attached document context (if provided)
        attached_doc = self.get_attached_doc_context(source_id) if source_id else None
        if attached_doc:
            doc_text = attached_doc["full_text"][:2000] if attached_doc["full_text"] else ""
            fp_info = ""
            if attached_doc["fingerprint"]:
                fp = attached_doc["fingerprint"]
                fp_info = f" (வகை: {fp.get('content_type')}, முக்கிய தலைப்புகள்: {', '.join(fp.get('detected_schemes', []) or fp.get('key_entities', []) or [])})"

            context_blocks.append(
                f"【இணைக்கப்பட்ட கோப்பு: {attached_doc['source_id']}{fp_info}】\n"
                f"{doc_text if doc_text else 'கோப்பு வெற்றிகரமாக இணைக்கப்பட்டு பகுப்பாய்வு செய்யப்பட்டது.'}"
            )
            sources_list.append(f"இணைக்கப்பட்ட ஆவணம்: {Path(attached_doc['raw_path']).name}")

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

        # Attempt LLM generation if Ollama model available
        model_name = self._get_active_ollama_model()
        if model_name:
            try:
                system_prompt = (
                    "You are an expert AI administrative assistant for the Erode District Collectorate (ஈரோடு மாவட்ட ஆட்சியரகம்), Tamil Nadu. "
                    "Provide clear, professional, well-structured, and helpful answers in pure official Tamil (தமிழ்). "
                    "Always base your answers strictly on the provided Collectorate Guidelines, Attached Document, and Database Context. "
                    "Include relevant procedural steps, required documents, responsible officers (Tahsildar, VAO, RDO), and timelines when applicable."
                )
                user_prompt = (
                    f"Context / ஆவண தகவல்கள்:\n{combined_context if combined_context else 'பொதுவான மாவட்ட நிர்வாக விதிமுறைகள்'}\n\n"
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
                    timeout=25,
                )
                if resp.status_code == 200:
                    answer = resp.json().get("response", "").strip()
                    if answer:
                        return {
                            "answer": answer,
                            "sources": sources_list if sources_list else ["Erode Collectorate Master Knowledge Base"],
                            "engine": f"RAG + Ollama ({model_name})",
                        }
            except Exception as e:
                logger.warning(f"Ollama generation failed or timed out: {e}")

        # Grounded response for attached document
        if attached_doc:
            doc_name = Path(attached_doc['raw_path']).name
            doc_snippet = attached_doc["full_text"][:400] if attached_doc["full_text"] else "கோப்பு பகுப்பாய்வு முடிந்தது."
            return {
                "answer": (
                    f"📄 **இணைக்கப்பட்ட ஆவணம்:** `{doc_name}`\n\n"
                    f"**சுருக்கக் குறிப்பு:**\n{doc_snippet}...\n\n"
                    f"📌 இக்கோப்பு தொடர்பான துறை சார்ந்த தகவல்கள் மற்றும் பரிந்துரை வினவல்களை கீழே தேர்ந்தெடுக்கலாம்."
                ),
                "sources": sources_list if sources_list else [f"ஆவணம்: {doc_name}"],
                "engine": "RAG Document Extractor",
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
