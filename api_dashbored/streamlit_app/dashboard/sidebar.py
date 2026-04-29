"""dashboard/components/sidebar.py - Professional sidebar navigation."""
import streamlit as st
from dashboard.config import APP_NAME, APP_VERSION


PAGES = [
    ("🏠", "Home",           "Overview & live stats"),
    ("📡", "Real-Time",      "Live spectrum monitor"),
    ("📊", "Analytics",      "Charts & trends"),
    ("📋", "History",        "Signal history"),
    ("🚨", "Alerts Log",     "Alert records"),
    ("📄", "Reports",        "AI-generated reports"),
    ("💻", "System Monitor", "System health"),
    ("🤖", "AI Agent",       "Chat with SpectrumAI"),
    ("🗺️", "Live Map",       "Geographic view"),
]


def render_sidebar() -> str:
    """Render sidebar and return selected page name."""
    with st.sidebar:
        # Logo & branding
        st.markdown(f"""
        <div class="sidebar-brand">
            <div class="sidebar-logo">📡</div>
            <div class="sidebar-brand-text">
                <span class="sidebar-title">{APP_NAME}</span>
                <span class="sidebar-version">v{APP_VERSION}</span>
            </div>
        </div>
        <div class="sidebar-divider"></div>
        """, unsafe_allow_html=True)

        # User info
        username = st.session_state.get("username", "User")
        role = st.session_state.get("role", "Operator")
        role_color = "#6c63ff" if role == "Admin" else "#00d4ff"

        st.markdown(f"""
        <div class="sidebar-user">
            <div class="sidebar-avatar">{username[0].upper()}</div>
            <div class="sidebar-user-info">
                <span class="sidebar-username">{username}</span>
                <span class="sidebar-role" style="color:{role_color}">{role}</span>
            </div>
        </div>
        <div class="sidebar-divider"></div>
        """, unsafe_allow_html=True)

        # Navigation
        st.markdown('<div class="sidebar-nav-label">NAVIGATION</div>', unsafe_allow_html=True)

        if "current_page" not in st.session_state:
            st.session_state.current_page = "Home"

        for icon, name, desc in PAGES:
            is_active = st.session_state.current_page == name
            btn_class = "nav-btn nav-btn-active" if is_active else "nav-btn"

            if st.button(
                f"{icon}  {name}",
                key=f"nav_{name}",
                use_container_width=True,
                help=desc,
            ):
                st.session_state.current_page = name
                st.rerun()

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        # Status indicator
        st.markdown("""
        <div class="sidebar-status">
            <div class="status-dot status-online"></div>
            <span class="status-text">System Online</span>
        </div>
        """, unsafe_allow_html=True)

        # Logout
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["access_token", "username", "role", "current_page"]:
                st.session_state.pop(key, None)
            st.rerun()

    return st.session_state.current_page
