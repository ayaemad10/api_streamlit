"""dashboard/pages/live_map.py - Geographic signal heatmap."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dashboard.api_client import APIClient
from dashboard.config import COLORS


def render():
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">🗺️ Live Map</h1>
        <p class="page-subtitle">Geographic distribution of detected signals</p>
    </div>
    """, unsafe_allow_html=True)

    client = APIClient()
    history = client.get_history(limit=200)

    # Base location: Cairo, Egypt (ITC Egypt HQ area)
    BASE_LAT, BASE_LON = 30.0626, 31.2497

    # ── Controls ──────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 2])
    with col1:
        view_type = st.radio("Map View", ["Scatter Map", "Density Heatmap", "3D Terrain"])
    with col2:
        show_labels = st.multiselect("Show Signal Types", ["Normal", "Jamming", "Drone"],
                                     default=["Jamming", "Drone"])

    # ── Generate geo data ─────────────────────────────────────────────
    # Real deployments would use GPS data from SDR/hardware
    signals = history.get("signals", []) if history else []
    geo_df = _generate_geo_data(signals, BASE_LAT, BASE_LON)
    geo_df = geo_df[geo_df["label"].isin(show_labels)] if show_labels else geo_df

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)

    if view_type == "Scatter Map":
        _scatter_map(geo_df, BASE_LAT, BASE_LON)
    elif view_type == "Density Heatmap":
        _density_map(geo_df, BASE_LAT, BASE_LON)
    else:
        _terrain_3d(geo_df, BASE_LAT, BASE_LON)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Legend ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="legend-item"><span style="color:#2ed573">●</span> Normal Signal</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="legend-item"><span style="color:#ff4757">●</span> Jamming Attack</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="legend-item"><span style="color:#ffa502">●</span> Drone Signal</div>', unsafe_allow_html=True)

    # ── Table ─────────────────────────────────────────────────────────
    if not geo_df.empty:
        st.markdown("#### 📍 Signal Locations")
        st.dataframe(
            geo_df[["label", "lat", "lon", "confidence", "frequency"]].head(20),
            use_container_width=True, hide_index=True,
        )


def _generate_geo_data(signals: list, base_lat: float, base_lon: float) -> pd.DataFrame:
    """Map signals to pseudo-GPS coordinates around the base location."""
    np.random.seed(42)

    if signals:
        df = pd.DataFrame(signals)
        n = len(df)
        df["lat"] = base_lat + np.random.normal(0, 0.08, n)
        df["lon"] = base_lon + np.random.normal(0, 0.08, n)
        df["frequency"] = df.get("frequency", pd.Series([433.0] * n)).fillna(433.0)
    else:
        # Demo data
        records = []
        for label, count in [("Normal", 40), ("Jamming", 15), ("Drone", 10)]:
            for _ in range(count):
                records.append({
                    "label": label,
                    "lat": base_lat + np.random.normal(0, 0.06),
                    "lon": base_lon + np.random.normal(0, 0.06),
                    "confidence": np.random.uniform(0.7, 0.99),
                    "frequency": np.random.uniform(400, 950),
                })
        df = pd.DataFrame(records)

    return df


def _scatter_map(df: pd.DataFrame, clat: float, clon: float):
    color_map = {"Normal": "#2ed573", "Jamming": "#ff4757", "Drone": "#ffa502"}

    fig = go.Figure()
    for label, color in color_map.items():
        sub = df[df["label"] == label]
        if sub.empty:
            continue
        fig.add_trace(go.Scattermapbox(
            lat=sub["lat"], lon=sub["lon"],
            mode="markers",
            marker=dict(size=10, color=color, opacity=0.8),
            name=label,
            hovertemplate=f"<b>{label}</b><br>Lat: %{{lat:.4f}}<br>Lon: %{{lon:.4f}}<extra></extra>",
        ))

    fig.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=clat, lon=clon), zoom=10),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=0),
        height=500,
        legend=dict(bgcolor="rgba(20,20,40,0.8)", font=dict(color="white")),
    )
    st.plotly_chart(fig, use_container_width=True)


def _density_map(df: pd.DataFrame, clat: float, clon: float):
    fig = go.Figure(go.Densitymapbox(
        lat=df["lat"], lon=df["lon"],
        z=[1] * len(df),
        radius=25,
        colorscale=[[0, "rgba(0,0,0,0)"], [0.5, "#6c63ff"], [1, "#ff4757"]],
        showscale=False,
    ))
    fig.update_layout(
        mapbox=dict(style="carto-darkmatter", center=dict(lat=clat, lon=clon), zoom=10),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=0),
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)


def _terrain_3d(df: pd.DataFrame, clat: float, clon: float):
    color_map = {"Normal": "#2ed573", "Jamming": "#ff4757", "Drone": "#ffa502"}
    fig = go.Figure()

    for label, color in color_map.items():
        sub = df[df["label"] == label]
        if sub.empty:
            continue
        z = sub.get("confidence", pd.Series([0.5] * len(sub)))
        fig.add_trace(go.Scatter3d(
            x=sub["lon"], y=sub["lat"], z=z,
            mode="markers",
            marker=dict(size=6, color=color, opacity=0.75),
            name=label,
        ))

    fig.update_layout(
        scene=dict(
            xaxis_title="Longitude", yaxis_title="Latitude", zaxis_title="Confidence",
            bgcolor="rgba(10,14,26,1)",
            xaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1e2535"),
            yaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1e2535"),
            zaxis=dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="#1e2535"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=0),
        height=500,
        legend=dict(bgcolor="rgba(20,20,40,0.8)", font=dict(color="white")),
    )
    st.plotly_chart(fig, use_container_width=True)
