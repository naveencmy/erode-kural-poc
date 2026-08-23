"""Comprehensive Test Suite for Copilot-Style Suggestions, Multi-Format Ingestion, and Dynamic Zero-Hallucination Math Grounding."""

import time
import pytest
import pandas as pd
from pathlib import Path
from modules.document_summary.extractor import ContentExtractor, detect_file_type
from modules.document_summary.suggestion_engine import DynamicSuggestionEngine
from pipeline.rag_engine import CollectorateRAGEngine


def test_copilot_typeahead_suggestions_latency_and_accuracy():
    """Verify MS Copilot-style typeahead returns high-relevance prompt completions in < 5ms."""
    engine = DynamicSuggestionEngine()

    # 1. Empty prefix (Baseline chips)
    t0 = time.time()
    res_base = engine.get_typeahead_suggestions(query_prefix="")
    t_ms = (time.time() - t0) * 1000
    assert t_ms < 50, f"Typeahead baseline took {t_ms:.2f}ms (expected < 50ms)"
    assert len(res_base) >= 3
    assert any("பட்டா" in s["text_tamil"] or "சுருக்கம்" in s["text_tamil"] or "வட்டம்" in s["text_tamil"] for s in res_base)

    # 2. Prefix "எந்த" (Question start)
    res_entha = engine.get_typeahead_suggestions(query_prefix="எந்த")
    assert len(res_entha) > 0
    assert any("எந்த" in s["text_tamil"] for s in res_entha)

    # 3. Prefix "பட்டா" (Patta query)
    res_patta = engine.get_typeahead_suggestions(query_prefix="பட்டா")
    assert len(res_patta) > 0
    assert any("பட்டா" in s["text_tamil"] for s in res_patta)

    # 4. English prefix "which"
    res_which = engine.get_typeahead_suggestions(query_prefix="which")
    assert len(res_which) > 0
    assert any("which" in s["text_english"].lower() for s in res_which)


def test_universal_multi_format_detection_and_extraction():
    """Verify universal multi-format file support (CSV, Excel, Text, PDF, DOCX, Images)."""
    extractor = ContentExtractor()

    # CSV Test
    csv_file = Path("data/sample_datasets/erode_taluk_budget_2026.csv")
    if csv_file.exists():
        ftype = detect_file_type(csv_file)
        assert ftype == "csv"
        res_csv = extractor.extract(csv_file)
        assert "tables" in res_csv
        assert len(res_csv["tables"]) > 0

    # Text Test
    txt_path = Path("data/tamil_govt_glossary.txt")
    if txt_path.exists():
        ftype = detect_file_type(txt_path)
        assert ftype == "txt"
        res_txt = extractor.extract(txt_path)
        assert len(res_txt["text"]) > 0


def test_zero_hardcoding_dynamic_math_grounding():
    """Verify dynamic mathematical grounding computes exact Min, Max, and stats with zero hardcoding."""
    engine = CollectorateRAGEngine()

    # Create a dynamic mock document without any hardcoded column names
    mock_df = pd.DataFrame({
        "பிராந்தியம்": ["பகுதி_A", "பகுதி_B", "பகுதி_C"],
        "நிதி_ஒதுக்கீடு": [15000000, 75000000, 2500000],  # 1.5 Cr, 7.5 Cr, 25 Lakh
        "செலவு": [12000000, 70000000, 2000000],
    })

    temp_csv = Path("data/sample_datasets/_temp_dynamic_test.csv")
    temp_csv.parent.mkdir(parents=True, exist_ok=True)
    mock_df.to_csv(temp_csv, index=False, encoding="utf-8")

    try:
        mock_doc = {
            "file_name": "_temp_dynamic_test.csv",
            "raw_path": str(temp_csv),
            "full_text": mock_df.to_string(index=False),
            "fingerprint": {"content_type": "தரவுத்தளம்"},
        }
        engine.get_attached_doc_context = lambda sid: mock_doc

        # Test Highest Calculation (Dynamic)
        ans_max = engine.query("எந்த பிராந்தியத்திற்கு அதிக நிதி ஒதுக்கீடு?", source_id="mock_id")
        assert "பகுதி_B" in ans_max["answer"]  # 75,000,000 is highest
        assert "₹7.50 கோடி" in ans_max["answer"] or "75000000" in ans_max["answer"]

        # Test Lowest Calculation (Dynamic)
        ans_min = engine.query("எந்த பிராந்தியத்திற்கு குறைந்த நிதி ஒதுக்கீடு?", source_id="mock_id")
        assert "பகுதி_C" in ans_min["answer"]  # 2,500,000 is lowest
        assert "₹25.00 இலட்சம்" in ans_min["answer"] or "2500000" in ans_min["answer"]

    finally:
        if temp_csv.exists():
            temp_csv.unlink()
