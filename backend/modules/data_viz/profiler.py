"""Deterministic Data Profiling & Outlier Engine for Module 2: Data & Visualization.

Calculates statistical aggregates, categorical frequencies, and detects
outliers using the 1.5 x IQR rule with zero hallucination.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from modules.data_viz.schema_detector import (
    detect_column_type,
    detect_special_columns,
    normalize_column_name_tamil,
)


def profile_dataset_columns(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generate comprehensive column-by-column deterministic statistical profiles."""
    columns_profile = []

    for idx, col in enumerate(df.columns):
        series = df[col]
        col_type = detect_column_type(series)
        special_tags = detect_special_columns(str(col), series)
        non_nulls = series.dropna()

        null_count = int(series.isnull().sum())
        distinct_count = int(series.nunique(dropna=True))
        is_categorical = distinct_count < 20 and distinct_count > 1

        # First 5 sample non-null values
        sample_values = [str(x) for x in non_nulls.head(5).tolist()]

        min_val = None
        max_val = None
        mean_val = None
        std_val = None

        if col_type == "number":
            # Coerce to numeric for profiling
            numeric_s = pd.to_numeric(
                non_nulls.astype(str).str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False),
                errors="coerce"
            ).dropna()
            if len(numeric_s) > 0:
                min_val = float(numeric_s.min())
                max_val = float(numeric_s.max())
                mean_val = round(float(numeric_s.mean()), 2)
                std_val = round(float(numeric_s.std()), 2) if len(numeric_s) > 1 else 0.0
        elif col_type == "date":
            try:
                date_s = pd.to_datetime(non_nulls, errors="coerce").dropna()
                if len(date_s) > 0:
                    min_val = str(date_s.min().strftime("%Y-%m-%d"))
                    max_val = str(date_s.max().strftime("%Y-%m-%d"))
            except Exception:
                pass
        else:
            if len(non_nulls) > 0:
                min_val = str(sample_values[0]) if sample_values else None
                max_val = str(sample_values[-1]) if sample_values else None

        col_profile = {
            "column_name": str(col),
            "column_name_tamil": normalize_column_name_tamil(str(col)),
            "column_index": idx,
            "data_type_detected": col_type,
            "sample_values": sample_values,
            "null_count": null_count,
            "distinct_count": distinct_count,
            "min_value": min_val,
            "max_value": max_val,
            "mean_value": mean_val,
            "std_dev": std_val,
            "is_categorical": is_categorical,
            **special_tags,
        }
        columns_profile.append(col_profile)

    return columns_profile


def detect_outliers_iqr(
    df: pd.DataFrame,
    column: str,
    group_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Detect statistical outliers using the 1.5 x IQR rule.
    Returns exact row indices, values, expected range, and Tamil explanations.
    """
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in dataset")

    # Clean numeric series
    s_raw = df[column]
    s_numeric = pd.to_numeric(
        s_raw.astype(str).str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False),
        errors="coerce"
    )

    outliers_list = []

    if group_by and group_by in df.columns:
        # Group-wise IQR
        for grp, grp_df in df.groupby(group_by):
            grp_numeric = s_numeric.loc[grp_df.index].dropna()
            if len(grp_numeric) < 4:
                continue

            q1 = float(grp_numeric.quantile(0.25))
            q3 = float(grp_numeric.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            mean_val = float(grp_numeric.mean()) if len(grp_numeric) > 0 else 1.0

            for idx in grp_df.index:
                val = s_numeric.get(idx)
                if pd.notnull(val) and (val < lower_bound or val > upper_bound):
                    dev_factor = round(abs(val - mean_val) / (iqr if iqr > 0 else (mean_val or 1)), 1)
                    row_data = df.loc[idx].to_dict()
                    outliers_list.append({
                        "row_index": int(idx),
                        "value": float(val),
                        "column": column,
                        group_by: str(grp),
                        "expected_range": [round(lower_bound, 2), round(upper_bound, 2)],
                        "deviation_factor": max(1.0, dev_factor),
                        "reason_tamil": f"{grp} பிரிவில் {column} மதிப்பு {val:,.2f} என்பது எதிர்பார்க்கப்பட்ட வரம்பை விட ({lower_bound:,.2f} - {upper_bound:,.2f}) விலகி உள்ளது.",
                        "row_context": {k: str(v) for k, v in row_data.items() if k != column}
                    })
    else:
        # Overall IQR
        valid_numeric = s_numeric.dropna()
        if len(valid_numeric) >= 4:
            q1 = float(valid_numeric.quantile(0.25))
            q3 = float(valid_numeric.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            mean_val = float(valid_numeric.mean()) if len(valid_numeric) > 0 else 1.0

            for idx, val in s_numeric.items():
                if pd.notnull(val) and (val < lower_bound or val > upper_bound):
                    dev_factor = round(abs(val - mean_val) / (iqr if iqr > 0 else (mean_val or 1)), 1)
                    row_data = df.loc[idx].to_dict()
                    outliers_list.append({
                        "row_index": int(idx),
                        "value": float(val),
                        "column": column,
                        "expected_range": [round(lower_bound, 2), round(upper_bound, 2)],
                        "deviation_factor": max(1.0, dev_factor),
                        "reason_tamil": f"வரிசை {idx}-ல் {column} மதிப்பு {val:,.2f} என்பது மாவட்ட சராசரியை விட {dev_factor} மடங்கு விலகி உள்ளது.",
                        "row_context": {k: str(v) for k, v in row_data.items() if k != column}
                    })

    return {
        "outliers": outliers_list,
        "total_outliers": len(outliers_list),
        "method_used": "iqr",
    }
