import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from pathlib import Path
import pymupdf as fitz

pdf_path = Path(r"e:\test_rat\Erode_Collectrate\backend\uploads\documents\doc_29a338568ca469_78_press_release.pdf")
doc = fitz.open(str(pdf_path))
print("Page count:", len(doc))
for i, page in enumerate(doc):
    txt = page.get_text()
    print(f"--- Page {i+1} text (length {len(txt)}) ---")
    print(repr(txt[:500]))
    images = page.get_images()
    print(f"Page {i+1} embedded images count: {len(images)}")
