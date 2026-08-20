"""Comprehensive Automated Pipeline Tests for Erode District Collectorate Bulk Workflow Module V0.2."""

import os
import sqlite3
from pathlib import Path

import cv2
import numpy as np
import pytest

import config
from pipeline.classification import DepartmentClassifier
from pipeline.database import (
    generate_department_file_number,
    get_db_connection,
    get_imap_cursor,
    get_source_details,
    init_db,
    log_audit,
    record_source,
    update_draft_approval,
    update_imap_cursor,
    update_source_status,
)
from pipeline.extraction import TamilEntityExtractor, compute_entity_confidence, normalize_tamil_date
from pipeline.generation import TamilDraftGenerator, export_draft_to_docx
from pipeline.ingestion import compute_sha256, process_file_path, process_raw_email
from pipeline.ocr_engine import IndicOCREngine
from pipeline.orchestrator import WorkflowPipeline
from pipeline.verhoeff import generate_verhoeff, validate_verhoeff


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(tmp_path_factory):
    """Setup isolated test database and directories."""
    test_dir = tmp_path_factory.mktemp("erode_test")
    test_db = test_dir / "test_collectorate.db"

    # Initialize DB
    init_db(test_db)

    # Point config database path
    original_db = config.DATABASE_PATH
    config.DATABASE_PATH = test_db

    yield

    config.DATABASE_PATH = original_db


class TestDatabaseAndCursor:
    """Test SQLite schema initialization, sequence counters, and checkpoint cursor."""

    def test_schema_tables_exist(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row["name"] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            "sources",
            "ocr_results",
            "entities",
            "classifications",
            "drafts",
            "audit_log",
            "imap_cursor",
            "sequence_counters",
        }
        assert expected_tables.issubset(tables)

    def test_imap_cursor_progression(self):
        initial_uid = get_imap_cursor()
        assert isinstance(initial_uid, int)

        update_imap_cursor(105)
        updated_uid = get_imap_cursor()
        assert updated_uid == 105

        update_imap_cursor(210)
        assert get_imap_cursor() == 210

    def test_sequence_counters(self):
        seq1 = generate_department_file_number("வருவாய்", "OFFICER_01")
        seq2 = generate_department_file_number("வருவாய்", "OFFICER_01")
        seq3 = generate_department_file_number("பொதுப்பணித்துறை", "OFFICER_01")

        assert seq1.startswith("1001/REV/")
        assert seq2.startswith("1002/REV/")
        assert seq3.startswith("1001/PWD/")


class TestVerhoeffAadhaarValidation:
    """Test Verhoeff algorithm compliance for Indian UIDAI Aadhaar validation."""

    def test_valid_verhoeff_aadhaar(self):
        # Generate valid 12-digit number
        base_11 = "21904921402"
        chk = generate_verhoeff(base_11)
        valid_num = f"{base_11}{chk}"
        assert validate_verhoeff(valid_num) is True

    def test_invalid_aadhaar_checksum_rejected(self):
        # Random 12 digits that fail Verhoeff checksum
        assert validate_verhoeff("123456789012") is False
        assert validate_verhoeff("987654321098") is False


class TestConfidenceDampenerAndDates:
    """Test OCR confidence propagation and Tamil date normalization."""

    def test_confidence_dampener_nearby_uncertainty(self):
        clean_text = "மனுதாரர் பெயர்: சுப்பிரமணி வட்டம்: ஈரோடு"
        conf_clean, status_clean = compute_entity_confidence("ஈரோடு", clean_text, base_conf=0.95)
        assert conf_clean == 0.95
        assert status_clean == "verified"

        uncertain_text = "மனுதாரர் பெயர்: சுப்பிரமணி [?] வட்டம்: [?] ஈரோடு [?]"
        conf_damp, status_damp = compute_entity_confidence("ஈரோடு", uncertain_text, base_conf=0.95)
        assert conf_damp < 0.85
        assert status_damp == "suspect"

    def test_tamil_date_normalization(self):
        d1, ambig1 = normalize_tamil_date("28.09.20")
        assert d1 == "28/09/2020"
        assert ambig1 is True

        d2, ambig2 = normalize_tamil_date("15/08/2026")
        assert d2 == "15/08/2026"
        assert ambig2 is False


class TestTamilEntityExtractor:
    """Test deterministic Tamil entity extraction and grounding contracts."""

    def test_valid_aadhaar_redaction(self):
        extractor = TamilEntityExtractor()
        # Generate valid aadhaar
        base = "45678901234"
        chk = generate_verhoeff(base)
        valid_aadhaar = f"{base}{chk}"
        text = f"மனுதாரர்: கந்தசாமி ஆதார் எண்: {valid_aadhaar} கைபேசி: 9842712345"

        sanitized, valid_list = extractor.mask_aadhaar(text)
        assert len(valid_list) == 1
        assert valid_list[0]["masked"] == f"XXXX-XXXX-{valid_aadhaar[-4:]}"

    def test_missing_entities_fallback_to_missing(self):
        extractor = TamilEntityExtractor()
        text = "பொது மனு - எந்த விபரங்களும் இல்லை."
        entities = extractor.extract_entities(text, source_id="test_missing_id")

        assert entities["file_number"] == config.MISSING_DATA_PLACEHOLDER
        assert entities["mobile_number"] == config.MISSING_DATA_PLACEHOLDER
        assert entities["aadhaar_number"] == config.MISSING_DATA_PLACEHOLDER
        assert entities["applicant_name"] == config.MISSING_DATA_PLACEHOLDER


class TestGroundedDraftAndDocxExport:
    """Test Jinja2 grounded template drafting and Word DOCX generation."""

    def test_grounded_drafting_zero_fabrication(self):
        drafter = TamilDraftGenerator()
        record_source("test_source_grounded", "scan", "test.png")
        entities = {
            "applicant_name": "மு. ராமசாமி",
            "date": "19/08/2026",
            "taluk": "மொடக்குறிச்சி",
            "village": "நஞ்சை ஊத்துக்குளி",
            "_grounding_map": {
                "applicant_name": {"value": "மு. ராமசாமி", "source": "ocr", "confidence": 0.88},
                "date": {"value": "19/08/2026", "source": "ocr", "confidence": 0.95},
                "taluk": {"value": "மொடக்குறிச்சி", "source": "ocr", "confidence": 0.99},
            },
        }

        res = drafter.render_draft("test_source_grounded", "வருவாய்", entities)
        draft_text = res["draft_text"]

        assert "மு. ராமசாமி" in draft_text
        assert "மொடக்குறிச்சி" in draft_text
        assert "கைமுறையாக நிரப்பவும்" in draft_text
        assert "560/PWD/2026" not in draft_text

    def test_docx_export_generation(self, tmp_path):
        sample_draft = """தமிழ்நாடு அரசு
மாவட்ட ஆட்சியர் அலுவலகம், ஈரோடு மாவட்டம்
மனு எண்: 1001/REV/2026
நாள்: 19/08/2026
மனுதாரர் பெயர்: மு. ராமசாமி
துறை: வருவாய்"""
        out_docx = tmp_path / "test_output.docx"
        res_path = export_draft_to_docx(sample_draft, "source_123", out_docx)
        assert res_path.exists()
        assert res_path.stat().st_size > 1000


class TestEndToEndPipeline:
    """End-to-end integration test of Ingestion -> OCR -> Extraction -> Drafting -> Correction."""

    def test_full_pipeline_run_and_correction(self, tmp_path):
        pipeline = WorkflowPipeline()

        sample_email = """From: citizen@erode.tn.gov.in
Subject: பட்டா மாறுதல் கோருதல்
Date: Wed, 19 Aug 2026 10:00:00 +0530

மனுதாரர் பெயர்: த. உமா
வட்டம்: ஈரோடு
மனு எண்: 402/REV/2026
""".encode("utf-8")

        source_id, fpath = process_raw_email(sample_email, filename="test_e2e.eml")
        res = pipeline.process_source(source_id, file_path=fpath)

        assert res["status"] == "draft_ready"
        assert res["classification"]["department"] == "வருவாய்"
        assert "த. உமா" in res["draft"]["draft_text"]

        # Test officer inline OCR correction flow
        corrected_text = "மனுதாரர் பெயர்: உ.மா. பாரதியார்\nவட்டம்: மொடக்குறிச்சி\nமனு எண்: 999/REV/2026"
        res_corrected = pipeline.reprocess_from_corrected_ocr(source_id, 1, corrected_text, "DRO_ERODE_01")

        assert "உ.மா. பாரதியார்" in res_corrected["draft"]["draft_text"]
        assert "மொடக்குறிச்சி" in res_corrected["draft"]["draft_text"]
