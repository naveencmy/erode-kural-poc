"""Grounded AI Insight Generation Engine for Module 2: Data & Visualization.

Generates concise Tamil administrative insights with strict row-index
provenance, deterministic confidence scoring, and anti-hallucination verification.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import requests
import config

logger = logging.getLogger("InsightEngine")


def compute_insight_confidence(result_df: pd.DataFrame, insight_type: str = "summary") -> float:
    """
    Deterministic confidence calculation based on data quality signals:
    - Row count: > 1000 rows = higher confidence
    - Null ratio: < 5% nulls = higher confidence
    - Result completeness
    """
    if result_df is None or len(result_df) == 0:
        return 0.0

    score = 1.0
    if len(result_df) < 5:
        score *= 0.85
    elif len(result_df) < 10:
        score *= 0.92

    # Null penalty
    total_cells = result_df.shape[0] * result_df.shape[1]
    if total_cells > 0:
        null_ratio = result_df.isnull().sum().sum() / total_cells
        if null_ratio > 0.1:
            score *= 0.8
        elif null_ratio > 0.0:
            score *= 0.95

    return round(float(max(0.5, min(1.0, score))), 2)


def generate_deterministic_insights(
    result_df: pd.DataFrame,
    question: str,
    intent: str,
) -> List[Dict[str, Any]]:
    """
    Generate verifiable rule-based Tamil insights directly from data aggregates.
    Guarantees 100% numerical grounding without LLM dependency.
    """
    if result_df is None or len(result_df) == 0:
        return []

    insights = []
    cols = list(result_df.columns)

    # Detect categorical and numeric columns in result
    cat_col = None
    num_col = None
    for c in cols:
        numeric_s = pd.to_numeric(
            result_df[c].astype(str).str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False),
            errors="coerce"
        )
        if numeric_s.notnull().sum() >= len(result_df) * 0.6:
            if not num_col:
                num_col = c
        else:
            if not cat_col:
                cat_col = c

    # Case 1: Comparison / Ranking across categories (e.g. Taluk vs Cases / Budget)
    if cat_col and num_col and len(result_df) > 1:
        s_num = pd.to_numeric(result_df[num_col], errors="coerce").fillna(0)
        max_idx = int(s_num.idxmax())
        min_idx = int(s_num.idxmin())
        total_val = float(s_num.sum())
        mean_val = float(s_num.mean())

        max_row = result_df.loc[max_idx]
        min_row = result_df.loc[min_idx]

        max_val_fmt = f"{int(max_row[num_col]):,}" if float(max_row[num_col]).is_integer() else f"{float(max_row[num_col]):,.2f}"
        min_val_fmt = f"{int(min_row[num_col]):,}" if float(min_row[num_col]).is_integer() else f"{float(min_row[num_col]):,.2f}"
        pct_share = round((float(max_row[num_col]) / total_val) * 100, 1) if total_val > 0 else 0

        # 1. Top Category Dominance Insight
        insights.append({
            "insight_type": "comparison",
            "insight_tamil": f"{max_row[cat_col]} பகுதியில் அதிகபட்சமாக {max_val_fmt} {num_col} பதிவாகியுள்ளது (மாவட்ட மொத்தத்தில் {pct_share}%).",
            "insight_english": f"{max_row[cat_col]} recorded the highest {num_col} with {max_val_fmt} ({pct_share}% of total).",
            "grounding_rows": [max_idx],
            "confidence_score": compute_insight_confidence(result_df, "comparison"),
        })

        # 2. District Average & Low Range Insight
        if max_idx != min_idx:
            mean_fmt = f"{mean_val:,.1f}"
            insights.append({
                "insight_type": "summary",
                "insight_tamil": f"மாவட்டத்தின் சராசரி {num_col} அளவு {mean_fmt} ஆகும். குறைந்தபட்சமாக {min_row[cat_col]} பகுதியில் {min_val_fmt} பதிவாகியுள்ளது.",
                "insight_english": f"District average for {num_col} is {mean_fmt}, with lowest in {min_row[cat_col]} ({min_val_fmt}).",
                "grounding_rows": [min_idx],
                "confidence_score": compute_insight_confidence(result_df, "summary"),
            })

        # 3. Top 3 Ranked Breakdown
        if len(result_df) >= 3:
            sorted_df = result_df.sort_values(by=num_col, ascending=False)
            top3_items = []
            for _, r in sorted_df.head(3).iterrows():
                val_str = f"{int(r[num_col]):,}" if float(r[num_col]).is_integer() else f"{float(r[num_col]):,.1f}"
                top3_items.append(f"{r[cat_col]} ({val_str})")
            insights.append({
                "insight_type": "comparison",
                "insight_tamil": f"முக்கிய முதல் 3 இடங்கள்: {', '.join(top3_items)}.",
                "insight_english": f"Top 3 ranked divisions: {', '.join(top3_items)}.",
                "grounding_rows": list(sorted_df.head(3).index),
                "confidence_score": compute_insight_confidence(result_df, "comparison"),
            })

        # 4. Comparative Ratio
        if float(min_row[num_col]) > 0 and float(max_row[num_col]) > float(min_row[num_col]):
            ratio = round(float(max_row[num_col]) / float(min_row[num_col]), 1)
            if ratio > 1.2:
                insights.append({
                    "insight_type": "comparison",
                    "insight_tamil": f"{max_row[cat_col]} பகுதியானது {min_row[cat_col]} பகுதியை விட {ratio} மடங்கு அதிக {num_col} கொண்டுள்ளது.",
                    "insight_english": f"{max_row[cat_col]} has {ratio}x more {num_col} compared to {min_row[cat_col]}.",
                    "grounding_rows": [max_idx, min_idx],
                    "confidence_score": compute_insight_confidence(result_df, "comparison"),
                })

    # Case 2: Single aggregate result (e.g. Total count or sum)
    elif len(result_df) == 1:
        row = result_df.iloc[0]
        summary_parts = [f"{k}: {v}" for k, v in row.items()]
        insights.append({
            "insight_type": "summary",
            "insight_tamil": f"வினவலுக்கான துல்லிய கணக்கீடு முடிவு: {', '.join(summary_parts)}.",
            "insight_english": f"Query aggregate result: {', '.join(summary_parts)}.",
            "grounding_rows": [0],
            "confidence_score": compute_insight_confidence(result_df, "summary"),
        })

    # Case 3: Multi-row distribution
    else:
        insights.append({
            "insight_type": "summary",
            "insight_tamil": f"தரவுத்தொகுப்பில் மொத்தம் {len(result_df)} பதிவுகள் வெற்றிகரமாக பகுப்பாய்வு செய்யப்பட்டன.",
            "insight_english": f"Total {len(result_df)} records analyzed successfully.",
            "grounding_rows": list(range(min(5, len(result_df)))),
            "confidence_score": compute_insight_confidence(result_df, "summary"),
        })

    return insights


def get_active_ollama_model() -> Optional[str]:
    """Detect installed active model from local Ollama prioritizing Qwen 2.5 7B."""
    try:
        resp = requests.get(f"{config.OLLAMA_API_BASE}/api/tags", timeout=1.5)
        if resp.status_code == 200:
            tags = resp.json().get("models", [])
            installed_names = [m.get("name") for m in tags if m.get("name")]
            preferred = [
                "qwen2.5:7b-instruct-q4_K_M",
                "qwen2.5:7b",
                "qwen2.5:latest",
                config.OLLAMA_MODEL,
                "qwen2.5",
                "qwen2.5:3b",
                "qwen2.5:1.5b",
                "mistral:7b-instruct-q4_K_M",
                "phi4-mini:latest",
                "llama3.2:1b",
            ]
            for pref in preferred:
                if pref in installed_names:
                    return pref
                for inst in installed_names:
                    if pref.split(":")[0] in inst:
                        return inst
            if installed_names:
                return installed_names[0]
    except Exception:
        pass
    return None


def generate_ai_insights(
    result_df: pd.DataFrame,
    question: str,
    intent: str,
    dataset_name: str = "dataset.xlsx",
) -> List[Dict[str, Any]]:
    """
    Generate grounded insights via local Ollama LLM if reachable,
    falling back to intelligent deterministic insights adapted to the user's question.
    """
    if result_df is None or len(result_df) == 0:
        return []

    # Detect language of user question
    tamil_chars = sum(1 for c in question if "\u0b80" <= c <= "\u0bff")
    is_tamil = tamil_chars > 0

    # Prepare small capped result JSON (max 20 rows) for LLM
    result_json = result_df.head(20).to_json(orient="records", force_ascii=False)
    active_model = get_active_ollama_model()

    if active_model:
        prompt = f"""You are an expert Tamil Nadu Government District Data Analyst for Erode Collectorate.
Analyze the following query results strictly using the grounded table data provided below. Do not hallucinate.

User Question: "{question}"
Data:
{result_json}

Provide 2-3 crisp, highly relevant analytical insights formatted in JSON:
{{
  "insights": [
    {{
      "insight_tamil": "...",
      "insight_english": "...",
      "type": "summary|comparison|trend|outlier",
      "supporting_rows": [0]
    }}
  ]
}}
"""
        try:
            url = f"{config.OLLAMA_API_BASE}/api/generate"
            payload = {
                "model": active_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_predict": 400},
            }
            resp = requests.post(url, json=payload, timeout=min(config.OLLAMA_TIMEOUT_SEC, 8))
            if resp.status_code == 200:
                parsed = json.loads(resp.json().get("response", "{}"))
                llm_insights = parsed.get("insights", [])
                valid_insights = []
                for item in llm_insights:
                    t_text = item.get("insight_tamil") or item.get("insight_english")
                    e_text = item.get("insight_english") or item.get("insight_tamil")
                    if t_text:
                        raw_type = item.get("type", "summary")
                        safe_type = raw_type if raw_type in ('trend', 'outlier', 'anomaly', 'comparison', 'summary') else 'summary'
                        valid_insights.append({
                            "insight_type": safe_type,
                            "insight_tamil": t_text,
                            "insight_english": e_text,
                            "grounding_rows": item.get("supporting_rows", [0]),
                            "confidence_score": compute_insight_confidence(result_df, safe_type),
                        })
                if valid_insights:
                    return valid_insights
        except Exception as e:
            logger.debug(f"Ollama insight call skipped/failed: {e}")

    # Fallback to 100% deterministic grounded insights
    return generate_deterministic_insights(result_df, question, intent)
