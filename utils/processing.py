"""
processing.py — Business logic for Login Business and Issued Business processing
Handles all 17 steps documented in the business process specification.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from utils.validation import check_column


# ─── Per-transaction audit logger ─────────────────────────────────────────────
def _log_change(logs: list, row_id, field: str, old_val, new_val, reason: str = ""):
    """Append a colour-coded per-row field-change entry."""
    reason_str = f" ← {reason}" if reason else ""
    logs.append(
        f'<span class="log-change">'
        f'[CHANGE] Row {row_id} | {field}: "{old_val}" → "{new_val}"{reason_str}'
        f'</span>'
    )


def _log_row_ok(logs: list, row_id, ref=None):
    ref_str = f" | Ref: {ref}" if ref else ""
    logs.append(
        f'<span class="log-ok">[OK] Row {row_id}{ref_str} — processed</span>'
    )


def _log_skip(logs: list, row_id, reason: str):
    logs.append(
        f'<span class="log-skip">[SKIP] Row {row_id} — {reason}</span>'
    )



# ─── CRM → Business Source mapping (configurable) ────────────────────────────
CRM_MAPPING: dict[str, str] = {

    # ─── Direct ─────────────────────────
    "Ankush Jamunde": "Direct",
    "Tejas Loke": "Direct",
    "Ravi Raj Rathore": "Direct",
    "Soman Soni": "Direct",
    "Shraddha Pawar": "Direct",
    "Gautam Rajendra Soni": "Direct",
    "Krutika Chalke": "Direct",
    "Manisha Singh": "Direct",
    "Mohammad Shaikh": "Direct",
    "Sachin Dubey": "Direct",
    "Pradeep Yadav": "Direct",
    "Aakash Hirekhan": "Direct",
    "Priti Gajare": "Direct",
    "Puja Ganesh Kamble": "Direct",
    "Milind Chilhate": "Direct",
    "Vivek Dave": "Direct",
    "Gyanendra Tiwari": "Direct",
    "Girish Konkar": "Direct",
    "Sanidev Vishwakarma": "Direct",
    "Mehtab Khan": "Direct",
    "Satish Durgoli": "Direct",
    "Direct": "Direct",
    "Tejas Loke, Shraddha Pawar": "Direct",

    # ─── Affiliate ──────────────────────
    "Sachin Dubey": "Affiliate",
    "Krutika Chalke": "Affiliate",
    "Pradnya Shikhre": "Affiliate",
    "Sonam Mulay": "Affiliate",
    "Siddhesh Gore": "Affiliate",
    "Sundar Naik": "Affiliate",
    "Rasika Parab": "Affiliate",
    "Pradeep Yadav": "Affiliate",
    "Sarjerao Gorad": "Affiliate",
    "Amit Kumar Pandey": "Affiliate",
    "Vishal Pandya": "Affiliate",
    "Mehtab Khan": "Affiliate",
    "Avinash Maurya": "Affiliate",
    "Aakash Hirekhan": "Affiliate",
    "Ajay Jaiswal": "Affiliate",
    "Manisha Singh": "Affiliate",
    "Pramila Jadhav": "Affiliate",
    "Pratishtha Anil  Singh": "Affiliate",
    "Milind Chilhate": "Affiliate",
    "Priti Gajare": "Affiliate",
    "Puja Ganesh Kamble": "Affiliate",
    "Ravi Raj Rathore": "Affiliate",
    "Gyanendra Tiwari": "Affiliate",
    "Mamta Gupta": "Affiliate",
    "Suresh Murtadak": "Affiliate",
    "Santosh Mirashi": "Affiliate",
    "Vikrant Gharat": "Affiliate",
    "Priya Choube": "Affiliate",
    "Prawesh Rathod": "Affiliate",
    "Ranapratap Yadav": "Affiliate",
    "Sheetal Kadam": "Affiliate",
    "VIJAY SANMUKH KAMBE": "Affiliate",

    # ─── IMA ────────────────────────────
    "Milind Chilhate": "IMA",
    "Vinita Mohan Rane": "IMA",
    "Suvarna Gawai": "IMA",
    "Vaishali Bhivsane": "IMA",
    "Snehal Owhal": "IMA",
    "Yogesh Tribhuvan": "IMA",
    "Rasika Parab": "IMA",
    "Teesha Sonawane": "IMA",
    "Manisha Singh": "IMA",
    "Lakshmi Kagada": "IMA",
    "Sejal Rai": "IMA",
    "Savitri Pandey": "IMA",
    "Harsh Mahale": "IMA",
    "Prisha Jadhav": "IMA",
    "Tejas Loke": "IMA",
    "Antara Kadam": "IMA",
    "Supriya Mishra": "IMA",
    "Yogita Tiwari": "IMA",
    "Mehtab Khan": "IMA",
    "Ranveer Singh": "IMA",
    "Manasi Gite": "IMA",
    "Divya Naik": "IMA",
    "Anita Sonone": "IMA",
    "Vishal Shelke": "IMA",
    "Rajendra Bhosale": "IMA",
    "Girish Konkar": "IMA",
    "Nandini Devendra": "IMA",
    "Jyoti Jaiswal": "IMA",
    "Aman Yadav": "IMA",
    "Mohammad Shaikh": "IMA",
    "Sayali Gangar": "IMA",
    "Neha Prajapati": "IMA",
    "Pratik Jaywant kashte": "IMA",
    "Muskan Mishra": "IMA",
    "Riya Yadav": "IMA",
    "Sanika Kanekar": "IMA",
    "Sahil Karambele": "IMA",
    "SHREYA DILIP BARE": "IMA",
    "SADIYA RAFIQUE SHAIKH": "IMA",
    "VISHAKHA BHOSLE": "IMA",
    "Shraddha Pawar": "IMA",
    "Anil Yadav": "IMA",
    "Harsh Raul": "IMA",
    "Alok Gauda": "IMA",
    "Pintu Gauda": "IMA",
    "Babaji Naiksatam": "IMA",
    "Yash More": "IMA",
    "Ritali Samindre": "IMA",
    "Radha Choudhary": "IMA",
    "Shivangi Kaushik": "IMA",
    "Sonika Singh": "IMA",
    "Ankita Sutar": "IMA",
    "Jayesh Jain": "IMA",
    "Vivek Chiplunkar": "IMA",
    "Vivek Dave": "IMA",
    "Direct": "IMA",

    # ─── IMA Cross Sales ─────────────────
    "Ravi Raj Rathore": "IMA Cross Sales",
    "Milind Chilhate": "IMA Cross Sales",
    "Manisha Singh": "IMA Cross Sales",
    "Prisha Jadhav": "IMA Cross Sales",
    "Antara Kadam": "IMA Cross Sales",
    "Rasika Parab": "IMA Cross Sales",
    "Snehal Owhal": "IMA Cross Sales",
    "Mehtab Khan": "IMA Cross Sales",
    "Yogesh Tribhuvan": "IMA Cross Sales",
    "Siddhesh Gore": "IMA Cross Sales",
    "Vaishali Bhivsane": "IMA Cross Sales",
    "Ranveer Singh": "IMA Cross Sales",
    "Priti Gajare": "IMA Cross Sales",
    "Girish Konkar": "IMA Cross Sales",
    "Sanidev Vishwakarma": "IMA Cross Sales",
    "Manasi Gite": "IMA Cross Sales",
    "Vivek Dave": "IMA Cross Sales",
    "Krutika Chalke": "IMA Cross Sales",
    "Rahul Singh": "IMA Cross Sales",
    "Divya Naik": "IMA Cross Sales",
    "Sachin Dubey": "IMA Cross Sales",
    "Anita Sonone": "IMA Cross Sales",
    "Satish Durgoli": "IMA Cross Sales",
    "Suvarna Gawai": "IMA Cross Sales",
    "Prasad Gargade": "IMA Cross Sales",
    "Tejas Loke": "IMA Cross Sales",
    "Yogita Tiwari": "IMA Cross Sales",
    "Pradnya Shikhre": "IMA Cross Sales",
    "Suryakant Kamble": "IMA Cross Sales",
    "Vikrant Sawant": "IMA Cross Sales",
    "PURVESH ASHOK KHARAT": "IMA Cross Sales",
    "DINBAHADUR PAAN SINGH": "IMA Cross Sales",
    "Ankush Jamunde": "IMA Cross Sales",
    "Muskan Mishra": "IMA Cross Sales",
    "Shraddha Pawar": "IMA Cross Sales",
    "Riya Yadav": "IMA Cross Sales",
    "Vinita Mohan Rane": "IMA Cross Sales",
    "Babaji Naiksatam": "IMA Cross Sales",
    "Radha Choudhary": "IMA Cross Sales",
    "Sonam Mulay": "IMA Cross Sales",
    "MAHESH GOLE": "IMA Cross Sales",
    "Jyoti Jaiswal": "IMA Cross Sales",

    # ─── Corporate ──────────────────────
    "Kedar Gorathe": "Corporate",
    "Pratishtha Anil  Singh": "Corporate",

    # ─── PBHD ───────────────────────────
    "Puja Ganesh Kamble": "PBHD",
    "Soman Soni": "PBHD",


    # ─── Multi CRM Names ────────────────
    "Milind Chilhate, Milind Chilhate": "IMA",
    "Pradnya Shikhre, Antara Kadam": "IMA Cross Sales",
    "Pradnya Shikhre, Sejal Rai": "IMA Cross Sales",
    "Sejal Rai, Mehtab Khan": "IMA Cross Sales",
    "Ravi Raj Rathore, Anita Sonone": "IMA Cross Sales",
    "Antara Kadam, Mehtab Khan": "IMA Cross Sales",
    "Yogita Tiwari, Ranveer Singh": "IMA Cross Sales",
    "Yogesh Tribhuvan, Mehtab Khan": "IMA Cross Sales",
    "Yogita Tiwari, Mehtab Khan": "IMA Cross Sales",
    "Manisha Singh, Vivek Dave": "IMA Cross Sales",
    "Mehtab Khan, Manasi Gite": "IMA Cross Sales",
    "Mehtab Khan, Anita Sonone": "IMA Cross Sales",
    "Milind Chilhate, Krutika Chalke": "IMA Cross Sales",
    "Sanika Kanekar, Sanika Kanekar, Sanika Kanekar": "IMA",
    "Divya Naik, Divya Naik": "IMA",
    "Suvarna Gawai, Suvarna Gawai": "IMA",
}

HEALTH_LIFE_CLASSES = ["Health", "Life", "Health (Non Life)"]
PRIVATE_CAR_POLICIES = ["Private Car Comp", "Private Car SAOD","Private Car - Comp New Vehicle",
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

    # STEP 3 — Exclude only "Direct Code". Blank BookedIn rows are KEPT.
    if check_column(df, "BookedIn"):
        before = len(df)
        booked_str = df["BookedIn"].fillna("").astype(str).str.strip()
        df = df[booked_str != "Direct Code"].copy()
        logs.append(f"  Step 3: Excluded {before - len(df)} 'Direct Code' rows. Blank BookedIn rows kept.")

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

    # STEP 3 — Exclude only "Direct Code". Blank BookedIn rows are KEPT.
    if check_column(df, "BookedIn"):
        before = len(df)
        booked_str = df["BookedIn"].fillna("").astype(str).str.strip()
        df = df[booked_str != "Direct Code"].copy()
        logs.append(f"  Step 3: Excluded {before - len(df)} 'Direct Code' rows. Blank BookedIn rows kept.")

    # Policy Awaited + Cancelled removal for Issued mode is handled in Step 14 (_shared_steps)

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
    # LOGIN : Keep ALL rows. Policy Awaited → "Not Issued". Cancelled → "Cancelled". Others → "Issued".
    # ISSUED: DELETE Policy Awaited rows (not yet issued = irrelevant for issued report).
    #         Keep Cancelled. Keep Issued. No other deletions.
    status_col = "Policy Status"
    if status_col in df.columns:
        status_str = df[status_col].fillna("").astype(str).str.strip()

        if mode == "login":
            # LOGIN — no deletions, just relabel
            awaited_mask   = status_str == "Policy Awaited"
            cancelled_mask = status_str == "Cancelled"
            other_mask     = ~awaited_mask & ~cancelled_mask
            df.loc[awaited_mask,   status_col] = "Not Issued"
            df.loc[cancelled_mask, status_col] = "Cancelled"
            df.loc[other_mask,     status_col] = "Issued"
            logs.append(f"  Step 14 (Login): {other_mask.sum()} → 'Issued', "
                        f"{awaited_mask.sum()} → 'Not Issued', "
                        f"{cancelled_mask.sum()} → 'Cancelled'. No rows deleted.")
        else:
            # ISSUED — remove Policy Awaited rows (these are not issued yet)
            before = len(df)
            df = df[status_str != "Policy Awaited"].copy()
            removed = before - len(df)
            # Re-evaluate after deletion
            status_str2 = df[status_col].fillna("").astype(str).str.strip()
            cancelled_mask2 = status_str2 == "Cancelled"
            other_mask2     = ~cancelled_mask2
            df.loc[cancelled_mask2, status_col] = "Cancelled"
            df.loc[other_mask2,     status_col] = "Issued"
            logs.append(f"  Step 14 (Issued): Removed {removed} 'Policy Awaited' rows. "
                        f"{other_mask2.sum()} → 'Issued', "
                        f"{cancelled_mask2.sum()} → 'Cancelled'.")

    # STEP 15 — Brokerage logic
    # Only calculate when Total Brokerage Receivable is 0 or blank.
    # If already has a value → leave untouched.
    # For rows that need calculation:
    #   45% when Insurer = Generali AND Policy Name = PI Hospital or PI Doctors
    #   15% for all other rows
    brok_col = "Total Brokerage Receivable"
    if brok_col not in df.columns:
        df[brok_col] = 0.0
    df[brok_col] = pd.to_numeric(df[brok_col], errors="coerce").fillna(0.0)

    if "TPOD" in df.columns:
        # Only rows where brokerage is currently 0 or blank need calculation
        needs_calc = _is_blank_or_zero(df[brok_col])
        count_needs = needs_calc.sum()

        if count_needs > 0:
            # Default: 15% for all rows needing calculation
            df.loc[needs_calc, brok_col] = (_safe_numeric(df, "TPOD")[needs_calc] * 0.15).round(2)
            count_45 = 0

            # Override: 45% only for Generali + PI Hospital/Doctors combination
            if "Insurer Name" in df.columns and "Policy Name" in df.columns:
                generali_mask = df["Insurer Name"].fillna("").astype(str).str.strip() == GENERALI
                pi_mask = df["Policy Name"].fillna("").astype(str).str.upper().str.strip().isin(
                    [p.upper() for p in PI_POLICIES])
                special_mask = needs_calc & generali_mask & pi_mask
                count_45 = special_mask.sum()
                df.loc[special_mask, brok_col] = (_safe_numeric(df, "TPOD")[special_mask] * 0.45).round(2)

            logs.append(f"  Step 15: Brokerage calculated for {count_needs} rows "
                        f"(was 0/blank). 45% → {count_45} Generali+PI rows; "
                        f"15% → {count_needs - count_45} other rows.")
        else:
            logs.append(f"  Step 15: All rows already have brokerage values — no recalculation needed.")

    # STEP 16 & 17 — Create helper column 'Transaction Type' from original Type column
    # This preserves the original Type values and maps them to business categories.
    # Endorsement  : Type == "Endorsement" (exact)
    # Installment  : Type contains "Installment" (covers Installment 1, 2, 3 etc.)
    # All others   : copy Type of business as-is
    if "Type" in df.columns and tob_col in df.columns:
        type_str = df["Type"].fillna("").astype(str).str.strip()

        # Create helper column starting from current Type of business values
        df["Transaction Type"] = df[tob_col].fillna("").astype(str).str.strip()

        # Endorsement: exact match on Type column
        endo_mask = type_str.str.lower() == "endorsement"
        df.loc[endo_mask, "Transaction Type"] = "Endorsement"
        df.loc[endo_mask, tob_col] = "Endorsement"
        logs.append(f"  Step 16: Set {endo_mask.sum()} Endorsement rows in Type of business & Transaction Type.")

        # Installment: Type contains "Installment" (case-insensitive) — covers 1, 2, 3 etc.
        inst_mask = type_str.str.lower().str.contains("installment", na=False)
        df.loc[inst_mask, "Transaction Type"] = "Installment"
        df.loc[inst_mask, tob_col] = "Installment"
        logs.append(f"  Step 17: Set {inst_mask.sum()} Installment rows in Type of business & Transaction Type.")

        # Fix zero/blank brokerage for Installment rows (minimum 1%)
        if brok_col in df.columns and "TPOD" in df.columns:
            zero_brok = inst_mask & _is_blank_or_zero(df[brok_col])
            df.loc[zero_brok, brok_col] = (df.loc[zero_brok, "TPOD"] * 0.01).round(2)
            if zero_brok.sum() > 0:
                logs.append(f"  Step 17b: Fixed {zero_brok.sum()} zero-brokerage Installment rows at 1%.")

        logs.append(f"  Transaction Type column created with values: "
                    f"{df['Transaction Type'].value_counts().to_dict()}")
    elif tob_col in df.columns:
        # Fallback: if no Type column, Transaction Type = Type of business
        df["Transaction Type"] = df[tob_col].fillna("").astype(str).str.strip()

    return df
