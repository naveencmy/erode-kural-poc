import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from pathlib import Path
import pymupdf as fitz
import numpy as np
import cv2
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
pdf_path = Path(r"e:\test_rat\Erode_Collectrate\backend\uploads\documents\doc_29a338568ca469_78_press_release.pdf")
doc = fitz.open(str(pdf_path))
pix = doc[0].get_pixmap(dpi=300)
img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
if pix.n >= 3:
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

result, elapse = ocr(img)
print("OCR result count:", len(result) if result else 0)
if result:
    for line in result[:15]:
        print(line[1], "(score:", line[2], ")")
