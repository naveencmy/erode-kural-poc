"""Tests for Module 3 — Official Government Content Generator & Exporter."""

import os
from pathlib import Path
import pytest

from modules.official_content.generator import OfficialContentGenerator
from modules.official_content.exporter import export_to_docx, export_to_pdf
from pipeline.database import (
    save_official_content,
    list_official_content,
    get_official_content,
)

@pytest.fixture
def generator():
    return OfficialContentGenerator()

def test_generate_press_release(generator):
    res = generator.generate(
        template_type="press_release",
        subject="ஈரோடு மாவட்ட விவசாயிகள் குறைதீர்க்கும் நாள் கூட்டம்",
        details="மாவட்ட ஆட்சியர் தலைமையில் வருகிற வெள்ளிக்கிழமை காலை 10 மணிக்கு விவசாயிகள் குறைதீர்க்கும் நாள் கூட்டம் நடைபெறும்.",
        officer_id="OFC001",
    )
    assert res["status"] == "generated"
    assert res["ref_number"] != ""
    assert "செய்தி" in res["template_title_ta"]
    assert "விவசாயிகள்" in res["subject"]
    assert len(res["content_body"]) > 20

def test_generate_circular(generator):
    res = generator.generate(
        template_type="circular",
        subject="மழைக்கால முன்னெச்சரிக்கை நடவடிக்கைகள்",
        details="அனைத்து வட்டாட்சியர்களும் தீவிர கண்காணிப்பில் ஈடுபட வேண்டும்.",
        officer_id="OFC001",
    )
    assert res["status"] == "generated"
    assert "CIR" in res["ref_number"]
    assert "சுற்றறிக்கை" in res["template_title_ta"]

def test_generate_memo(generator):
    res = generator.generate(
        template_type="memo",
        subject="நிலுவையில் உள்ள பட்டா மாறுதல் மனுக்கள் விரைவுபடுத்தல்",
        details="ஒரு வாரத்திற்குள் நிலுவை மனுக்கள் மீது நடவடிக்கை எடுக்க வேண்டும்.",
        officer_id="OFC001",
    )
    assert res["status"] == "generated"
    assert "MEM" in res["ref_number"]

def test_generate_meeting_minutes(generator):
    res = generator.generate(
        template_type="meeting_minutes",
        subject="மாவட்ட அளவிலான குடிநீர் விநியோக ஆய்வுக் கூட்டம்",
        details="குடிநீர் பற்றாக்குறை உள்ள பகுதிகளில் லாரிகள் மூலம் குடிநீர் வழங்க உத்தரவு.",
        officer_id="OFC001",
    )
    assert res["status"] == "generated"
    assert "MIN" in res["ref_number"]

def test_invalid_template(generator):
    with pytest.raises(ValueError):
        generator.generate(
            template_type="invalid_template_xyz",
            subject="Test",
            details="Test details",
        )

def test_export_docx(generator):
    res = generator.generate(
        template_type="press_release",
        subject="சோதனை செய்தி வெளியீடு",
        details="இது ஒரு சோதனை செய்தி வெளியீடு.",
        officer_id="OFC001",
    )
    docx_path = export_to_docx(res)
    assert Path(docx_path).exists()
    assert docx_path.name.endswith(".docx")
    assert docx_path.stat().st_size > 0

def test_export_pdf(generator):
    res = generator.generate(
        template_type="circular",
        subject="சோதனை சுற்றறிக்கை",
        details="இது ஒரு சோதனை சுற்றறிக்கை.",
        officer_id="OFC001",
    )
    pdf_path = export_to_pdf(res)
    assert Path(pdf_path).exists()
    assert pdf_path.name.endswith(".pdf")
    assert pdf_path.stat().st_size > 0

def test_database_persistence(generator):
    res = generator.generate(
        template_type="memo",
        subject="DB சோதனை மெமோ",
        details="DB சோதனை விவரங்கள்.",
        officer_id="OFC_TEST",
    )
    save_official_content(
        content_id=res["content_id"],
        template_type=res["template_type"],
        ref_number=res["ref_number"],
        subject=res["subject"],
        details=res["details"],
        generated_text=res["generated_text"],
        content_body=res["content_body"],
        officer_id=res["officer_id"],
        source=res["source"],
    )
    record = get_official_content(res["content_id"])
    assert record is not None
    assert record["ref_number"] == res["ref_number"]
    assert record["subject"] == "DB சோதனை மெமோ"

    history = list_official_content(officer_id="OFC_TEST")
    assert len(history) >= 1
