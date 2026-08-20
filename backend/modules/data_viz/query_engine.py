"""Natural Language to Pandas & SQL Query Engine for Module 2: Data & Visualization.

Classifies user intents in Tamil/English, builds guarded Pandas analysis pipelines,
executes safely in sandbox, and generates equivalent SQL audit trails.
"""

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import requests
import config
from modules.data_viz.code_sandbox import execute_sandboxed_pandas
from modules.data_viz.insight_engine import generate_ai_insights

logger = logging.getLogger("QueryEngine")

INTENT_RULES = {
    "summary": ["சுருக்கம்", "மொத்தம்", "எத்தனை", "count", "total", "sum", "சராசரி", "average", "கணக்கிடு", "விபரம்"],
    "trend": ["போக்கு", "trend", "காலப்போக்கில்", "over time", "வளர்ச்சி", "குறைவு", "ஆண்டுவாரியாக", "மாதவாரியாக"],
    "comparison": ["ஒப்பிடு", "compare", "வித்தியாசம்", "difference", "எது அதிகம்", "ஒப்பீடு"],
    "outlier": ["விதிவிலக்கு", "outlier", "விசித்திரமான", "unusual", "அதிகமான", "குறைவான", "முரண்பாடு"],
    "distribution": ["பகிர்வு", "distribution", "விழுக்காடு", "percentage", "எத்தனை சதவீதம்", "விகிதம்"],
    "ranking": ["முதல்", "top", "கடைசி", "bottom", "உயர்ந்த", "குறைந்த", "அதிகபட்ச", "குறைந்தபட்ச"]
}


def classify_intent(question: str) -> Tuple[str, str]:
    """
    Classify question intent and language (ta/en).
    Returns (intent, language).
    """
    q_lower = question.lower()

    # Detect language
    tamil_chars = sum(1 for c in question if "\u0b80" <= c <= "\u0bff")
    lang = "ta" if tamil_chars > 0 else "en"

    # Score intents
    scores = {intent: 0 for intent in INTENT_RULES}
    for intent, kws in INTENT_RULES.items():
        for kw in kws:
            if kw.lower() in q_lower:
                scores[intent] += 1

    best_intent = max(scores, key=scores.get)
    if scores[best_intent] == 0:
        best_intent = "summary"

    return best_intent, lang


def build_deterministic_pandas_code(
    df: pd.DataFrame,
    question: str,
    intent: str,
    columns_info: List[Dict[str, Any]],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Construct high-precision deterministic Pandas and equivalent SQL queries
    for standard Tamil administrative queries without LLM overhead.
    Returns (pandas_code, equivalent_sql, chart_type).
    """
    q = question.strip()
    col_names = list(df.columns)

    # Identify key column types
    taluk_col = next((c["column_name"] for c in columns_info if c.get("is_taluk_column")), None)
    dept_col = next((c["column_name"] for c in columns_info if c.get("is_department_column")), None)
    amount_col = next((c["column_name"] for c in columns_info if c.get("is_amount_column")), None)
    date_col = next((c["column_name"] for c in columns_info if c.get("is_date_column")), None)
    numeric_cols = [c["column_name"] for c in columns_info if c.get("data_type_detected") == "number"]

    # Target metric column (default to amount or first numeric)
    metric_col = amount_col or (numeric_cols[0] if numeric_cols else None)

    # Check for specific mentioned taluk in Erode
    mentioned_taluk = None
    for t in config.ERODE_TALUKS:
        if t in q:
            mentioned_taluk = t
            break

    # Scenario 1: Specific Taluk Filter (e.g. "ஈரோடு வட்டத்தில் நிலுவை வழக்குகள்")
    if mentioned_taluk and taluk_col and metric_col:
        code = f"result = df[df['{taluk_col}'].astype(str).str.contains('{mentioned_taluk}', na=False)]"
        sql = f"SELECT * FROM dataset WHERE {taluk_col} LIKE '%{mentioned_taluk}%'"
        chart_type = "bar"
        return code, sql, chart_type

    # Scenario 2: Comparison between taluks or departments
    if intent == "comparison" and taluk_col and metric_col:
        code = f"result = df.groupby('{taluk_col}')['{metric_col}'].sum().reset_index().sort_values(by='{metric_col}', ascending=False)"
        sql = f"SELECT {taluk_col}, SUM({metric_col}) FROM dataset GROUP BY {taluk_col} ORDER BY SUM({metric_col}) DESC"
        chart_type = "bar"
        return code, sql, chart_type

    # Scenario 3: Department-wise aggregate
    if dept_col and ("துறை" in q or "department" in q.lower()) and metric_col:
        code = f"result = df.groupby('{dept_col}')['{metric_col}'].sum().reset_index().sort_values(by='{metric_col}', ascending=False)"
        sql = f"SELECT {dept_col}, SUM({metric_col}) FROM dataset GROUP BY {dept_col} ORDER BY SUM({metric_col}) DESC"
        chart_type = "bar"
        return code, sql, chart_type

    # Scenario 4: Taluk-wise aggregate
    if taluk_col and ("வட்டம்" in q or "taluk" in q.lower() or "தாலுகா" in q) and metric_col:
        code = f"result = df.groupby('{taluk_col}')['{metric_col}'].sum().reset_index().sort_values(by='{metric_col}', ascending=False)"
        sql = f"SELECT {taluk_col}, SUM({metric_col}) FROM dataset GROUP BY {taluk_col} ORDER BY SUM({metric_col}) DESC"
        chart_type = "bar"
        return code, sql, chart_type

    # Scenario 5: Top N / Ranking
    if intent == "ranking" and taluk_col and metric_col:
        code = f"result = df.groupby('{taluk_col}')['{metric_col}'].sum().reset_index().sort_values(by='{metric_col}', ascending=False).head(5)"
        sql = f"SELECT {taluk_col}, SUM({metric_col}) FROM dataset GROUP BY {taluk_col} ORDER BY SUM({metric_col}) DESC LIMIT 5"
        chart_type = "horizontal_bar"
        return code, sql, chart_type

    # Scenario 6: Default general summary
    if taluk_col and metric_col:
        code = f"result = df.groupby('{taluk_col}')['{metric_col}'].sum().reset_index()"
        sql = f"SELECT {taluk_col}, SUM({metric_col}) FROM dataset GROUP BY {taluk_col}"
        chart_type = "bar"
        return code, sql, chart_type

    # Generic Fallback: Head 20
    code = "result = df.head(20)"
    sql = "SELECT * FROM dataset LIMIT 20"
    return code, sql, "table"


def generate_llm_pandas_code(
    df: pd.DataFrame,
    question: str,
    columns_info: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Call Ollama Qwen 2.5 7B using the prompt template from Section 15.
    """
    columns_str = ", ".join(c["column_name"] for c in columns_info)
    types_str = ", ".join(f"{c['column_name']}: {c['data_type_detected']}" for c in columns_info)
    samples_str = json.dumps({c["column_name"]: c.get("sample_values", [])[:3] for c in columns_info}, ensure_ascii=False)

    prompt = f"""நீ ஒரு தமிழ்நாடு அரசு தரவு பகுப்பாய்வு உதவியாளர்.
கீழ்கண்ட விதிகளை கண்டிப்பாக பின்பற்று:

1. வழங்கப்பட்ட நெடுவரிசை பெயர்களை மட்டுமே பயன்படுத்து. புதிய நெடுவரிசைகளை உருவாக்காதே.
2. pandas DataFrame 'df' ஏற்கனவே ஏற்றப்பட்டுள்ளது. அதை மீண்டும் ஏற்ற வேண்டாம்.
3. தரவை மாற்றாதே (no inplace=True, no drop, no delete).
4. GroupBy, agg, filter, sort மட்டுமே பயன்படுத்து.
5. விடையை JSON வடிவத்தில் மட்டுமே அச்சிடு.
6. குறியீட்டில் விளக்கங்கள் (comments) தமிழில் இருக்கலாம், ஆனால் குறியீடு ஆங்கிலத்தில் இருக்க வேண்டும்.

தரவு அட்டவணை:
- நெடுவரிசைகள்: {columns_str}
- வகைகள்: {types_str}
- மாதிரி மதிப்புகள்: {samples_str}
- மொத்த வரிசைகள்: {len(df)}

கேள்வி: {question}

விடை (JSON):
{{
  "intent": "summary|trend|comparison|outlier|distribution",
  "pandas_code": "df.groupby(...)...",
  "explanation_tamil": "...",
  "expected_columns": ["col1", "col2"],
  "chart_suggested": true,
  "chart_type": "bar|line|pie"
}}
"""
    try:
        url = f"{config.OLLAMA_API_BASE}/api/generate"
        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 400},
        }
        resp = requests.post(url, json=payload, timeout=min(config.OLLAMA_TIMEOUT_SEC, 12))
        if resp.status_code == 200:
            raw = resp.json().get("response", "")
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"Ollama code generation call skipped/failed: {e}")
    return None


def execute_data_query(
    df: pd.DataFrame,
    question: str,
    columns_info: List[Dict[str, Any]],
    officer_id: str,
    dataset_name: str = "dataset.xlsx",
) -> Dict[str, Any]:
    """
    Main entrypoint:
    1. Classifies intent
    2. Builds/generates Pandas code
    3. Executes safely in sandbox
    4. Generates Tamil summary and grounded insights
    5. Returns unified execution payload
    """
    intent, lang = classify_intent(question)

    # Attempt LLM generation first, fall back to deterministic pipeline
    llm_result = generate_llm_pandas_code(df, question, columns_info)
    pandas_code = None
    equivalent_sql = None
    chart_type = "bar"
    explanation_tamil = ""

    if llm_result and llm_result.get("pandas_code"):
        candidate_code = llm_result["pandas_code"]
        # Ensure code assigns to result
        if not candidate_code.strip().startswith("result ="):
            candidate_code = f"result = {candidate_code}"
        pandas_code = candidate_code
        chart_type = llm_result.get("chart_type", "bar")
        explanation_tamil = llm_result.get("explanation_tamil", "")
        equivalent_sql = f"SELECT * FROM dataset -- Generated from LLM intent: {intent}"

    if not pandas_code:
        pandas_code, equivalent_sql, chart_type = build_deterministic_pandas_code(
            df, question, intent, columns_info
        )

    # Execute in AST Sandbox
    exec_result = execute_sandboxed_pandas(pandas_code, df, timeout_sec=config.QUERY_TIMEOUT_SEC)

    if exec_result["status"] != "success":
        # If LLM code failed sandbox, fallback to deterministic code immediately
        if llm_result:
            pandas_code, equivalent_sql, chart_type = build_deterministic_pandas_code(
                df, question, intent, columns_info
            )
            exec_result = execute_sandboxed_pandas(pandas_code, df, timeout_sec=config.QUERY_TIMEOUT_SEC)

    result_df = exec_result.get("result_df")
    result_data = []
    if result_df is not None:
        result_data = result_df.to_dict(orient="records")

    # Generate insights
    insights = []
    if result_df is not None and len(result_df) > 0:
        insights = generate_ai_insights(result_df, question, intent, dataset_name)

    # Tamil Summary Generation
    if result_df is not None and len(result_df) > 0:
        row_count = len(result_df)
        cols = list(result_df.columns)
        if row_count == 1:
            val_str = ", ".join(f"{k}: {v}" for k, v in result_df.iloc[0].items())
            summary_ta = f"வினவலுக்கான கணக்கீடு முடிவு: {val_str}."
            summary_en = f"Query calculation result: {val_str}."
        else:
            summary_ta = f"வினவலுக்கு {row_count} பதிவுகள் பெறப்பட்டன (நெடுவரிசைகள்: {', '.join(cols[:3])})."
            summary_en = f"Retrieved {row_count} records for query."
    else:
        summary_ta = "பொருந்தும் தகவல்கள் ஏதும் கிடைக்கவில்லை."
        summary_en = "No matching records found."

    return {
        "execution_status": exec_result["status"],
        "execution_error": exec_result.get("error"),
        "execution_time_ms": exec_result["execution_time_ms"],
        "row_count_returned": exec_result["row_count"],
        "generated_code": pandas_code,
        "generated_sql": equivalent_sql,
        "parsed_intent": intent,
        "question_language": lang,
        "result_data": result_data,
        "result_df": result_df,
        "result_summary_tamil": summary_ta,
        "result_summary_english": summary_en,
        "chart_suggested": chart_type != "table",
        "chart_type": chart_type,
        "insights": insights,
    }
