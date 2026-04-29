"""
api/websocket.py
----------------
WebSocket endpoint for real-time spectrum monitoring.
Streams prediction results as JSON events every N seconds.
"""

import asyncio
import json
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.logger import get_logger

logger = get_logger("api.websocket")
ws_router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WebSocket connected. Total connections: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all active connections."""
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)


manager = ConnectionManager()


@ws_router.websocket("/ws/realtime")
async def realtime_stream(websocket: WebSocket):
    """
    WebSocket endpoint that streams live spectrum predictions.

    Clients connect and receive JSON packets:
    {
      "type": "prediction",
      "class": "Normal",
      "confidence": 0.97,
      "timestamp": "...",
      "spectrogram_b64": "..."
    }

    Send "ping" to get a pong. Send "stop" to close.
    """
    await manager.connect(websocket)
    logger.info("Real-time WebSocket session started")

    try:
        # Start background simulation task
        sim_task = asyncio.create_task(_simulate_and_send(websocket))

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if data == "stop":
                    sim_task.cancel()
                    break
                elif data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass  # No client message, continue streaming

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


async def _simulate_and_send(websocket: WebSocket, interval: float = 3.0):
    """Background task: generate synthetic signal, predict, broadcast result."""
    import random
    import base64
    import io
    from datetime import datetime
    from signal_processing.signal_generator import generate_signal
    from signal_processing.spectrogram import generate_spectrogram
    from PIL import Image

    labels = ["Normal", "Normal", "Normal", "Jamming", "Drone"]

    while True:
        try:
            label = random.choice(labels)
            samples = generate_signal(label.lower(), snr_db=random.uniform(15, 30))
            spec = generate_spectrogram(samples)  # (224, 224, 3)

            # Encode spectrogram
            img = Image.fromarray((spec * 255).astype(np.uint8))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            # Fake confidence for demo (real model used in /predict endpoint)
            confidence = round(random.uniform(0.80, 0.99), 4)

            payload = {
                "type": "prediction",
                "class": label,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "spectrogram_b64": b64,
                "frequency": round(random.uniform(433, 915), 2),
                "snr": round(random.uniform(10, 35), 1),
            }

            await websocket.send_json(payload)
            await asyncio.sleep(interval)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Stream error: {e}")
            await asyncio.sleep(interval)
