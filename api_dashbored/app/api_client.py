"""
dashboard/api_client.py
-----------------------
HTTP client for communicating with the FastAPI backend.
Wraps all endpoints with error handling and auth headers.
"""

import requests
import streamlit as st
from dashboard.config import API_BASE_URL
from utils.logger import get_logger

logger = get_logger("dashboard.api_client")


class APIClient:
    """Stateless API client. Uses session_state token automatically."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base = base_url

    @property
    def _headers(self) -> dict:
        token = st.session_state.get("access_token", "")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _get(self, path: str, params: dict = None) -> dict | None:
        try:
            r = requests.get(f"{self.base}{path}", headers=self._headers, params=params, timeout=15)
            if r.status_code == 401:
                st.session_state.access_token = None
                st.warning("Session expired. Please login again.")
                st.rerun()
            r.raise_for_status()
            return r.json()
        except requests.exceptions.ConnectionError:
            st.error("⚠️ Cannot connect to API server. Is it running?")
            return None
        except Exception as e:
            logger.error(f"GET {path} failed: {e}")
            return None

    def _post(self, path: str, **kwargs) -> dict | None:
        try:
            r = requests.post(f"{self.base}{path}", headers=self._headers, timeout=30, **kwargs)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"POST {path} failed: {e}")
            return None

    # ── Auth ──────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict | None:
        try:
            r = requests.post(
                f"{self.base}/auth/login",
                json={"username": username, "password": password},
                timeout=10,
            )
            if r.status_code == 200:
                return r.json()
            return None
        except Exception:
            return None

    def get_me(self, token: str) -> dict:
        try:
            r = requests.get(
                f"{self.base}/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    # ── Data ─────────────────────────────────────────────────────────

    def get_history(self, limit=100, label=None) -> dict | None:
        params = {"limit": limit}
        if label:
            params["label"] = label
        return self._get("/history", params=params)

    def get_stats(self) -> dict | None:
        return self._get("/history/stats")

    def get_alerts(self, limit=50) -> dict | None:
        return self._get("/alerts", params={"limit": limit})

    def get_settings(self) -> dict | None:
        return self._get("/settings")

    # ── AI ────────────────────────────────────────────────────────────

    def predict_signal(self, signal_type: str, snr_db: float) -> dict | None:
        return self._post(
            "/predict/signal",
            data={"signal_type": signal_type, "snr_db": snr_db},
        )

    def predict_image(self, img_bytes: bytes, filename: str) -> dict | None:
        return self._post(
            "/predict",
            files={"file": (filename, img_bytes, "image/png")},
        )

    def agent_chat(self, message: str, session_id: str = "default") -> dict | None:
        return self._post(
            "/agent/chat",
            json={"message": message, "session_id": session_id},
        )

    def get_report(self) -> dict | None:
        return self._get("/agent/report")
