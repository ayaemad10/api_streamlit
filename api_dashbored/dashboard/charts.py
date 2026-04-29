"""dashboard/components/charts.py - Reusable Plotly chart components."""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from dashboard.config import COLORS, PLOTLY_TEMPLATE


def signal_distribution_pie(data: list[dict]) -> go.Figure:
    """Donut chart of signal class distribution."""
    labels = [d["label"] for d in data]
    values = [d["count"] for d in data]
    color_map = {"Normal": COLORS["normal"], "Jamming": COLORS["jamming"], "Drone": COLORS["drone"]}
    colors = [color_map.get(l, "#888") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#0a0e1a", width=2)),
        textinfo="label+percent",
        textfont=dict(size=13, color="white"),
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=20, l=20, r=20),
        showlegend=False,
        annotations=[dict(text="Signals", x=0.5, y=0.5, font_size=16, showarrow=False, font_color="white")],
    )
    return fig


def confidence_timeline(df: pd.DataFrame) -> go.Figure:
    """Line chart of confidence scores over time, colored by label."""
    fig = go.Figure()
    color_map = {"Normal": COLORS["normal"], "Jamming": COLORS["jamming"], "Drone": COLORS["drone"]}

    for label in df["label"].unique():
        sub = df[df["label"] == label]
        fig.add_trace(go.Scatter(
            x=sub["timestamp"], y=sub["confidence"],
            mode="lines+markers",
            name=label,
            line=dict(color=color_map.get(label, "#888"), width=2),
            marker=dict(size=5),
        ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Time", gridcolor="#1e2535"),
        yaxis=dict(title="Confidence", range=[0, 1], gridcolor="#1e2535"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white")),
        margin=dict(t=20, b=40, l=50, r=20),
        hovermode="x unified",
    )
    return fig


def hourly_heatmap(hourly_data: list[dict]) -> go.Figure:
    """Heatmap of signal counts by hour and label."""
    if not hourly_data:
        return go.Figure()

    df = pd.DataFrame(hourly_data)
    pivot = df.pivot_table(index="label", columns="hour", values="count", fill_value=0)

    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=list(pivot.columns),
        y=list(pivot.index),
        colorscale=[[0, "#0a0e1a"], [0.5, "#6c63ff"], [1, "#ff4757"]],
        showscale=True,
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=40),
        xaxis=dict(title="Hour"),
        yaxis=dict(title="Signal Type"),
    )
    return fig


def gauge_chart(value: float, title: str, max_val: float = 1.0) -> go.Figure:
    """Gauge/speedometer chart for a single metric."""
    pct = value / max_val

    if pct < 0.5:
        color = COLORS["normal"]
    elif pct < 0.75:
        color = COLORS["drone"]
    else:
        color = COLORS["jamming"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(suffix="%" if max_val == 1 else "", font=dict(color="white", size=24)),
        title=dict(text=title, font=dict(color="#94a3b8", size=14)),
        gauge=dict(
            axis=dict(range=[0, max_val], tickcolor="#94a3b8"),
            bar=dict(color=color),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            steps=[
                dict(range=[0, max_val * 0.5], color="#1e2535"),
                dict(range=[max_val * 0.5, max_val * 0.75], color="#1e2535"),
                dict(range=[max_val * 0.75, max_val], color="#1e2535"),
            ],
        ),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, b=10, l=20, r=20),
        height=200,
    )
    return fig


def bar_chart_labels(data: list[dict]) -> go.Figure:
    """Horizontal bar chart of signal counts by label."""
    labels = [d["label"] for d in data]
    counts = [d["count"] for d in data]
    confs  = [round(d["avg_confidence"] * 100, 1) for d in data]
    color_map = {"Normal": COLORS["normal"], "Jamming": COLORS["jamming"], "Drone": COLORS["drone"]}
    colors = [color_map.get(l, "#888") for l in labels]

    fig = go.Figure(go.Bar(
        x=counts, y=labels, orientation="h",
        marker=dict(color=colors, opacity=0.85),
        text=[f"{c} signals ({cf}% avg conf)" for c, cf in zip(counts, confs)],
        textposition="outside",
        textfont=dict(color="white"),
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#1e2535"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        margin=dict(t=10, b=20, l=20, r=100),
        showlegend=False,
    )
    return fig
