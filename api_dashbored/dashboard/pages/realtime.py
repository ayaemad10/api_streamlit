"""dashboard/pages/realtime.py - Live spectrum monitoring with auto-refresh."""
import streamlit as st
import base64
import time
import random
import numpy as np
from dashboard.api_client import APIClient


def render():
    st.markdown("""
    <div class="page-header">
        <div class="page-header-content">
            <h1 class="page-title">📡 Real-Time Monitor</h1>
            <p class="page-subtitle">Live spectrum scanning and anomaly detection</p>
        </div>
        <div class="page-header-badge live-badge">● LIVE</div>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()

    # ── Controls ─────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        signal_type = st.selectbox("Signal Type", ["normal", "jamming", "drone"], key="rt_type")
    with col2:
        snr_db = st.slider("SNR (dB)", 5.0, 40.0, 20.0, step=0.5, key="rt_snr")
    with col3:
        auto_refresh = st.toggle("Auto Scan", value=False, key="rt_auto")
    with col4:
        interval = st.slider("Interval (sec)", 2, 15, 5, key="rt_interval")

    # ── Scan button ──────────────────────────────────────────────────
    scan_col, _ = st.columns([1, 3])
    with scan_col:
        run_scan = st.button("▶ Run Scan", use_container_width=True, type="primary")

    placeholder = st.empty()

    def do_scan():
        result = client.predict_signal(signal_type, snr_db)
        if not result:
            placeholder.warning("⚠️ API unavailable — showing simulated data")
            result = _simulate_result(signal_type, snr_db)
        _render_result(placeholder, result)

    if run_scan:
        do_scan()

    if auto_refresh:
        while True:
            do_scan()
            time.sleep(interval)
            st.rerun()


def _render_result(placeholder, result: dict):
    """Render a prediction result with spectrogram and stats."""
    label = result.get("class", "Unknown")
    confidence = result.get("confidence", 0)
    spec_b64 = result.get("spectrogram_b64", "")

    label_colors = {"Normal": "#2ed573", "Jamming": "#ff4757", "Drone": "#ffa502"}
    color = label_colors.get(label, "#94a3b8")
    icon = {"Normal": "✅", "Jamming": "🔴", "Drone": "🚁"}.get(label, "❓")

    with placeholder.container():
        st.markdown(f"""
        <div class="detection-banner" style="border-left: 5px solid {color}">
            <span class="detection-icon">{icon}</span>
            <span class="detection-label" style="color:{color}">{label}</span>
            <span class="detection-conf">Confidence: {confidence:.1%}</span>
            <span class="detection-time">Signal ID: {result.get('signal_id', 'N/A')}</span>
        </div>
        """, unsafe_allow_html=True)

        col_spec, col_stats = st.columns([2, 1])

        with col_spec:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### Spectrogram")
            if spec_b64:
                img_bytes = base64.b64decode(spec_b64)
                st.image(img_bytes, caption=f"{label} Signal Spectrogram", use_container_width=True)
            else:
                st.info("No spectrogram available")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_stats:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown("#### Class Probabilities")
            scores = result.get("scores", {})
            for cls, score in sorted(scores.items(), key=lambda x: -x[1]):
                bar_color = label_colors.get(cls, "#94a3b8")
                pct = score * 100
                st.markdown(f"""
                <div class="prob-row">
                    <span class="prob-label">{cls}</span>
                    <div class="prob-bar-bg">
                        <div class="prob-bar-fill" style="width:{pct:.1f}%; background:{bar_color}"></div>
                    </div>
                    <span class="prob-value" style="color:{bar_color}">{pct:.1f}%</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.metric("Inference Time", f"{result.get('inference_time_ms', '—')} ms")
            st.metric("SNR", f"{result.get('snr', '—')} dB")
            st.markdown('</div>', unsafe_allow_html=True)


def _simulate_result(signal_type: str, snr_db: float) -> dict:
    """Generate a fake result for demo when API is offline."""
    label_map = {"normal": "Normal", "jamming": "Jamming", "drone": "Drone"}
    label = label_map.get(signal_type, "Normal")
    conf = round(random.uniform(0.80, 0.97), 4)
    others = [round(random.uniform(0.01, 0.1), 4)] * 2
    scores = {"Normal": 0.0, "Jamming": 0.0, "Drone": 0.0}
    scores[label] = conf
    rest = 1.0 - conf
    other_labels = [k for k in scores if k != label]
    scores[other_labels[0]] = round(rest * 0.6, 4)
    scores[other_labels[1]] = round(rest * 0.4, 4)
    return {
        "class": label, "confidence": conf, "scores": scores,
        "signal_id": random.randint(1000, 9999),
        "inference_time_ms": random.randint(50, 300),
        "snr": snr_db, "spectrogram_b64": "",
    }
