"""dashboard/pages/home.py - Overview home page with KPIs."""
import streamlit as st
import pandas as pd
from dashboard.api_client import APIClient
from dashboard.components.charts import signal_distribution_pie, bar_chart_labels


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-header-content">
            <h1 class="page-title">🏠 Mission Control</h1>
            <p class="page-subtitle">RF Spectrum Anomaly Detection — Real-Time Overview</p>
        </div>
        <div class="page-header-badge">LIVE</div>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()
    stats = client.get_stats()
    alerts_data = client.get_alerts(limit=5)

    if not stats:
        st.warning("⚠️ Cannot connect to API. Start the server with: `uvicorn api.main:app --reload`")
        _show_demo_mode()
        return

    by_label = {d["label"]: d for d in stats.get("by_label", [])}
    total = stats.get("total", 0)

    # ── KPI Cards ────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        _kpi_card("Total Signals", f"{total:,}", "📡", "primary")
    with c2:
        normal = by_label.get("Normal", {}).get("count", 0)
        _kpi_card("Normal", f"{normal:,}", "✅", "success")
    with c3:
        jamming = by_label.get("Jamming", {}).get("count", 0)
        _kpi_card("Jamming", f"{jamming:,}", "🔴", "danger")
    with c4:
        drone = by_label.get("Drone", {}).get("count", 0)
        _kpi_card("Drones", f"{drone:,}", "🚁", "warning")
    with c5:
        alert_count = len(alerts_data.get("alerts", [])) if alerts_data else 0
        _kpi_card("Alerts", f"{alert_count}", "🚨", "danger")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ───────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1.5])

    with col_l:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### Signal Distribution")
        if stats["by_label"]:
            st.plotly_chart(signal_distribution_pie(stats["by_label"]), use_container_width=True)
        else:
            st.info("No signal data yet. Run a prediction to populate.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("#### Signal Counts by Class")
        if stats["by_label"]:
            st.plotly_chart(bar_chart_labels(stats["by_label"]), use_container_width=True)
        else:
            st.info("No data available.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Recent Alerts ────────────────────────────────────────────────
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("#### 🚨 Recent Alerts")
    if alerts_data and alerts_data.get("alerts"):
        df = pd.DataFrame(alerts_data["alerts"])
        df = df[["timestamp", "label", "confidence", "alert_type", "status", "location"]].copy()
        df["confidence"] = df["confidence"].apply(lambda x: f"{x:.1%}")
        _styled_table(df)
    else:
        st.success("✅ No alerts recorded. System is clean.")
    st.markdown('</div>', unsafe_allow_html=True)


def _kpi_card(title: str, value: str, icon: str, variant: str = "primary"):
    color_map = {
        "primary": "#6c63ff", "success": "#2ed573",
        "danger": "#ff4757",  "warning": "#ffa502",
    }
    color = color_map.get(variant, "#6c63ff")
    st.markdown(f"""
    <div class="kpi-card" style="border-top: 3px solid {color}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-label">{title}</div>
    </div>
    """, unsafe_allow_html=True)


def _styled_table(df: pd.DataFrame):
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": st.column_config.TextColumn("Time"),
            "label": st.column_config.TextColumn("Type"),
            "confidence": st.column_config.TextColumn("Confidence"),
            "alert_type": st.column_config.TextColumn("Channel"),
            "status": st.column_config.TextColumn("Status"),
        },
    )


def _show_demo_mode():
    """Show demo stats when API is offline."""
    st.info("📊 Showing demo data — connect the API for live data")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: _kpi_card("Total Signals", "1,247", "📡", "primary")
    with c2: _kpi_card("Normal", "980", "✅", "success")
    with c3: _kpi_card("Jamming", "187", "🔴", "danger")
    with c4: _kpi_card("Drones", "80", "🚁", "warning")
    with c5: _kpi_card("Alerts", "267", "🚨", "danger")
