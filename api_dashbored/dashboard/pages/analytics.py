"""dashboard/pages/analytics.py - Analytics with charts and trends."""
import streamlit as st
import pandas as pd
from dashboard.api_client import APIClient
from dashboard.components.charts import (
    confidence_timeline, hourly_heatmap, signal_distribution_pie, gauge_chart
)


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-header-content">
            <h1 class="page-title">📊 Analytics</h1>
            <p class="page-subtitle">Signal trends, patterns, and performance metrics</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()
    stats = client.get_stats()
    history = client.get_history(limit=500)

    if not stats or not history:
        st.warning("⚠️ No data available. Run some predictions first.")
        return

    by_label = stats.get("by_label", [])
    hourly = stats.get("hourly_trend", [])
    total = stats.get("total", 0)

    # ── Top metrics row ───────────────────────────────────────────────
    anomaly_count = sum(d["count"] for d in by_label if d["label"] != "Normal")
    anomaly_pct = anomaly_count / total if total else 0
    avg_conf_all = sum(d["avg_confidence"] * d["count"] for d in by_label) / total if total else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(gauge_chart(anomaly_pct, "Anomaly Rate", 1.0), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(gauge_chart(avg_conf_all, "Avg Confidence", 1.0), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(signal_distribution_pie(by_label), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Confidence timeline ───────────────────────────────────────────
    signals = history.get("signals", [])
    if signals:
        df = pd.DataFrame(signals)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### Confidence Over Time")
        st.plotly_chart(confidence_timeline(df), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Hourly heatmap ────────────────────────────────────────────────
    if hourly:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### Activity Heatmap (Last 24h)")
        st.plotly_chart(hourly_heatmap(hourly), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Summary table ─────────────────────────────────────────────────
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("#### Class Statistics Summary")
    if by_label:
        summary_df = pd.DataFrame(by_label)
        summary_df["avg_confidence"] = summary_df["avg_confidence"].apply(lambda x: f"{x:.2%}")
        summary_df.columns = ["Signal Type", "Count", "Avg Confidence"]
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
