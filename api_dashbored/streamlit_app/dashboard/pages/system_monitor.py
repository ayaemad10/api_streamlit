"""dashboard/pages/system_monitor.py - System health and settings."""
import streamlit as st
import platform
import os
from datetime import datetime
from dashboard.api_client import APIClient


def render():
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">💻 System Monitor</h1>
        <p class="page-subtitle">System health, API status, and configuration</p>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()

    # ── API Status ───────────────────────────────────────────────────
    st.markdown("#### 🔌 Service Status")
    c1, c2, c3 = st.columns(3)

    api_ok = _check_api()
    with c1:
        _status_card("FastAPI Backend", api_ok, "http://localhost:8000")
    with c2:
        _status_card("Streamlit Dashboard", True, "http://localhost:8501")
    with c3:
        ollama_ok = _check_ollama()
        _status_card("Ollama LLM", ollama_ok, "http://localhost:11434")

    # ── System Info ──────────────────────────────────────────────────
    st.markdown("#### 🖥️ System Information")
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)

    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("CPU Usage", f"{cpu:.1f}%")
        with c2: st.metric("RAM Used", f"{ram.used / 1e9:.1f} GB", f"/ {ram.total / 1e9:.1f} GB")
        with c3: st.metric("RAM %", f"{ram.percent}%")
        with c4: st.metric("Disk Free", f"{disk.free / 1e9:.1f} GB")
    except ImportError:
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Platform", platform.system())
        with c2: st.metric("Python", platform.python_version())
        with c3: st.metric("Time", datetime.now().strftime("%H:%M:%S"))

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Settings ─────────────────────────────────────────────────────
    st.markdown("#### ⚙️ System Settings")
    settings = client.get_settings()

    if settings:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        cols = st.columns([2, 2, 3])
        cols[0].markdown("**Setting**")
        cols[1].markdown("**Value**")
        cols[2].markdown("**Description**")

        for key, info in settings.items():
            c1, c2, c3 = st.columns([2, 2, 3])
            with c1: st.text(key)
            with c2: st.code(info["value"], language=None)
            with c3: st.caption(info.get("description", "—"))
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Cannot load settings — API may be offline.")

    # ── Log viewer ───────────────────────────────────────────────────
    st.markdown("#### 📋 Application Logs")
    log_file = "logs/app.log"
    if os.path.exists(log_file):
        with open(log_file) as f:
            lines = f.readlines()
        last_lines = "".join(lines[-50:])
        st.code(last_lines, language="log")
    else:
        st.info("Log file not found. Logs are written to logs/app.log")


def _status_card(name: str, ok: bool, url: str):
    color = "#2ed573" if ok else "#ff4757"
    dot = "●" if ok else "○"
    status = "Online" if ok else "Offline"
    st.markdown(f"""
    <div class="status-card">
        <div class="status-card-dot" style="color:{color}">{dot}</div>
        <div class="status-card-name">{name}</div>
        <div class="status-card-status" style="color:{color}">{status}</div>
        <div class="status-card-url">{url}</div>
    </div>
    """, unsafe_allow_html=True)


def _check_api() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:8000/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _check_ollama() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:11434", timeout=3)
        return r.status_code in (200, 404)
    except Exception:
        return False
