for pkg in ['easyocr', 'rapidocr_onnxruntime', 'pytesseract', 'tesserocr', 'paddleocr']:
    try:
        __import__(pkg)
        print(f"AVAILABLE: {pkg}")
    except ImportError:
        print(f"NOT available: {pkg}")
