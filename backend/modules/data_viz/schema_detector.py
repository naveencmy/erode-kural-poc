"""Deterministic Schema Detection Engine for Module 2: Data & Visualization.

Performs deterministic column type detection, special column tagging
(taluk, department, date, amount), and Tamil name normalization without
AI hallucination.
"""

import re
from typing import Any, Dict, List, Tuple
import pandas as pd
import config

TALUK_KEYWORDS = ["வட்டம்", "taluk", "தாலுகா", "தாசில்தார்", "வட்டாட்சியர்", "ஒன்றியம்"]
DEPT_KEYWORDS = ["துறை", "department", "பிரிவு", "துறைப்பெயர்", "அலுவலகம்"]
DATE_KEYWORDS = ["தேதி", "date", "ஆண்டு", "year", "மாதம்", "month", "நாள்", "காலம்"]
AMOUNT_KEYWORDS = ["தொகை", "amount", "பட்ஜெட்", "budget", "செலவு", "செலவினம்", "₹", "rs", "ரூபாய்", "மதிப்பு", "நிதி", "ஒதுக்கீடு", "செலவிடப்பட்ட"]

COLUMN_NAME_MAP = {
    "taluk": "வட்டம்",
    "taluk_name": "வட்டம்",
    "department": "துறை",
    "dept": "துறை",
    "dept_name": "துறை",
    "amount": "தொகை",
    "budget": "பட்ஜெட்_தொகை",
    "allocated_amount": "ஒதுக்கப்பட்ட_தொகை",
    "expenditure": "செலவு_தொகை",
    "date": "தேதி",
    "year": "ஆண்டு",
    "month": "மாதம்",
    "pending_cases": "நிலுவை_வழக்குகள்",
    "total_cases": "மொத்த_வழக்குகள்",
    "resolved_cases": "தீர்க்கப்பட்ட_வழக்குகள்",
    "village": "கிராமம்",
    "panchayat": "ஊராட்சி",
    "beneficiaries": "பயனாளிகள்",
    "applications": "விண்ணப்பங்கள்",
    "status": "நிலை",
    "priority": "முன்னுரிமை",
}


def detect_column_type(series: pd.Series) -> str:
    """
    Priority order for deterministic type detection:
    1. If numeric -> 'number'
    2. If boolean-like -> 'boolean'
    3. If datetime -> 'date'
    4. Else -> 'text'
    """
    non_nulls = series.dropna()
    if len(non_nulls) == 0:
        return "text"

    # Numeric check
    if pd.api.types.is_numeric_dtype(series):
        # Check if boolean represented as 0/1 with distinct count 2 and bool name
        if set(non_nulls.unique()).issubset({0, 1, 0.0, 1.0}) and len(non_nulls.unique()) <= 2:
            return "boolean"
        return "number"

    # Boolean check
    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    # Try numeric conversion for string formatted numbers (e.g. "1,200", "₹5000", "45.5")
    sample_str = non_nulls.astype(str).str.strip().str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False)
    try:
        pd.to_numeric(sample_str)
        return "number"
    except (ValueError, TypeError):
        pass

    # Datetime check
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    # Try parsing dates from string sample
    sample_items = non_nulls.head(10).astype(str).tolist()
    date_matches = 0
    for s in sample_items:
        # Check common formats: DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY
        if re.search(r"^\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}$", s.strip()):
            date_matches += 1
    if date_matches >= max(1, len(sample_items) * 0.8):
        try:
            pd.to_datetime(non_nulls.head(10), dayfirst=True)
            return "date"
        except Exception:
            pass

    return "text"


def detect_special_columns(column_name: str, series: pd.Series) -> Dict[str, bool]:
    """Detect special administrative meanings based on column names and contents."""
    name_lower = str(column_name).lower().strip()
    non_nulls = series.dropna().astype(str).str.strip()
    sample_vals = non_nulls.head(20).tolist()

    is_taluk = False
    is_dept = False
    is_date = False
    is_amount = False

    # Check taluk keywords
    for kw in TALUK_KEYWORDS:
        if kw in name_lower:
            is_taluk = True
            break
    # Or check if contents match Erode taluks
    if not is_taluk and len(sample_vals) > 0:
        taluk_matches = sum(1 for v in sample_vals if any(t in v for t in config.ERODE_TALUKS))
        if taluk_matches >= max(1, len(sample_vals) * 0.4):
            is_taluk = True

    # Check department keywords
    for kw in DEPT_KEYWORDS:
        if kw in name_lower:
            is_dept = True
            break

    # Check date keywords
    for kw in DATE_KEYWORDS:
        if kw in name_lower:
            is_date = True
            break

    # Check amount keywords
    for kw in AMOUNT_KEYWORDS:
        if kw in name_lower:
            is_amount = True
            break

    return {
        "is_taluk_column": is_taluk,
        "is_department_column": is_dept,
        "is_date_column": is_date,
        "is_amount_column": is_amount,
    }


def detect_dataset_language(df: pd.DataFrame) -> str:
    """Detect whether dataset contains Tamil, English, or mixed text."""
    tamil_chars = 0
    total_chars = 0

    # Sample column names and first 5 rows
    text_samples = list(df.columns.astype(str))
    for col in df.select_dtypes(include=["object"]).columns[:5]:
        text_samples.extend(df[col].dropna().head(5).astype(str).tolist())

    for text in text_samples:
        for char in text:
            total_chars += 1
            if "\u0b80" <= char <= "\u0bff":
                tamil_chars += 1

    if total_chars == 0:
        return "en"

    ratio = tamil_chars / total_chars
    if ratio > 0.4:
        return "ta"
    elif ratio > 0.05:
        return "mixed"
    return "en"


def normalize_column_name_tamil(col_name: str) -> str:
    """Return Tamil normalized name for a column if mapped, else original."""
    clean = str(col_name).lower().strip().replace(" ", "_")
    return COLUMN_NAME_MAP.get(clean, str(col_name))
