import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from pathlib import Path
import re
from pipeline.rag_engine import CollectorateRAGEngine

rag = CollectorateRAGEngine()
source_id = rag._resolve_source_from_text("[இணைப்பு: 78_press_release.pdf] இதில் குறிப்பிடப்பட்டுள்ள முக்கியமான தேதிகள் என்ன?")
print("Resolved source_id:", source_id)

ctx = rag.get_attached_doc_context(source_id)
print("Context retrieved:", ctx is not None)
if ctx:
    print("file_name:", ctx.get("file_name"))
    print("full_text length:", len(ctx.get("full_text", "")))
    print("full_text snippet:\n", ctx.get("full_text", "")[:300])

# Test regex for dates
full_text = ctx.get("full_text", "") if ctx else ""
date_pattern = re.compile(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:ஜனவரி|பிப்ரவரி|மார்ச்|ஏப்ரல்|மே|ஜூன்|ஜூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|டிசம்பர்|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})', re.IGNORECASE)
raw_lines = full_text.splitlines()
cleaned_lines = [l.strip() for l in raw_lines if l.strip()]
found_dates = []
for line in cleaned_lines:
    for match in date_pattern.findall(line):
        if match not in found_dates:
            found_dates.append(match)
print("Found dates in doc:", found_dates)

# Test analytical answer directly
ans = rag._generate_analytical_document_answer(ctx, "இதில் குறிப்பிடப்பட்டுள்ள முக்கியமான தேதிகள் என்ன?", "OFC001")
print("\nAnalytical Dates Answer:\n", ans)

ans2 = rag._generate_analytical_document_answer(ctx, "இந்த நாளில் எதைப் பற்றி", "OFC001")
print("\nAnalytical 'இந்த நாளில் எதைப் பற்றி' Answer:\n", ans2)

ans3 = rag._generate_analytical_document_answer(ctx, "இது எதை பத்தி சொல்லுது", "OFC001")
print("\nAnalytical 'இது எதை பத்தி சொல்லுது' Answer:\n", ans3)
