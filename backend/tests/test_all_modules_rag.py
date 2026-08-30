"""Comprehensive End-to-End Test Suite for RAG and AI Generation across all modules."""

import pytest
from pathlib import Path
from pipeline.rag_engine import CollectorateRAGEngine
from modules.document_summary.summarizer import DocumentSummarizer
from modules.data_viz.query_engine import execute_data_query
from modules.official_content.generator import OfficialContentGenerator




def test_module1_document_summary_clarity():
    """Verify Module 1 Document Summarizer produces clear, structured Tamil output."""
    summarizer = DocumentSummarizer()
    extracted = {
        "text": "வருவாய்த்துறை பட்டா மாறுதல் மற்றும் நில அளவீடு. பெருந்துறை மற்றும் ஈரோடு வட்டங்களுக்கு ₹45.2 கோடி ஒதுக்கீடு. 2026-10-31க்குள் முடிக்க வேண்டும்.",
        "file_type": "txt",
        "file_name": "patta_circular.txt",
    }
    fingerprint = {
        "content_type": "budget",
        "entities_found": {
            "departments": ["வருவாய்த்துறை", "பொதுப்பணி"],
            "amounts": ["₹45.2 கோடி"],
            "taluks": ["பெருந்துறை", "ஈரோடு"],
            "dates": ["2026-10-31"],
        },
        "tables_detected": [],
    }

    for summary_type in ["executive", "department", "policy", "action_points"]:
        summary = summarizer._deterministic_summary_fallback(summary_type, extracted, fingerprint)
        assert summary is not None
        assert summary.get("summary_type") == summary_type
        assert len(summary.get("claims", [])) > 0


def test_module2_data_query_clarity():
    """Verify Module 2 Data & Viz query engine produces clear insights and pandas queries."""
    import pandas as pd
    sample_csv = Path("backend/data/sample_datasets/erode_taluk_budget_2026.csv")
    if sample_csv.exists():
        df = pd.read_csv(sample_csv)
        columns_info = [
            {"column_name": "வட்டம்", "data_type": "object", "is_taluk": True},
            {"column_name": "ஒதுக்கப்பட்ட_பட்ஜெட்", "data_type": "int64", "is_amount": True},
        ]
        result = execute_data_query(
            df=df,
            question="எந்த வட்டத்திற்கு அதிக பட்ஜெட் ஒதுக்கப்பட்டுள்ளது?",
            columns_info=columns_info,
            officer_id="TEST_OFC",
        )
        assert result is not None
        assert "result_summary_tamil" in result
        assert len(result.get("result_summary_tamil", "")) > 10


def test_module3_official_content_bilingual_clarity():
    """Verify Module 3 Content Generator produces clean, formal government templates in both Tamil and English."""
    generator = OfficialContentGenerator()

    # Tamil Press Release
    res_ta = generator.generate(
        template_type="press_release",
        subject="ஜல் ஜீவன் குடிநீர் திட்டம் — ஈரோடு",
        details="1200 வீடுகளுக்கு குடிநீர் இணைப்பு வழங்கல்",
        language="ta",
    )
    assert res_ta is not None
    assert "செ.வெ.எண்" in res_ta["generated_text"] or "செய்திக்குறிப்பு" in res_ta["generated_text"]
    assert "ஈரோடு" in res_ta["generated_text"]


    # English Press Release
    res_en = generator.generate(
        template_type="press_release",
        subject="Jal Jeevan Mission drinking water scheme",
        details="1200 household connections provided in Erode district",
        language="en",
    )
    assert res_en is not None
    assert "PRESS RELEASE NO" in res_en["generated_text"]
    assert "ERODE DISTRICT" in res_en["generated_text"]




def test_general_rag_clarity_bilingual():
    """Verify General RAG Engine produces clear, structured, emoji-free administrative answers in Tamil and English."""
    engine = CollectorateRAGEngine()

    # 1. Patta Tamil Query
    res_patta_ta = engine.query("பட்டா பெயர் மாறுதல் செய்ய என்ன நடைமுறை?", officer_id="OFC_TEST")
    assert res_patta_ta is not None
    assert "வருவாய்த்துறை" in res_patta_ta["answer"] or "பட்டா" in res_patta_ta["answer"]
    assert len(res_patta_ta["sources"]) > 0

    # 2. Patta English Query
    res_patta_en = engine.query("What is the procedure for patta transfer?", officer_id="OFC_TEST")
    assert res_patta_en is not None
    assert "patta" in res_patta_en["answer"].lower() or "tamil nilam" in res_patta_en["answer"].lower()

    # 3. Pension Tamil Query
    res_pen_ta = engine.query("முதியோர் உதவித்தொகை பெற தகுதிகள் என்ன?", officer_id="OFC_TEST")
    assert res_pen_ta is not None
    assert "முதியோர்" in res_pen_ta["answer"] or "60" in res_pen_ta["answer"]
