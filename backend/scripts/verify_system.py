import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

try:
    from server import app
    client = TestClient(app)
    print(f"[OK] App loaded successfully. Total routes: {len(app.routes)}\n")

    endpoints_to_test = [
        ("System Config", "GET", "/api/config"),
        ("System Stats", "GET", "/api/stats"),
        ("Audit Logs", "GET", "/api/audit"),
        ("Content History", "GET", "/api/content/history"),
        ("Data Datasets", "GET", "/api/v2/data/datasets"),
        ("Suggestions", "GET", "/api/v1/suggestions?source_id=general"),
        ("OpenAPI Docs", "GET", "/openapi.json"),
    ]

    all_passed = True
    for name, method, path in endpoints_to_test:
        resp = client.get(path)
        status = "PASSED" if resp.status_code == 200 else f"FAILED ({resp.status_code})"
        if resp.status_code != 200:
            all_passed = False
        print(f"[{status}] {name} ({method} {path}) -> HTTP {resp.status_code}")

    if all_passed:
        print("\nAll module backend endpoints are healthy and operational (100% PASS)!")
    else:
        print("\nSome endpoints returned non-200 status.")

except Exception as e:
    print(f"[FAIL] Error during system verification: {e}")
    sys.exit(1)
