import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("DataVizRouter")

import config

from pipeline.database import (
    delete_dataset,
    get_chart_record,
    get_data_insights,
    get_dataset,
    list_datasets,
    save_chart_record,
    save_data_insight,
    save_data_query,
)
from modules.data_viz.chart_engine import generate_chart_png
from modules.data_viz.ingestion import ingest_dataset_file, load_dataset_dataframe
from modules.data_viz.profiler import detect_outliers_iqr
from modules.data_viz.query_engine import execute_data_query
from modules.data_viz.utils import TAMIL_ERROR_MESSAGES, audit_data_event

router = APIRouter(prefix="/api/v2/data", tags=["Module 2 - Data & Visualization"])


# ---------------------------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    dataset_id: str
    question: str
    officer_id: str = "OFFICER"
    output_format: str = "both"  # "chart", "table", "both"
    chart_type: Optional[str] = None  # "bar", "line", "pie", "horizontal_bar", "table"


class ChartRequest(BaseModel):
    dataset_id: str
    chart_type: str = "bar"
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    group_by: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    title_tamil: str = "வட்ட வாரியான புள்ளிவிவரம்"
    title_english: Optional[str] = None
    officer_id: str = "OFFICER"


class OutlierRequest(BaseModel):
    dataset_id: str
    column: str
    method: str = "iqr"  # "iqr", "zscore"
    group_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Dataset Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    officer_id: str = Form("OFFICER"),
    source_id: Optional[str] = Form(None),
):
    """Upload and profile an Excel or CSV file."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".xlsx", ".xls", ".csv"):
        raise HTTPException(
            status_code=400,
            detail=TAMIL_ERROR_MESSAGES["INVALID_FORMAT"],
        )

    # Save to temp file first to inspect size and hash
    temp_dir = Path(tempfile.gettempdir()) / "erode_data_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"{uuid.uuid4().hex}_{file.filename}"

    try:
        with open(temp_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = ingest_dataset_file(
            file_path=temp_file,
            officer_id=officer_id,
            source_id=source_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal processing error: {e}")
    finally:
        if temp_file.exists():
            temp_file.unlink()


@router.get("/datasets")
async def get_datasets_list(
    officer_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List uploaded datasets with metadata."""
    datasets = list_datasets(officer_id=officer_id, limit=limit, offset=offset)
    return {"datasets": datasets, "total": len(datasets)}


@router.get("/datasets/{dataset_id}/schema")
async def get_dataset_schema(dataset_id: str):
    """Retrieve full schema with profiling stats for a dataset."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=TAMIL_ERROR_MESSAGES["DATASET_NOT_FOUND"])
    return ds


@router.get("/datasets/{dataset_id}/data")
async def get_dataset_rows(dataset_id: str, limit: int = Query(200, ge=1, le=1000)):
    """Retrieve tabular rows of a dataset for frontend table and charting."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=TAMIL_ERROR_MESSAGES["DATASET_NOT_FOUND"])

    try:
        df = load_dataset_dataframe(ds["file_path"], sheet_name=ds.get("sheet_name", "Sheet1"))
        records = df.head(limit).to_dict(orient="records")
        # Clean NaN/Infinity for JSON serialization
        cleaned = []
        for r in records:
            cleaned_row = {}
            for k, v in r.items():
                if isinstance(v, float) and (v != v or v == float("inf") or v == float("-inf")):
                    cleaned_row[k] = None
                else:
                    cleaned_row[k] = v
            cleaned.append(cleaned_row)
        return {
            "dataset_id": dataset_id,
            "total_rows": len(df),
            "columns": list(df.columns),
            "rows": cleaned,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset data: {e}")


@router.delete("/datasets/{dataset_id}")
async def remove_dataset(dataset_id: str, officer_id: str = Query("OFFICER")):
    """Delete a dataset and log audit trail."""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=TAMIL_ERROR_MESSAGES["DATASET_NOT_FOUND"])

    success = delete_dataset(dataset_id)
    if success:
        # Delete file on disk if exists
        ds_file = Path(ds["file_path"])
        if ds_file.exists():
            try:
                if ds_file.parent.name == dataset_id:
                    shutil.rmtree(ds_file.parent, ignore_errors=True)
                else:
                    ds_file.unlink()
            except Exception:
                pass

        audit_data_event(
            action="DATASET_DELETED",
            details=f"Deleted dataset {ds['file_name']}",
            officer_id=officer_id,
            dataset_id=dataset_id,
        )
        return {"status": "ok", "message": "தரவுத்தொகுப்பு வெற்றிகரமாக நீக்கப்பட்டது."}
    raise HTTPException(status_code=500, detail="Failed to delete dataset")


# ---------------------------------------------------------------------------
# Natural Language Query Engine Endpoint
# ---------------------------------------------------------------------------

@router.post("/query")
async def query_dataset_endpoint(req: QueryRequest):
    """
    Interrogate dataset using Tamil/English natural language questions.
    Generates sandboxed code, executes, produces insights and charts.
    """
    ds = get_dataset(req.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=TAMIL_ERROR_MESSAGES["DATASET_NOT_FOUND"])

    query_id = f"qry_{uuid.uuid4().hex[:12]}"
    audit_data_event(
        action="QUERY_SUBMITTED",
        details=f"Question: {req.question}",
        officer_id=req.officer_id,
        dataset_id=req.dataset_id,
    )

    try:
        df = load_dataset_dataframe(ds["file_path"], sheet_name=ds.get("sheet_name", "Sheet1"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}")

    # Execute Query Pipeline
    query_result = execute_data_query(
        df=df,
        question=req.question,
        columns_info=ds.get("columns", []),
        officer_id=req.officer_id,
        dataset_name=ds.get("file_name", "dataset.xlsx"),
    )

    exec_status = query_result["execution_status"]
    chart_url = None
    chart_id = None

    # Generate Chart if requested/suggested and successful
    result_df = query_result.get("result_df")
    if exec_status == "success" and result_df is not None and len(result_df) > 0:
        if req.output_format in ("chart", "both") or query_result.get("chart_suggested"):
            c_type = req.chart_type or query_result.get("chart_type", "bar")
            try:
                chart_info = generate_chart_png(
                    df=result_df,
                    chart_type=c_type,
                    title_tamil=req.question[:60],
                    file_name=ds.get("file_name", "dataset.xlsx"),
                    officer_id=req.officer_id,
                )
                chart_url = chart_info["chart_url"]
                chart_id = chart_info["chart_id"]
            except Exception as e:
                logger.warning(f"Chart rendering skipped: {e}")

    # 1. Save Parent Query Record in DB FIRST (satisfies foreign key constraints)
    save_data_query(
        query_id=query_id,
        dataset_id=req.dataset_id,
        officer_id=req.officer_id,
        question_text=req.question,
        question_language=query_result["question_language"],
        parsed_intent=query_result["parsed_intent"],
        generated_code=query_result["generated_code"],
        generated_sql=query_result["generated_sql"],
        execution_status=exec_status,
        execution_error=query_result.get("execution_error"),
        result_json=str(query_result.get("result_data", [])),
        result_summary=query_result["result_summary_tamil"],
        chart_path=chart_url,
        execution_time_ms=query_result["execution_time_ms"],
        row_count_returned=query_result["row_count_returned"],
    )

    # 2. Save Child Chart Record (references query_id)
    if chart_id and chart_info:
        try:
            save_chart_record(
                chart_id=chart_id,
                query_id=query_id,
                dataset_id=req.dataset_id,
                chart_type=chart_info.get("chart_type", req.chart_type or "bar"),
                chart_title_tamil=req.question[:60],
                file_path=chart_info["file_path"],
                file_size_bytes=chart_info["file_size_bytes"],
                officer_id=req.officer_id,
            )
            audit_data_event(
                action="CHART_GENERATED",
                details=f"Chart {chart_id} generated",
                officer_id=req.officer_id,
                dataset_id=req.dataset_id,
            )
        except Exception as e:
            logger.warning(f"Save chart record skipped: {e}")

    # 3. Save Child Grounded Insights (references query_id)
    saved_insights = []
    for ins in query_result.get("insights", []):
        ins_id = save_data_insight(
            query_id=query_id,
            dataset_id=req.dataset_id,
            insight_type=ins["insight_type"],
            insight_text_tamil=ins["insight_tamil"],
            insight_text_english=ins.get("insight_english"),
            grounding_sql=query_result["generated_sql"],
            grounding_rows=ins.get("grounding_rows", []),
            confidence_score=ins.get("confidence_score", 1.0),
        )
        saved_insights.append({**ins, "insight_id": ins_id})


    # Audit final execution status
    if exec_status == "success":
        audit_data_event(
            action="QUERY_EXECUTED",
            details=f"Query {query_id} returned {query_result['row_count_returned']} rows in {query_result['execution_time_ms']}ms",
            officer_id=req.officer_id,
            dataset_id=req.dataset_id,
        )
    elif exec_status == "unsafe_blocked":
        audit_data_event(
            action="QUERY_BLOCKED",
            details=f"Query blocked for security: {query_result.get('execution_error')}",
            officer_id=req.officer_id,
            dataset_id=req.dataset_id,
        )
    else:
        audit_data_event(
            action="QUERY_ERROR",
            details=f"Query error: {query_result.get('execution_error')}",
            officer_id=req.officer_id,
            dataset_id=req.dataset_id,
        )

    return {
        "query_id": query_id,
        "execution_status": exec_status,
        "execution_error": query_result.get("execution_error"),
        "execution_time_ms": query_result["execution_time_ms"],
        "result_summary_tamil": query_result["result_summary_tamil"],
        "result_summary_english": query_result["result_summary_english"],
        "result_data": query_result["result_data"],
        "chart_url": chart_url,
        "insights": saved_insights,
        "generated_code": query_result["generated_code"],
        "generated_sql": query_result["generated_sql"],
        "row_count_returned": query_result["row_count_returned"],
    }


# ---------------------------------------------------------------------------
# Custom Chart Generation Endpoint
# ---------------------------------------------------------------------------

@router.post("/chart")
async def create_custom_chart(req: ChartRequest):
    """Generate custom chart PNG with user-specified dimensions and filters."""
    ds = get_dataset(req.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=TAMIL_ERROR_MESSAGES["DATASET_NOT_FOUND"])

    try:
        df = load_dataset_dataframe(ds["file_path"], sheet_name=ds.get("sheet_name", "Sheet1"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}")

    # Apply optional filter
    if req.filter:
        for col, allowed_vals in req.filter.items():
            if col in df.columns and isinstance(allowed_vals, list):
                df = df[df[col].isin(allowed_vals)]

    chart_info = generate_chart_png(
        df=df,
        chart_type=req.chart_type,
        x_column=req.x_column,
        y_column=req.y_column,
        group_by=req.group_by,
        title_tamil=req.title_tamil,
        title_english=req.title_english,
        file_name=ds.get("file_name", "dataset.xlsx"),
        officer_id=req.officer_id,
    )

    save_chart_record(
        chart_id=chart_info["chart_id"],
        query_id=None,
        dataset_id=req.dataset_id,
        chart_type=req.chart_type,
        chart_title_tamil=req.title_tamil,
        chart_title_english=req.title_english,
        x_axis_column=req.x_column,
        y_axis_column=req.y_column,
        group_by_column=req.group_by,
        file_path=chart_info["file_path"],
        file_size_bytes=chart_info["file_size_bytes"],
        officer_id=req.officer_id,
    )

    audit_data_event(
        action="CHART_GENERATED",
        details=f"Custom chart {chart_info['chart_id']} ({req.chart_type}) created",
        officer_id=req.officer_id,
        dataset_id=req.dataset_id,
    )

    return chart_info


@router.get("/charts/{chart_id}")
async def get_chart_image(chart_id: str):
    """Serve generated chart PNG file."""
    chart_record = get_chart_record(chart_id)
    if not chart_record:
        # Fallback to direct file path in charts directory
        chart_path = config.OUTPUTS_CHARTS_DIR / f"{chart_id}.png"
        if not chart_path.exists():
            chart_path = config.OUTPUTS_CHARTS_DIR / chart_id
        if not chart_path.exists():
            raise HTTPException(status_code=404, detail="Chart not found")
        return FileResponse(path=str(chart_path), media_type="image/png")

    file_path = Path(chart_record["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Chart image file missing on disk")

    return FileResponse(path=str(file_path), media_type="image/png")


# ---------------------------------------------------------------------------
# Outlier Detection Endpoint
# ---------------------------------------------------------------------------

@router.post("/outliers")
async def detect_outliers_endpoint(req: OutlierRequest):
    """Detect numerical outliers using the 1.5 x IQR rule."""
    ds = get_dataset(req.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=TAMIL_ERROR_MESSAGES["DATASET_NOT_FOUND"])

    try:
        df = load_dataset_dataframe(ds["file_path"], sheet_name=ds.get("sheet_name", "Sheet1"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {e}")

    try:
        result = detect_outliers_iqr(df=df, column=req.column, group_by=req.group_by)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Outlier calculation failed: {e}")
