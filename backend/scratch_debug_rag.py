import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

import sqlite3
from pathlib import Path
from pipeline.rag_engine import CollectorateRAGEngine

conn = sqlite3.connect('collectorate_workflow.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check ocr_results for doc_29a338568ca469
ocr = cur.execute("SELECT source_id, substr(full_text, 1, 500) as txt FROM ocr_results WHERE source_id='doc_29a338568ca469'").fetchone()
print("OCR for doc_29a338568ca469:", dict(ocr) if ocr else "None")

rag = CollectorateRAGEngine()
print("\nActive Ollama Model:", rag._get_active_ollama_model())

print("\n--- Testing RAG query 1: [இணைப்பு: 78_press_release.pdf] இதில் குறிப்பிடப்பட்டுள்ள முக்கியமான தேதிகள் என்ன? ---")
res1 = rag.query("[இணைப்பு: 78_press_release.pdf] இதில் குறிப்பிடப்பட்டுள்ள முக்கியமான தேதிகள் என்ன?", officer_id="OFC001")
print("Query 1 result:\n", res1.get("answer"))

print("\n--- Testing RAG query 2: இந்த நாளில் எதைப் பற்றி ---")
res2 = rag.query("இந்த நாளில் எதைப் பற்றி", officer_id="OFC001")
print("Query 2 result:\n", res2.get("answer"))

print("\n--- Testing RAG query 3: இது எதை பத்தி சொல்லுது ---")
res3 = rag.query("இது எதை பத்தி சொல்லுது", officer_id="OFC001")
print("Query 3 result:\n", res3.get("answer"))
