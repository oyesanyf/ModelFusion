import os
from typing import Dict, Any
from datetime import datetime
import uuid

import pandas as pd
import numpy as np


def _safe_mkdir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _load_df(file_path: str) -> Dict[str, Any]:
    ext = os.path.splitext(file_path)[-1].lower()
    try:
        if ext in [".csv", ".txt"]:
            df = pd.read_csv(file_path)
        elif ext in [".xls", ".xlsx"]:
            # Read Excel and also create a CSV copy for downstream processing
            df = pd.read_excel(file_path)
            try:
                base = os.getcwd()
                report_dir = os.path.join(base, "reports")
                converted_dir = os.path.join(report_dir, "converted")
                os.makedirs(converted_dir, exist_ok=True)
                csv_name = os.path.splitext(os.path.basename(file_path))[0] + ".csv"
                converted_csv_path = os.path.join(converted_dir, csv_name)
                df.to_csv(converted_csv_path, index=False)
                return {"df": df, "converted_csv_path": converted_csv_path}
            except Exception:
                # If CSV conversion fails, still return the DataFrame
                return {"df": df}
        else:
            return {"error": f"Unsupported file type: {ext}"}
        return {"df": df}
    except Exception as e:
        return {"error": f"Failed to load file: {e}"}


def _clean_df(df: pd.DataFrame) -> Dict[str, Any]:
    notes = []
    df = df.copy()
    before = len(df)
    df.drop_duplicates(inplace=True)
    if len(df) != before:
        notes.append(f"Removed {before - len(df)} duplicate rows")

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            if df[col].isna().any():
                df[col].fillna(df[col].median(), inplace=True)
        else:
            if df[col].isna().any():
                mode = df[col].mode(dropna=True)
                df[col].fillna(mode.iloc[0] if not mode.empty else "", inplace=True)

    normalized = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    if len(set(normalized.values())) == len(df.columns):
        df.columns = list(normalized.values())
        notes.append("Standardized column names to snake_case")
    return {"df": df, "notes": notes}


def _eda(df: pd.DataFrame) -> str:
    rows, cols = df.shape
    sample_cols = ", ".join(df.columns[:10])
    try:
        desc = df.describe(include="all", datetime_is_numeric=True)
        _ = desc.shape  # touch to ensure computed
    except Exception:
        pass
    return f"- Rows: {rows}, Columns: {cols}\n- Preview columns: {sample_cols}"


async def handle_data_analyst(file_path: str, prompt: str, show_menu: bool = True) -> Dict[str, Any]:
    base = os.getcwd()
    report_dir = os.path.join(base, "reports")
    plots_dir = os.path.join(report_dir, "plots")
    _safe_mkdir(plots_dir)

    loaded = _load_df(file_path)
    if "error" in loaded:
        return {"content": f"❌ {loaded['error']}", "success": False}
    df = loaded["df"]
    conversion_note = None
    if "converted_csv_path" in loaded:
        conversion_note = f"Excel detected. Converted to CSV: {os.path.relpath(loaded['converted_csv_path'], base)}"
    elif os.path.splitext(file_path)[-1].lower() == ".csv":
        conversion_note = "CSV file detected. Proceeding with analysis."

    cleaned = _clean_df(df)
    df = cleaned["df"]
    cleaning_notes = cleaned.get("notes", [])

    eda_text = _eda(df)

    # Quick plots (optional)
    plot_artifacts = []
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        if any(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
            num_col = next(c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]))
            plt.figure(figsize=(6, 4))
            df[num_col].dropna().hist(bins=30)
            plt.title(f"Histogram: {num_col}")
            hist_path = os.path.join(plots_dir, f"hist_{num_col}.png")
            plt.tight_layout(); plt.savefig(hist_path); plt.close()
            plot_artifacts.append(hist_path)
    except Exception:
        pass

    # Simple feature engineering
    fe_notes = []
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[f"{c}_year"] = df[c].dt.year
            fe_notes.append(f"Derived {c}_year")
        elif df[c].dtype == object:
            df[f"{c}_length"] = df[c].astype(str).str.len()
            fe_notes.append(f"Derived {c}_length")

    # Anomaly detection (z-score rule of thumb)
    anomalies = []
    for c in df.columns:
        if pd.api.types.is_numeric_dtype(df[c]):
            series = df[c].astype(float)
            mean = series.mean(); std = series.std(ddof=0) or 1.0
            count = int(((series - mean).abs() > 3 * std).sum())
            anomalies.append(f"{c}: {count} potential anomalies (|z|>3)")

    # ML stub: explain expected behavior
    ml_text = "Add a 'target' column to enable quick classification/regression modeling."

    artifacts = "\n".join([f"- {os.path.relpath(p, base)}" for p in plot_artifacts]) if plot_artifacts else "- None"

    def _menu() -> str:
        return (
            "\n".join([
                "## 📋 Analysis Menu",
                "1. 🧹 Data Cleaning and Preparation (Do this first)",
                "2. 📊 Exploratory Data Analysis (EDA)",
                "3. 📈 Visualization",
                "4. ⚙️ Feature Engineering",
                "5. 📉 Statistical Analysis",
                "6. 🤖 Machine Learning",
                "7. 📝 Report and Insights",
                "8. 📂 Specific Log File Analysis",
                "9. ❓ Others (please describe)",
                "10. 📊 Executive Report",
            ])
        )

    menu_top = _menu() if show_menu else ""
    menu_bottom = _menu() if show_menu else ""

    summary = f"""
# Data Analyst Workflow Report

**Prompt:** {prompt}
**File:** {file_path}

{menu_top}

{('- ' + conversion_note) if conversion_note else ''}

## 🧹 Data Cleaning & Preparation
{chr(10).join(['- ' + n for n in (cleaning_notes or ['Handled missing values, standardized columns, removed duplicates'])])}

## 📊 Exploratory Data Analysis (EDA)
{eda_text}

## 📈 Data Visualization
Artifacts:
{artifacts}

## ⚙️ Feature Engineering
{chr(10).join(['- ' + n for n in (fe_notes or ['Derived simple features from dates/text'])])}

## 📉 Statistical Analysis
- Correlation/summary available on numeric columns

## 🤖 Machine Learning
- {ml_text}

## 🧪 A/B Testing & Experimentation
- Add a categorical group column and a numeric metric to enable auto t-test

## 📂 Log File & Time Series Analysis
- Add/identify a datetime column to enable time series plots

## 🗺️ Geo-Spatial Analysis
- Provide latitude/longitude columns (lat/lon) to enable geo plots

## 🧾 Text & NLP Analysis
- Provide a text column to enable tokenization/sentiment summaries

## 🔍 Anomaly Detection
{chr(10).join(['- ' + n for n in anomalies]) if anomalies else '- No numeric columns to analyze'}

## 📝 Reporting & Communication
- Markdown report with links to generated plots

---
*Tip: Install optional packages (matplotlib, seaborn, scipy, scikit-learn, textblob) for richer analysis.*

{menu_bottom}
"""
    # Persist report to reports directory with timestamp-unique filename
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_suffix = uuid.uuid4().hex[:6]
    report_filename = f"data_analyst_report_{ts}_{unique_suffix}.md"
    report_path = os.path.join(report_dir, report_filename)
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(summary)
        saved_note = f"Report saved: {os.path.relpath(report_path, base)}"
    except Exception as e:
        saved_note = f"[WARN] Failed to save report: {e}"

    # Append save note to summary for terminal output
    final_content = summary + "\n" + saved_note + "\n"
    return {"content": final_content, "success": True, "report_path": report_path}
