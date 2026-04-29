"""
dashboard/app.py
----------------
Streamlit multi-page application entry point.
Handles authentication gate and page routing.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.config import API_BASE_URL, APP_NAME, APP_VERSION
from dashboard.api_client import APIClient
from dashboard.components.sidebar import render_sidebar

# ── Page configuration ───────────────────────────────────────────────
st.set_page_config(
    page_title="SpectrumAI — Anomaly Detection",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load CSS ─────────────────────────────────────────────────────────
def load_css():
    css_files = [
        "dashboard/assets/style.css",
        "dashboard/assets/theme.css",
        "dashboard/assets/components.css",
        "dashboard/assets/animations.css",
        "dashboard/assets/typography.css",
        "dashboard/assets/responsive.css",
    ]
    combined = ""
    for f in css_files:
        if os.path.exists(f):
            with open(f) as fp:
                combined += fp.read() + "\n"
    if combined:
        st.markdown(f"<style>{combined}</style>", unsafe_allow_html=True)

load_css()


# ── Auth state ───────────────────────────────────────────────────────
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None


def login_page():
    """Full-page login screen with professional SaaS design."""
    st.markdown("""
    <div class="login-container">
        <div class="login-card">
            <div class="login-header">
                <div class="login-logo">📡</div>
                <h1 class="login-title">SpectrumAI</h1>
                <p class="login-subtitle">RF Spectrum Anomaly Detection Platform</p>
                <div class="login-badge">ITC Egypt · Defense Systems</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="login-form-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 Secure Login")

        username = st.text_input("Username", placeholder="Enter username", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")

        if st.button("Sign In →", use_container_width=True, type="primary"):
            client = APIClient()
            result = client.login(username, password)
            if result:
                st.session_state.access_token = result["access_token"]
                st.session_state.username = username
                st.session_state.role = client.get_me(result["access_token"]).get("role", "Operator")
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("Invalid credentials. Default: admin / admin123")

        st.markdown('<p class="login-hint">Default credentials: admin / admin123</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ── Main routing ─────────────────────────────────────────────────────
if not st.session_state.access_token:
    login_page()
else:
    page = render_sidebar()

    # Dynamic page routing
    page_map = {
        "Home":           "dashboard.pages.home",
        "Real-Time":      "dashboard.pages.realtime",
        "Analytics":      "dashboard.pages.analytics",
        "History":        "dashboard.pages.history",
        "Alerts Log":     "dashboard.pages.alerts_log",
        "Reports":        "dashboard.pages.reports",
        "System Monitor": "dashboard.pages.system_monitor",
        "AI Agent":       "dashboard.pages.agent_chat",
        "Live Map":       "dashboard.pages.live_map",
    }

    module_name = page_map.get(page, "dashboard.pages.home")
    import importlib
    try:
        mod = importlib.import_module(module_name)
        mod.render()
    except Exception as e:
        st.error(f"Page load error: {e}")
        import traceback
        st.code(traceback.format_exc())
