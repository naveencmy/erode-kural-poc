"""AI-Driven Content Fingerprinter for Government Documents.

Uses local Qwen 2.5 7B with deterministic structural fallback to produce
rich structured metadata fingerprints that drive zero-hardcoded suggestions.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import requests

import config

logger = logging.getLogger("ContentFingerprinter")


class ContentFingerprinter:
    """Produces structured content fingerprints from extracted text and tabular metadata."""

    FINGERPRINT_SYSTEM_PROMPT = """
நீ ஒரு தமிழ்நாடு அரசு தரவு மற்றும் ஆவண பகுப்பாய்வு நிபுணர்.
கீழ்கண்ட கோப்பின் மாதிரி உரை மற்றும் அட்டவணை விவரங்களை முழுமையாக பகுப்பாய்வு செய்து,
ஒரு கட்டமைக்கப்பட்ட JSON சுருக்கத்தை (Fingerprint) மட்டுமே உருவாக்கவும்.

கட்டமைப்பு வடிவம் (Strict JSON only):
{
  "content_type": "budget|policy|petition|land_record|case_tracking|welfare|general",
  "confidence": 0.95,
  "entities_found": {
    "departments": ["வருவாய்", "பொதுப்பணி"],
    "amounts": [45.2, 150.0],
    "dates": ["2026-03-15", "19/08/2026"],
    "villages": ["பெரியசேமூர்", "நஞ்சை ஊத்துக்குளி"],
    "taluks": ["ஈரோடு", "பெருந்துறை", "பவானி"],
    "people": ["ராமசாமி", "செந்தில்நாதன்"],
    "file_numbers": ["1042/REV/2026"]
  },
  "tables_detected": [
    {
      "name": "துறை வாரியான ஒதுக்கீடு",
      "columns": ["துறை", "தொகை", "ஆண்டு"],
      "row_count": 8,
      "contains_amounts": true
    }
  ],
  "time_span": {"start_year": 2024, "end_year": 2027},
  "geographic_scope": ["ஈரோடு", "பெருந்துறை"],
  "key_metrics": ["பட்ஜெட் ஒதுக்கீடு", "நிலுவை மனுக்கள்", "திட்ட மதிப்பீடு"],
  "summary_description": "2026-27 நிதியாண்டுக்கான மாவட்ட பட்ஜெட் மற்றும் திட்ட ஒதுக்கீடுகள் ஆவணம்."
}

விதிகள்:
1. உள்ளடக்கத்தில் உள்ள உண்மையான சொற்கள், எண்கள், பெயர்களை மட்டுமே எடுக்கவும்.
2. கற்பனையாக எதையும் உருவாக்காதே.
3. JSON மட்டுமே வெளியிடு.
"""

    def __init__(
        self,
        ollama_url: str = config.OLLAMA_API_BASE,
        model: str = config.OLLAMA_MODEL,
        timeout: int = config.OLLAMA_TIMEOUT_SEC,
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout

    def fingerprint(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured fingerprint from extracted content via AI with deterministic fallback."""
        text_sample = extracted_content.get("text", "")[:3500]
        tables_sample = extracted_content.get("tables", [])[:3]
        columns_sample = extracted_content.get("columns", [])[:15]

        # 1. Attempt AI analysis via local Ollama
        ai_fp = self._call_ollama_fingerprint(text_sample, tables_sample, columns_sample)
        
        # 2. Extract deterministic base entities & structural stats
        det_fp = self._deterministic_extract(extracted_content)

        # 3. Merge AI output with deterministic ground truth
        final_fp = self._merge_fingerprints(ai_fp, det_fp, extracted_content)

        # 4. Enrich with deterministic file stats
        final_fp["file_stats"] = {
            "file_name": extracted_content.get("file_name", ""),
            "file_type": extracted_content.get("file_type", "unknown"),
            "file_size_bytes": extracted_content.get("file_size_bytes", 0),
            "page_count": extracted_content.get("page_count", 1),
            "text_length": len(extracted_content.get("text", "")),
            "table_count": len(extracted_content.get("tables", [])),
            "has_amounts": len(extracted_content.get("amount_columns", [])) > 0 or len(final_fp["entities_found"].get("amounts", [])) > 0,
        }

        return final_fp

    def _call_ollama_fingerprint(
        self,
        text_sample: str,
        tables_sample: List[Dict[str, Any]],
        columns_sample: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Call Ollama Qwen 2.5 7B to parse content fingerprint."""
        context_str = f"மாதிரி உரை:\n{text_sample}\n\nஅட்டவணைகள்:\n{json.dumps(tables_sample, ensure_ascii=False)}\n\nநெடுவரிசைகள்:\n{json.dumps(columns_sample, ensure_ascii=False)}"
        user_prompt = f"{self.FINGERPRINT_SYSTEM_PROMPT}\n\nஆவண உள்ளடக்கம்:\n{context_str}\n\nJSON விடை:"

        try:
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": user_prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 768},
            }
            resp = requests.post(url, json=payload, timeout=min(self.timeout, 12))
            if resp.status_code == 200:
                raw = resp.json().get("response", "")
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and "content_type" in parsed:
                    return parsed
        except Exception as e:
            logger.debug(f"Ollama fingerprinting call skipped/failed: {e}")

        return None

    def _deterministic_extract(self, extracted_content: Dict[str, Any]) -> Dict[str, Any]:
        """Perform reliable deterministic regex and dictionary entity extraction."""
        full_text = extracted_content.get("text", "")
        text_lower = full_text.lower()

        # Extract Taluks
        found_taluks = []
        for t in config.ERODE_TALUKS:
            if t in full_text or t.lower() in text_lower:
                found_taluks.append(t)

        # Extract Departments
        found_depts = []
        for d_ta in config.DEPARTMENTS.keys():
            if d_ta in full_text or d_ta in text_lower:
                found_depts.append(d_ta)

        # Extract Financial Amounts
        amount_matches = re.findall(
            r'(?:₹\s*|\bRs\.?\s*|\bINR\s*)?(\d+(?:,\d+)*(?:\.\d+)?)\s*(கோடி|லட்சம்|cr|crore|lakh|ரூபாய்)?',
            full_text,
            re.IGNORECASE,
        )
        found_amounts = []
        for num_str, unit in amount_matches:
            try:
                cleaned = num_str.replace(",", "")
                val = float(cleaned)
                if val > 0:
                    unit_lower = (unit or "").lower()
                    if "கோடி" in unit_lower or "cr" in unit_lower:
                        found_amounts.append(f"₹{val} கோடி")
                    elif "லட்சம்" in unit_lower or "lakh" in unit_lower:
                        found_amounts.append(f"₹{val} லட்சம்")
                    elif val >= 1000:
                        found_amounts.append(f"₹{val:,.0f}")
            except Exception:
                continue

        # Extract Dates
        found_dates = list(set(re.findall(r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b', full_text)))

        # Extract File Numbers
        found_files = list(set(re.findall(r'\b\d{1,5}/[A-Za-z\u0B80-\u0BFF]+/\d{4}\b', full_text)))

        # Extract Survey Numbers
        found_surveys = list(set(re.findall(r'(?:புல\s*எண்|சர்வே\s*எண்|survey\s*no\.?)\s*[:\-]?\s*([0-9]+[A-Za-z0-9/_\-]*)', full_text, re.IGNORECASE)))

        # Extract Villages
        village_keywords = ["கிராமம்", "village", "ஊராட்சி", "நஞ்சை", "புன்செய்", "பாளையம்"]
        found_villages = []
        for line in full_text.splitlines():
            for vk in village_keywords:
                if vk in line:
                    match = re.search(r'([^\s,:]+)\s*கிராமம்', line)
                    if match:
                        found_villages.append(match.group(1).strip())

        # Determine Content Type deterministically
        content_type = "general"
        if any(k in text_lower for k in ["பட்ஜெட்", "ஒதுக்கீடு", "வருவு செலவு", "நிதி ஒதுக்கீடு", "budget", "allocation", "expenditure"]):
            content_type = "budget"
        elif any(k in text_lower for k in ["அரசாணை", "கொள்கை", "திட்டம்", "சுற்றறிக்கை", "g.o.", "policy", "circular", "guidelines"]):
            content_type = "policy"
        elif any(k in text_lower for k in ["மனு", "கோரிக்கை", "குறைதீர்க்கும்", "petition", "grievance", "விண்ணப்ப"]):
            content_type = "petition"
        elif any(k in text_lower for k in ["பட்டா", "புல எண்", "சிட்டா", "நில அளவீடு", "சர்வே", "கிரய", "land record", "patta", "chitta"]):
            content_type = "land_record"
        elif any(k in text_lower for k in ["நிலுவை", "வழக்கு", "கோப்புகள் பட்டியல்", "pending", "case tracking"]):
            content_type = "case_tracking"
        elif any(k in text_lower for k in ["உதவித்தொகை", "முதியோர்", "விதவை", "மாற்றுத்திறனாளி", "welfare", "pension"]):
            content_type = "welfare"

        # Tables
        tables = []
        for t in extracted_content.get("tables", []):
            tables.append({
                "name": t.get("name", "Table"),
                "columns": t.get("columns", []),
                "row_count": t.get("row_count", 0),
                "contains_amounts": t.get("contains_amounts", False),
            })

        return {
            "content_type": content_type,
            "confidence": 0.88,
            "entities_found": {
                "departments": list(set(found_depts)),
                "amounts": list(set(found_amounts))[:10],
                "dates": found_dates[:5],
                "villages": list(set(found_villages))[:5],
                "taluks": list(set(found_taluks)),
                "people": [],
                "file_numbers": found_files[:5],
                "survey_numbers": found_surveys[:5],
            },
            "tables_detected": tables,
            "time_span": {"start_year": 2024, "end_year": 2027},
            "geographic_scope": list(set(found_taluks)) or ["ஈரோடு மாவட்டம்"],
            "key_metrics": ["துறை ஒதுக்கீடுகள்", "மனு நிலை", "செயல்பாடுகள்"],
            "summary_description": f"ஈரோடு மாவட்ட ஆட்சியர் அலுவலக ஆவணம் — வகை: {content_type}",
        }

    def _merge_fingerprints(
        self,
        ai_fp: Optional[Dict[str, Any]],
        det_fp: Dict[str, Any],
        extracted_content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge AI and deterministic outputs ensuring no hallucinated entities."""
        if not ai_fp:
            return det_fp

        merged = dict(det_fp)
        merged["content_type"] = ai_fp.get("content_type") or det_fp["content_type"]
        merged["confidence"] = max(ai_fp.get("confidence", 0.8), det_fp["confidence"])
        merged["summary_description"] = ai_fp.get("summary_description") or det_fp["summary_description"]

        if ai_fp.get("time_span"):
            merged["time_span"] = ai_fp["time_span"]

        if ai_fp.get("key_metrics"):
            merged["key_metrics"] = list(set(merged["key_metrics"] + ai_fp["key_metrics"]))

        # Merge entities safely
        ai_entities = ai_fp.get("entities_found", {})
        det_entities = det_fp.get("entities_found", {})

        for k in ["departments", "amounts", "dates", "villages", "taluks", "people", "file_numbers"]:
            ai_vals = ai_entities.get(k, [])
            det_vals = det_entities.get(k, [])
            if isinstance(ai_vals, list) and isinstance(det_vals, list):
                # Filter AI values to ensure they occur in the source text or are valid
                full_text = extracted_content.get("text", "").lower()
                clean_ai_vals = [v for v in ai_vals if str(v).lower() in full_text or any(str(v).lower() in str(c).lower() for c in det_vals)]
                merged["entities_found"][k] = list(set(det_vals + clean_ai_vals))

        if ai_fp.get("tables_detected"):
            merged["tables_detected"] = ai_fp["tables_detected"]

        return merged
