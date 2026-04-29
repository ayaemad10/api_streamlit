"""dashboard/pages/alerts_log.py - Alert history log."""
import streamlit as st
import pandas as pd
from dashboard.api_client import APIClient


def render():
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">🚨 Alerts Log</h1>
        <p class="page-subtitle">Complete record of triggered security alerts</p>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()
    data = client.get_alerts(limit=200)

    if not data:
        st.warning("⚠️ Cannot reach API.")
        return

    alerts = data.get("alerts", [])

    if not alerts:
        st.markdown("""
        <div class="success-banner">
            <span>✅ No alerts on record. All signals within normal parameters.</span>
        </div>
        """, unsafe_allow_html=True)
        return

    # Summary metrics
    df = pd.DataFrame(alerts)
    total = len(df)
    sent = len(df[df["status"] == "sent"]) if "status" in df.columns else 0
    failed = total - sent

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Alerts", total)
    with c2:
        st.metric("Successfully Sent", sent, delta=None)
    with c3:
        st.metric("Failed", failed, delta=failed if failed else None,
                  delta_color="inverse" if failed else "off")

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)

    display_cols = [c for c in ["id", "timestamp", "label", "confidence", "alert_type", "status", "location"] if c in df.columns]

    if "confidence" in df.columns:
        df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").apply(
            lambda x: f"{x:.1%}" if pd.notna(x) else "—"
        )
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=500)
    st.markdown('</div>', unsafe_allow_html=True)

    csv = df.to_csv(index=False)
    st.download_button("⬇ Export Alerts CSV", csv, "alerts_log.csv", "text/csv")
