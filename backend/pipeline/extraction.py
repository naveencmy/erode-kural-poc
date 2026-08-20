"""Deterministic Tamil Regex Entity Extractor with Verhoeff Aadhaar Redaction and Confidence Propagation."""

import difflib
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import config
from pipeline.database import log_audit, save_entities
from pipeline.verhoeff import validate_verhoeff

logger = logging.getLogger("TamilEntityExtractor")


def normalize_tamil_date(date_str: str) -> Tuple[str, bool]:
    """Normalize various Tamil date formats (DD.MM.YY, DD/MM/YYYY, etc.) to DD/MM/YYYY and flag ambiguity."""
    if not date_str:
        return "", False
    clean = re.sub(r"[^\d./-]", "", date_str)
    parts = re.split(r"[./-]", clean)
    if len(parts) != 3:
        return date_str, True

    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        is_ambiguous = False
        if y < 100:
            is_ambiguous = True
            if y < 50:
                y += 2000
            else:
                y += 1900

        if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100:
            return f"{d:02d}/{m:02d}/{y:04d}", is_ambiguous
    except Exception:
        pass
    return date_str, True


def compute_entity_confidence(
    entity_text: str,
    full_text: str,
    base_conf: float = 0.95,
    window_chars: int = 25,
) -> Tuple[float, str]:
    """Calculate entity confidence dampened by nearby OCR uncertainty tokens ([?])."""
    if not entity_text or entity_text == config.MISSING_DATA_PLACEHOLDER:
        return 0.0, "missing"

    idx = full_text.find(entity_text)
    if idx == -1:
        return base_conf, "verified" if base_conf >= 0.85 else "suspect"

    start = max(0, idx - window_chars)
    end = min(len(full_text), idx + len(entity_text) + window_chars)
    window_str = full_text[start:end]

    low_conf_count = window_str.count(config.LOW_CONF_FLAG)
    if low_conf_count > 0:
        dampened = max(0.50, base_conf - (0.20 * low_conf_count))
        status = "verified" if dampened >= 0.85 else "suspect"
        return round(dampened, 2), status

    return base_conf, "verified"


class TamilEntityExtractor:
    """Extracts Tamil administrative entities using strict regex contracts, masks PII, and validates locations."""

    def __init__(self, master_locations_db: Optional[Path] = None):
        self.locations_db_path = master_locations_db or config.MASTER_LOCATIONS_DB
        self.taluks, self.villages = self._load_master_locations()

        # Deterministic Regex Patterns
        self.PAT_FILE_NO = re.compile(r"\b(\d{1,5}/[A-Z]{2,5}/\d{4})\b")
        self.PAT_DATE = re.compile(r"\b(\d{1,2}[./-]\d{1,2}[./-](?:\d{4}|\d{2}))\b")
        self.PAT_SURVEY_NO = re.compile(r"\b(\d{3}/\d{1,2}[A-Z]?)\b")
        self.PAT_MOBILE = re.compile(r"\b(?:(?:\+91|0)?([6-9]\d{9}))\b")
        self.PAT_AADHAAR = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")

        # Tamil Applicant Name Patterns
        self.PAT_NAME = re.compile(
            r"(?:அனுப்புநர்|விண்ணப்பதாரர்|மனுதாரர்(?:\s+பெயர்)?|பெயர்|திரு|திருமதி|செல்வி)\s*[:\-]?\s*([^\r\n,;:\(\)\d/]{2,40})",
            re.UNICODE,
        )

    def _load_master_locations(self) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
        """Load taluks and villages from master_locations.db."""
        taluks = {}
        villages = []
        if not self.locations_db_path.exists():
            logger.warning(f"Master locations DB not found at {self.locations_db_path}")
            return taluks, villages

        try:
            conn = sqlite3.connect(str(self.locations_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT id, taluk_ta, taluk_en FROM taluks")
            for row in cursor.fetchall():
                taluks[row["taluk_ta"]] = row["taluk_en"]
                taluks[row["taluk_en"].lower()] = row["taluk_ta"]

            cursor.execute("""
                SELECT v.village_ta, v.village_en, v.firka, t.taluk_ta, t.taluk_en
                FROM villages v
                JOIN taluks t ON v.taluk_id = t.id
            """)
            for row in cursor.fetchall():
                villages.append(dict(row))

            conn.close()
        except Exception as e:
            logger.error(f"Error loading master locations: {e}")

        return taluks, villages

    def mask_aadhaar(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Identify Aadhaar numbers, validate via Verhoeff algorithm, and mask to XXXX-XXXX-1234."""
        valid_aadhaars = []

        def repl(match):
            val = match.group(1)
            digits = re.sub(r"\s+", "", val)
            if len(digits) == 12 and validate_verhoeff(digits):
                masked = f"XXXX-XXXX-{digits[-4:]}"
                valid_aadhaars.append({
                    "raw_digits": digits,
                    "masked": masked,
                    "source_chunk": match.group(0),
                })
                return masked
            return val

        redacted_text = self.PAT_AADHAAR.sub(repl, text)
        return redacted_text, valid_aadhaars

    def match_location(self, text: str) -> Dict[str, Any]:
        """Fuzzy-match taluks and revenue villages from text against Erode District master data."""
        extracted_village = config.MISSING_DATA_PLACEHOLDER
        extracted_taluk = config.MISSING_DATA_PLACEHOLDER
        status = "missing"
        confidence = 0.0
        source_chunk = ""

        # 1. Look for explicit field labels
        pat_v_label = re.search(r"(?:கிராமம்|வருவாய்\s+கிராமம்|ஊர்)\s*[:\-]?\s*([^\r\n,;:\(\)\d]+)", text)
        pat_t_label = re.search(r"(?:வட்டம்|தாலுகா)\s*[:\-]?\s*([^\r\n,;:\(\)\d]+)", text)

        explicit_v_text = pat_v_label.group(1).strip() if pat_v_label else ""
        explicit_t_text = pat_t_label.group(1).strip() if pat_t_label else ""

        # Check explicit village label against master villages
        if explicit_v_text:
            for v in self.villages:
                if v["village_ta"] in explicit_v_text or explicit_v_text in v["village_ta"]:
                    extracted_village = v["village_ta"]
                    extracted_taluk = v["taluk_ta"]
                    confidence = 0.99
                    status = "verified"
                    source_chunk = pat_v_label.group(0)
                    break
            if status == "missing":
                for v in self.villages:
                    score = difflib.SequenceMatcher(None, explicit_v_text, v["village_ta"]).ratio()
                    if score >= 0.75:
                        extracted_village = v["village_ta"]
                        extracted_taluk = v["taluk_ta"]
                        confidence = round(score, 2)
                        status = "verified" if score >= 0.85 else "suspect"
                        source_chunk = pat_v_label.group(0)
                        break

        # Check explicit taluk label
        if explicit_t_text and status == "missing":
            for t_ta, t_en in self.taluks.items():
                if t_ta in explicit_t_text or explicit_t_text in t_ta:
                    extracted_taluk = t_ta
                    confidence = 0.99
                    status = "verified"
                    source_chunk = pat_t_label.group(0)
                    break

        # 2. Match longest village first
        if status == "missing":
            sorted_villages = sorted(self.villages, key=lambda v: len(v["village_ta"]), reverse=True)
            for v in sorted_villages:
                if v["village_ta"] in text:
                    extracted_village = v["village_ta"]
                    extracted_taluk = v["taluk_ta"]
                    confidence = 0.95
                    status = "verified"
                    source_chunk = v["village_ta"]
                    break

        # 3. Match taluk directly
        if extracted_taluk == config.MISSING_DATA_PLACEHOLDER:
            for t_ta, t_en in self.taluks.items():
                if len(t_ta) >= 4 and t_ta in text:
                    extracted_taluk = t_ta
                    if status == "missing":
                        confidence = 0.90
                        status = "verified"
                        source_chunk = t_ta
                    break

        # Check for low confidence dampening
        if source_chunk and source_chunk != config.MISSING_DATA_PLACEHOLDER:
            confidence, status = compute_entity_confidence(source_chunk, text, base_conf=confidence)

        return {
            "village": extracted_village,
            "taluk": extracted_taluk,
            "confidence": confidence,
            "validation_status": status,
            "source_chunk": source_chunk,
        }

    def extract_entities(self, text: str, source_id: str) -> Dict[str, Any]:
        """Extract structured entities with Verhoeff validation, confidence dampening, and grounding provenance."""
        sanitized_text, valid_aadhaars = self.mask_aadhaar(text)
        entities_list: List[Dict[str, Any]] = []
        structured_entities: Dict[str, Any] = {}
        grounding_map: Dict[str, Any] = {}

        # 1. File Number (Ground from OCR; if missing -> None, do not fabricate)
        file_match = self.PAT_FILE_NO.search(sanitized_text)
        if file_match:
            val = file_match.group(1)
            conf, status = compute_entity_confidence(val, sanitized_text, base_conf=0.98)
            structured_entities["file_number"] = val
            entities_list.append({
                "entity_type": "file_number",
                "entity_value": val,
                "confidence": conf,
                "validation_status": status,
                "source_chunk": val,
            })
            grounding_map["file_number"] = {
                "value": val,
                "source": "ocr",
                "confidence": conf,
                "validation_status": status,
                "source_chunk": val,
            }
        else:
            structured_entities["file_number"] = config.MISSING_DATA_PLACEHOLDER
            grounding_map["file_number"] = {
                "value": None,
                "source": None,
                "confidence": 0.0,
                "validation_status": "missing",
                "source_chunk": "",
            }

        # 2. Date (Normalize and check ambiguity)
        date_match = self.PAT_DATE.search(sanitized_text)
        if date_match:
            raw_date = date_match.group(1)
            norm_date, is_ambig = normalize_tamil_date(raw_date)
            base_conf = 0.85 if is_ambig else 0.95
            conf, status = compute_entity_confidence(raw_date, sanitized_text, base_conf=base_conf)
            if is_ambig and status == "verified":
                status = "suspect"

            structured_entities["date"] = norm_date
            entities_list.append({
                "entity_type": "date",
                "entity_value": norm_date,
                "confidence": conf,
                "validation_status": status,
                "source_chunk": raw_date,
            })
            grounding_map["date"] = {
                "value": norm_date,
                "raw_value": raw_date,
                "source": "ocr",
                "confidence": conf,
                "validation_status": status,
                "is_ambiguous": is_ambig,
                "source_chunk": raw_date,
            }
        else:
            system_date = datetime.now().strftime("%d/%m/%Y")
            structured_entities["date"] = system_date
            grounding_map["date"] = {
                "value": system_date,
                "source": "system",
                "confidence": 1.0,
                "validation_status": "verified",
                "source_chunk": "Today's System Date",
            }

        # 3. Survey Number
        survey_match = self.PAT_SURVEY_NO.search(sanitized_text)
        if survey_match:
            val = survey_match.group(1)
            conf, status = compute_entity_confidence(val, sanitized_text, base_conf=0.95)
            structured_entities["survey_number"] = val
            entities_list.append({
                "entity_type": "survey_number",
                "entity_value": val,
                "confidence": conf,
                "validation_status": status,
                "source_chunk": val,
            })
            grounding_map["survey_number"] = {
                "value": val,
                "source": "ocr",
                "confidence": conf,
                "validation_status": status,
                "source_chunk": val,
            }
        else:
            structured_entities["survey_number"] = config.MISSING_DATA_PLACEHOLDER
            grounding_map["survey_number"] = {
                "value": None,
                "source": None,
                "confidence": 0.0,
                "validation_status": "missing",
                "source_chunk": "",
            }

        # 4. Mobile Number
        mobile_match = self.PAT_MOBILE.search(sanitized_text)
        if mobile_match:
            val = mobile_match.group(1)
            conf, status = compute_entity_confidence(val, sanitized_text, base_conf=0.98)
            structured_entities["mobile_number"] = val
            entities_list.append({
                "entity_type": "mobile_number",
                "entity_value": val,
                "confidence": conf,
                "validation_status": status,
                "source_chunk": val,
            })
            grounding_map["mobile_number"] = {
                "value": val,
                "source": "ocr",
                "confidence": conf,
                "validation_status": status,
                "source_chunk": val,
            }
        else:
            structured_entities["mobile_number"] = config.MISSING_DATA_PLACEHOLDER
            grounding_map["mobile_number"] = {
                "value": None,
                "source": None,
                "confidence": 0.0,
                "validation_status": "missing",
                "source_chunk": "",
            }

        # 5. Aadhaar (Verhoeff Checked: only set if mathematically valid)
        if valid_aadhaars:
            aadhaar_info = valid_aadhaars[0]
            masked_val = aadhaar_info["masked"]
            structured_entities["aadhaar_number"] = masked_val
            entities_list.append({
                "entity_type": "aadhaar_number",
                "entity_value": masked_val,
                "confidence": 0.99,
                "validation_status": "verified",
                "source_chunk": aadhaar_info["source_chunk"],
            })
            grounding_map["aadhaar_number"] = {
                "value": masked_val,
                "source": "ocr",
                "confidence": 0.99,
                "validation_status": "verified",
                "source_chunk": aadhaar_info["source_chunk"],
            }
        else:
            structured_entities["aadhaar_number"] = config.MISSING_DATA_PLACEHOLDER
            grounding_map["aadhaar_number"] = {
                "value": None,
                "source": None,
                "confidence": 0.0,
                "validation_status": "missing",
                "source_chunk": "",
            }

        # 6. Applicant Name
        name_match = self.PAT_NAME.search(sanitized_text)
        if name_match:
            raw_name = name_match.group(1).strip()
            first_line = raw_name.splitlines()[0] if raw_name else ""
            clean_name = re.split(r"(?:\s+த/பெ|\s+க/பெ|\s+ம/பெ|\s+W/O|\s+S/O|\s+D/O|/)", first_line, flags=re.IGNORECASE)[0].split(",")[0].split(";")[0].strip()
            clean_name = re.sub(r"\[\?\]", "", clean_name).strip(" :-")
            
            if len(clean_name) >= 3:
                conf, status = compute_entity_confidence(clean_name, sanitized_text, base_conf=0.88)
                structured_entities["applicant_name"] = clean_name
                entities_list.append({
                    "entity_type": "applicant_name",
                    "entity_value": clean_name,
                    "confidence": conf,
                    "validation_status": status,
                    "source_chunk": name_match.group(0),
                })
                grounding_map["applicant_name"] = {
                    "value": clean_name,
                    "source": "ocr",
                    "confidence": conf,
                    "validation_status": status,
                    "source_chunk": name_match.group(0),
                }
            else:
                structured_entities["applicant_name"] = config.MISSING_DATA_PLACEHOLDER
                grounding_map["applicant_name"] = {"value": None, "source": None, "confidence": 0.0, "validation_status": "missing", "source_chunk": ""}
        else:
            structured_entities["applicant_name"] = config.MISSING_DATA_PLACEHOLDER
            grounding_map["applicant_name"] = {"value": None, "source": None, "confidence": 0.0, "validation_status": "missing", "source_chunk": ""}

        # 7. Location Match (Village & Taluk)
        loc = self.match_location(sanitized_text)
        structured_entities["village"] = loc["village"]
        structured_entities["taluk"] = loc["taluk"]

        if loc["village"] != config.MISSING_DATA_PLACEHOLDER:
            entities_list.append({
                "entity_type": "village",
                "entity_value": loc["village"],
                "confidence": loc["confidence"],
                "validation_status": loc["validation_status"],
                "source_chunk": loc["source_chunk"],
            })
            grounding_map["village"] = {
                "value": loc["village"],
                "source": "ocr",
                "confidence": loc["confidence"],
                "validation_status": loc["validation_status"],
                "source_chunk": loc["source_chunk"],
            }
        else:
            grounding_map["village"] = {"value": None, "source": None, "confidence": 0.0, "validation_status": "missing", "source_chunk": ""}

        if loc["taluk"] != config.MISSING_DATA_PLACEHOLDER:
            entities_list.append({
                "entity_type": "taluk",
                "entity_value": loc["taluk"],
                "confidence": loc["confidence"],
                "validation_status": loc["validation_status"],
                "source_chunk": loc["source_chunk"],
            })
            grounding_map["taluk"] = {
                "value": loc["taluk"],
                "source": "ocr" if loc["source_chunk"] else "inferred",
                "confidence": loc["confidence"],
                "validation_status": loc["validation_status"],
                "source_chunk": loc["source_chunk"],
            }
        else:
            grounding_map["taluk"] = {"value": None, "source": None, "confidence": 0.0, "validation_status": "missing", "source_chunk": ""}

        # 8. Grievance Context
        lines = [l.strip() for l in sanitized_text.splitlines() if len(l.strip()) > 10]
        summary = lines[0] if lines else "மனு பரிசீலனை கோருதல்"
        structured_entities["grievance_summary"] = summary
        grounding_map["grievance_summary"] = {
            "value": summary,
            "source": "ocr",
            "confidence": 0.90,
            "validation_status": "verified",
            "source_chunk": summary[:60],
        }

        # Store grounding map in structured entities
        structured_entities["_grounding_map"] = grounding_map

        # Persist extracted entities to SQLite
        save_entities(source_id=source_id, entities_list=entities_list)
        log_audit(
            source_id=source_id,
            action="ENTITIES_EXTRACTED",
            officer_id="SYSTEM_EXTRACTOR",
            details=f"Extracted {len(entities_list)} entities. Valid Verhoeff Aadhaar: {len(valid_aadhaars)}",
        )

        return structured_entities
