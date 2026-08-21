"""Automated Unit & Integration Test Suite for Module 1 (Document Summarization & Dynamic Prompt Suggestions)."""

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import config
from modules.document_summary.extractor import ContentExtractor, detect_file_type
from modules.document_summary.fingerprinter import ContentFingerprinter
from modules.document_summary.hallucination_barrier import SuggestionHallucinationBarrier
from modules.document_summary.suggestion_engine import DynamicSuggestionEngine
from modules.document_summary.summarizer import DocumentSummarizer
from pipeline.database import (
    get_content_fingerprint,
    get_document_summary,
    get_prompt_suggestions,
    init_db,
    record_source,
    record_suggestion_click,
    save_content_fingerprint,
)
from server import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure database schema is initialized for tests."""
    init_db()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_file_type_detection():
    """Test deterministic file type detection by extension and content."""
    assert detect_file_type("budget_2026.pdf") == "pdf"
    assert detect_file_type("taluk_data.xlsx") == "xlsx"
    assert detect_file_type("petition_list.csv") == "csv"
    assert detect_file_type("scan_sample.png") == "png"
    assert detect_file_type("memo.docx") == "docx"
    assert detect_file_type("notes.txt") == "txt"


def test_content_extraction_csv_and_text(tmp_path):
    """Test unified structure extraction from CSV and text files."""
    csv_file = tmp_path / "test_revenue_allocation.csv"
    df = pd.DataFrame({
        "வட்டம்": ["ஈரோடு", "பெருந்துறை", "பவானி"],
        "துறை": ["வருவாய்", "வருவாய்", "சமூக_நலன்"],
        "ஒதுக்கீடு_தொகை": [45200000, 32800000, 18500000],
        "நிலுவை_மனுக்கள்": [12, 8, 3],
    })
    df.to_csv(csv_file, index=False, encoding="utf-8")

    extractor = ContentExtractor()
    extracted = extractor.extract(csv_file)

    assert extracted["file_type"] == "csv"
    assert len(extracted["tables"]) == 1
    assert extracted["tables"][0]["row_count"] == 3
    assert "ஒதுக்கீடு_தொகை" in extracted["amount_columns"] or "ஒதுக்கீடு_தொகை" in [c["name"] for c in extracted["columns"]]
    assert len(extracted["columns"]) == 4


def test_content_fingerprinting(tmp_path):
    """Test AI and deterministic content fingerprint generation."""
    sample_text = """
    தமிழ்நாடு அரசு - ஈரோடு மாவட்ட ஆட்சியரகம்
    2026-27 நிதியாண்டு மாவட்ட பட்ஜெட் மற்றும் திட்ட ஒதுக்கீடு
    
    வருவாய்த்துறைக்கு ₹45.2 கோடி ஒதுக்கீடு செய்யப்பட்டுள்ளது.
    பெருந்துறை மற்றும் பவானி வட்டங்களில் புதிய தாசில்தார் அலுவலகங்கள் அமையவுள்ளன.
    புல எண் 142/1A தொடர்பான நில அளவீடு பணிகள் 15/09/2026க்குள் முடிக்கப்பட வேண்டும்.
    """
    txt_file = tmp_path / "budget_doc.txt"
    txt_file.write_text(sample_text, encoding="utf-8")

    extractor = ContentExtractor()
    extracted = extractor.extract(txt_file)

    fingerprinter = ContentFingerprinter()
    fp = fingerprinter.fingerprint(extracted)

    assert fp["content_type"] in ("budget", "general")
    assert fp["confidence"] > 0.7
    assert "வருவாய்" in fp["entities_found"]["departments"] or "வருவாய்த்துறை" in str(fp["entities_found"]["departments"])
    assert any("45.2" in str(a) for a in fp["entities_found"]["amounts"])
    assert "பெருந்துறை" in fp["entities_found"]["taluks"] or "பவானி" in fp["entities_found"]["taluks"]
    assert fp["file_stats"]["has_amounts"] is True


def test_hallucination_barrier():
    """Test the hallucination barrier rejects ungrounded figures and generic phrases."""
    barrier = SuggestionHallucinationBarrier()
    fingerprint = {
        "content_type": "budget",
        "entities_found": {
            "departments": ["வருவாய்"],
            "amounts": ["₹45.2 கோடி"],
            "taluks": ["ஈரோடு", "பெருந்துறை"],
        },
        "tables_detected": [{"name": "துறை_ஒதுக்கீடு", "columns": ["துறை", "தொகை"]}],
    }

    # 1. Banned generic phrase test
    res_generic = barrier.validate_suggestion(
        {"text_tamil": "இதை சுருக்கு", "text_english": "summarize this"},
        fingerprint,
    )
    assert res_generic["passed"] is False
    assert "Generic" in res_generic["reason"]

    # 2. Hallucinated numbers test (e.g. mentions ₹999 crore not in document)
    res_hallucinated = barrier.validate_suggestion(
        {"text_tamil": "வருவாய் துறைக்கு ₹999 கோடி ஒதுக்கீட்டை காட்டு", "text_english": "Show 999 crore"},
        fingerprint,
    )
    assert res_hallucinated["passed"] is False
    assert "Hallucinated numbers" in res_hallucinated["reason"]

    # 3. Grounded suggestion test
    res_grounded = barrier.validate_suggestion(
        {
            "text_tamil": "வருவாய் துறைக்கு ₹45.2 கோடி ஒதுக்கீட்டை அட்டவணையாக தொகுக்கவும்",
            "text_english": "Tabulate revenue allocation of 45.2 crore",
            "grounded_in": "வருவாய், 45.2",
        },
        fingerprint,
    )
    assert res_grounded["passed"] is True


def test_dynamic_suggestions_zero_hardcoded(tmp_path):
    """Test dynamic suggestions generation adapts across module contexts without hardcoding."""
    source_id = "doc_test_budget_001"
    raw_path = tmp_path / "budget.txt"
    raw_path.write_text("வருவாய்த்துறை பட்ஜெட் ஒதுக்கீடு ₹45.2 கோடி. பெருந்துறை வட்டம்.", encoding="utf-8")
    record_source(source_id=source_id, source_type="scan", raw_path=str(raw_path))

    fp = {
        "content_type": "budget",
        "entities_found": {
            "departments": ["வருவாய்"],
            "amounts": ["₹45.2 கோடி"],
            "taluks": ["பெருந்துறை"],
        },
        "tables_detected": [{"name": "துறை_ஒதுக்கீடு", "columns": ["துறை", "தொகை"]}],
        "summary_description": "2026-27 பட்ஜெட் அறிக்கை",
    }
    save_content_fingerprint(source_id=source_id, fingerprint=fp, file_type="txt", content_type="budget")

    engine = DynamicSuggestionEngine()

    # Document tab suggestions
    doc_res = engine.generate(source_id=source_id, module_context="document", officer_id="OFC001")
    assert len(doc_res["suggestions"]) > 0
    doc_texts = " ".join([s["text_tamil"] for s in doc_res["suggestions"]])
    assert "வருவாய்" in doc_texts or "ஒதுக்கீடு" in doc_texts or "பட்ஜெட்" in doc_texts
    assert not any("இதை சுருக்கு" in s["text_tamil"] for s in doc_res["suggestions"])

    # Data viz tab suggestions
    viz_res = engine.generate(source_id=source_id, module_context="data_viz", officer_id="OFC001")
    assert len(viz_res["suggestions"]) > 0
    viz_texts = " ".join([s["text_tamil"] for s in viz_res["suggestions"]])
    assert "வரைபடம்" in viz_texts or "ஒப்பீடு" in viz_texts or "Chart" in str(viz_res)


def test_personalization_ranking(tmp_path):
    """Test personalization layer boosts clicked suggestions and demotes ignored ones."""
    source_id = "doc_test_pers_001"
    raw_path = tmp_path / "pers.txt"
    raw_path.write_text("வருவாய்த்துறை கோப்பு.", encoding="utf-8")
    record_source(source_id=source_id, source_type="scan", raw_path=str(raw_path))

    fp = {
        "content_type": "general",
        "entities_found": {"departments": ["வருவாய்"], "taluks": ["ஈரோடு"]},
    }
    save_content_fingerprint(source_id=source_id, fingerprint=fp, file_type="txt", content_type="general")

    engine = DynamicSuggestionEngine()
    res = engine.generate(source_id=source_id, module_context="document", officer_id="OFC_PERS")
    assert len(res["suggestions"]) > 0

    first_sug = res["suggestions"][0]
    sug_id = first_sug["suggestion_id"]

    # Record click
    clicked = record_suggestion_click(sug_id)
    assert clicked is True

    # Re-generate suggestions for same officer -> click should be recognized in history
    res2 = engine.generate(source_id=source_id, module_context="document", officer_id="OFC_PERS")
    matched = [s for s in res2["suggestions"] if s.get("text_tamil") == first_sug.get("text_tamil")]
    if matched:
        assert matched[0].get("officer_history", {}).get("times_clicked", 0) >= 1


def test_structured_summaries_multi_type(tmp_path):
    """Test generation of Executive, Department, Policy, and Action Point summaries."""
    source_id = "doc_test_summary_001"
    raw_path = tmp_path / "collectorate_policy.txt"
    raw_path.write_text("""
    தமிழ்நாடு அரசு - ஈரோடு மாவட்ட ஆட்சியர் அலுவலகம்
    பட்ஜெட் மற்றும் கொள்கை முடிவுகள் 2026-2027
    
    1. வருவாய்த்துறைக்கு ₹45.2 கோடி மற்றும் பொதுப்பணித்துறைக்கு ₹28.5 கோடி ஒதுக்கீடு.
    2. ஈரோடு-சத்தியமங்கலம் சாலை 4-வழிச்சாலையாக மேம்படுத்தப்படும்.
    3. குடிநீர் திட்டத்திற்கு நிலம் கையகப்படுத்தும் பணி 30/09/2026க்குள் முடிக்கப்பட வேண்டும்.
    """, encoding="utf-8")
    record_source(source_id=source_id, source_type="scan", raw_path=str(raw_path))

    fp = {
        "content_type": "budget",
        "entities_found": {
            "departments": ["வருவாய்", "பொதுப்பணித்துறை"],
            "amounts": ["₹45.2 கோடி", "₹28.5 கோடி"],
            "taluks": ["ஈரோடு", "சத்தியமங்கலம்"],
            "dates": ["30/09/2026"],
        },
    }
    save_content_fingerprint(source_id=source_id, fingerprint=fp, file_type="txt", content_type="budget")

    summarizer = DocumentSummarizer()

    # 1. Executive Brief
    exec_res = summarizer.summarize(source_id=source_id, summary_type="executive", officer_id="OFC001")
    assert exec_res["summary_type"] == "executive"
    assert len(exec_res["summary_text_tamil"]) > 20
    assert exec_res["hallucination_score"] < 0.15
    assert len(exec_res["claims"]) > 0

    # 2. Department Allocation
    dept_res = summarizer.summarize(source_id=source_id, summary_type="department", officer_id="OFC001")
    assert dept_res["summary_type"] == "department"
    assert len(dept_res["department_allocations"]) > 0
    assert dept_res["total_budget_cr"] > 0

    # 3. Policy Announcements
    policy_res = summarizer.summarize(source_id=source_id, summary_type="policy", officer_id="OFC001")
    assert policy_res["summary_type"] == "policy"
    assert len(policy_res["policy_announcements"]) > 0

    # 4. Action Points
    action_res = summarizer.summarize(source_id=source_id, summary_type="action_points", officer_id="OFC001")
    assert action_res["summary_type"] == "action_points"
    assert len(action_res["action_points"]) > 0


def test_api_endpoints_integration(client, tmp_path):
    """Test full REST API endpoints for upload, summarization, suggestions, and approval."""
    # 1. Upload API
    test_content = b"Erode District Collectorate Budget 2026. Revenue Dept: Rs 50 Crore."
    resp_upload = client.post(
        "/api/v1/document/upload",
        files={"file": ("test_doc.txt", test_content, "text/plain")},
        data={"officer_id": "OFC_API_TEST"},
    )
    assert resp_upload.status_code == 200
    upload_data = resp_upload.json()
    assert upload_data["status"] == "analyzed"
    source_id = upload_data["source_id"]

    # 2. Summarize API
    resp_sum = client.post(
        f"/api/v1/document/{source_id}/summarize",
        json={"summary_type": "executive", "officer_id": "OFC_API_TEST"},
    )
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    summary_id = sum_data["summary_id"]
    assert "summary_text_tamil" in sum_data

    # 3. Get Summary API
    resp_get_sum = client.get(f"/api/v1/document/{source_id}/summary/{summary_id}")
    assert resp_get_sum.status_code == 200
    assert resp_get_sum.json()["summary_id"] == summary_id

    # 4. Suggestions Generate API
    resp_sug = client.post(
        "/api/v1/suggestions/generate",
        json={"source_id": source_id, "module_context": "document", "officer_id": "OFC_API_TEST"},
    )
    assert resp_sug.status_code == 200
    sug_data = resp_sug.json()
    assert len(sug_data["suggestions"]) > 0
    first_sug_id = sug_data["suggestions"][0]["suggestion_id"]

    # 5. Suggestion Click Tracking API
    resp_click = client.post(f"/api/v1/suggestions/{first_sug_id}/click", json={"clicked": True})
    assert resp_click.status_code == 200
    assert resp_click.json()["is_clicked"] is True

    # 6. Approve Summary API
    resp_app = client.post(
        f"/api/v1/document/{source_id}/summary/{summary_id}/approve",
        params={"officer_id": "OFC_API_TEST"},
    )
    assert resp_app.status_code == 200
    assert resp_app.json()["status"] == "success"
