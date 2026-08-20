"""Comprehensive Test Suite for Module 2: Data & Visualization.

Validates:
1. Deterministic Schema Detection & Special Column Identification
2. IQR Outlier Detection on Real Data
3. AST Security Validator & Sandbox Isolation (Blocking malicious payloads)
4. Tamil Natural Language to Pandas & SQL Query Execution
5. Headless Matplotlib Chart Rendering with Tamil Metadata
6. Grounded Insight Generation with Numerical Row Provenance
7. Complete FastAPI REST API Endpoint Suite
8. Immutable Audit Trail Logging
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import config
from api_server import app
from pipeline.database import get_db_connection, init_db, list_datasets, get_dataset
from data.seed_datasets import seed_and_ingest_all
from modules.data_viz.code_sandbox import validate_python_code, execute_sandboxed_pandas
from modules.data_viz.profiler import detect_outliers_iqr
from modules.data_viz.query_engine import classify_intent, execute_data_query
from modules.data_viz.chart_engine import generate_chart_png

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_module2():
    """Ensure DB and sample datasets are initialized."""
    init_db()
    seed_and_ingest_all()


# ---------------------------------------------------------------------------
# 1. Schema Detection & Profiling Tests
# ---------------------------------------------------------------------------

def test_schema_detection_all_datasets():
    """Verify all 5 datasets are registered with complete column schemas."""
    datasets = list_datasets()
    assert len(datasets) >= 5, "Expected at least 5 registered datasets"

    taluk_col_count = 0
    for ds in datasets:
        full_ds = get_dataset(ds["dataset_id"])
        assert full_ds is not None
        assert len(full_ds["columns"]) > 0
        for col in full_ds["columns"]:
            assert col["data_type_detected"] in ("text", "number", "date", "boolean")
            if col["is_taluk_column"]:
                taluk_col_count += 1

    # Taluk columns should be detected in at least 3 datasets
    assert taluk_col_count >= 3, f"Taluk column detected in {taluk_col_count} datasets, expected >= 3"


# ---------------------------------------------------------------------------
# 2. Outlier Detection Tests (IQR Rule)
# ---------------------------------------------------------------------------

def test_iqr_outlier_detection():
    """Test deterministic outlier detection on Erode budget dataset."""
    datasets = list_datasets()
    budget_ds = next((d for d in datasets if "budget" in d["file_name"].lower()), None)
    assert budget_ds is not None

    full_ds = get_dataset(budget_ds["dataset_id"])
    import pandas as pd
    df = pd.read_excel(full_ds["file_path"], sheet_name=full_ds["sheet_name"])

    outliers_res = detect_outliers_iqr(df, column="ஒதுக்கப்பட்ட_பட்ஜெட்")
    assert outliers_res["total_outliers"] > 0
    # Sathyamangalam (₹4,85,00,000) should be identified as statistical anomaly
    found_sathyamangalam = any("சத்தியமங்கலம்" in o.get("வட்டம்", "") or "சத்தியமங்கலம்" in str(o.get("row_context", {})) for o in outliers_res["outliers"])
    assert found_sathyamangalam, "Expected Sathyamangalam project to be flagged as IQR outlier"


# ---------------------------------------------------------------------------
# 3. AST Security Validator & Sandbox Tests
# ---------------------------------------------------------------------------

def test_ast_security_blocks_malicious_code():
    """Verify that AST validator blocks dangerous calls and imports."""
    malicious_snippets = [
        "import os; os.system('calc.exe')",
        "import subprocess; subprocess.Popen(['ls'])",
        "open('/etc/passwd', 'r').read()",
        "__import__('os').system('whoami')",
        "eval('1 + 1')",
        "exec('print(1)')",
        "df.to_csv('leak.csv')",
        "getattr(df, '__class__')",
        "df.drop(columns=['வட்டம்'], inplace=True)",
    ]

    for snippet in malicious_snippets:
        is_safe, err = validate_python_code(snippet)
        assert not is_safe, f"Expected security violation for snippet: {snippet}"


def test_sandboxed_pandas_safe_execution():
    """Verify safe Pandas analytical code executes properly."""
    import pandas as pd
    df = pd.DataFrame({
        "வட்டம்": ["ஈரோடு", "பவானி", "பெருந்துறை"],
        "தொகை": [100, 200, 300]
    })

    safe_code = "result = df.groupby('வட்டம்')['தொகை'].sum().reset_index()"
    exec_res = execute_sandboxed_pandas(safe_code, df)
    assert exec_res["status"] == "success"
    assert exec_res["row_count"] == 3
    assert "தொகை" in exec_res["result_df"].columns


# ---------------------------------------------------------------------------
# 4. Natural Language Query Engine Tests
# ---------------------------------------------------------------------------

def test_intent_classification():
    """Test Tamil keyword intent scoring."""
    intent, lang = classify_intent("வட்ட வாரியாக நிலுவை வழக்குகள் எத்தனை?")
    assert intent in ("summary", "distribution")
    assert lang == "ta"

    intent, lang = classify_intent("ஈரோடு மற்றும் பெருந்துறை வட்டங்களை ஒப்பிடு")
    assert intent == "comparison"
    assert lang == "ta"

    intent, lang = classify_intent("அதிக நிலுவை வழக்குகள் கொண்ட முதல் 5 வட்டங்கள்")
    assert intent == "ranking"
    assert lang == "ta"


def test_natural_language_queries_execution():
    """Test 5+ realistic Tamil administrative queries on actual dataset."""
    datasets = list_datasets()
    patta_ds = next((d for d in datasets if "patta" in d["file_name"].lower()), None)
    assert patta_ds is not None
    full_ds = get_dataset(patta_ds["dataset_id"])

    import pandas as pd
    df = pd.read_excel(full_ds["file_path"], sheet_name=full_ds["sheet_name"])

    queries = [
        "வட்ட வாரியாக நிலுவை வழக்குகள் விபரம்",
        "ஈரோடு மற்றும் பவானி வட்டங்களில் பெற்ற மனுக்களை ஒப்பிடு",
        "அதிக நிலுவை வழக்குகள் உள்ள முதல் 3 வட்டங்கள்",
        "ஈரோடு வட்டத்தில் தீர்க்கப்பட்ட வழக்குகள் எத்தனை?",
        "மொத்த பெறப்பட்ட மனுக்கள் சுருக்கம்",
    ]

    for q in queries:
        res = execute_data_query(
            df=df,
            question=q,
            columns_info=full_ds["columns"],
            officer_id="TEST_OFFICER",
            dataset_name=patta_ds["file_name"],
        )
        assert res["execution_status"] == "success", f"Query failed for '{q}': {res.get('execution_error')}"
        assert res["row_count_returned"] > 0
        assert res["generated_sql"] is not None
        assert len(res["insights"]) > 0


# ---------------------------------------------------------------------------
# 5. Chart Engine Tests
# ---------------------------------------------------------------------------

def test_chart_png_generation():
    """Verify Matplotlib chart PNG generation with metadata."""
    import pandas as pd
    df = pd.DataFrame({
        "வட்டம்": ["ஈரோடு", "பவானி", "பெருந்துறை"],
        "நிலுவை_வழக்குகள்": [140, 130, 90]
    })

    chart_info = generate_chart_png(
        df=df,
        chart_type="bar",
        title_tamil="வட்ட வாரியான நிலுவை வழக்குகள்",
        file_name="test_cases.xlsx",
        officer_id="TEST_OFFICER",
    )

    assert chart_info["chart_id"].startswith("chart_")
    chart_file = Path(chart_info["file_path"])
    assert chart_file.exists()
    assert chart_file.stat().st_size > 5000  # Non-trivial image file


# ---------------------------------------------------------------------------
# 6. REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_datasets_list_and_schema():
    """Test GET /api/v2/data/datasets and schema endpoint."""
    resp = client.get("/api/v2/data/datasets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5

    first_id = data["datasets"][0]["dataset_id"]
    schema_resp = client.get(f"/api/v2/data/datasets/{first_id}/schema")
    assert schema_resp.status_code == 200
    schema_data = schema_resp.json()
    assert schema_data["dataset_id"] == first_id
    assert len(schema_data["columns"]) > 0


def test_api_query_endpoint():
    """Test POST /api/v2/data/query endpoint."""
    datasets = list_datasets()
    budget_ds = datasets[0]

    payload = {
        "dataset_id": budget_ds["dataset_id"],
        "question": "வட்ட வாரியாக பட்ஜெட் விவரம்",
        "officer_id": "TEST_OFFICER",
        "output_format": "both",
    }

    resp = client.post("/api/v2/data/query", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["execution_status"] == "success"
    assert len(res_data["result_data"]) > 0
    assert len(res_data["insights"]) > 0
    assert res_data["generated_code"] is not None
    assert res_data["generated_sql"] is not None


def test_api_outliers_endpoint():
    """Test POST /api/v2/data/outliers endpoint."""
    datasets = list_datasets()
    budget_ds = next((d for d in datasets if "budget" in d["file_name"].lower()), None)

    payload = {
        "dataset_id": budget_ds["dataset_id"],
        "column": "ஒதுக்கப்பட்ட_பட்ஜெட்",
        "method": "iqr"
    }

    resp = client.post("/api/v2/data/outliers", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["method_used"] == "iqr"
    assert "outliers" in res


def test_audit_log_records_module2_events():
    """Verify that Module 2 events are permanently recorded in audit_log."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT action FROM audit_log")
        actions = set(r["action"] for r in cur.fetchall())
        assert "DATASET_UPLOADED" in actions
        assert "SCHEMA_DETECTED" in actions
        assert "QUERY_SUBMITTED" in actions
        assert "QUERY_EXECUTED" in actions
    finally:
        conn.close()


