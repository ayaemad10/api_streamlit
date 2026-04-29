"""dashboard/pages/history.py - Paginated signal history with filters."""
import streamlit as st
import pandas as pd
from dashboard.api_client import APIClient


def render():
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">📋 Signal History</h1>
        <p class="page-subtitle">Full detection log with filtering and export</p>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        label_filter = st.selectbox("Filter by Class", ["All", "Normal", "Jamming", "Drone"])
    with col2:
        limit = st.selectbox("Rows per page", [50, 100, 250, 500], index=1)
    with col3:
        search = st.text_input("Search by source or frequency", placeholder="e.g. SDR, 433.5")

    label = None if label_filter == "All" else label_filter
    data = client.get_history(limit=limit, label=label)

    if not data:
        st.warning("No history data available.")
        return

    signals = data.get("signals", [])
    total = data.get("total", 0)

    st.markdown(f'<div class="stat-badge">Showing {len(signals)} of {total:,} records</div>', unsafe_allow_html=True)

    if signals:
        df = pd.DataFrame(signals)

        if search:
            mask = df.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            df = df[mask]

        # Format columns
        if "confidence" in df.columns:
            df["confidence"] = df["confidence"].apply(lambda x: f"{x:.1%}")
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        display_cols = [c for c in ["id", "timestamp", "label", "confidence", "frequency", "snr", "source", "model_version"] if c in df.columns]

        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True,
            height=450,
        )

        # Export
        csv = df.to_csv(index=False)
        st.download_button("⬇ Export CSV", csv, "spectrum_history.csv", "text/csv")
    else:
        st.info("No signals found for the selected filter.")
