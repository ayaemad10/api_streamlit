"""
api/routes.py
-------------
All REST API endpoints grouped by tag:
  - Auth    : /auth/login, /auth/refresh, /auth/me
  - Predict : /predict  (spectrogram → classification)
  - Signal  : /signal   (raw IQ → spectrogram)
  - History : /history
  - Alerts  : /alerts
  - Agent   : /agent/chat
  - Settings: /settings
"""

import io
import base64
import sqlite3
from datetime import datetime
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, status, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.dependencies import get_current_user, require_admin, require_operator
from security.auth import verify_password, create_token_pair, TokenData, decode_token
from utils.logger import get_logger

logger = get_logger("api.routes")
router = APIRouter()


# ════════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login", tags=["Auth"])
async def login(body: LoginRequest):
    """
    Authenticate user and return JWT access + refresh token pair.
    Default: admin / admin123
    """
    conn = sqlite3.connect("spectrum.db")
    cur = conn.cursor()
    cur.execute("SELECT id, password, role FROM users WHERE username = ?", (body.username,))
    row = cur.fetchone()
    conn.close()

    if not row or not verify_password(body.password, row[1]):
        logger.warning(f"Failed login attempt for username: {body.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_token_pair(body.username, row[2])
    logger.info(f"User '{body.username}' logged in successfully")

    # Update last_login
    conn = sqlite3.connect("spectrum.db")
    conn.execute("UPDATE users SET last_login = ? WHERE username = ?",
                 (datetime.now().isoformat(), body.username))
    conn.commit()
    conn.close()

    return token


@router.post("/auth/refresh", tags=["Auth"])
async def refresh_token(refresh_token: str):
    """Exchange a refresh token for a new access token."""
    token_data = decode_token(refresh_token)
    new_token = create_token_pair(token_data.username, token_data.role)
    return new_token


@router.get("/auth/me", tags=["Auth"])
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Return current authenticated user info."""
    return {"username": current_user.username, "role": current_user.role}


# ════════════════════════════════════════════════════════════════════
#  PREDICT
# ════════════════════════════════════════════════════════════════════

@router.post("/predict", tags=["AI Model"])
async def predict(
    file: UploadFile = File(...),
    frequency: Optional[float] = Form(None),
    source: Optional[str] = Form("API"),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Classify a spectrogram image (PNG/JPG, 224×224).

    Returns:
        { class, confidence, signal_id, inference_time_ms }
    """
    import time
    from PIL import Image
    from ai_model.model_loader import ModelLoader
    from ai_model.predictor import Predictor

    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents)).convert("RGB").resize((224, 224))
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_batch = img_array[np.newaxis, ...]  # (1, 224, 224, 3)

        model = ModelLoader.get_instance()
        predictor = Predictor(model)

        t0 = time.perf_counter()
        result = predictor.predict(img_batch)
        inference_ms = int((time.perf_counter() - t0) * 1000)

        # Persist to database
        conn = sqlite3.connect("spectrum.db")
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO signals
               (timestamp, label, confidence, frequency, source, inference_time_ms, model_version)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), result["class"], result["confidence"],
             frequency, source, inference_ms, "v2.0"),
        )
        conn.commit()
        signal_id = cur.lastrowid
        conn.close()

        # Fire alert if anomaly detected
        if result["class"] != "Normal" and result["confidence"] >= 0.75:
            from alerts.alert_manager import AlertManager
            AlertManager.trigger(result["class"], result["confidence"], signal_id)

        logger.info(f"Prediction: {result['class']} ({result['confidence']:.2%}) by {current_user.username}")
        return {**result, "signal_id": signal_id, "inference_time_ms": inference_ms}

    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/signal", tags=["AI Model"])
async def predict_from_signal(
    signal_type: str = Form("normal"),
    snr_db: float = Form(20.0),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Generate synthetic signal, compute spectrogram, then classify.
    Useful for testing without real SDR hardware.
    """
    import time
    from signal_processing.signal_generator import generate_signal
    from signal_processing.spectrogram import generate_spectrogram
    from ai_model.model_loader import ModelLoader
    from ai_model.predictor import Predictor

    try:
        samples = generate_signal(signal_type, snr_db=snr_db)
        spec = generate_spectrogram(samples)  # (224, 224, 3)
        img_batch = spec[np.newaxis, ...]

        model = ModelLoader.get_instance()
        predictor = Predictor(model)

        t0 = time.perf_counter()
        result = predictor.predict(img_batch)
        inference_ms = int((time.perf_counter() - t0) * 1000)

        # Encode spectrogram as base64 PNG for dashboard display
        from PIL import Image
        img_uint8 = (spec * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_uint8)
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        spec_b64 = base64.b64encode(buf.getvalue()).decode()

        conn = sqlite3.connect("spectrum.db")
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO signals (timestamp, label, confidence, snr, source, inference_time_ms, model_version)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), result["class"], result["confidence"],
             snr_db, "Simulator", inference_ms, "v2.0"),
        )
        conn.commit()
        signal_id = cur.lastrowid
        conn.close()

        if result["class"] != "Normal" and result["confidence"] >= 0.75:
            from alerts.alert_manager import AlertManager
            AlertManager.trigger(result["class"], result["confidence"], signal_id)

        return {
            **result,
            "signal_id": signal_id,
            "inference_time_ms": inference_ms,
            "spectrogram_b64": spec_b64,
        }
    except Exception as e:
        logger.error(f"Signal predict error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════
#  SIGNAL → SPECTROGRAM
# ════════════════════════════════════════════════════════════════════

@router.post("/signal", tags=["Signal Processing"])
async def signal_to_spectrogram(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Accept raw IQ binary file and return a base64-encoded spectrogram PNG.
    """
    from signal_processing.spectrogram import generate_spectrogram
    from PIL import Image

    try:
        raw = await file.read()
        samples = np.frombuffer(raw, dtype=np.complex64)

        spec = generate_spectrogram(samples)
        img_uint8 = (spec * 255).astype(np.uint8)
        pil_img = Image.fromarray(img_uint8)

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        return {"spectrogram_b64": b64, "shape": list(spec.shape)}
    except Exception as e:
        logger.error(f"Signal processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════
#  HISTORY
# ════════════════════════════════════════════════════════════════════

@router.get("/history", tags=["Data"])
async def get_history(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    label: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_user),
):
    """Return paginated signal history, optionally filtered by label."""
    conn = sqlite3.connect("spectrum.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if label:
        cur.execute(
            "SELECT * FROM signals WHERE label = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (label, limit, offset),
        )
    else:
        cur.execute(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    rows = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) FROM signals" + (" WHERE label = ?" if label else ""),
                (label,) if label else ())
    total = cur.fetchone()[0]
    conn.close()

    return {"signals": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/history/stats", tags=["Data"])
async def get_stats(current_user: TokenData = Depends(get_current_user)):
    """Aggregate statistics: counts by label, avg confidence, recent trend."""
    conn = sqlite3.connect("spectrum.db")
    cur = conn.cursor()

    cur.execute("SELECT label, COUNT(*) as count, AVG(confidence) as avg_conf FROM signals GROUP BY label")
    label_stats = [{"label": r[0], "count": r[1], "avg_confidence": round(r[2] or 0, 4)} for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) FROM signals")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT strftime('%Y-%m-%d %H:00', timestamp) as hour, label, COUNT(*) as count
        FROM signals
        WHERE timestamp >= datetime('now', '-24 hours')
        GROUP BY hour, label
        ORDER BY hour
    """)
    hourly = [{"hour": r[0], "label": r[1], "count": r[2]} for r in cur.fetchall()]

    conn.close()
    return {"total": total, "by_label": label_stats, "hourly_trend": hourly}


# ════════════════════════════════════════════════════════════════════
#  ALERTS
# ════════════════════════════════════════════════════════════════════

@router.get("/alerts", tags=["Alerts"])
async def get_alerts(
    limit: int = Query(50, ge=1, le=500),
    current_user: TokenData = Depends(get_current_user),
):
    """Return recent alert log."""
    conn = sqlite3.connect("spectrum.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT a.*, s.label, s.confidence
        FROM alerts a
        JOIN signals s ON a.signal_id = s.id
        ORDER BY a.timestamp DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"alerts": rows}


# ════════════════════════════════════════════════════════════════════
#  AI AGENT CHAT
# ════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@router.post("/agent/chat", tags=["AI Agent"])
async def agent_chat(
    body: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Send a message to the AI Agent (Ollama + RAG)."""
    from ai_agent.agent import SpectrumAgent
    try:
        agent = SpectrumAgent()
        response = await agent.chat(body.message, body.session_id)

        # Persist chat history
        conn = sqlite3.connect("spectrum.db")
        conn.execute(
            "INSERT INTO chat_history (session_id, user_query, agent_response, timestamp) VALUES (?, ?, ?, ?)",
            (body.session_id, body.message, response["answer"], datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

        return response
    except Exception as e:
        logger.error(f"Agent chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/agent/report", tags=["AI Agent"])
async def generate_report(
    current_user: TokenData = Depends(require_operator),
):
    """Generate a full threat analysis report using AI Agent."""
    from ai_agent.report_generator import ReportGenerator
    try:
        gen = ReportGenerator()
        report = await gen.generate()
        return {"report": report, "generated_at": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════
#  SETTINGS
# ════════════════════════════════════════════════════════════════════

@router.get("/settings", tags=["Settings"])
async def get_settings_db(current_user: TokenData = Depends(get_current_user)):
    """Return system settings."""
    conn = sqlite3.connect("spectrum.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT key, value, description FROM settings")
    rows = {r["key"]: {"value": r["value"], "description": r["description"]} for r in cur.fetchall()}
    conn.close()
    return rows


@router.put("/settings/{key}", tags=["Settings"])
async def update_setting(
    key: str,
    value: str,
    current_user: TokenData = Depends(require_admin),
):
    """Update a system setting (Admin only)."""
    conn = sqlite3.connect("spectrum.db")
    conn.execute(
        "UPDATE settings SET value = ?, updated_at = ? WHERE key = ?",
        (value, datetime.now().isoformat(), key),
    )
    conn.commit()
    conn.close()
    logger.info(f"Setting '{key}' updated to '{value}' by {current_user.username}")
    return {"key": key, "value": value, "updated_by": current_user.username}
