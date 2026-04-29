"""
mock_server.py
--------------
Lightweight mock of the Spectrum Anomaly Detection API.
No TensorFlow or model file required.
Runs on port 8000 and serves realistic fake data.
Replace with the real main.py when the model is ready.
"""

import random
import time
import math
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="SpectrumGuard Mock API", version="v1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Seeded fake database ──────────────────────────────────────────
random.seed(42)

LABELS    = ["Normal", "Jamming", "Drone"]
WEIGHTS   = [0.70,      0.20,      0.10]
SOURCES   = ["SDR-01", "SDR-02", "SDR-03", "MOBILE-A", "FIXED-B"]
LOCATIONS = [
    "Sector 7, Cairo", "Heliopolis, Cairo", "Maadi, Cairo",
    "Zamalek, Cairo",  "Nasr City, Cairo",  "Giza Station",
    "Alexandria Port", "Demo Station",
]
ALERT_TYPES = ["email", "whatsapp", "sound"]


def _make_signals(n: int = 120) -> list[dict]:
    signals = []
    base_time = datetime.now() - timedelta(hours=6)
    for i in range(1, n + 1):
        label = random.choices(LABELS, WEIGHTS)[0]
        conf  = round(random.uniform(0.72, 0.99), 4)
        signals.append({
            "id":               i,
            "label":            label,
            "confidence":       conf,
            "frequency":        round(random.uniform(400, 6000), 2),
            "snr":              round(random.uniform(-5, 30), 2),
            "source":           random.choice(SOURCES),
            "inference_time_ms": random.randint(80, 450),
            "model_version":    "v1.0",
            "timestamp":        (base_time + timedelta(minutes=i * 3)).isoformat(),
        })
    return signals


def _make_alerts(signals: list[dict]) -> list[dict]:
    alerts = []
    aid = 1
    for sig in signals:
        if sig["label"] != "Normal" and sig["confidence"] > 0.78:
            alerts.append({
                "id":         aid,
                "signal_id":  sig["id"],
                "alert_type": random.choice(ALERT_TYPES),
                "status":     random.choice(["sent", "sent", "pending"]),
                "location":   random.choice(LOCATIONS),
                "timestamp":  sig["timestamp"],
            })
            aid += 1
    return alerts


# Generate once at startup
_SIGNALS = _make_signals(120)
_ALERTS  = _make_alerts(_SIGNALS)
_NEXT_ID = len(_SIGNALS) + 1
_NEXT_AID = len(_ALERTS) + 1


# ── Routes ────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "model_version": "v1.0"}


@app.get("/api/v1/statistics")
def statistics():
    counts = {}
    for s in _SIGNALS:
        counts[s["label"]] = counts.get(s["label"], 0) + 1
    return {
        "total_signals":   len(_SIGNALS),
        "label_counts":    counts,
        "alert_count":     len(_ALERTS),
        "alert_threshold": 0.75,
    }


@app.get("/api/v1/predictions")
def predictions(
    label:  Optional[str] = Query(None),
    limit:  int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    data = _SIGNALS
    if label:
        data = [s for s in data if s["label"] == label]
    page = data[offset: offset + limit]
    return {"total": len(data), "page": offset // limit + 1, "limit": limit, "signals": page}


@app.get("/api/v1/alerts")
def alerts():
    return _ALERTS


@app.get("/api/v1/reports/{signal_id}")
def report(signal_id: int):
    sig = next((s for s in _SIGNALS if s["id"] == signal_id), None)
    if not sig:
        from fastapi import HTTPException
        raise HTTPException(404, f"Signal {signal_id} not found")
    alert = next((a for a in _ALERTS if a["signal_id"] == signal_id), None)
    return {
        **sig,
        "alert_triggered": alert is not None,
        "alert_id":        alert["id"] if alert else None,
        "location":        alert["location"] if alert else "No alert",
    }


class PredictRequest(BaseModel):
    features:   list[float]
    frequency:  Optional[float] = None
    snr:        Optional[float] = None
    source:     str = "UI"
    alert_type: str = "email"
    location:   str = "Unknown"


@app.post("/api/v1/predict")
def predict(payload: PredictRequest):
    global _NEXT_ID, _NEXT_AID

    # Deterministic mock: use feature mean to pick class
    mean = sum(payload.features) / len(payload.features) if payload.features else 0.5
    if mean > 0.65:
        label, conf = "Jamming", round(random.uniform(0.85, 0.98), 4)
    elif mean > 0.45:
        label, conf = "Drone",   round(random.uniform(0.78, 0.92), 4)
    else:
        label, conf = "Normal",  round(random.uniform(0.80, 0.97), 4)

    inf_ms    = random.randint(90, 400)
    sig_id    = _NEXT_ID
    _NEXT_ID += 1
    ts        = datetime.now().isoformat()

    new_signal = {
        "id": sig_id, "label": label, "confidence": conf,
        "frequency": payload.frequency, "snr": payload.snr,
        "source": payload.source, "inference_time_ms": inf_ms,
        "model_version": "v1.0", "timestamp": ts,
    }
    _SIGNALS.append(new_signal)

    alert_triggered = label != "Normal" and conf >= 0.75
    alert_id = None
    if alert_triggered:
        alert_id = _NEXT_AID
        _NEXT_AID += 1
        _ALERTS.append({
            "id": alert_id, "signal_id": sig_id,
            "alert_type": payload.alert_type, "status": "sent",
            "location": payload.location, "timestamp": ts,
        })

    return {
        "signal_id":          sig_id,
        "label":              label,
        "confidence":         conf,
        "inference_time_ms":  inf_ms,
        "alert_triggered":    alert_triggered,
        "alert_id":           alert_id,
        "timestamp":          ts,
        "model_version":      "v1.0",
    }


class ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/api/v1/chat")
def chat(payload: ChatRequest):
    msg = payload.message.lower()
    counts = {}
    for s in _SIGNALS:
        counts[s["label"]] = counts.get(s["label"], 0) + 1

    if any(w in msg for w in ["jamming", "jam"]):
        reply = f"⚡ **Jamming signals detected:** {counts.get('Jamming', 0)} total. Highest confidence seen: {max((s['confidence'] for s in _SIGNALS if s['label']=='Jamming'), default=0):.1%}."
    elif any(w in msg for w in ["drone"]):
        reply = f"🚁 **Drone signals:** {counts.get('Drone', 0)} detected. All recorded in the alerts log."
    elif any(w in msg for w in ["alert", "alerts"]):
        reply = f"🚨 **Total alerts triggered:** {len(_ALERTS)}. Most recent: {_ALERTS[-1]['location'] if _ALERTS else 'None'} at {(_ALERTS[-1]['timestamp'] if _ALERTS else 'N/A')[:19]}."
    elif any(w in msg for w in ["stat", "statistic", "summary"]):
        reply = (f"📊 **System Summary:**\n"
                 f"- Total signals: {len(_SIGNALS)}\n"
                 f"- Normal: {counts.get('Normal',0)} | Jamming: {counts.get('Jamming',0)} | Drone: {counts.get('Drone',0)}\n"
                 f"- Alerts triggered: {len(_ALERTS)}\n"
                 f"- Alert threshold: 75%")
    elif any(w in msg for w in ["model", "version"]):
        reply = "🤖 Running **SpectrumGuard v1.0** — a deep learning RF classifier (Keras/TensorFlow). Input: feature vector. Output: Normal / Jamming / Drone + confidence score."
    elif any(w in msg for w in ["threat", "level", "critical"]):
        j = counts.get("Jamming", 0)
        level = "🔴 HIGH" if j > 20 else ("🟡 MEDIUM" if j > 5 else "🟢 LOW")
        reply = f"Current threat level: **{level}** — {j} jamming events recorded."
    elif any(w in msg for w in ["confidence", "score"]):
        avg = sum(s["confidence"] for s in _SIGNALS) / len(_SIGNALS) if _SIGNALS else 0
        reply = f"🎯 Average model confidence: **{avg:.1%}** across {len(_SIGNALS)} signals."
    elif any(w in msg for w in ["location", "where", "map"]):
        from collections import Counter
        locs = Counter(a["location"] for a in _ALERTS)
        top  = locs.most_common(3)
        reply = "📍 **Top alert locations:**\n" + "\n".join(f"- {l}: {c} alerts" for l, c in top)
    else:
        reply = (f"👋 I'm **SpectrumAgent**. I can tell you about:\n"
                 f"- Signal statistics & threat levels\n"
                 f"- Alert locations & counts\n"
                 f"- Model confidence & version\n"
                 f"- Jamming & drone detections\n\n"
                 f"Currently monitoring **{len(_SIGNALS)} signals** with **{len(_ALERTS)} alerts** on record.")

    return {"response": reply}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
