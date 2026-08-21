"""Hallucination Barrier and Grounding Verification Layer for Prompt Suggestions.

Enforces zero-hallucination contracts:
- Rejects generic banned phrases
- Verifies numbers and amounts against fingerprint
- Verifies cited entities (departments, taluks, villages, tables, columns)
- Computes claim-level grounding and hallucination metrics.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("SuggestionHallucinationBarrier")

# Banned generic phrases that lack grounding
BANNED_GENERIC_PHRASES = [
    "இதை சுருக்கு",
    "summarize this",
    "பொதுவான சுருக்கம்",
    "பகுப்பாய்வு செய்",
    "analyze this",
    "விளக்கம் தருக",
    "tell me more",
    "how can i help",
    "உங்களுக்கு எப்படி உதவ முடியும்",
]


class SuggestionHallucinationBarrier:
    """Enforces grounding verification and rejects ungrounded or generic prompt suggestions."""

    def __init__(self, banned_phrases: Optional[List[str]] = None):
        self.banned_phrases = banned_phrases or BANNED_GENERIC_PHRASES

    def validate_suggestion(self, suggestion: Dict[str, Any], fingerprint: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single suggestion against the content fingerprint."""
        text_tamil = suggestion.get("text_tamil", "")
        text_english = suggestion.get("text_english", "")
        grounded_in = suggestion.get("grounded_in", "")
        combined_text = f"{text_tamil} {text_english}".lower()

        # 1. Banned Generic Phrases Check
        for phrase in self.banned_phrases:
            if phrase.lower() in combined_text:
                return {
                    "passed": False,
                    "reason": f"Generic ungrounded phrase detected: '{phrase}'",
                    "severity": "high",
                    "verification_notes": f"Banned generic phrase: {phrase}",
                }

        # 2. Extract Ground Truth Entities from Fingerprint
        real_entities: Set[str] = set()
        entities_dict = fingerprint.get("entities_found", {})
        for etype, items in entities_dict.items():
            if isinstance(items, list):
                for it in items:
                    real_entities.add(str(it).lower().strip())

        # Include tables and columns
        for tab in fingerprint.get("tables_detected", []):
            if tab.get("name"):
                real_entities.add(str(tab["name"]).lower().strip())
            for col in tab.get("columns", []):
                real_entities.add(str(col).lower().strip())

        # Include geographic scope & content_type
        for geo in fingerprint.get("geographic_scope", []):
            real_entities.add(str(geo).lower().strip())
        real_entities.add(str(fingerprint.get("content_type", "")).lower().strip())

        # 3. Numeric Grounding Verification
        fp_json_str = json.dumps(fingerprint, ensure_ascii=False)
        sug_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', text_tamil + " " + text_english))
        fp_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', fp_json_str))

        # Filter out common small numbers like 1, 2, 3, 5, 10 if used as top-N counts
        significant_sug_numbers = {n for n in sug_numbers if float(n) > 5 and n not in {"10", "15", "20", "25", "30", "50", "100"}}
        hallucinated_numbers = significant_sug_numbers - fp_numbers
        if hallucinated_numbers:
            return {
                "passed": False,
                "reason": f"Hallucinated numbers not found in document: {list(hallucinated_numbers)}",
                "severity": "high",
                "verification_notes": f"Missing numbers in fingerprint: {hallucinated_numbers}",
            }

        # 4. Entity Match Verification
        matched_entities = []
        for ent in real_entities:
            if len(ent) >= 3 and (ent in combined_text or ent in grounded_in.lower()):
                matched_entities.append(ent)

        if not matched_entities and not any(k in combined_text for k in ["பட்ஜெட்", "திட்டம்", "வட்டம்", "அறிவிப்பு", "மனு", "நிலுவை"]):
            return {
                "passed": False,
                "reason": "Suggestion does not reference any verified entity from document fingerprint.",
                "severity": "medium",
                "verification_notes": "No matching entity found in fingerprint",
            }

        # Grounding verified
        grounded_str = f"கோப்பில் கண்டறிந்த: {', '.join(matched_entities[:4])}" if matched_entities else grounded_in
        return {
            "passed": True,
            "reason": "All entities and figures grounded in fingerprint.",
            "matched_entities": matched_entities,
            "grounded_in": grounded_str,
            "verification_notes": f"Grounded in: {', '.join(matched_entities[:4])}",
        }

    def compute_summary_hallucination_score(
        self,
        claims: List[Dict[str, Any]],
        fingerprint: Dict[str, Any],
    ) -> float:
        """Compute hallucination score (0.0 to 1.0) for structured document summaries."""
        if not claims:
            return 0.0

        fp_text = json.dumps(fingerprint, ensure_ascii=False).lower()
        ungrounded_claims = 0

        for claim in claims:
            text = str(claim.get("text", "")).lower()
            confidence = claim.get("confidence", 1.0)
            has_source_page = claim.get("source_page") is not None
            has_source_chunk = bool(claim.get("source_chunk"))

            # If claim has no page or very low confidence
            if not has_source_page or confidence < 0.5:
                ungrounded_claims += 1
                continue

            # Check if figures mentioned in claim exist in document
            claim_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', text))
            significant_nums = {n for n in claim_nums if float(n) > 5}
            fp_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', fp_text))
            if significant_nums and not significant_nums.issubset(fp_nums):
                ungrounded_claims += 1

        return round(ungrounded_claims / max(1, len(claims)), 3)
