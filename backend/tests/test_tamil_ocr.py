"""Interactive Tamil Image OCR Inspector & CLI Tool."""

import sys
import io
import argparse
from pathlib import Path

# Set UTF-8 encoding for Windows terminal output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config
from pipeline.database import init_db
from pipeline.ocr_engine import IndicOCREngine
from pipeline.extraction import TamilEntityExtractor


def generate_sample_tamil_petition_image(output_path: Path) -> Path:
    """Generate a realistic Tamil Government Petition document image for OCR testing."""
    # Create white canvas (A4 ratio)
    width, height = 1200, 1500
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try loading Tamil fonts available on Windows (Latha, Nirmala UI, Vijaya, Arial)
    font_large = None
    font_medium = None
    font_small = None

    font_candidates = [
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/NirmalaB.ttf",
        "C:/Windows/Fonts/Latha.ttf",
        "C:/Windows/Fonts/Vijaya.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    for fpath in font_candidates:
        if Path(fpath).exists():
            try:
                font_large = ImageFont.truetype(fpath, 32)
                font_medium = ImageFont.truetype(fpath, 26)
                font_small = ImageFont.truetype(fpath, 22)
                break
            except Exception:
                continue

    if font_large is None:
        font_large = font_medium = font_small = ImageFont.load_default()

    # Draw header banner
    draw.rectangle([50, 40, width - 50, 130], fill="#1e3c72")
    draw.text((width // 2, 60), "தமிழ்நாடு அரசு - ஈரோடு மாவட்ட ஆட்சியரகம்", fill="#ffffff", font=font_large, anchor="mm")
    draw.text((width // 2, 100), "மக்கள் குறைதீர்க்கும் மனு (Grievance Petition)", fill="#d1e3ff", font=font_medium, anchor="mm")

    # Document Metadata
    y = 160
    draw.text((80, y), "மனு எண் / கோப்பு எண் : 1450/REV/2026", fill="#000000", font=font_medium)
    draw.text((width - 400, y), "நாள் : 19/08/2026", fill="#000000", font=font_medium)

    y += 50
    draw.line([(80, y), (width - 80, y)], fill="#cccccc", width=2)
    y += 30

    # Applicant details
    details = [
        "பெறுநர் : மாவட்ட ஆட்சியர் அவர்கள், ஈரோடு மாவட்டம்.",
        "",
        "மனுதாரர் பெயர் : கே. சுப்பிரமணியம் (K. Subramaniam)",
        "த/பெயர் : கந்தசாமி கவுண்டர்",
        "கைபேசி எண் : 9842567890",
        "ஆதார் எண் : 4567 8901 2345",
        "மாவட்டம் : ஈரோடு",
        "வட்டம் (Taluk) : பவானி",
        "வருவாய் கிராமம் : கவிந்தபாடி",
        "புல எண் (Survey No) : 205/3B",
        "",
        "பொருள் : நில பட்டா பெயர் மாற்றம் மற்றும் சர்வே எல்லை அளவீடு செய்ய கோருதல்.",
        "",
        "விபரம் :",
        "மேற்படி பவானி வட்டம், கவிந்தபாடி கிராமத்தில் எனக்குச் சொந்தமான சர்வே எண் 205/3B-ல் உள்ள",
        "75 சென்ட் புன்செய் நிலத்திற்கு உரிய கிரயப் பத்திரம் மற்றும் வில்லங்கச் சான்றிதழ் என்னிடம் உள்ளது.",
        "இதற்கு கணினி பட்டா மாறுதல் கோரி கிராம நிர்வாக அலுவலர் (VAO) மற்றும் வட்டாட்சியர்",
        "அலுவலகத்தில் விண்ணப்பித்தும் உரிய நடவடிக்கை எடுக்கப்படவில்லை.",
        "",
        "எனவே மாவட்ட ஆட்சியர் அவர்கள் தலையிட்டு விரைந்து பட்டா வழங்கிட உத்தரவிடுமாறு கேட்டுக்கொள்கிறேன்.",
        "",
        "இப்படிக்கு,",
        "கே. சுப்பிரமணியம்",
    ]

    for line in details:
        draw.text((80, y), line, fill="#111111", font=font_small)
        y += 38

    img.save(str(output_path), "PNG")
    # Also save companion text
    txt_path = output_path.with_suffix(".txt")
    full_text_content = "\n".join([
        "தமிழ்நாடு அரசு - ஈரோடு மாவட்ட ஆட்சியரகம்",
        "மனு எண் / கோப்பு எண் : 1450/REV/2026",
        "நாள் : 19/08/2026",
        *details
    ])
    txt_path.write_text(full_text_content, encoding="utf-8")
    return output_path


def inspect_image_ocr(image_path: Path):
    """Run full OCR and Tamil Entity inspection on a specified image file."""
    print("=" * 80)
    print(f"🔍 INSPECTING TAMIL IMAGE OCR: {image_path.name}")
    print("=" * 80)

    if not image_path.exists():
        print(f"❌ Error: Image file not found at {image_path}")
        return

    init_db()
    engine = IndicOCREngine()

    print(f"1. Loading image and computing OpenCV deskew...")
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"❌ Error: OpenCV could not decode image at {image_path}")
        return

    deskewed, thresh = engine.preprocess_image(img)
    print(f"   - Original Size: {img.shape[1]}x{img.shape[0]} px")
    print(f"   - Preprocessed Binary Threshold Matrix: {thresh.shape}")

    print(f"\n2. Running Indic OCR Layout Segmentation & Tamil Recognition...")
    from pipeline.database import record_source
    from pipeline.ingestion import compute_file_sha256
    source_id = compute_file_sha256(image_path)
    record_source(source_id=source_id, source_type="scan", raw_path=str(image_path))
    ocr_res = engine.process_image(image_path, source_id=source_id, page_number=1)

    print(f"\n3. Extracted Tamil OCR Text:")
    print("-" * 80)
    text_content = ocr_res["full_text"]
    print(text_content)
    print("-" * 80)
    print(f"📊 Average OCR Confidence: {ocr_res['avg_confidence']:.2%}")
    print(f"🧩 Layout Text Blocks Detected: {len(ocr_res['blocks'])}")

    print(f"\n4. Running Tamil Regex Entity Extractor & Aadhaar Masking...")
    extractor = TamilEntityExtractor()
    entities = extractor.extract_entities(text_content, source_id=source_id)

    print(f"   - File Number   : {entities.get('file_number')}")
    print(f"   - Date          : {entities.get('date')}")
    print(f"   - Survey Number : {entities.get('survey_number')}")
    print(f"   - Mobile Number : {entities.get('mobile_number')}")
    print(f"   - Aadhaar PII   : {entities.get('aadhaar_number')} (Redacted)")
    print(f"   - Applicant Name: {entities.get('applicant_name')}")
    print(f"   - Taluk         : {entities.get('taluk')}")
    print(f"   - Village       : {entities.get('village')}")

    print(f"\n5. How to View in Web UI:")
    print(f"   👉 Open http://localhost:8501 -> Go to Tab 2 (OCR Review) to inspect side-by-side with confidence highlighting.")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Test Tamil Image OCR directly.")
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to any Tamil document image (.png, .jpg, .jpeg, .pdf)",
    )
    parser.add_argument(
        "--generate-sample",
        action="store_true",
        help="Generate a high-res Tamil petition document image and test it",
    )
    args = parser.parse_args()

    sample_path = config.UPLOADS_SCANNED_DIR / "tamil_petition_sample.png"

    if args.generate_sample or args.image is None:
        print("Generating realistic Tamil petition image with Tamil fonts...")
        generate_sample_tamil_petition_image(sample_path)
        inspect_image_ocr(sample_path)
    else:
        inspect_image_ocr(Path(args.image))


if __name__ == "__main__":
    main()
