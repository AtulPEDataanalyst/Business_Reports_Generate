"""
processing.py — Business logic for Login Business and Issued Business processing
Handles all 17 steps documented in the business process specification.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from utils.validation import check_column

# ─── CRM → Business Source mapping (configurable) ────────────────────────────
CRM_MAPPING: dict[str, str] = {
    "Direct": "Direct",
    "Soman Soni": "Direct",
    "Sachin Dubey": "Affiliate",
    "Milind Chilhate": "IMA",
    "Ravi Raj Rathore": "Direct",
    "Vinita Mohan Rane": "IMA",
    "Suvarna Gawai": "IMA",
    # Add more CRM → Source mappings here as needed
}

HEALTH_LIFE_CLASSES = ["Health", "Life", "Health (Non Life)"]
PRIVATE_CAR_POLICIES = ["Private Car Comp", "Private Car SAOD",
                        "Private Car - Comp", "Private Car - SAOD"]
PI_POLICIES = [
    "PROFESSIONAL INDEMNITY HOSPITAL",
    "PROFESSIONAL INDEMNITY DOCTORS",
    "PROFFESSIONAL INDEMNITY HOSPITAL",
    "PROFFESSIONAL INDEMNITY DOCTORS",
]
GENERALI = "Generali Central Insurance Company Limited"


def _safe_numeric(df: pd.DataFrame, col: str) -> pd.Series:
    """Return numeric series for col, 0 if missing."""
    if col not in df.columns:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def _is_blank_or_zero(series: pd.Series) -> pd.Series:
    return (series.isna()) | (series == 0)


def process_login_business(df: pd.DataFrame, logs: list) -> pd.DataFrame:
    """Run all 17 Login Business steps and return processed DataFrame."""
    df = df.copy()
    initial_rows = len(df)
    logs.append(f"▶ Starting Login Business processing with {initial_rows} rows.")

    # STEP 1 — Fill blank Policy Request Date from Business Date
    if check_column(df, "Policy Request Date") and check_column(df, "Business Date"):
        df["Policy Request Date"] = pd.to_datetime(df["Policy Request Date"], errors="coerce")
        df["Business Date"] = pd.to_datetime(df["Business Date"], errors="coerce")
        mask = df["Policy Request Date"].isna()
        df.loc[mask, "Policy Request Date"] = df.loc[mask, "Business Date"]
        logs.append(f"  Step 1: Filled {mask.sum()} blank Policy Request Dates from Business Date.")

    # STEP 2 — Filter current month data from Policy Request Date
    now = datetime.now()
    if check_column(df, "Policy Request Date"):
        before = len(df)
        mask = (df["Policy Request Date"].dt.month == now.month) & \
               (df["Policy Request Date"].dt.year == now.year)
        df = df[mask].copy()
        logs.append(f"  Step 2: Filtered to current month ({now.strftime('%B %Y')}): {before} → {len(df)} rows.")

    # STEP 3 — Delete rows where BookedIn == "Direct Code"
    if check_column(df, "BookedIn"):
        before = len(df)
        df = df[df["BookedIn"].astype(str).str.strip() != "Direct Code"].copy()
        logs.append(f"  Step 3: Deleted {before - len(df)} 'Direct Code' rows.")

    df = _shared_steps(df, logs, mode="login")
    logs.append(f"✅ Login Business processing complete: {len(df)} rows output.")
    return df


def process_issued_business(df: pd.DataFrame, logs: list) -> pd.DataFrame:
    """Run all Issued Business steps (same as Login with noted differences)."""
    df = df.copy()
    initial_rows = len(df)
    logs.append(f"▶ Starting Issued Business processing with {initial_rows} rows.")

    # DIFF 1 — Use Policy Issue Date instead of Policy Request Date
    if check_column(df, "Policy Issue Date") and check_column(df, "Business Date"):
        df["Policy Issue Date"] = pd.to_datetime(df["Policy Issue Date"], errors="coerce")
        df["Business Date"] = pd.to_datetime(df["Business Date"], errors="coerce")
        mask = df["Policy Issue Date"].isna()
        df.loc[mask, "Policy Issue Date"] = df.loc[mask, "Business Date"]
        logs.append(f"  Step 1: Filled {mask.sum()} blank Policy Issue Dates from Business Date.")

    now = datetime.now()
    if check_column(df, "Policy Issue Date"):
        before = len(df)
        mask = (df["Policy Issue Date"].dt.month == now.month) & \
               (df["Policy Issue Date"].dt.year == now.year)
        df = df[mask].copy()
        logs.append(f"  Step 2: Filtered to current month ({now.strftime('%B %Y')}): {before} → {len(df)} rows.")

    # STEP 3 — Same: delete Direct Code
    if check_column(df, "BookedIn"):
        before = len(df)
        df = df[df["BookedIn"].astype(str).str.strip() != "Direct Code"].copy()
        logs.append(f"  Step 3: Deleted {before - len(df)} 'Direct Code' rows.")

    # DIFF 2 — Delete rows where Policy Status == "Policy Awaited" (before shared steps)
    if check_column(df, "Policy Status"):
        before = len(df)
        df = df[df["Policy Status"].astype(str).str.strip() != "Policy Awaited"].copy()
        logs.append(f"  Step 3b (Issued): Deleted {before - len(df)} 'Policy Awaited' rows.")

    df = _shared_steps(df, logs, mode="issued")
    logs.append(f"✅ Issued Business processing complete: {len(df)} rows output.")
    return df


def _shared_steps(df: pd.DataFrame, logs: list, mode: str) -> pd.DataFrame:
    """Steps 4–17 shared by both Login and Issued Business."""

    # STEP 4 — Fill blank Business Source from CRM mapping
    if check_column(df, "Business Source") and check_column(df, "Customer Relationship Manager"):
        mask = df["Business Source"].isna() | (df["Business Source"].astype(str).str.strip() == "")
        filled = 0
        for idx in df[mask].index:
            crm = str(df.at[idx, "Customer Relationship Manager"]).strip()
            mapped = CRM_MAPPING.get(crm, "")
            if mapped:
                df.at[idx, "Business Source"] = mapped
                filled += 1
        logs.append(f"  Step 4: Filled {filled} blank Business Source values from CRM mapping.")

    # STEP 5 & 6 & 7 — Fix Net Premium and Gross Premium
    net_col = "Net Premium"
    gross_col = "Gross Premium"
    paid_col = "Premium Paid"
    class_col = "Class of Policy"

    if net_col in df.columns:
        df[net_col] = pd.to_numeric(df[net_col], errors="coerce").fillna(0.0)
    if gross_col in df.columns:
        df[gross_col] = pd.to_numeric(df[gross_col], errors="coerce").fillna(0.0)
    if paid_col in df.columns:
        df[paid_col] = pd.to_numeric(df[paid_col], errors="coerce").fillna(0.0)

    non_health_life = ~df[class_col].astype(str).isin(HEALTH_LIFE_CLASSES) if class_col in df.columns else pd.Series(True, index=df.index)

    # Step 5: If Net Premium == 0 or blank, fill Gross Premium from Premium Paid
    if net_col in df.columns and gross_col in df.columns:
        need_fix = non_health_life & _is_blank_or_zero(df[net_col])
        gross_blank = _is_blank_or_zero(df[gross_col])
        # If Gross Premium is blank/0, use Premium Paid
        if paid_col in df.columns:
            df.loc[need_fix & gross_blank, gross_col] = df.loc[need_fix & gross_blank, paid_col]
        logs.append(f"  Step 5: Filled Gross Premium from Premium Paid for {(need_fix & gross_blank).sum()} rows.")

    # Step 6: Delete rows where both Gross Premium and Premium Paid are 0/blank
    if gross_col in df.columns and paid_col in df.columns:
        before = len(df)
        both_zero = non_health_life & _is_blank_or_zero(df[gross_col]) & _is_blank_or_zero(df[paid_col])
        df = df[~both_zero].copy()
        logs.append(f"  Step 6: Deleted {before - len(df)} rows where both Gross Premium and Premium Paid are 0/blank.")

    # Step 7: Net Premium = Gross Premium / 1.18
    if net_col in df.columns and gross_col in df.columns:
        need_calc = non_health_life & _is_blank_or_zero(df[net_col])
        df.loc[need_calc, net_col] = (df.loc[need_calc, gross_col] / 1.18).round(2)
        logs.append(f"  Step 7: Recalculated Net Premium for {need_calc.sum()} rows.")

    # STEP 8 — Temp column: Difference = Gross Premium - Net Premium
    if gross_col in df.columns and net_col in df.columns:
        df["_Difference"] = (_safe_numeric(df, gross_col) - _safe_numeric(df, net_col)).round(2)

    # STEP 9 — Where Difference == 0 (not Health/Life), recalculate Net Premium
    if "_Difference" in df.columns and net_col in df.columns and gross_col in df.columns:
        recalc = non_health_life & (df["_Difference"] == 0) & ~_is_blank_or_zero(df[gross_col])
        df.loc[recalc, net_col] = (df.loc[recalc, gross_col] / 1.18).round(2)
        logs.append(f"  Step 9: Recalculated Net Premium (Difference==0) for {recalc.sum()} rows.")

    # STEP 10 — Delete temp column, create TPOD
    if "_Difference" in df.columns:
        df.drop(columns=["_Difference"], inplace=True)

    # STEP 11 — TPOD column
    bod_col = "Basic / Own Damage Premium"
    df["TPOD"] = 0.0
    if net_col in df.columns:
        df["TPOD"] = _safe_numeric(df, net_col)
    if bod_col in df.columns and "Policy Name" in df.columns:
        car_mask = df["Policy Name"].astype(str).str.strip().isin(PRIVATE_CAR_POLICIES)
        df.loc[car_mask, "TPOD"] = _safe_numeric(df, bod_col)[car_mask]
        logs.append(f"  Step 11: Set TPOD = Basic/Own Damage Premium for {car_mask.sum()} Private Car rows.")

    # STEP 12 — PI policies: if New and Order ID contains "_", change to Renew
    tob_col = "Type of business"
    if tob_col in df.columns and "Policy Name" in df.columns and "Order ID" in df.columns:
        pi_mask = df["Policy Name"].astype(str).str.upper().str.strip().isin(
            [p.upper() for p in PI_POLICIES])
        new_mask = df[tob_col].astype(str).str.strip().str.lower() == "new"
        underscore_mask = df["Order ID"].astype(str).str.contains("_", na=False)
        change_mask = pi_mask & new_mask & underscore_mask
        df.loc[change_mask, tob_col] = "Renew"
        logs.append(f"  Step 12: Changed {change_mask.sum()} PI 'New' rows to 'Renew' (Order ID has '_').")

    # STEP 13 — Parent PL# not blank + Type == Policy → Renew
    if "Parent PL#" in df.columns and "Type" in df.columns and tob_col in df.columns:
        parent_not_blank = df["Parent PL#"].notna() & (df["Parent PL#"].astype(str).str.strip() != "")
        type_policy = df["Type"].astype(str).str.strip().str.lower() == "policy"
        mask = parent_not_blank & type_policy
        df.loc[mask, tob_col] = "Renew"
        logs.append(f"  Step 13: Changed {mask.sum()} rows to 'Renew' (Parent PL# set + Type = Policy).")

    # STEP 14 — Policy Status handling
    status_col = "Policy Status"
    if status_col in df.columns:
        if mode == "login":
            # Exclude Policy Awaited and Cancelled
            before = len(df)
            df = df[~df[status_col].astype(str).str.strip().isin(["Policy Awaited", "Cancelled"])].copy()
            logs.append(f"  Step 14: Removed {before - len(df)} 'Policy Awaited'/'Cancelled' rows.")
            # Set remaining to "Issued"
            df[status_col] = "Issued"
            logs.append(f"  Step 14: Set all remaining Policy Status = 'Issued'.")
        else:
            # Issued mode: only exclude Cancelled (Policy Awaited already removed)
            before = len(df)
            df = df[df[status_col].astype(str).str.strip() != "Cancelled"].copy()
            logs.append(f"  Step 14 (Issued): Removed {before - len(df)} 'Cancelled' rows.")
            not_awaited = df[status_col].astype(str).str.strip() != "Not Issued"
            df.loc[not_awaited, status_col] = "Issued"

        # Replace Policy Awaited with Not Issued (in case any remain)
        df[status_col] = df[status_col].astype(str).str.replace("Policy Awaited", "Not Issued", regex=False)

    # STEP 15 — Brokerage logic
    brok_col = "Total Brokerage Receivable"
    if "Insurer Name" in df.columns and "TPOD" in df.columns:
        generali_mask = df["Insurer Name"].astype(str).str.strip() == GENERALI
        df.loc[generali_mask, brok_col] = (df.loc[generali_mask, "TPOD"] * 0.45).round(2)
        df.loc[~generali_mask, brok_col] = (df.loc[~generali_mask, "TPOD"] * 0.15).round(2)
        logs.append(f"  Step 15: Brokerage set (45% Generali: {generali_mask.sum()} rows, 15% others: {(~generali_mask).sum()} rows).")

    # STEP 16 — Type == Endorsement → Type of Business = Endorsement
    if "Type" in df.columns and tob_col in df.columns:
        endo_mask = df["Type"].astype(str).str.strip().str.lower() == "endorsement"
        df.loc[endo_mask, tob_col] = "Endorsement"
        logs.append(f"  Step 16: Set {endo_mask.sum()} Endorsement rows.")

    # STEP 17 — Type contains Installment → Type of Business = Installment; fix zero brokerage
    if "Type" in df.columns and tob_col in df.columns:
        inst_mask = df["Type"].astype(str).str.strip().str.lower().str.contains("installment", na=False)
        df.loc[inst_mask, tob_col] = "Installment"
        if brok_col in df.columns:
            zero_brok = inst_mask & _is_blank_or_zero(df[brok_col])
            df.loc[zero_brok, brok_col] = (df.loc[zero_brok, "TPOD"] * 0.01).round(2)
            logs.append(f"  Step 17: Set {inst_mask.sum()} Installment rows; fixed {zero_brok.sum()} zero brokerage rows.")

    return df
