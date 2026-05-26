"""
validation.py — Input validation for the Insurance Processing App
"""

import pandas as pd
import streamlit as st

# Columns expected for core processing (others are optional/extra)
REQUIRED_COLUMNS = [
    "Business Date",
    "Policy Request Date",
    "Policy Issue Date",
    "BookedIn",
    "Business Source",
    "Customer Relationship Manager",
    "Class of Policy",
    "Policy Name",
    "Type of business",
    "Policy Status",
    "Insurer Name",
    "Total Brokerage Receivable",
    "Net Premium",
    "Gross Premium",
    "Premium Paid",
    "Basic / Own Damage Premium",
    "Parent PL#",
    "Type",
    "Order ID",
]

OPTIONAL_COLUMNS = [
    "Net Premium",
    "Gross Premium",
    "Premium Paid",
    "Basic / Own Damage Premium",
    "Parent PL#",
    "Order ID",
]


def validate_upload(df: pd.DataFrame, logs: list) -> tuple[bool, list]:
    """
    Validate the uploaded dataframe.
    Returns (is_valid, list_of_warnings).
    """
    warnings = []

    if df.empty:
        logs.append("❌ Uploaded file is empty.")
        return False, warnings

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns and c not in OPTIONAL_COLUMNS]
    if missing:
        logs.append(f"⚠️  Missing columns (will be skipped): {missing}")
        warnings.extend(missing)

    logs.append(f"✅ File validated: {len(df)} rows, {len(df.columns)} columns.")
    return True, warnings


def check_column(df: pd.DataFrame, col: str) -> bool:
    return col in df.columns
