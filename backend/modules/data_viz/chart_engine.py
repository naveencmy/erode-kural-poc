"""Matplotlib Chart Generation Engine for Module 2: Data & Visualization.

Generates publication-quality charts styled with Tamil Nadu Government color
palettes, Tamil typography, and anti-hallucination provenance metadata footers.
"""

import logging
import warnings
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # Headless backend for server execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import config

# Suppress findfont fallback warnings from cluttering logs
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# Configure font priority for Tamil Unicode rendering (Nirmala UI is the default Windows 10/11 Tamil font)
plt.rcParams["font.family"] = ["Nirmala UI", "Noto Sans Tamil", "Latha", "Segoe UI", "Arial Unicode MS", "DejaVu Sans", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


# TN Government Palette Tokens
TN_PRIMARY = "#1a3a5c"
TN_ACCENT = "#c8a951"
TN_SUCCESS = "#22c55e"
TN_WARNING = "#f59e0b"
TN_DANGER = "#ef4444"
TN_PALETTE = [TN_PRIMARY, TN_ACCENT, "#3b82f6", "#10b981", "#8b5cf6", "#ec4899", "#f97316", "#14b8a6"]


def generate_chart_png(
    df: pd.DataFrame,
    chart_type: str,
    x_column: Optional[str] = None,
    y_column: Optional[str] = None,
    group_by: Optional[str] = None,
    title_tamil: str = "தரவு விளக்கப்படம்",
    title_english: Optional[str] = None,
    file_name: str = "dataset.xlsx",
    officer_id: str = "OFFICER",
    dark_mode: bool = True,
) -> Dict[str, Any]:
    """
    Render and save a chart PNG from a pandas DataFrame.
    Returns { chart_id, file_path, file_size_bytes, chart_url }.
    """
    chart_id = f"chart_{uuid.uuid4().hex[:12]}"
    output_path = config.OUTPUTS_CHARTS_DIR / f"{chart_id}.png"

    # Set up colors
    bg_fig = "#0f172a" if dark_mode else "#ffffff"
    bg_ax = "#1e293b" if dark_mode else "#f8f9fa"
    text_color = "#f1f5f9" if dark_mode else "#1e293b"
    grid_color = "#334155" if dark_mode else "#e2e8f0"

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor(bg_fig)
    ax.set_facecolor(bg_ax)

    # Determine x and y columns if not provided
    cols = list(df.columns)
    if not x_column and len(cols) > 0:
        x_column = cols[0]
    if not y_column and len(cols) > 1:
        y_column = cols[1]

    clean_df = df.dropna(subset=[x_column] if x_column in df.columns else []).copy()

    # Chart Type Logic
    chart_type = chart_type.lower()
    if chart_type in ("bar", "horizontal_bar") and y_column and y_column in clean_df.columns:
        # Numeric coercion for y
        clean_df[y_column] = pd.to_numeric(
            clean_df[y_column].astype(str).str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False),
            errors="coerce"
        )
        plot_df = clean_df.dropna(subset=[y_column]).head(15)

        if chart_type == "horizontal_bar":
            bars = ax.barh(plot_df[x_column].astype(str), plot_df[y_column], color=TN_PALETTE[:len(plot_df)], edgecolor="none")
            ax.set_xlabel(y_column, fontsize=11, color=text_color)
            ax.set_ylabel(x_column, fontsize=11, color=text_color)
        else:
            bars = ax.bar(plot_df[x_column].astype(str), plot_df[y_column], color=TN_PALETTE[:len(plot_df)], edgecolor="none")
            ax.set_xlabel(x_column, fontsize=11, color=text_color)
            ax.set_ylabel(y_column, fontsize=11, color=text_color)
            plt.xticks(rotation=30, ha="right", fontsize=9, color=text_color)

    elif chart_type == "line" and y_column and y_column in clean_df.columns:
        clean_df[y_column] = pd.to_numeric(
            clean_df[y_column].astype(str).str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False),
            errors="coerce"
        )
        plot_df = clean_df.dropna(subset=[y_column]).head(30)
        ax.plot(plot_df[x_column].astype(str), plot_df[y_column], marker="o", linewidth=2.5, color=TN_ACCENT, label=y_column)
        ax.set_xlabel(x_column, fontsize=11, color=text_color)
        ax.set_ylabel(y_column, fontsize=11, color=text_color)
        plt.xticks(rotation=30, ha="right", fontsize=9, color=text_color)

    elif chart_type == "pie" and y_column and y_column in clean_df.columns:
        clean_df[y_column] = pd.to_numeric(
            clean_df[y_column].astype(str).str.replace(",", "").str.replace("₹", "").str.replace("Rs.", "", case=False),
            errors="coerce"
        )
        plot_df = clean_df.dropna(subset=[y_column]).head(6)
        wedges, texts, autotexts = ax.pie(
            plot_df[y_column],
            labels=plot_df[x_column].astype(str),
            autopct="%1.1f%%",
            colors=TN_PALETTE[:len(plot_df)],
            startangle=140,
            textprops={"color": text_color, "fontsize": 10},
        )
        for at in autotexts:
            at.set_color("#ffffff")
            at.set_weight("bold")

    else:
        # Generic Bar fallback
        val_col = cols[1] if len(cols) > 1 else cols[0]
        numeric_s = pd.to_numeric(clean_df[val_col], errors="coerce").fillna(1)
        ax.bar(clean_df[cols[0]].astype(str).head(10), numeric_s.head(10), color=TN_PRIMARY)
        ax.set_xlabel(cols[0], fontsize=11, color=text_color)
        plt.xticks(rotation=30, ha="right", fontsize=9, color=text_color)

    # Title styling
    title_text = title_tamil
    if title_english:
        title_text += f"\n({title_english})"
    ax.set_title(title_text, fontsize=14, fontweight="bold", color=text_color, pad=18)

    # Grid & Spines
    ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
    for spine in ax.spines.values():
        spine.set_color(grid_color)
    ax.tick_params(colors=text_color)

    # Stamped Provenance Metadata Footer
    timestamp_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    footer_text = f"மூலம்: {file_name} | உருவாக்கப்பட்ட தேதி: {timestamp_str} | அலுவலர்: {officer_id}"
    fig.text(0.5, 0.01, footer_text, ha="center", fontsize=8, color="#94a3b8", style="italic")

    # Save to disk
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    plt.savefig(output_path, bbox_inches="tight", facecolor=bg_fig)
    plt.close(fig)

    file_size = output_path.stat().st_size if output_path.exists() else 0

    return {
        "chart_id": chart_id,
        "file_path": str(output_path),
        "file_size_bytes": file_size,
        "chart_url": f"/outputs/charts/{chart_id}.png",
    }
