"""Department Classification Layer: Deterministic Tamil Rule Engine + Guarded Ollama Qwen2.5 Fallback."""

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

import requests

import config
from pipeline.database import log_audit, save_classification, update_source_status

logger = logging.getLogger("DepartmentClassifier")

# Tamil Department Keyword Clusters
KEYWORD_CLUSTERS = {
    "வருவாய்": [
        "நிலம்", "பட்டா", "சர்வே", "சொத்து", "வரி", "ஆதாயம்", "வட்டாட்சியர்",
        "கிராம நிர்வாக அலுவலர்", "சிட்டா", "அடங்கல்", "புல எண்", "ஆக்கிரமிப்பு",
        "வருவாய் கோட்டாட்சியர்", "நத்தம்", "தரிசு", "புன்செய்", "நன்செய்", "REV"
    ],
    "சமூக_நலன்": [
        "உதவித்தொகை", "முதியோர்", "மாற்றுத்திறனாளி", "விதவை", "முதியோர் உதவித்தொகை",
        "கல்வி உதவி", "பெண் குழந்தை", "திருமண உதவி", "மகளிர் உரிமை", "தையல் இயந்திரம்",
        "உழவர் பாதுகாப்பு", "SOC"
    ],
    "பொதுப்பணித்துறை": [
        "சாலை", "குடிநீர்", "பாலம்", "கட்டிடம்", "சாக்கடை", "தெருவிளக்கு", "மின் விளக்கு",
        "மின்விளக்கு", "மாநகராட்சி", "நகராட்சி", "ஊராட்சி", "விளக்கு", "குழாய்",
        "மேல்நிலை நீர்த்தேக்கத் தொட்டி", "சாக்கடை கால்வாய்", "திடக்கழிவு", "மின்சாரம்", "தெரு", "PWD"
    ],
    "காவல்துறை": [
        "புகார்", "குற்றம்", "போலீஸ்", "நடவடிக்கை", "மோசடி", "அத்துமீறல்",
        "எஃப்ஐஆர்", "விசாரணை", "கட்டப்பஞ்சாயத்து", "நில அபகரிப்பு", "பாதுகாப்பு", "POL"
    ],
    "பதிவுத்துறை": [
        "பதிவு", "பத்திரம்", "விற்பனை", "கிரயம்", "வில்லங்கம்", "சார்பதிவாளர்",
        "தானப் பத்திரம்", "முத்திரைத் தாள்", "வழிகாட்டி மதிப்பு", "REG"
    ],
}

HIGH_PRIORITY_KEYWORDS = [
    "அவசரம்", "உடனடி", "உயிர்", "அபாயம்", "மாற்றுத்திறனாளி", "மோசடி", "வன்முறை",
    "ஆபத்து", "மருத்துவ உதவி", "பாதிக்கப்பட்டு"
]


class DepartmentClassifier:
    """Classifies Tamil grievance petitions into departments with priority assignment."""

    def __init__(
        self,
        ollama_url: str = config.OLLAMA_API_BASE,
        ollama_model: str = config.OLLAMA_MODEL,
        ollama_timeout: int = config.OLLAMA_TIMEOUT_SEC,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.ollama_timeout = ollama_timeout

    def _calculate_rule_scores(self, text: str) -> Dict[str, int]:
        """Count keyword occurrences across departmental clusters."""
        scores = {}
        for dept, keywords in KEYWORD_CLUSTERS.items():
            count = 0
            for kw in keywords:
                count += len(re.findall(re.escape(kw), text))
            scores[dept] = count
        return scores

    def _determine_priority(self, text: str, department: str) -> str:
        """Determine petition priority based on urgent indicators."""
        for kw in HIGH_PRIORITY_KEYWORDS:
            if kw in text:
                return "HIGH"
        if department in ("காவல்துறை", "சமூக_நலன்"):
            return "MEDIUM"
        return "LOW"

    def _query_ollama_fallback(self, text: str) -> Tuple[str, str, float]:
        """Query local Ollama (qwen2.5:7b) for fallback classification with strict anti-hallucination rules."""
        prompt = f"""நீ ஒரு தமிழ்நாடு அரசு ஆவண தயாரிப்பு முறை. 
கீழ்கண்ட விதிகளை கண்டிப்பாக பின்பற்று:
1. வழங்கப்பட்ட உரையில் இல்லாத எந்த தகவலையும் உருவாக்காதே.
2. தேதி, கோப்பு எண், கைபேசி எண், ஆதார் போன்ற உணர்திறன் வாய்ந்த தகவல்களை 
   கண்டிப்பாக கண்டுபிடித்த உரையில் இருந்து மட்டுமே எடு.
3. தகவல் இல்லை என்றால் "[தகவல் இல்லை]" என குறிப்பிடு.
4. JSON வடிவத்தில் மட்டுமே விடையளி.

வழங்கப்பட்ட துறைகளில் இருந்து ஒன்றை தேர்ந்தெடு:
[வருவாய், சமூக_நலன், பொதுப்பணித்துறை, காவல்துறை, பதிவுத்துறை, பொது_வழக்கு]

JSON வடிவம்:
{{"department": "...", "priority": "HIGH/MEDIUM/LOW", "confidence": 0.85}}

மனு உரை:
{text[:800]}
"""
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "15m",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 80,
                        "num_ctx": 1024,
                    },
                },
                timeout=min(self.ollama_timeout, 8),
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_response = data.get("response", "{}")
                parsed = json.loads(raw_response)
                dept = parsed.get("department", "பொது_வழக்கு")
                priority = parsed.get("priority", "MEDIUM")
                confidence = float(parsed.get("confidence", 0.70))

                if dept not in config.DEPARTMENTS:
                    dept = "பொது_வழக்கு"
                if priority not in config.PRIORITY_LEVELS:
                    priority = "MEDIUM"

                return dept, priority, confidence

        except Exception as e:
            logger.warning(f"Ollama fallback query failed or timed out: {e}")

        # Guarded Fail-Safe
        return "பொது_வழக்கு", "MEDIUM", 0.50

    def classify(self, text: str, source_id: str) -> Dict[str, Any]:
        """Classify petition using rule-based scoring first; trigger guarded Ollama fallback if score < 1."""
        scores = self._calculate_rule_scores(text)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_dept, top_score = sorted_scores[0] if sorted_scores else ("பொது_வழக்கு", 0)

        if top_score >= 1:
            # High-confidence Rule Route
            priority = self._determine_priority(text, top_dept)
            rule_score = top_score
            ai_confidence = 1.0
            final_decision = "rule"
            selected_dept = top_dept
        else:
            # Guarded AI Fallback
            ai_dept, ai_priority, ai_conf = self._query_ollama_fallback(text)
            rule_score = top_score
            ai_confidence = ai_conf

            if ai_conf >= config.AI_CONFIDENCE_THRESHOLD:
                selected_dept = ai_dept
                priority = ai_priority
                final_decision = "ai"
            else:
                selected_dept = "பொது_வழக்கு"
                priority = "MEDIUM"
                final_decision = "rule"

        # Persist classification
        save_classification(
            source_id=source_id,
            department=selected_dept,
            priority=priority,
            rule_score=rule_score,
            ai_confidence=ai_confidence,
            final_decision=final_decision,
        )
        update_source_status(source_id=source_id, status="classified")
        log_audit(
            source_id=source_id,
            action="CLASSIFIED",
            officer_id="SYSTEM_CLASSIFIER",
            details=f"Classified to {selected_dept} (Priority: {priority}, Decision: {final_decision}, Score: {rule_score})",
        )

        return {
            "source_id": source_id,
            "department": selected_dept,
            "priority": priority,
            "rule_score": rule_score,
            "ai_confidence": ai_confidence,
            "final_decision": final_decision,
        }
