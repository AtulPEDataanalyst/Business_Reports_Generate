"""
pivot.py — Pivot report generation for Insurance Processing App
Uses Transaction Type column for grouping.
Fresh  = New, Roll Over
Renewal = Renew, Installment, Endorsement
Shows Premium (TPOD) and Total Brokerage Receivable with subtotals per Policy Status and Business Source.
"""

import pandas as pd
import numpy as np

FRESH_TYPES   = ["New", "Rollover"]
RENEWAL_TYPES = ["Renew", "Installment", "Endorsement"]

VALUE_COLS = ["TPOD", "Total Brokerage Receivable"]
INDEX_COLS = ["Policy Status", "Business Source"]

# Column used for pivot grouping — helper column created in Step 16/17
TOB_COL = "Transaction Type"


def _fmt_inr(val) -> str:
    """Format a number in Indian numbering system with ₹ symbol."""
    try:
        val = float(val)
    except (TypeError, ValueError):
        return str(val)
    if val == 0:
        return "₹0.00"
    negative = val < 0
    val = abs(val)
    # Split integer and decimal
    int_part = int(val)
    dec_part = round((val - int_part) * 100)
    # Indian grouping: last 3 digits, then groups of 2
    s = str(int_part)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        s = ",".join(groups) + "," + last3
    result = f"₹{s}.{dec_part:02d}"
    return f"-{result}" if negative else result


def _build_pivot(df: pd.DataFrame, type_filter: list, title: str) -> pd.DataFrame:
    """
    Build pivot table for given Transaction Type values.
    Structure:
      Rows    : Policy Status > Business Source (with subtotals)
      Columns : Transaction Type values
      Values  : TPOD (Premium) and Total Brokerage Receivable
      Margins : Grand Total row at bottom
    Returns a flat DataFrame ready for Excel writing.
    The _is_subtotal and _is_grandtotal columns flag rows for formatting.
    """
    col = TOB_COL if TOB_COL in df.columns else "Type of business"
    if col not in df.columns:
        return pd.DataFrame()

    subset = df[df[col].isin(type_filter)].copy()
    if subset.empty:
        return pd.DataFrame()

    # Ensure numeric values
    for v in VALUE_COLS:
        if v in subset.columns:
            subset[v] = pd.to_numeric(subset[v], errors="coerce").fillna(0.0)
        else:
            subset[v] = 0.0

    available_index = [c for c in INDEX_COLS if c in subset.columns]
    if not available_index:
        return pd.DataFrame()

    # Get unique transaction types present in this subset (in defined order)
    present_types = [t for t in type_filter if t in subset[col].unique()]

    rows = []

    # Group by Policy Status
    status_col = "Policy Status" if "Policy Status" in subset.columns else None
    source_col = "Business Source" if "Business Source" in subset.columns else None

    statuses = subset[status_col].unique() if status_col else ["All"]

    for status in sorted(statuses):
        status_mask = subset[status_col] == status if status_col else pd.Series(True, index=subset.index)
        status_df = subset[status_mask]

        sources = status_df[source_col].unique() if source_col else ["All"]

        for source in sorted(sources):
            src_mask = status_df[source_col] == source if source_col else pd.Series(True, index=status_df.index)
            src_df = status_df[src_mask]

            row = {
                "Policy Status": status,
                "Business Source": source,
                "_is_subtotal": False,
                "_is_grandtotal": False,
            }
            for t in present_types:
                t_df = src_df[src_df[col] == t]
                row[f"Premium | {t}"]    = t_df["TPOD"].sum() if "TPOD" in t_df.columns else 0.0
                row[f"Brokerage | {t}"]  = t_df["Total Brokerage Receivable"].sum() if "Total Brokerage Receivable" in t_df.columns else 0.0
            rows.append(row)

        # Subtotal row per Policy Status
        sub_row = {
            "Policy Status": status,
            "Business Source": "Subtotal",
            "_is_subtotal": True,
            "_is_grandtotal": False,
        }
        for t in present_types:
            t_df = status_df[status_df[col] == t]
            sub_row[f"Premium | {t}"]   = t_df["TPOD"].sum() if "TPOD" in t_df.columns else 0.0
            sub_row[f"Brokerage | {t}"] = t_df["Total Brokerage Receivable"].sum() if "Total Brokerage Receivable" in t_df.columns else 0.0
        rows.append(sub_row)

    # Grand Total row
    gt_row = {
        "Policy Status": "Grand Total",
        "Business Source": "",
        "_is_subtotal": False,
        "_is_grandtotal": True,
    }
    for t in present_types:
        t_df = subset[subset[col] == t]
        gt_row[f"Premium | {t}"]   = t_df["TPOD"].sum() if "TPOD" in t_df.columns else 0.0
        gt_row[f"Brokerage | {t}"] = t_df["Total Brokerage Receivable"].sum() if "Total Brokerage Receivable" in t_df.columns else 0.0
    rows.append(gt_row)

    result = pd.DataFrame(rows)
    result.insert(0, "_Report", title)
    return result


def generate_pivots(df: pd.DataFrame, mode: str, logs: list) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate Fresh and Renewal pivot reports.
    mode: 'login' or 'issued'
    Returns (fresh_pivot_df, renewal_pivot_df)
    """
    fresh_title   = "Fresh Login Business"   if mode == "login" else "Fresh Issued"
    renewal_title = "Renewal Login Business" if mode == "login" else "Renewal Issued"

    fresh_df   = _build_pivot(df, FRESH_TYPES,   fresh_title)
    renewal_df = _build_pivot(df, RENEWAL_TYPES, renewal_title)

    logs.append(f"  Pivot — Fresh rows: {len(fresh_df)}, Renewal rows: {len(renewal_df)}")
    return fresh_df, renewal_df
