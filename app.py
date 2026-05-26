"""
app.py — Insurance Business Processing Automation
Streamlit dashboard for Login Business and Issued Business processing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import io
import time
import logging
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from utils.validation import validate_upload
from utils.processing import process_login_business, process_issued_business
from utils.pivot import generate_pivots
from utils.formatting import build_excel_output

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Insurance Processing Automation",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p  { color: #BDD7EE; margin: 0.3rem 0 0; font-size: 0.9rem; }

    /* Metric cards */
    .metric-card {
        background: #F0F4FA;
        border-left: 4px solid #2E75B6;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
    }
    .metric-card .label { font-size: 0.75rem; color: #666; font-weight: 600; text-transform: uppercase; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700; color: #1F4E79; }

    /* Log box */
    .log-box {
        background: #0D1117;
        color: #58A6FF;
        font-family: 'Courier New', monospace;
        font-size: 0.78rem;
        padding: 1rem;
        border-radius: 8px;
        max-height: 320px;
        overflow-y: auto;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #F8FAFD; }
    
    /* Download button */
    .stDownloadButton button {
        background: linear-gradient(135deg, #1F4E79, #2E75B6) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-size: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=64)
    st.title("⚙️ Controls")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "📂 Upload Business Report",
        type=["xlsx", "xls"],
        help="Upload the SIBRO Excel business report file.",
    )

    process_type = st.selectbox(
        "🔄 Process Type",
        ["Login Business", "Issued Business"],
        help="Select the type of business processing to apply.",
    )

    st.markdown("---")
    st.markdown("**ℹ️ About**")
    st.caption("Insurance Business Processing Automation v1.0\nBuilt with Streamlit + Pandas + OpenPyXL")
    st.caption(f"📅 Today: {datetime.now().strftime('%d %b %Y')}")


# ─── Main Header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🛡️ Insurance Business Processing Automation</h1>
  <p>Upload your Excel business report and generate processed Login / Issued Business reports with Pivot summaries.</p>
</div>
""", unsafe_allow_html=True)


# ─── Main content ─────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.info("👈  Upload an Excel file from the sidebar to get started.", icon="📂")

    # Show feature cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("### 📥 Upload\nAccepts `.xlsx` and `.xls` business reports from SIBRO.")
    with col2:
        st.markdown("### ⚙️ Process\nApplies all 17 business logic steps automatically.")
    with col3:
        st.markdown("### 📊 Pivot\nGenerates Fresh & Renewal pivot summaries.")
    with col4:
        st.markdown("### 💾 Download\nExports formatted Excel with 3 sheets ready to use.")

else:
    # ── Read uploaded file ────────────────────────────────────────────────────
    try:
        engine = "xlrd" if uploaded_file.name.endswith(".xls") else "openpyxl"
        df_raw = pd.read_excel(uploaded_file, engine=engine)
    except Exception as e:
        st.error(f"❌ Failed to read the uploaded file: {e}")
        st.stop()

    # ── Validate ──────────────────────────────────────────────────────────────
    logs: list[str] = []
    is_valid, warnings = validate_upload(df_raw, logs)

    if not is_valid:
        st.error("❌ Validation failed. " + " | ".join(logs))
        st.stop()

    if warnings:
        st.warning(f"⚠️  Missing optional columns (will be skipped): {warnings}")

    # ── Summary row ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class='metric-card'>
          <div class='label'>Total Rows Uploaded</div>
          <div class='value'>{len(df_raw):,}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='metric-card'>
          <div class='label'>Total Columns</div>
          <div class='value'>{len(df_raw.columns)}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='metric-card'>
          <div class='label'>Process Mode</div>
          <div class='value'>{process_type}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Process button ────────────────────────────────────────────────────────
    if st.button(f"▶ Run {process_type} Processing", type="primary", use_container_width=True):
        progress = st.progress(0, text="Initialising…")
        status   = st.empty()

        try:
            # Step 1 — process
            status.info("⚙️  Applying business logic…")
            progress.progress(20, text="Processing data…")
            time.sleep(0.2)

            mode = "login" if process_type == "Login Business" else "issued"

            if mode == "login":
                df_processed = process_login_business(df_raw.copy(), logs)
            else:
                df_processed = process_issued_business(df_raw.copy(), logs)

            progress.progress(55, text="Generating pivot reports…")
            time.sleep(0.1)

            # Step 2 — pivots
            fresh_df, renewal_df = generate_pivots(df_processed, mode, logs)

            progress.progress(75, text="Formatting Excel output…")
            time.sleep(0.1)

            # Step 3 — format & build Excel
            excel_bytes = build_excel_output(df_processed, fresh_df, renewal_df, mode)

            progress.progress(100, text="Done!")
            status.success(f"✅ Processing complete — {len(df_processed):,} rows in output.")
            time.sleep(0.3)
            progress.empty()

            # ── Store results in session state ────────────────────────────────
            st.session_state["df_processed"] = df_processed
            st.session_state["fresh_df"]     = fresh_df
            st.session_state["renewal_df"]   = renewal_df
            st.session_state["excel_bytes"]  = excel_bytes
            st.session_state["logs"]         = logs
            st.session_state["mode"]         = mode
            st.session_state["process_type"] = process_type

        except Exception as e:
            progress.empty()
            status.error(f"❌ Processing error: {e}")
            logger.exception("Processing failed")
            st.stop()

    # ── Display results if available ──────────────────────────────────────────
    if "df_processed" in st.session_state:
        df_processed = st.session_state["df_processed"]
        fresh_df     = st.session_state["fresh_df"]
        renewal_df   = st.session_state["renewal_df"]
        excel_bytes  = st.session_state["excel_bytes"]
        logs         = st.session_state["logs"]
        mode         = st.session_state["mode"]
        process_type = st.session_state["process_type"]

        # ── Metrics row ───────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class='metric-card'>
              <div class='label'>Output Rows</div>
              <div class='value'>{len(df_processed):,}</div>
            </div>""", unsafe_allow_html=True)
        with m2:
            dropped = len(df_raw) - len(df_processed)
            st.markdown(f"""
            <div class='metric-card'>
              <div class='label'>Rows Removed</div>
              <div class='value'>{dropped:,}</div>
            </div>""", unsafe_allow_html=True)
        with m3:
            total_tpod = df_processed["TPOD"].sum() if "TPOD" in df_processed.columns else 0
            st.markdown(f"""
            <div class='metric-card'>
              <div class='label'>Total Premium (TPOD)</div>
              <div class='value'>₹{total_tpod:,.0f}</div>
            </div>""", unsafe_allow_html=True)
        with m4:
            brok_col = "Total Brokerage Receivable"
            total_brok = df_processed[brok_col].sum() if brok_col in df_processed.columns else 0
            st.markdown(f"""
            <div class='metric-card'>
              <div class='label'>Total Brokerage</div>
              <div class='value'>₹{total_brok:,.0f}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Tabs: Data Preview / Pivots / Logs ────────────────────────────────
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📋 Processed Data", "📊 Fresh Report", "🔄 Renewal Report", "📝 Process Log"]
        )

        with tab1:
            st.subheader(f"Processed Data — {len(df_processed):,} rows")
            # Show key columns first
            key_cols = [c for c in [
                "Policy Status", "Type of business", "Business Source",
                "Class of Policy", "Policy Name", "Insurer Name",
                "Net Premium", "Gross Premium", "TPOD", "Total Brokerage Receivable",
            ] if c in df_processed.columns]
            other_cols = [c for c in df_processed.columns if c not in key_cols]
            st.dataframe(df_processed[key_cols + other_cols], use_container_width=True, height=400)

        with tab2:
            fresh_title = "Fresh Login Business" if mode == "login" else "Fresh Issued"
            st.subheader(f"📊 {fresh_title}")
            if fresh_df.empty:
                st.info("No Fresh Business data (New / Roll Over) found.")
            else:
                disp = fresh_df.drop(columns=["_Report"], errors="ignore")
                st.dataframe(disp, use_container_width=True)

        with tab3:
            renewal_title = "Renewal Login Business" if mode == "login" else "Renewal Issued"
            st.subheader(f"🔄 {renewal_title}")
            if renewal_df.empty:
                st.info("No Renewal Business data (Endorse / Renew / Installment) found.")
            else:
                disp = renewal_df.drop(columns=["_Report"], errors="ignore")
                st.dataframe(disp, use_container_width=True)

        with tab4:
            st.subheader("📝 Processing Log")
            log_html = "<div class='log-box'>" + "<br>".join(logs) + "</div>"
            st.markdown(log_html, unsafe_allow_html=True)

        st.markdown("---")

        # ── Download ──────────────────────────────────────────────────────────
        fname = f"{process_type.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        st.download_button(
            label=f"⬇️  Download {process_type} Report (.xlsx)",
            data=excel_bytes,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption(f"📁 File: **{fname}** — Contains: Raw Processed Data, Fresh Report, Renewal Report")
