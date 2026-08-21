"""DOCX and PDF Exporter for Official Content Documents.

Generates formatted Microsoft Word (.docx) and PDF files with
authentic Tamil Nadu Government styling for official document export.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

import config

logger = logging.getLogger("OfficialContentExporter")

# TN Government colors
TN_NAVY = RGBColor(0x1A, 0x3A, 0x5C)
TN_GOLD = RGBColor(0xC8, 0xA9, 0x51)


def _extract_clean_body_paragraphs_and_footer(body_text: str, default_footer: str = "வெளியீடு செய்தி மக்கள் தொடர்பு அலுவலர், ஈரோடு மாவட்டம்.") -> Tuple[List[str], str]:
    """Extract clean body paragraphs and separate/deduplicate issuing footer line."""
    if not body_text:
        return [], default_footer

    paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip()]
    cleaned = []
    detected_footer = None

    for p in paragraphs:
        lines = [l.strip() for l in p.split("\n") if l.strip()]
        kept_lines = []
        for line in lines:
            line_no_num = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
            is_short = len(line_no_num) < 140

            if is_short and (
                re.match(r"^செ\.வெ\.எண்\s*[-–:]", line_no_num) or
                re.match(r"^சுற்றறிக்கை\s*எண்\s*[-–:]", line_no_num) or
                re.match(r"^குறிப்பாணை\s*எண்\s*[-–:]", line_no_num) or
                re.match(r"^எண்:\s*வே/", line_no_num) or
                re.match(r"^நாள்\s*[-–:]", line_no_num) or
                line_no_num in ["----", "---", "----------------", "<><><>"] or
                line_no_num == "அவர்களின் செய்திக்குறிப்பு-" or
                line_no_num == "அவர்களின் சுற்றறிக்கை-" or
                line_no_num == "அவர்களின் அலுவலகக் குறிப்பாணை-" or
                line_no_num == "ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.," or
                line_no_num.startswith("--------------------------------") or
                line_no_num.startswith("================================")
            ):
                continue

            if is_short and (
                line_no_num.startswith("வெளியீடு") or
                "செய்தி மக்கள் தொடர்பு அலுவலர்" in line_no_num or
                line_no_num.startswith("இப்படிக்கு")
            ):
                detected_footer = line_no_num
                continue

            kept_lines.append(line)

        if kept_lines:
            cleaned.append("\n".join(kept_lines))

    final_footer = default_footer
    if detected_footer:
        norm_det = re.sub(r'[\s\-_,.:;]', '', detected_footer)
        norm_def = re.sub(r'[\s\-_,.:;]', '', default_footer)
        if norm_det != norm_def:
            final_footer = detected_footer

    return cleaned, final_footer


def _extract_clean_body_paragraphs(body_text: str) -> List[str]:
    paras, _ = _extract_clean_body_paragraphs_and_footer(body_text)
    return paras


def _add_header(doc: Document, template_title: str, ref_number: str, date_str: str, officer_id: str):
    """Add government-styled header to the document."""
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header_para.add_run("தமிழ்நாடு அரசு — மாவட்ட ஆட்சியர் அலுவலகம்\n")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = TN_NAVY

    run2 = header_para.add_run("ஈரோடு மாவட்டம்\n")
    run2.font.size = Pt(12)
    run2.font.bold = True
    run2.font.color.rgb = TN_NAVY

    run3 = header_para.add_run("ERODE DISTRICT")
    run3.font.size = Pt(10)
    run3.font.color.rgb = TN_NAVY

    # Separator
    doc.add_paragraph("─" * 60)

    # Document type title
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_para.add_run(template_title)
    title_run.font.size = Pt(14)
    title_run.font.bold = True
    title_run.font.color.rgb = TN_GOLD

    # Metadata
    meta_para = doc.add_paragraph()
    meta_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    meta_items = [
        f"குறிப்பு எண் / Ref No: {ref_number}",
        f"நாள் / Date: {date_str}",
        f"அலுவலர் / Officer: {officer_id}",
    ]
    for item in meta_items:
        run = meta_para.add_run(item + "\n")
        run.font.size = Pt(10)
        run.font.color.rgb = TN_NAVY

    doc.add_paragraph("─" * 60)


def _add_footer(doc: Document):
    """Add government-styled footer / signature block."""
    doc.add_paragraph("─" * 60)
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    lines = [
        "மாவட்ட ஆட்சியர் சார்பாக,",
        "ஈரோடு மாவட்டம்.",
        "",
        "On behalf of District Collector,",
        "Erode District.",
    ]
    for line in lines:
        run = footer_para.add_run(line + "\n")
        run.font.size = Pt(10)
        run.font.color.rgb = TN_NAVY

    # Watermark / audit line
    audit_para = doc.add_paragraph()
    audit_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    audit_run = audit_para.add_run(
        f"── AI-Assisted Draft | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        "Erode Collectorate AI System ──"
    )
    audit_run.font.size = Pt(7)
    audit_run.font.italic = True
    audit_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)


def _export_press_release_docx(doc: Document, content_data: Dict[str, Any]):
    """Format specifically according to Erode District DIPR Press Release layout."""
    # Top header line: செ.வெ.எண் and நாள்
    header_table = doc.add_table(rows=1, cols=2)
    header_table.autofit = True
    row = header_table.rows[0]

    # Left: செ.வெ.எண்
    p_left = row.cells[0].paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_ref = p_left.add_run(f"செ.வெ.எண் - {content_data['ref_number']}")
    r_ref.font.size = Pt(11)
    r_ref.font.bold = True
    r_ref.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # Right: நாள்
    p_right = row.cells[1].paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_date = p_right.add_run(f"நாள் - {content_data['date_display']}")
    r_date.font.size = Pt(11)
    r_date.font.bold = True
    r_date.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # Spacing
    doc.add_paragraph()

    # Centered Title
    title_p1 = doc.add_paragraph()
    title_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title1 = title_p1.add_run("ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,\nஅவர்களின் செய்திக்குறிப்பு-")
    r_title1.font.size = Pt(13)
    r_title1.font.bold = True
    r_title1.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # Centered dash separator
    sep_p = doc.add_paragraph()
    sep_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sep = sep_p.add_run("----")
    r_sep.font.size = Pt(12)
    r_sep.font.bold = True
    r_sep.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # Clean body paragraphs and deduplicate footer
    body_text = content_data.get("content_body", "")
    clean_paras, final_footer = _extract_clean_body_paragraphs_and_footer(body_text)

    for p_text in clean_paras:
        body_p = doc.add_paragraph()
        body_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        body_p.paragraph_format.line_spacing = 1.3
        body_p.paragraph_format.space_after = Pt(10)
        run = body_p.add_run(p_text)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    # Bottom separator
    doc.add_paragraph("─" * 60)

    # DIPR Footer
    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_footer = footer_p.add_run(final_footer)
    r_footer.font.size = Pt(10.5)
    r_footer.font.bold = True
    r_footer.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


def _export_circular_docx(doc: Document, content_data: Dict[str, Any]):
    """Format specifically according to Erode District Collectorate Circular layout."""
    header_table = doc.add_table(rows=1, cols=2)
    header_table.autofit = True
    row = header_table.rows[0]

    p_left = row.cells[0].paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_ref = p_left.add_run(f"சுற்றறிக்கை எண் - {content_data['ref_number']}")
    r_ref.font.size = Pt(11)
    r_ref.font.bold = True
    r_ref.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    p_right = row.cells[1].paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_date = p_right.add_run(f"நாள் - {content_data['date_display']}")
    r_date.font.size = Pt(11)
    r_date.font.bold = True
    r_date.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    doc.add_paragraph()

    title_p1 = doc.add_paragraph()
    title_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title1 = title_p1.add_run("ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,\nஅவர்களின் சுற்றறிக்கை-")
    r_title1.font.size = Pt(13)
    r_title1.font.bold = True
    r_title1.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    sep_p = doc.add_paragraph()
    sep_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sep = sep_p.add_run("----")
    r_sep.font.size = Pt(12)
    r_sep.font.bold = True
    r_sep.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    body_text = content_data.get("content_body", "")
    clean_paras, final_footer = _extract_clean_body_paragraphs_and_footer(body_text)

    for p_text in clean_paras:
        body_p = doc.add_paragraph()
        body_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        body_p.paragraph_format.line_spacing = 1.3
        body_p.paragraph_format.space_after = Pt(10)
        run = body_p.add_run(p_text)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    doc.add_paragraph("─" * 60)

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_footer = footer_p.add_run(final_footer)
    r_footer.font.size = Pt(10.5)
    r_footer.font.bold = True


def _export_memo_docx(doc: Document, content_data: Dict[str, Any]):
    """Format specifically according to Erode District Collectorate Office Memorandum layout."""
    header_table = doc.add_table(rows=1, cols=2)
    header_table.autofit = True
    row = header_table.rows[0]

    p_left = row.cells[0].paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_ref = p_left.add_run(f"குறிப்பாணை எண் - {content_data['ref_number']}")
    r_ref.font.size = Pt(11)
    r_ref.font.bold = True
    r_ref.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    p_right = row.cells[1].paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_date = p_right.add_run(f"நாள் - {content_data['date_display']}")
    r_date.font.size = Pt(11)
    r_date.font.bold = True
    r_date.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    doc.add_paragraph()

    title_p1 = doc.add_paragraph()
    title_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title1 = title_p1.add_run("ஈரோடு மாவட்ட ஆட்சித்தலைவர் திரு.ச.கந்தசாமி இ.ஆ.ப.,\nஅவர்களின் அலுவலகக் குறிப்பாணை-")
    r_title1.font.size = Pt(13)
    r_title1.font.bold = True
    r_title1.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    sep_p = doc.add_paragraph()
    sep_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sep = sep_p.add_run("----")
    r_sep.font.size = Pt(12)
    r_sep.font.bold = True
    r_sep.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    body_text = content_data.get("content_body", "")
    clean_paras, final_footer = _extract_clean_body_paragraphs_and_footer(body_text)

    for p_text in clean_paras:
        body_p = doc.add_paragraph()
        body_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        body_p.paragraph_format.line_spacing = 1.3
        body_p.paragraph_format.space_after = Pt(10)
        run = body_p.add_run(p_text)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    doc.add_paragraph("─" * 60)

    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_footer = footer_p.add_run(final_footer)
    r_footer.font.size = Pt(10.5)
    r_footer.font.bold = True


def _export_meeting_minutes_docx(doc: Document, content_data: Dict[str, Any]):
    """Format specifically according to Erode District Meeting Minutes layout."""
    title_p1 = doc.add_paragraph()
    title_p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title1 = title_p1.add_run(
        f"ஈரோடு மாவட்ட ஆட்சித்தலைவர் அவர்கள் தலைமையில் {content_data['date_display']} அன்று\n"
        f"நடைபெற்ற {content_data['subject']} கூட்ட நடவடிக்கைகள்\n"
        f"முன்னிலை: திரு.ச.கந்தசாமி, இ.ஆ.ப.,"
    )
    r_title1.font.size = Pt(12)
    r_title1.font.bold = True
    r_title1.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    header_table = doc.add_table(rows=1, cols=2)
    header_table.autofit = True
    row = header_table.rows[0]

    p_left = row.cells[0].paragraphs[0]
    p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_ref = p_left.add_run(f"எண்: வே/{content_data['ref_number']}/2026")
    r_ref.font.size = Pt(11)
    r_ref.font.bold = True
    r_ref.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    p_right = row.cells[1].paragraphs[0]
    p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_date = p_right.add_run(f"நாள்: {content_data['date_display']}")
    r_date.font.size = Pt(11)
    r_date.font.bold = True
    r_date.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    doc.add_paragraph("─" * 60)

    subj_p = doc.add_paragraph()
    r_subj = subj_p.add_run(f"பொருள்: {content_data['subject']} – கூட்ட நடவடிக்கைகள் – ஒப்புதல் அளித்தல் – தொடர்பாக.")
    r_subj.font.size = Pt(10.5)
    r_subj.font.bold = True
    r_subj.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    ref_p = doc.add_paragraph()
    r_ref_line = ref_p.add_run("பார்வை: அரசாணை எண்: 78 வேளாண்மை (வே.உ.6) துறை, நாள்: 17.02.2016.")
    r_ref_line.font.size = Pt(10)
    r_ref_line.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    sep_p = doc.add_paragraph()
    sep_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sep = sep_p.add_run("<><><>")
    r_sep.font.size = Pt(11)
    r_sep.font.bold = True

    body_text = content_data.get("content_body", "")
    clean_paras = _extract_clean_body_paragraphs(body_text)

    for p_text in clean_paras:
        body_p = doc.add_paragraph()
        body_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        body_p.paragraph_format.line_spacing = 1.3
        body_p.paragraph_format.space_after = Pt(10)
        run = body_p.add_run(p_text)
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    doc.add_paragraph("─" * 60)

    sign_p = doc.add_paragraph()
    sign_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_sign = sign_p.add_run("ஓம்/-ச.கந்தசாமி\nமாவட்ட ஆட்சித்தலைவர்,\nஈரோடு.\n")
    r_sign.font.size = Pt(11)
    r_sign.font.bold = True
    r_sign.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

    pa_p = doc.add_paragraph()
    pa_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_pa = pa_p.add_run("/உத்தரவுப்படி/\n\nநேர்முக உதவியாளர்,\nமாவட்ட ஆட்சியர் அலுவலகம்,\nஈரோடு.")
    r_pa.font.size = Pt(10)
    r_pa.font.color.rgb = RGBColor(0x33, 0x33, 0x33)


def export_to_docx(content_data: Dict[str, Any]) -> Path:
    """Export generated content to a formatted .docx file."""
    doc = Document()

    # Set margins (0.8 inch)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    template_type = content_data.get("template_type", "press_release")

    # Route to specialized authentic Erode district layout
    if template_type == "press_release":
        _export_press_release_docx(doc, content_data)
    elif template_type == "circular":
        _export_circular_docx(doc, content_data)
    elif template_type == "memo":
        _export_memo_docx(doc, content_data)
    elif template_type == "meeting_minutes":
        _export_meeting_minutes_docx(doc, content_data)
    else:
        # Generic official document
        _add_header(
            doc,
            template_title=content_data.get("template_title_ta", "அலுவல் ஆவணம்"),
            ref_number=content_data.get("ref_number", "ERD/GEN/2026/001"),
            date_str=content_data.get("date_display", datetime.now().strftime("%d.%m.%Y")),
            officer_id=content_data.get("officer_id", "OFC001"),
        )
        body_text = content_data.get("content_body", "")
        clean_paras = _extract_clean_body_paragraphs(body_text)
        for p_text in clean_paras:
            body_p = doc.add_paragraph()
            body_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            body_p.paragraph_format.line_spacing = 1.3
            body_p.paragraph_format.space_after = Pt(10)
            run = body_p.add_run(p_text)
            run.font.size = Pt(11)
        _add_footer(doc)

    output_dir = config.OUTPUTS_CONTENT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{content_data['content_id']}_{content_data['template_type']}.docx"
    output_path = output_dir / filename

    doc.save(str(output_path))
    logger.info(f"DOCX exported: {output_path}")
    return output_path


def export_to_pdf(content_data: Dict[str, Any]) -> Path:
    """Export generated content directly to an official formatted .pdf file."""
    import pymupdf

    font_path = "C:/Windows/Fonts/Nirmala.ttc"
    if not Path(font_path).exists():
        font_path = None

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    c_navy = (0.10, 0.23, 0.36)
    c_dark = (0.13, 0.13, 0.13)
    c_gray = (0.50, 0.50, 0.50)

    template_type = content_data.get("template_type", "press_release")

    if template_type == "press_release":
        page.insert_text((50, 55), f"செ.வெ.எண் - {content_data['ref_number']}", fontfile=font_path, fontsize=10.5, color=c_navy)
        page.insert_text((430, 55), f"நாள் - {content_data['date_display']}", fontfile=font_path, fontsize=10.5, color=c_navy)
        page.insert_text((235, 95), "ஈரோடு மாவட்டம்", fontfile=font_path, fontsize=14, color=c_navy)

        subj_rect = pymupdf.Rect(50, 110, 545, 160)
        page.insert_textbox(subj_rect, content_data['subject'], fontfile=font_path, fontsize=11.5, color=c_navy, align=1)
        page.draw_line(pymupdf.Point(50, 165), pymupdf.Point(545, 165), color=c_navy, width=0.8)

        body_text = content_data.get("content_body", "")
        cleaned_paras = _extract_clean_body_paragraphs(body_text)
        full_body = "\n\n".join(cleaned_paras)

        body_rect = pymupdf.Rect(50, 180, 545, 750)
        page.insert_textbox(body_rect, full_body, fontfile=font_path, fontsize=10.5, color=c_dark, lineheight=1.5)

        page.draw_line(pymupdf.Point(50, 770), pymupdf.Point(545, 770), color=c_gray, width=0.5)
        page.insert_text((50, 790), "வெளியீடு - செய்தி மக்கள் தொடர்பு அலுவலர், ஈரோடு மாவட்டம்.", fontfile=font_path, fontsize=9.5, color=c_navy)

    else:
        page.insert_text((180, 55), "தமிழ்நாடு அரசு — மாவட்ட ஆட்சியர் அலுவலகம்", fontfile=font_path, fontsize=12, color=c_navy)
        page.insert_text((245, 75), "ஈரோடு மாவட்டம்", fontfile=font_path, fontsize=11, color=c_navy)

        template_title = f"{content_data.get('template_title_ta', '')} ({content_data.get('template_title_en', '')})"
        page.insert_text((200, 105), template_title, fontfile=font_path, fontsize=12, color=c_navy)

        page.insert_text((50, 130), f"குறிப்பு எண்: {content_data['ref_number']}", fontfile=font_path, fontsize=10, color=c_navy)
        page.insert_text((430, 130), f"நாள்: {content_data['date_display']}", fontfile=font_path, fontsize=10, color=c_navy)

        page.draw_line(pymupdf.Point(50, 145), pymupdf.Point(545, 145), color=c_navy, width=0.8)

        body_text = content_data.get("content_body", "")
        cleaned_paras = _extract_clean_body_paragraphs(body_text)
        full_body = "\n\n".join(cleaned_paras)

        body_rect = pymupdf.Rect(50, 160, 545, 740)
        page.insert_textbox(body_rect, full_body, fontfile=font_path, fontsize=10.5, color=c_dark, lineheight=1.5)

        page.draw_line(pymupdf.Point(50, 755), pymupdf.Point(545, 755), color=c_gray, width=0.5)
        page.insert_text((380, 775), "மாவட்ட ஆட்சியர் சார்பாக,", fontfile=font_path, fontsize=10, color=c_navy)
        page.insert_text((410, 790), "ஈரோடு மாவட்டம்.", fontfile=font_path, fontsize=10, color=c_navy)

    output_dir = config.OUTPUTS_CONTENT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{content_data['content_id']}_{content_data['template_type']}.pdf"
    output_path = output_dir / filename
    doc.save(str(output_path))
    logger.info(f"PDF exported: {output_path}")
    return output_path
