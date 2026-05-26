"""
pivot.py — Pivot report generation for Insurance Processing App
Generates Fresh and Renewal pivot tables grouped by Policy Status and Business Source.
"""

import pandas as pd
import numpy as np


FRESH_TYPES = ["New", "Roll Over"]
RENEWAL_TYPES = ["Endorsement", "Renew", "Installment"]

VALUE_COLS = ["TPOD", "Total Brokerage Receivable"]
INDEX_COLS = ["Policy Status", "Business Source"]


def _build_pivot(df: pd.DataFrame, type_filter: list, title: str) -> pd.DataFrame:
    """
    Build a pivot table for a given subset of Type of Business values.
    Returns a formatted DataFrame with multi-level columns.
    """
    tob_col = "Type of business"
    if tob_col not in df.columns:
        return pd.DataFrame()

    subset = df[df[tob_col].isin(type_filter)].copy()
    if subset.empty:
        return pd.DataFrame()

    # Ensure numeric
    for col in VALUE_COLS:
        if col in subset.columns:
            subset[col] = pd.to_numeric(subset[col], errors="coerce").fillna(0.0)

    available_values = [c for c in VALUE_COLS if c in subset.columns]
    available_index = [c for c in INDEX_COLS if c in subset.columns]

    if not available_values or not available_index:
        return pd.DataFrame()

    pivot = pd.pivot_table(
        subset,
        values=available_values,
        index=available_index,
        columns=tob_col,
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="Grand Total",
    )

    # Flatten column multi-index
    if isinstance(pivot.columns, pd.MultiIndex):
        pivot.columns = [f"{v} | {t}" if t != "" else v for v, t in pivot.columns]
    
    pivot = pivot.reset_index()
    pivot.insert(0, "_Report", title)
    return pivot


def generate_pivots(df: pd.DataFrame, mode: str, logs: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate Fresh and Renewal pivot reports.
    mode: 'login' or 'issued'
    Returns (fresh_pivot_df, renewal_pivot_df)
    """
    fresh_title = "Fresh Login Business" if mode == "login" else "Fresh Issued"
    renewal_title = "Renewal Login Business" if mode == "login" else "Renewal Issued"

    fresh_df = _build_pivot(df, FRESH_TYPES, fresh_title)
    renewal_df = _build_pivot(df, RENEWAL_TYPES, renewal_title)

    logs.append(f"  Pivot — Fresh rows: {len(fresh_df)}, Renewal rows: {len(renewal_df)}")
    return fresh_df, renewal_df
